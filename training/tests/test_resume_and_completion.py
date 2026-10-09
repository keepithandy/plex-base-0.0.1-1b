"""P1-19 checks for exact resume state and bounded BPE completion."""

import random
import json
import os
import copy
import struct
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path, PureWindowsPath
from types import SimpleNamespace
from unittest.mock import patch

import torch

from plex_training.checkpoint import read_checkpoint, restore_optimizer, restore_random_states
from plex_training.config import tiny_test_config
from plex_training.data import TokenCorpus
from plex_training.pilot import resume_pilot
from plex_training.runner import (
    SyntheticTokenSource, TrainingNumericsError, run_training,
    _require_metrics_run_identity, _require_unambiguous_windows_destination, _write_event,
)
from plex_training.tokenizer import CODEC


class ResumeAndCompletionTests(unittest.TestCase):
    @unittest.skipUnless(torch.cuda.is_available(), "CUDA placement check requires a local GPU")
    def test_cuda_optimizer_restore_keeps_adamw_step_counters_on_cpu(self) -> None:
        model = torch.nn.Linear(2, 1).cuda()
        original = torch.optim.AdamW(model.parameters(), lr=0.0003)
        model(torch.ones(1, 2, device="cuda")).sum().backward()
        original.step()
        continued_model = torch.nn.Linear(2, 1).cuda()
        continued_model.load_state_dict(model.state_dict())
        state = copy.deepcopy(original.state_dict())
        for values in state["state"].values():
            values["step"] = values["step"].cuda()  # Emulate checkpoint map_location=cuda.
        restored = torch.optim.AdamW(continued_model.parameters())
        restore_optimizer(restored, {"optimizerStateDict": state})
        for values in restored.state.values():
            self.assertEqual(values["step"].device.type, "cpu")
            self.assertEqual(float(values["step"]), 1.0)
            self.assertEqual(values["exp_avg"].device.type, "cuda")
            self.assertEqual(values["exp_avg_sq"].device.type, "cuda")
        original.zero_grad()
        model(torch.ones(1, 2, device="cuda")).sum().backward()
        original.step()
        restored.zero_grad()
        continued_model(torch.ones(1, 2, device="cuda")).sum().backward()
        restored.step()
        for values in restored.state.values():
            self.assertEqual(float(values["step"]), 2.0)
        for expected, actual in zip(model.parameters(), continued_model.parameters()):
            self.assertTrue(torch.equal(expected, actual))

    def setUp(self) -> None:
        self.previous_threads = torch.get_num_threads()
        torch.set_num_threads(1)

    def tearDown(self) -> None:
        torch.set_num_threads(self.previous_threads)

    @staticmethod
    def _corpora(root: Path) -> tuple[Path, Path]:
        train = root / "train.tokens.u16le"
        validation = root / "validation.tokens.u16le"
        train_ids = [4 + (index % 32) for index in range(256)]
        validation_ids = [4 + ((index * 7) % 32) for index in range(128)]
        train.write_bytes(struct.pack(f"<{len(train_ids)}H", *train_ids))
        validation.write_bytes(struct.pack(f"<{len(validation_ids)}H", *validation_ids))
        return train, validation

    @staticmethod
    def _identities() -> tuple[dict, dict]:
        return (
            {"codec": CODEC, "actualVocabularySize": 128, "tokenizerSha256": "fixture-tokenizer"},
            {"trainTokensSha256": "fixture-train", "validationTokensSha256": "fixture-validation"},
        )

    def _train(
        self,
        root: Path,
        train_path: Path,
        validation_path: Path,
        name: str,
        *,
        steps: int,
        resume_from: Path | None = None,
        micro_batch: int = 1,
        accumulation_steps: int = 2,
    ) -> tuple[dict, Path]:
        tokenizer_record, dataset_record = self._identities()
        output = root / name / "model.pt"
        with TokenCorpus(train_path) as train, TokenCorpus(validation_path) as validation:
            result = run_training(
                train_source=train,
                validation=validation,
                device_name="cpu",
                minutes=0.1,
                step_limit=steps,
                output_checkpoint=output,
                metrics_path=root / name / "metrics.jsonl",
                artifact_root=root,
                seed=42,
                micro_batch=micro_batch,
                accumulation_steps=accumulation_steps,
                checkpoint_interval_minutes=5,
                resume_from=resume_from,
                config=replace(tiny_test_config(), dropout=0.1),
                allow_tiny_config=True,
                codec=CODEC,
                tokenizer_record=tokenizer_record,
                dataset_record=dataset_record,
                loss_vocabulary_size=128,
                validation_maximum_batches=2,
            )
        return result, output

    def _assert_same_state(self, expected: object, actual: object) -> None:
        if isinstance(expected, torch.Tensor):
            self.assertIsInstance(actual, torch.Tensor)
            self.assertTrue(torch.equal(expected, actual))
        elif isinstance(expected, dict):
            self.assertIsInstance(actual, dict)
            self.assertEqual(expected.keys(), actual.keys())
            for key in expected:
                with self.subTest(key=key):
                    self._assert_same_state(expected[key], actual[key])
        elif isinstance(expected, (list, tuple)):
            self.assertIsInstance(actual, type(expected))
            self.assertEqual(len(expected), len(actual))
            for first, second in zip(expected, actual):
                self._assert_same_state(first, second)
        else:
            self.assertEqual(expected, actual)

    def test_bpe_resume_matches_uninterrupted_training_exactly_on_cpu(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            train, validation = self._corpora(root)
            full_result, full_path = self._train(root, train, validation, "full", steps=2)
            first_result, first_path = self._train(root, train, validation, "split-first", steps=1)
            resumed_result, resumed_path = self._train(
                root, train, validation, "split-second", steps=1, resume_from=first_path
            )
            self.assertEqual(full_result["step"], 2)
            self.assertEqual(first_result["step"], 1)
            self.assertEqual(resumed_result["step"], 2)
            self.assertEqual(resumed_result["stepsThisRun"], 1)
            _, uninterrupted = read_checkpoint(full_path, torch.device("cpu"))
            _, resumed = read_checkpoint(resumed_path, torch.device("cpu"))
            for key in (
                "modelStateDict", "optimizerStateDict", "samplingRngState",
                "torchCpuRngState", "trainingSettings", "scheduleState",
                "tokensProcessedTotal", "step",
            ):
                self.assertIn(key, uninterrupted)
                self.assertIn(key, resumed)
                with self.subTest(state=key):
                    self._assert_same_state(uninterrupted[key], resumed[key])
            self.assertEqual(resumed["tokenizerRecord"], uninterrupted["tokenizerRecord"])
            self.assertEqual(resumed["datasetRecord"], uninterrupted["datasetRecord"])
            _, first_payload = read_checkpoint(first_path, torch.device("cpu"))
            self.assertEqual(resumed["runId"], first_payload["runId"])
            self.assertEqual(resumed_result["runId"], first_payload["runId"])

    def test_bpe_resume_rejects_changed_batch_or_accumulation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            train, validation = self._corpora(root)
            _, first_path = self._train(root, train, validation, "first", steps=1)
            for name, micro_batch, accumulation_steps in (
                ("changed-batch", 2, 2),
                ("changed-accumulation", 1, 3),
            ):
                with self.subTest(name=name):
                    with self.assertRaises(ValueError):
                        self._train(
                            root, train, validation, name, steps=1,
                            resume_from=first_path, micro_batch=micro_batch,
                            accumulation_steps=accumulation_steps,
                        )
                    self.assertFalse((root / name / "model.pt").exists())

    def test_fresh_run_rejects_identical_checkpoint_and_metrics_before_model_work(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            shared = root / "shared-output"
            with patch("plex_training.runner.PlexLanguageModel") as model_mock, patch(
                "plex_training.runner.select_device"
            ) as device_mock:
                with self.assertRaisesRegex(
                    ValueError,
                    "Checkpoint and metrics destinations must be different files",
                ):
                    run_training(
                        train_source=SyntheticTokenSource(token_count=32),
                        validation=None,
                        device_name="cpu",
                        minutes=0.1,
                        step_limit=1,
                        output_checkpoint=shared,
                        metrics_path=shared,
                        artifact_root=root,
                        seed=3,
                        micro_batch=1,
                        accumulation_steps=1,
                        config=tiny_test_config(),
                        allow_tiny_config=True,
                    )
            model_mock.assert_not_called()
            device_mock.assert_not_called()
            self.assertFalse(shared.exists())

    def test_resume_rejects_hardlinked_checkpoint_and_metrics_before_checkpoint_io(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            resume_from = root / "resume.pt"
            resume_from.write_bytes(b"resume-placeholder")
            output = root / "owned-output"
            metrics = root / "metrics-alias"
            output.write_bytes(b"existing-artifact")
            metrics.hardlink_to(output)
            self.assertNotEqual(output, metrics)
            self.assertTrue(output.samefile(metrics))
            with patch("plex_training.runner.read_checkpoint") as read_checkpoint_mock, patch(
                "plex_training.runner.select_device"
            ) as device_mock:
                with self.assertRaisesRegex(
                    ValueError,
                    "Checkpoint and metrics destinations must be different files",
                ):
                    run_training(
                        train_source=SyntheticTokenSource(token_count=32),
                        validation=None,
                        device_name="cpu",
                        minutes=0.1,
                        step_limit=1,
                        output_checkpoint=output,
                        metrics_path=metrics,
                        artifact_root=root,
                        seed=3,
                        micro_batch=1,
                        accumulation_steps=1,
                        resume_from=resume_from,
                        config=tiny_test_config(),
                        allow_tiny_config=True,
                    )
            read_checkpoint_mock.assert_not_called()
            device_mock.assert_not_called()
            self.assertEqual(output.read_bytes(), b"existing-artifact")
            self.assertEqual(metrics.read_bytes(), b"existing-artifact")

    def test_resume_rejects_different_existing_checkpoint_destination_before_io(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            resume_from = root / "checkpoint-a.pt"
            output = root / "checkpoint-b.pt"
            metrics = root / "metrics.jsonl"
            resume_from.write_bytes(b"resume-a")
            output.write_bytes(b"preserve-b")
            with patch("plex_training.runner.read_checkpoint") as read_checkpoint_mock:
                with self.assertRaisesRegex(
                    FileExistsError,
                    "not the checkpoint being resumed",
                ):
                    run_training(
                        train_source=SyntheticTokenSource(token_count=32),
                        validation=None,
                        device_name="cpu",
                        minutes=0.1,
                        step_limit=1,
                        output_checkpoint=output,
                        metrics_path=metrics,
                        artifact_root=root,
                        seed=3,
                        micro_batch=1,
                        accumulation_steps=1,
                        resume_from=resume_from,
                        config=tiny_test_config(),
                        allow_tiny_config=True,
                    )
            read_checkpoint_mock.assert_not_called()
            self.assertEqual(output.read_bytes(), b"preserve-b")
            self.assertFalse(metrics.exists())

    def test_resume_rejects_unrelated_metrics_before_optimizer_work(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            resume_from = root / "checkpoint-a.pt"
            output = root / "fresh-output.pt"
            metrics = root / "metrics.jsonl"
            resume_from.write_bytes(b"checkpoint-placeholder")
            original_metrics = (
                '{"event":"run_started","runId":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}\n'
            )
            metrics.write_text(original_metrics, encoding="utf-8")
            fake_model = SimpleNamespace(config=tiny_test_config())
            payload = {"runId": "a" * 32}
            with patch(
                "plex_training.runner.select_device",
                return_value=torch.device("cpu"),
            ), patch(
                "plex_training.runner.read_checkpoint",
                return_value=(fake_model, payload),
            ) as read_checkpoint_mock, patch(
                "plex_training.runner.torch.optim.AdamW",
            ) as optimizer_mock:
                with self.assertRaisesRegex(
                    FileExistsError,
                    "different or unidentifiable run",
                ):
                    run_training(
                        train_source=SyntheticTokenSource(token_count=32),
                        validation=None,
                        device_name="cpu",
                        minutes=0.1,
                        step_limit=1,
                        output_checkpoint=output,
                        metrics_path=metrics,
                        artifact_root=root,
                        seed=3,
                        micro_batch=1,
                        accumulation_steps=1,
                        resume_from=resume_from,
                        config=tiny_test_config(),
                        allow_tiny_config=True,
                    )
            read_checkpoint_mock.assert_called_once()
            optimizer_mock.assert_not_called()
            self.assertEqual(metrics.read_text(encoding="utf-8"), original_metrics)
            self.assertFalse(output.exists())

    def test_nonfinite_training_failure_records_event_without_replacing_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            checkpoint = root / "model.pt"
            checkpoint.write_bytes(b"last-good-checkpoint")
            metrics = root / "metrics.jsonl"
            run_id = "a" * 32

            class FakeModel(torch.nn.Module):
                def __init__(self) -> None:
                    super().__init__()
                    self.config = tiny_test_config()
                    self.weight = torch.nn.Parameter(torch.tensor(1.0))

            fake_model = FakeModel()
            payload = {
                "runId": run_id,
                "stageTransitionRecord": None,
                "codec": "byte-v1",
                "step": 4,
                "initializationRecord": None,
            }
            failure = TrainingNumericsError(
                "nonfinite-gradient-norm",
                "Training gradient norm is nonfinite; refusing optimizer update",
            )
            with patch(
                "plex_training.runner.select_device",
                return_value=torch.device("cpu"),
            ), patch(
                "plex_training.runner.read_checkpoint",
                return_value=(fake_model, payload),
            ), patch(
                "plex_training.runner.restore_optimizer",
            ), patch(
                "plex_training.runner.restore_random_states",
            ), patch(
                "plex_training.runner._training_step",
                side_effect=failure,
            ), patch(
                "plex_training.runner.save_checkpoint",
            ) as save_checkpoint_mock:
                with self.assertRaisesRegex(
                    TrainingNumericsError,
                    "gradient norm is nonfinite",
                ):
                    run_training(
                        train_source=SyntheticTokenSource(token_count=32),
                        validation=None,
                        device_name="cpu",
                        minutes=0.1,
                        step_limit=1,
                        output_checkpoint=checkpoint,
                        metrics_path=metrics,
                        artifact_root=root,
                        seed=3,
                        micro_batch=1,
                        accumulation_steps=1,
                        resume_from=checkpoint,
                        config=tiny_test_config(),
                        allow_tiny_config=True,
                    )

            save_checkpoint_mock.assert_not_called()
            self.assertEqual(checkpoint.read_bytes(), b"last-good-checkpoint")
            events = [
                json.loads(line)
                for line in metrics.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual([event["event"] for event in events], ["run_started", "run_failed"])
            self.assertEqual({event["runId"] for event in events}, {run_id})
            self.assertEqual(events[-1]["reason"], "nonfinite-gradient-norm")
            self.assertEqual(events[-1]["step"], 4)
            self.assertEqual(events[-1]["stepsThisRun"], 0)

    def test_bpe_resume_rejects_changed_schedule_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            train, validation = self._corpora(root)
            _, first_path = self._train(root, train, validation, "first", steps=1)
            payload = torch.load(first_path, map_location="cpu", weights_only=True)
            payload["scheduleState"]["step"] += 1
            changed = root / "changed.pt"
            torch.save(payload, changed)
            with self.assertRaisesRegex(ValueError, "schedule"):
                self._train(root, train, validation, "rejected", steps=1,
                            resume_from=changed)
            self.assertFalse((root / "rejected" / "model.pt").exists())

    def test_resume_refuses_existing_output_before_reading_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "already-here"
            output.mkdir()
            marker = output / "marker.txt"
            marker.write_text("preserve", encoding="utf-8")
            with self.assertRaisesRegex(FileExistsError, "already exists"):
                resume_pilot(
                    bundle_dir=root / "missing-bundle",
                    checkpoint_path=root / "missing.pt",
                    output_dir=output,
                    artifact_root=root,
                    minutes=1,
                    steps=1,
                )
            self.assertEqual(marker.read_text(encoding="utf-8"), "preserve")

    def test_generation_masks_controls_and_unused_vocab_then_stops_on_eos(self) -> None:
        from plex_training.completion import _generate_token_ids

        class FakeModel:
            config = SimpleNamespace(context_length=8, vocab_size=12)

            def __init__(self) -> None:
                self.calls = 0

            def eval(self) -> "FakeModel":
                return self

            def __call__(self, visible: torch.Tensor) -> tuple[torch.Tensor, None]:
                scores = torch.full((1, visible.shape[1], 12), -20.0)
                scores[0, -1, 0:3] = 100.0  # PAD, UNK, BOS
                scores[0, -1, 9] = 200.0  # Model capacity beyond learned vocab
                scores[0, -1, 5] = 10.0
                if self.calls == 1:
                    scores[0, -1, 3] = 20.0  # EOS on the second step
                self.calls += 1
                return scores, None

        def complete() -> tuple[list[int], bool, int]:
            model = FakeModel()
            generated, stopped = _generate_token_ids(
                model, [4], actual_vocab=8, max_new_tokens=5,
                temperature=0.0, seed=7, device=torch.device("cpu"),
            )
            return generated, stopped, model.calls

        first = complete()
        second = complete()
        self.assertEqual(first, second)
        generated, stopped, calls = first
        self.assertTrue(stopped)
        self.assertEqual(calls, 2)
        self.assertIn(5, generated)
        self.assertFalse({0, 1, 2, 9} & set(generated))

    def test_temperature_sampling_repeats_with_the_same_seed(self) -> None:
        from plex_training.completion import _generate_token_ids

        class FakeModel:
            config = SimpleNamespace(context_length=8, vocab_size=8)

            def eval(self) -> "FakeModel":
                return self

            def __call__(self, visible: torch.Tensor) -> tuple[torch.Tensor, None]:
                scores = torch.full((1, visible.shape[1], 8), -100.0)
                scores[0, -1, 4:6] = 0.0
                return scores, None

        first = _generate_token_ids(
            FakeModel(), [4], actual_vocab=8, max_new_tokens=12,
            temperature=1.0, seed=19, device=torch.device("cpu"),
        )
        second = _generate_token_ids(
            FakeModel(), [4], actual_vocab=8, max_new_tokens=12,
            temperature=1.0, seed=19, device=torch.device("cpu"),
        )
        self.assertEqual(first, second)
        self.assertEqual(len(first[0]), 12)
        self.assertFalse(first[1])
        self.assertLessEqual(set(first[0]), {4, 5})

    @unittest.skipUnless(torch.cuda.is_available(), "CUDA is unavailable")
    def test_cuda_rng_restores_after_loading_checkpoint_on_cuda(self) -> None:
        original_cpu = torch.get_rng_state()
        original_cuda = torch.cuda.get_rng_state_all()
        sampling = random.Random(42)
        try:
            with tempfile.TemporaryDirectory() as temporary:
                path = Path(temporary) / "rng.pt"
                expected_cuda = torch.cuda.get_rng_state_all()
                torch.save({
                    "samplingRngState": sampling.getstate(),
                    "torchCpuRngState": torch.get_rng_state(),
                    "torchCudaRngStates": expected_cuda,
                }, path)
                loaded = torch.load(path, map_location="cuda", weights_only=True)
                torch.cuda.manual_seed_all(7)
                restore_random_states(loaded, random.Random(), torch.device("cuda"))
                actual_cuda = torch.cuda.get_rng_state_all()
                self.assertEqual(len(expected_cuda), len(actual_cuda))
                for expected, actual in zip(expected_cuda, actual_cuda):
                    self.assertTrue(torch.equal(expected, actual))
        finally:
            torch.set_rng_state(original_cpu)
            torch.cuda.set_rng_state_all(original_cuda)


class ArtifactDestinationRegressionTests(unittest.TestCase):
    def test_unterminated_owned_metrics_rejected_before_optimizer_work(self):
        for suffix in (b"", b" ", b"\n "):
            with self.subTest(suffix=suffix), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                metrics = root / "metrics.jsonl"
                original = json.dumps({"runId": "a" * 32, "event": "run_started"}).encode() + suffix
                metrics.write_bytes(original)
                model = SimpleNamespace(config=tiny_test_config())
                with patch("plex_training.runner.read_checkpoint", return_value=(model, {"runId": "a" * 32})), patch(
                    "plex_training.runner.select_device", return_value=torch.device("cpu")
                ), patch("plex_training.runner.torch.optim.AdamW") as optimizer:
                    with self.assertRaisesRegex(FileExistsError, "end with a newline"):
                        run_training(
                            train_source=SyntheticTokenSource(token_count=32), validation=None,
                            device_name="cpu", minutes=0.1, step_limit=1,
                            output_checkpoint=root / "new.pt", metrics_path=metrics,
                            artifact_root=root, resume_from=root / "source.pt",
                            config=tiny_test_config(), allow_tiny_config=True,
                        )
                optimizer.assert_not_called()
                self.assertEqual(metrics.read_bytes(), original)
                self.assertFalse((root / "new.pt").exists())

    def test_owned_metrics_append_preserves_records_with_supported_line_endings(self):
        for ending in (b"\n", b"\r\n", b"\r"):
            with self.subTest(ending=ending), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                metrics = root / "metrics.jsonl"
                first = {"runId": "a" * 32, "event": "run_started"}
                original = json.dumps(first).encode() + ending
                metrics.write_bytes(original)
                _require_metrics_run_identity(metrics, "a" * 32)
                _write_event(metrics, root, {"event": "run_finished"}, run_id="a" * 32, allow_existing=True)
                self.assertTrue(metrics.read_bytes().startswith(original))
                self.assertEqual(
                    [json.loads(line) for line in metrics.read_text().splitlines()],
                    [first, {"runId": "a" * 32, "event": "run_finished"}],
                )

    def test_windows_destination_spelling_rejects_aliases_and_devices(self):
        bad = [
            "output.", "output ", "dir./output", "dir /output", "output:stream",
            "NUL", "con.txt", "CON .txt", "CONIN$", "CONOUT$", "COM1.log", "LPT9",
            "COM\u00b9", "bad?name", "bad\x01name",
            "C:relative", "\\\\?\\C:\\output", "\\\\.\\NUL",
        ]
        for value in bad:
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "Windows"):
                _require_unambiguous_windows_destination(PureWindowsPath(value))
        for value in ("model.pt", "dir/../model.pt", "C:/runs/model.pt", "//server/share/model.pt"):
            with self.subTest(value=value):
                _require_unambiguous_windows_destination(PureWindowsPath(value))

    @unittest.skipUnless(os.name == "nt", "Win32 aliases require Windows")
    def test_windows_aliases_rejected_before_device_or_checkpoint_work(self):
        for resume in (False, True):
            for spelling in ("output.", "output ", "nested./output", "output:stream"):
                with self.subTest(resume=resume, spelling=spelling), tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    with patch("plex_training.runner.select_device") as device, patch(
                        "plex_training.runner.read_checkpoint"
                    ) as checkpoint:
                        with self.assertRaisesRegex(ValueError, "Windows"):
                            run_training(
                                train_source=SyntheticTokenSource(token_count=32), validation=None,
                                device_name="cpu", minutes=0.1, step_limit=1,
                                output_checkpoint=root / "output", metrics_path=root / spelling,
                                artifact_root=root, resume_from=root / "source.pt" if resume else None,
                                config=tiny_test_config(), allow_tiny_config=True,
                            )
                    device.assert_not_called()
                    checkpoint.assert_not_called()
                    self.assertEqual(list(root.iterdir()), [])

    @unittest.skipUnless(os.name == "nt", "Win32 aliases require Windows")
    def test_resolved_windows_destination_is_validated_too(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            # A link can hide a target spelling that was absent from the input.
            def resolved_destination(path, artifact_root):
                return root / "output." if path == root / "link" else path

            with patch("plex_training.runner.path_within_root", side_effect=resolved_destination), patch(
                "plex_training.runner.select_device"
            ) as device:
                with self.assertRaisesRegex(ValueError, "Windows"):
                    run_training(
                        train_source=SyntheticTokenSource(token_count=32), validation=None,
                        device_name="cpu", minutes=0.1, step_limit=1,
                        output_checkpoint=root / "output", metrics_path=root / "link",
                        artifact_root=root, config=tiny_test_config(), allow_tiny_config=True,
                    )
            device.assert_not_called()
            self.assertEqual(list(root.iterdir()), [])

    def test_checkpoint_staging_path_cannot_be_metrics_destination(self):
        for resume in (False, True):
            with self.subTest(resume=resume), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                with patch("plex_training.runner.select_device") as device, patch(
                    "plex_training.runner.read_checkpoint"
                ) as checkpoint:
                    with self.assertRaisesRegex(ValueError, "including checkpoint staging"):
                        run_training(
                            train_source=SyntheticTokenSource(token_count=32), validation=None,
                            device_name="cpu", minutes=0.1, step_limit=1,
                            output_checkpoint=root / "model.pt", metrics_path=root / "model.pt.tmp",
                            artifact_root=root, resume_from=root / "source.pt" if resume else None,
                            config=tiny_test_config(), allow_tiny_config=True,
                        )
                device.assert_not_called()
                checkpoint.assert_not_called()
                self.assertEqual(list(root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
