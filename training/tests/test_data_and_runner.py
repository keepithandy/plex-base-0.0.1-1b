import json
import random
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import torch

from plex_training.checkpoint import read_checkpoint
from plex_training.cli import build_parser
from plex_training.config import DEFAULT_CONFIG, ModelConfig, tiny_test_config
from plex_training.data import TokenCorpus, resolve_source_files, write_byte_corpus
from plex_training.runner import (
    SyntheticTokenSource,
    TrainingNumericsError,
    _training_step,
    evaluate_checkpoint,
    generate_bytes,
    run_training,
)


class DataAndRunnerTests(unittest.TestCase):
    def test_model_config_dimensions_require_exact_positive_integers(self) -> None:
        dimensions = (
            "vocab_size",
            "context_length",
            "width",
            "layers",
            "heads",
            "feed_forward_width",
        )
        invalid_values = (1.5, True, "2", 0, -1)
        defaults = DEFAULT_CONFIG.to_dict()

        for field in dimensions:
            for value in invalid_values:
                with self.subTest(path="constructor", field=field, value=value):
                    with self.assertRaises(ValueError):
                        ModelConfig(**{**defaults, field: value})

                with self.subTest(path="from_dict", field=field, value=value):
                    with self.assertRaisesRegex(
                        ValueError,
                        "Checkpoint model_config is invalid",
                    ):
                        ModelConfig.from_dict({**defaults, field: value})

    def test_controlled_default_model_size_is_unchanged(self) -> None:
        self.assertEqual(DEFAULT_CONFIG.parameter_count(), 27_566_080)
        self.assertEqual(
            DEFAULT_CONFIG,
            ModelConfig(
                vocab_size=16_384,
                context_length=512,
                width=512,
                layers=6,
                heads=8,
                feed_forward_width=2_048,
                dropout=0.1,
            ),
        )

    def test_packed_corpus_yields_next_token_pairs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "train.txt"
            source.write_bytes(b"abcdefghij")
            packed = root / "train.tokens.u16le"
            info = write_byte_corpus([source], packed, storage_limit=1024)
            self.assertEqual(info["tokenCount"], 11)  # includes the file separator
            self.assertEqual(packed.stat().st_size, info["tokenCount"] * 2)
            with TokenCorpus(packed) as corpus:
                inputs, targets = corpus.sample_batch(random.Random(3), 2, 4)
                self.assertEqual(tuple(inputs.shape), (2, 4))
                self.assertTrue(torch.equal(inputs[:, 1:], targets[:, :-1]))
                self.assertLess(int(inputs.max()), 256)
                self.assertLess(int(targets.max()), 256)

    def test_duplicate_source_files_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.txt"
            source.write_text("tiny corpus", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "more than once"):
                resolve_source_files([str(source), str(source)])

    def test_invalid_utf8_is_rejected_without_leaving_partial_corpus(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "invalid.txt"
            source.write_bytes(b"valid then invalid: \xff")
            packed = root / "invalid.tokens.u16le"
            with self.assertRaises(UnicodeDecodeError):
                write_byte_corpus([source], packed, storage_limit=1024)
            self.assertFalse(packed.exists())
            self.assertFalse(packed.with_name(packed.name + ".tmp").exists())

    def test_training_step_rejects_nonfinite_loss_before_backward(self) -> None:
        class NonfiniteLossModel:
            config = SimpleNamespace(context_length=4)

            def __init__(self) -> None:
                self.weight = torch.nn.Parameter(torch.tensor(1.0))

            def parameters(self):
                return [self.weight]

            def __call__(self, *_args, **_kwargs):
                loss = self.weight * torch.tensor(float("nan"))
                return torch.zeros((1, 4, 256)), loss

        model = NonfiniteLossModel()
        optimizer = Mock()
        with self.assertRaisesRegex(
            TrainingNumericsError,
            "Training loss is nonfinite",
        ) as raised:
            _training_step(
                model,
                optimizer,
                SyntheticTokenSource(token_count=32),
                random.Random(3),
                torch.device("cpu"),
                micro_batch=1,
                accumulation_steps=1,
            )
        self.assertEqual(raised.exception.reason, "nonfinite-loss")
        optimizer.zero_grad.assert_called_once_with(set_to_none=True)
        optimizer.step.assert_not_called()
        self.assertIsNone(model.weight.grad)

    def test_training_step_rejects_nonfinite_gradient_before_optimizer_step(self) -> None:
        class NonfiniteGradientModel:
            config = SimpleNamespace(context_length=4)

            def __init__(self) -> None:
                self.weight = torch.nn.Parameter(torch.tensor(1.0))
                self.weight.register_hook(
                    lambda gradient: torch.full_like(gradient, float("inf"))
                )

            def parameters(self):
                return [self.weight]

            def __call__(self, *_args, **_kwargs):
                loss = self.weight.square()
                return torch.zeros((1, 4, 256)), loss

        model = NonfiniteGradientModel()
        optimizer = Mock()
        with self.assertRaisesRegex(
            TrainingNumericsError,
            "gradient norm is nonfinite",
        ) as raised:
            _training_step(
                model,
                optimizer,
                SyntheticTokenSource(token_count=32),
                random.Random(3),
                torch.device("cpu"),
                micro_batch=1,
                accumulation_steps=1,
            )
        self.assertEqual(raised.exception.reason, "nonfinite-gradient-norm")
        optimizer.zero_grad.assert_called_once_with(set_to_none=True)
        optimizer.step.assert_not_called()
        self.assertIsNotNone(model.weight.grad)
        self.assertFalse(bool(torch.isfinite(model.weight.grad).all()))

    def test_tiny_training_checkpoint_resumes_and_runs_eval_and_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "run" / "model.pt"
            metrics = root / "run" / "metrics.jsonl"
            result = run_training(
                train_source=SyntheticTokenSource(token_count=256),
                validation=None,
                device_name="cpu",
                minutes=0.1,
                step_limit=1,
                output_checkpoint=output,
                metrics_path=metrics,
                artifact_root=root,
                seed=11,
                micro_batch=1,
                accumulation_steps=1,
                config=tiny_test_config(),
                allow_tiny_config=True,
            )
            self.assertEqual(result["stepsThisRun"], 1)
            run_id = result["runId"]
            self.assertEqual(len(run_id), 32)
            model, payload = read_checkpoint(output, torch.device("cpu"))
            self.assertEqual(payload["runId"], run_id)
            self.assertEqual(payload["step"], 1)
            self.assertEqual(model.config, tiny_test_config())

            resumed = run_training(
                train_source=SyntheticTokenSource(token_count=256),
                validation=None,
                device_name="cpu",
                minutes=0.1,
                step_limit=1,
                output_checkpoint=output,
                metrics_path=metrics,
                artifact_root=root,
                seed=11,
                micro_batch=1,
                accumulation_steps=1,
                resume_from=output,
                config=tiny_test_config(),
                allow_tiny_config=True,
            )
            self.assertEqual(resumed["step"], 2)
            self.assertEqual(resumed["runId"], run_id)
            resumed_model, resumed_payload = read_checkpoint(output, torch.device("cpu"))
            self.assertEqual(resumed_payload["runId"], run_id)
            self.assertEqual(resumed_model.config, tiny_test_config())
            self.assertEqual(resumed_payload["modelConfig"]["vocab_size"], 256)

            validation_source = root / "validation.txt"
            validation_text = "abcdefg " * 32
            validation_source.write_text(validation_text, encoding="ascii")
            tokens = root / "validation.tokens.u16le"
            write_byte_corpus([validation_source], tokens, storage_limit=1024)
            with TokenCorpus(tokens) as corpus:
                inputs, _ = corpus.sample_batch(
                    random.Random(5), 1, tiny_test_config().context_length
                )
                self.assertLess(int(inputs.max()), resumed_model.config.vocab_size)
            evaluation = evaluate_checkpoint(output, tokens, device_name="cpu", maximum_batches=2)
            self.assertGreater(evaluation["meanLoss"], 0)
            generated = generate_bytes(
                output, "Plex", device_name="cpu", max_new_tokens=4, seed=5
            )
            self.assertTrue(generated.startswith("Plex"))

            events = [json.loads(line) for line in metrics.read_text(encoding="utf-8").splitlines()]
            self.assertTrue(any(event["event"] == "run_finished" for event in events))
            self.assertTrue(events)
            self.assertEqual({event["runId"] for event in events}, {run_id})

    def test_smoke_has_a_ten_minute_hard_limit(self) -> None:
        args = build_parser().parse_args(["smoke", "--minutes", "10.1"])
        with self.assertRaisesRegex(ValueError, "no more than 10 minutes"):
            from plex_training.cli import _smoke

            _smoke(args)


if __name__ == "__main__":
    unittest.main()
