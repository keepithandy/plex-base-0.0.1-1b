"""Command-line entry point for local Plex model work."""

from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path
from typing import Any

from .config import DEFAULT_CONFIG, tiny_test_config
from .limits import MAX_PILOT_MINUTES, MAX_SMOKE_MINUTES

DEFAULT_ARTIFACT_ROOT = Path(__file__).resolve().parents[2] / "artifacts"


def _add_artifact_root(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=DEFAULT_ARTIFACT_ROOT,
        help="Plex data/checkpoint/log directory (default: training/artifacts; 200 GiB cap)",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="plex-train", description="Local from-scratch Plex training runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    environment = subparsers.add_parser("environment", help="Report Python, PyTorch, CUDA, and memory details")
    environment.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")

    prepare = subparsers.add_parser("prepare", help="Pack separate local UTF-8 files as temporary byte-v1 corpora")
    prepare.add_argument("--train-input", action="append", required=True, metavar="FILE")
    prepare.add_argument("--validation-input", action="append", required=True, metavar="FILE")
    prepare.add_argument("--output-dir", type=Path, default=None)
    prepare.add_argument("--storage-limit-gib", type=float, default=200.0)
    _add_artifact_root(prepare)

    dataset = subparsers.add_parser(
        "dataset-build", help="Filter reviewed local sources and create grouped train/validation JSONL splits"
    )
    dataset.add_argument("--source-manifest", type=Path, required=True)
    dataset.add_argument("--output-dir", type=Path, default=Path("datasets/p1-14"))
    dataset.add_argument("--validation-percent", type=int, default=10)
    dataset.add_argument("--seed", type=int, default=1337)
    dataset.add_argument("--storage-limit-gib", type=float, default=200.0)
    _add_artifact_root(dataset)

    web_dataset = subparsers.add_parser(
        "web-dataset-build",
        help="Build a Plex Web corpus from exactly the file paths accepted by web-source-verify",
    )
    web_dataset.add_argument("--source-manifest", type=Path, required=True)
    web_dataset.add_argument("--output-dir", type=Path, required=True)
    web_dataset.add_argument("--validation-percent", type=int, default=10)
    web_dataset.add_argument("--seed", type=int, default=1337)
    web_dataset.add_argument("--storage-limit-gib", type=float, default=200.0)
    web_dataset.add_argument(
        "--policy",
        type=Path,
        default=None,
        help="Optional Plex Web source-policy JSON",
    )
    _add_artifact_root(web_dataset)

    web_source_verify = subparsers.add_parser(
        "web-source-verify",
        help="Preflight reviewed local HTML/CSS/JavaScript sources against Plex Web policy",
    )
    web_source_verify.add_argument("--source-manifest", type=Path, required=True)
    web_source_verify.add_argument(
        "--policy",
        type=Path,
        default=None,
        help="Optional source-policy JSON; defaults to training/pretraining/source-policy.json",
    )

    web_contamination = subparsers.add_parser(
        "web-contamination-check",
        help="Block Plex Web corpus promotion when protected evaluation content overlaps the corpus",
    )
    web_contamination.add_argument("--dataset-dir", type=Path, required=True)
    web_contamination.add_argument(
        "--protected-config",
        type=Path,
        default=None,
        help="Optional protected-evaluation config; defaults to training/pretraining/protected-eval-paths.json",
    )
    web_contamination.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Optional contamination report path; defaults to DATASET_DIR/contamination-report.json",
    )

    web_materialize = subparsers.add_parser(
        "web-source-materialize",
        help="Fetch pinned reviewed P2-26 GitHub sources and write a local source manifest",
    )
    web_materialize.add_argument(
        "--registry",
        type=Path,
        default=Path("training/pretraining/p2-26-source-candidates.json"),
    )
    web_materialize.add_argument(
        "--policy",
        type=Path,
        default=Path("training/pretraining/source-policy.json"),
    )
    web_materialize.add_argument(
        "--manifest-output",
        type=Path,
        default=Path("training/pretraining/sources.p2-26.local.json"),
    )

    tokenizer = subparsers.add_parser("tokenizer-train", help="Fit Plex byte-level BPE on reviewed training text only")
    tokenizer.add_argument("--dataset-dir", type=Path, required=True)
    tokenizer.add_argument("--output-dir", type=Path, default=Path("tokenizers/p1-15-starter-v1"))
    tokenizer.add_argument("--vocab-size", type=int, default=DEFAULT_CONFIG.vocab_size)
    tokenizer.add_argument("--min-frequency", type=int, default=2)
    tokenizer.add_argument("--storage-limit-gib", type=float, default=200.0)
    _add_artifact_root(tokenizer)

    tokenizer_review = subparsers.add_parser(
        "tokenizer-review",
        help="Fit and compare fresh train-only tokenizer candidates without training model weights",
    )
    tokenizer_review.add_argument("--dataset-dir", type=Path, required=True)
    tokenizer_review.add_argument(
        "--output-dir",
        type=Path,
        default=Path("tokenizer-reviews/p2-27-web-v1"),
    )
    tokenizer_review.add_argument(
        "--vocab-sizes",
        type=int,
        nargs="+",
        default=[4096, 8192, 12288, 16384],
    )
    tokenizer_review.add_argument("--min-frequency", type=int, default=2)
    tokenizer_review.add_argument(
        "--baseline-tokenizer",
        type=Path,
        default=None,
        help="Optional existing Plex tokenizer bundle to measure on the frozen corpus",
    )
    tokenizer_review.add_argument("--storage-limit-gib", type=float, default=200.0)
    _add_artifact_root(tokenizer_review)


    task_repack = subparsers.add_parser(
        "task-finetune-repack",
        help="Retokenize an approved task split with the frozen Plex Web tokenizer without training",
    )
    task_repack.add_argument("--dataset-dir", type=Path, required=True)
    task_repack.add_argument("--tokenizer-dir", type=Path, required=True)
    task_repack.add_argument(
        "--contract",
        type=Path,
        default=Path("training/pretraining/p2-30-task-finetune-contract.json"),
    )
    task_repack.add_argument(
        "--output-dir",
        type=Path,
        default=Path("task-finetune/p2-30-request-v3-16k"),
    )
    task_repack.add_argument("--storage-limit-gib", type=float, default=200.0)
    _add_artifact_root(task_repack)

    task_stage = subparsers.add_parser(
        "task-finetune-stage",
        help="Create a step-zero task stage from verified pretrained Plex weights without training",
    )
    task_stage.add_argument("--base-checkpoint", type=Path, required=True)
    task_stage.add_argument("--bundle-dir", type=Path, required=True)
    task_stage.add_argument(
        "--contract",
        type=Path,
        default=Path("training/pretraining/p2-30-task-finetune-contract.json"),
    )
    task_stage.add_argument(
        "--output-dir",
        type=Path,
        default=Path("task-finetune/p2-30-stage0"),
    )
    task_stage.add_argument("--storage-limit-gib", type=float, default=200.0)
    _add_artifact_root(task_stage)

    task_run = subparsers.add_parser(
        "task-finetune-run",
        help="Run the single owner-authorized bounded P2-30 task fine-tune",
    )
    task_run.add_argument("--checkpoint", type=Path, required=True)
    task_run.add_argument("--bundle-dir", type=Path, required=True)
    task_run.add_argument(
        "--contract",
        type=Path,
        default=Path("training/pretraining/p2-30-first-finetune-contract.json"),
    )
    task_run.add_argument(
        "--preparation-contract",
        type=Path,
        default=Path("training/pretraining/p2-30-task-finetune-contract.json"),
    )
    task_run.add_argument(
        "--output-dir",
        type=Path,
        default=Path("task-finetune/p2-30-first-run"),
    )
    _add_artifact_root(task_run)

    initialize = subparsers.add_parser(
        "initialize", help="Create and record a fresh, randomly initialized Plex checkpoint"
    )
    initialize.add_argument("--tokenizer-dir", type=Path, default=Path("tokenizers/p1-15-starter-v1"))
    initialize.add_argument("--output-dir", type=Path, default=Path("initializations/p1-16-starter-v1"))
    initialize.add_argument("--seed", type=int, default=1337)
    initialize.add_argument("--storage-limit-gib", type=float, default=200.0)
    _add_artifact_root(initialize)

    learning = subparsers.add_parser(
        "learn-check", help="Overfit one short approved training record from the P1-16 checkpoint"
    )
    learning.add_argument("--initialization", type=Path,
                          default=Path("initializations/p1-16-starter-v1/initialization.pt"))
    learning.add_argument("--tokenizer-dir", type=Path, default=Path("tokenizers/p1-15-starter-v1"))
    learning.add_argument("--train-tokens", type=Path,
                          default=Path("tokenizers/p1-15-starter-v1/train.tokens.u16le"))
    learning.add_argument("--train-index", type=Path,
                          default=Path("tokenizers/p1-15-starter-v1/train.index.json"))
    learning.add_argument("--output-dir", type=Path, default=Path("learning/p1-17-tiny-v1"))
    learning.add_argument("--steps", type=int, default=250)
    learning.add_argument("--sample-tokens", type=int, default=16)
    learning.add_argument("--minutes", type=float, default=10.0)
    learning.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    learning.add_argument("--storage-limit-gib", type=float, default=200.0)
    _add_artifact_root(learning)

    pilot = subparsers.add_parser(
        "pilot", help="Train on approved BPE tokens with held-out validation (at most 120 minutes)"
    )
    pilot.add_argument("--bundle-dir", type=Path,
                       default=Path("training/artifacts/tokenizers/p1-15-starter-v1"))
    pilot.add_argument("--initialization", type=Path,
                       default=Path("training/artifacts/initializations/p1-16-starter-v1/initialization.pt"))
    pilot.add_argument("--output-dir", type=Path, default=Path("pilot/p1-18"))
    pilot.add_argument("--minutes", type=float, required=True)
    pilot.add_argument("--steps", type=int, default=None,
                       help="Optional step bound for a short preflight")
    pilot.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    pilot.add_argument("--micro-batch", type=int, default=1)
    pilot.add_argument("--gradient-accumulation", type=int, default=16)
    pilot.add_argument("--checkpoint-every-minutes", type=float, default=5.0)
    pilot.add_argument("--answer-weight", type=int, choices=(1, 4), default=1,
                       help="1 keeps ordinary loss; 4 weights verified answer and EOS targets")
    pilot.add_argument("--dataset-dir", type=Path, default=None,
                       help="Matching built dataset; required with answer weighting or record-start sampling")
    pilot.add_argument("--sampling-policy", choices=("random-window-v1", "record-start-v1", "complete-record-v1"),
                       default="random-window-v1",
                       help="Record sampling comparisons require ordinary loss, at most 100 steps and ten minutes")
    _add_artifact_root(pilot)

    pilot_evaluate = subparsers.add_parser(
        "pilot-evaluate", help="Recheck a BPE pilot checkpoint on the held-out validation split"
    )
    pilot_evaluate.add_argument("--bundle-dir", type=Path,
                                default=Path("training/artifacts/tokenizers/p1-15-starter-v1"))
    pilot_evaluate.add_argument("--checkpoint", type=Path, required=True)
    pilot_evaluate.add_argument("--max-batches", type=int, default=100)
    pilot_evaluate.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")

    pilot_resume = subparsers.add_parser(
        "pilot-resume", help="Check bounded continuation from a saved BPE pilot checkpoint"
    )
    pilot_resume.add_argument("--bundle-dir", type=Path,
                              default=Path("training/artifacts/tokenizers/p1-15-starter-v1"))
    pilot_resume.add_argument("--checkpoint", type=Path, required=True)
    pilot_resume.add_argument("--output-dir", type=Path, default=Path("pilot/p1-19-resume"))
    pilot_resume.add_argument("--minutes", type=float, default=10.0)
    pilot_resume.add_argument("--steps", type=int, default=1)
    pilot_resume.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    pilot_resume.add_argument("--micro-batch", type=int, default=1)
    pilot_resume.add_argument("--gradient-accumulation", type=int, default=16)
    pilot_resume.add_argument("--checkpoint-every-minutes", type=float, default=5.0)
    pilot_resume.add_argument("--dataset-dir", type=Path, default=None,
                              help="Matching built dataset; required for saved complete-record sampling")
    _add_artifact_root(pilot_resume)

    complete = subparsers.add_parser(
        "complete", help="Generate bounded BPE text from saved Plex weights and tokenizer"
    )
    complete.add_argument("--checkpoint", type=Path, required=True)
    complete.add_argument("--bundle-dir", type=Path, default=None,
                          help="Tokenizer bundle; defaults to the checkpoint's tokenizer sidecar")
    complete.add_argument("--prompt", required=True)
    complete.add_argument("--max-new-tokens", type=int, default=64)
    complete.add_argument("--temperature", type=float, default=0.0,
                          help="0 is greedy; positive values use seeded sampling")
    complete.add_argument("--seed", type=int, default=1337)
    complete.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")

    smoke = subparsers.add_parser("smoke", help="Run the synthetic-data smoke test (at most 10 minutes)")
    smoke.add_argument("--minutes", type=float, default=MAX_SMOKE_MINUTES)
    smoke.add_argument("--steps", type=int, default=None, help="Optional quick test bound; does not replace timed smoke")
    smoke.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    smoke.add_argument("--seed", type=int, default=1337)
    smoke.add_argument("--micro-batch", type=int, default=1)
    smoke.add_argument("--gradient-accumulation", type=int, default=16)
    smoke.add_argument("--checkpoint-every-minutes", type=float, default=5.0)
    smoke.add_argument("--output-dir", type=Path, default=None)
    smoke.add_argument("--tiny-test-model", action="store_true", help="Use a tiny config only with --steps for plumbing tests")
    _add_artifact_root(smoke)

    train = subparsers.add_parser("train", help="Train on separate local token corpora (hard cap: two hours)")
    train.add_argument("--train-tokens", type=Path, required=True)
    train.add_argument("--validation-tokens", type=Path, required=True)
    train.add_argument("--checkpoint", type=Path, required=True)
    train.add_argument("--resume", type=Path, default=None)
    train.add_argument("--minutes", type=float, default=10.0)
    train.add_argument("--steps", type=int, default=None, help="Optional additional step bound")
    train.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    train.add_argument("--seed", type=int, default=1337)
    train.add_argument("--micro-batch", type=int, default=1)
    train.add_argument("--gradient-accumulation", type=int, default=16)
    train.add_argument("--checkpoint-every-minutes", type=float, default=5.0)
    train.add_argument("--artifact-root", type=Path, default=DEFAULT_ARTIFACT_ROOT)

    evaluate = subparsers.add_parser("evaluate", help="Measure next-token loss on a held-out token corpus")
    evaluate.add_argument("--checkpoint", type=Path, required=True)
    evaluate.add_argument("--tokens", type=Path, required=True)
    evaluate.add_argument("--max-batches", type=int, default=100)
    evaluate.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")

    generate = subparsers.add_parser("generate", help="Generate byte-v1 text from a Plex checkpoint")
    generate.add_argument("--checkpoint", type=Path, required=True)
    generate.add_argument("--prompt", required=True)
    generate.add_argument("--max-new-tokens", type=int, default=128)
    generate.add_argument("--temperature", type=float, default=0.8)
    generate.add_argument("--seed", type=int, default=1337)
    generate.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")

    task_evaluate = subparsers.add_parser(
        "task-evaluate", help="Score local responses against a versioned HTML/CSS/JavaScript task set"
    )
    task_evaluate.add_argument("--task-set", type=Path, required=True)
    task_evaluate.add_argument("--responses", type=Path, required=True,
                               help="JSONL objects with taskId and generated text")
    task_evaluate.add_argument("--report", type=Path, default=None,
                               help="Optional new JSON report path; existing files are never overwritten")
    task_evaluate.add_argument("--node-timeout-seconds", type=float, default=5.0)
    task_evaluate.add_argument("--response-limit-bytes", type=int, default=65_536)

    task_generate = subparsers.add_parser(
        "task-generate", help="Generate deterministic responses for the development task set"
    )
    task_generate.add_argument("--task-set", type=Path,
                               default=Path("training/phase2/evaluation/p2-01b-dev-v1.json"))
    task_generate.add_argument("--checkpoint", type=Path, required=True)
    task_generate.add_argument("--bundle-dir", type=Path, required=True,
                                help="Tokenizer bundle matching the scratch-initialized checkpoint")
    task_generate.add_argument("--output-dir", type=Path, required=True,
                               help="New directory for responses and run manifest")
    task_generate.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    _add_artifact_root(task_generate)

    return parser


def _json_print(result: Any) -> None:
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))


def _under_artifact_root(path: Path, root: Path) -> Path:
    if not path.is_absolute():
        path = root / path
    canonical_root = root.resolve()
    canonical_path = path.resolve(strict=False)
    try:
        canonical_path.relative_to(canonical_root)
    except ValueError as exc:
        raise ValueError("Training outputs must stay under the configured artifact root") from exc
    return canonical_path


def _prepare(args: argparse.Namespace) -> dict[str, Any]:
    from .artifacts import enforce_storage_limit
    from .data import resolve_source_files, write_byte_corpus, write_dataset_manifest

    root = args.artifact_root.resolve()
    output_dir = _under_artifact_root(args.output_dir or Path("data"), root)
    train_inputs = resolve_source_files(args.train_input)
    validation_inputs = resolve_source_files(args.validation_input)
    if set(train_inputs) & set(validation_inputs):
        raise ValueError("Training and validation inputs must be separate files")
    if not 0 < args.storage_limit_gib <= 200:
        raise ValueError("storage-limit-gib must be greater than 0 and no more than 200")
    limit = int(args.storage_limit_gib * 1024**3)
    output_dir.mkdir(parents=True, exist_ok=True)
    train_path = output_dir / "train.tokens.u16le"
    validation_path = output_dir / "validation.tokens.u16le"
    remaining = limit - _artifact_size(root)
    train_info = write_byte_corpus(train_inputs, train_path, remaining)
    remaining = limit - _artifact_size(root)
    validation_info = write_byte_corpus(validation_inputs, validation_path, remaining)
    manifest_path = write_dataset_manifest(output_dir, train_info, validation_info)
    enforce_storage_limit(root, limit_bytes=limit)
    return {
        "manifest": str(manifest_path.relative_to(root)),
        "codec": "byte-v1",
        "trainTokens": train_info["tokenCount"],
        "validationTokens": validation_info["tokenCount"],
        "artifactBytes": _artifact_size(root),
        "storageLimitBytes": limit,
    }


def _artifact_size(root: Path) -> int:
    if not root.exists():
        return 0
    return sum(
        path.stat().st_size
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink()
    )


def _dataset_build(args: argparse.Namespace) -> dict[str, Any]:
    from .dataset import build_dataset

    root = args.artifact_root.resolve()
    output_dir = _under_artifact_root(args.output_dir, root)
    if not 0 < args.storage_limit_gib <= 200:
        raise ValueError("storage-limit-gib must be greater than 0 and no more than 200")
    limit = int(args.storage_limit_gib * 1024**3)
    remaining = limit - _artifact_size(root)
    result = build_dataset(
        args.source_manifest,
        output_dir,
        validation_percent=args.validation_percent,
        seed=args.seed,
        storage_limit_bytes=remaining,
    )
    return {
        **result,
        "outputDirectory": str(output_dir.relative_to(root)),
        "storageLimitBytes": limit,
    }


def _web_dataset_build(args: argparse.Namespace) -> dict[str, Any]:
    from .web_dataset import build_web_dataset

    root = args.artifact_root.resolve()
    output_dir = _under_artifact_root(args.output_dir, root)
    if not 0 < args.storage_limit_gib <= 200:
        raise ValueError("storage-limit-gib must be greater than 0 and no more than 200")
    limit = int(args.storage_limit_gib * 1024**3)
    remaining = limit - _artifact_size(root)
    result = build_web_dataset(
        args.source_manifest,
        output_dir,
        validation_percent=args.validation_percent,
        seed=args.seed,
        storage_limit_bytes=remaining,
        policy_path=args.policy,
    )
    return {
        **result,
        "outputDirectory": str(output_dir.relative_to(root)),
        "storageLimitBytes": limit,
    }


def _web_source_verify(args: argparse.Namespace) -> dict[str, Any]:
    from .web_sources import verify_web_sources

    return verify_web_sources(args.source_manifest, args.policy)


def _web_contamination_check(args: argparse.Namespace) -> dict[str, Any]:
    from .web_contamination import DEFAULT_PROTECTED_CONFIG, require_clean_contamination

    config = DEFAULT_PROTECTED_CONFIG if args.protected_config is None else args.protected_config
    return require_clean_contamination(
        args.dataset_dir,
        protected_config=config,
        report_path=args.report,
    )


def _web_source_materialize(args: argparse.Namespace) -> dict[str, Any]:
    from .web_materialize import materialize_sources

    return materialize_sources(
        args.registry,
        policy_path=args.policy,
        manifest_output=args.manifest_output,
    )


def _smoke(args: argparse.Namespace) -> dict[str, Any]:
    from .runner import SyntheticTokenSource, default_run_directory, run_training

    if not 0 < args.minutes <= MAX_SMOKE_MINUTES:
        raise ValueError("smoke test duration must be greater than 0 and no more than 10 minutes")
    if args.steps is not None and args.steps <= 0:
        raise ValueError("steps must be positive")
    if args.tiny_test_model and args.steps is None:
        raise ValueError("--tiny-test-model is only allowed with --steps; it is not a hardware-fit test")
    root = args.artifact_root.resolve()
    run_dir = (
        default_run_directory("smoke", root)
        if args.output_dir is None
        else _under_artifact_root(args.output_dir, root)
    )
    if run_dir.exists() and any(run_dir.iterdir()):
        raise FileExistsError("Smoke output directory is not empty; choose a fresh output directory")
    config = tiny_test_config() if args.tiny_test_model else DEFAULT_CONFIG
    result = run_training(
        train_source=SyntheticTokenSource(),
        validation=None,
        device_name=args.device,
        minutes=args.minutes,
        step_limit=args.steps,
        output_checkpoint=run_dir / "smoke-checkpoint.pt",
        metrics_path=run_dir / "metrics.jsonl",
        artifact_root=root,
        seed=args.seed,
        micro_batch=args.micro_batch,
        accumulation_steps=args.gradient_accumulation,
        checkpoint_interval_minutes=args.checkpoint_every_minutes,
        config=config,
        allow_tiny_config=args.tiny_test_model,
    )
    return {**result, "outputDirectory": str(run_dir.relative_to(root))}


def _tokenizer_train(args: argparse.Namespace) -> dict[str, Any]:
    from .tokenizer import train_tokenizer

    root = args.artifact_root.resolve()
    output = _under_artifact_root(args.output_dir, root)
    if not 0 < args.storage_limit_gib <= 200:
        raise ValueError("storage-limit-gib must be greater than 0 and no more than 200")
    limit = int(args.storage_limit_gib * 1024**3)
    result = train_tokenizer(args.dataset_dir, output, vocab_size=args.vocab_size,
                             min_frequency=args.min_frequency,
                             storage_limit_bytes=limit - _artifact_size(root))
    return {**result, "outputDirectory": str(output.relative_to(root)), "storageLimitBytes": limit}


def _tokenizer_review(args: argparse.Namespace) -> dict[str, Any]:
    from .tokenizer_review import review_tokenizers

    root = args.artifact_root.resolve()
    output = _under_artifact_root(args.output_dir, root)
    if not 0 < args.storage_limit_gib <= 200:
        raise ValueError("storage-limit-gib must be greater than 0 and no more than 200")
    limit = int(args.storage_limit_gib * 1024**3)
    remaining = limit - _artifact_size(root)
    result = review_tokenizers(
        args.dataset_dir,
        output,
        vocab_sizes=args.vocab_sizes,
        min_frequency=args.min_frequency,
        baseline_tokenizer=args.baseline_tokenizer,
        storage_limit_bytes=remaining,
    )
    return {
        **result,
        "outputDirectory": str(output.relative_to(root)),
        "storageLimitBytes": limit,
    }



def _task_finetune_repack(args: argparse.Namespace) -> dict[str, Any]:
    from .artifacts import artifact_bytes
    from .task_finetune import prepare_task_bundle

    root = args.artifact_root.resolve()
    output = _under_artifact_root(args.output_dir, root)
    if not 0 < args.storage_limit_gib <= 200:
        raise ValueError("storage-limit-gib must be greater than 0 and no more than 200")
    limit = int(args.storage_limit_gib * 1024**3)
    remaining = limit - artifact_bytes(root)
    result = prepare_task_bundle(
        args.dataset_dir,
        args.tokenizer_dir,
        output,
        contract_path=args.contract,
        storage_limit_bytes=remaining,
    )
    return {
        **result,
        "outputDirectory": str(output.relative_to(root)),
        "storageLimitBytes": limit,
    }


def _task_finetune_stage(args: argparse.Namespace) -> dict[str, Any]:
    from .artifacts import artifact_bytes
    from .task_finetune import create_task_stage

    root = args.artifact_root.resolve()
    output = _under_artifact_root(args.output_dir, root)
    if not 0 < args.storage_limit_gib <= 200:
        raise ValueError("storage-limit-gib must be greater than 0 and no more than 200")
    limit = int(args.storage_limit_gib * 1024**3)
    remaining = limit - artifact_bytes(root)
    result = create_task_stage(
        args.base_checkpoint,
        args.bundle_dir,
        output,
        contract_path=args.contract,
        artifact_root=root,
        storage_limit_bytes=remaining,
    )
    return {
        **result,
        "outputDirectory": str(output.relative_to(root)),
        "storageLimitBytes": limit,
    }


def _task_finetune_run(args: argparse.Namespace) -> dict[str, Any]:
    from .task_train import run_authorized_task_finetune

    root = args.artifact_root.resolve()
    output = _under_artifact_root(args.output_dir, root)
    return run_authorized_task_finetune(
        checkpoint_path=args.checkpoint,
        bundle_dir=args.bundle_dir,
        output_dir=output,
        artifact_root=root,
        contract_path=args.contract,
        preparation_contract_path=args.preparation_contract,
    )


def _initialize(args: argparse.Namespace) -> dict[str, Any]:
    from .initialization import initialize_model
    from .artifacts import artifact_bytes

    root = args.artifact_root.resolve()
    output = _under_artifact_root(args.output_dir, root)
    if not 0 < args.storage_limit_gib <= 200:
        raise ValueError("storage-limit-gib must be greater than 0 and no more than 200")
    limit = int(args.storage_limit_gib * 1024**3)
    remaining = limit - artifact_bytes(root)
    return initialize_model(args.tokenizer_dir, output, seed=args.seed,
                            artifact_root=root, storage_limit_bytes=remaining)


def _learn_check(args: argparse.Namespace) -> dict[str, Any]:
    from .artifacts import artifact_bytes
    from .learning import run_learning_check

    root = args.artifact_root.resolve()
    output = _under_artifact_root(args.output_dir, root)
    if not 0 < args.storage_limit_gib <= 200:
        raise ValueError("storage-limit-gib must be greater than 0 and no more than 200")
    limit = int(args.storage_limit_gib * 1024**3)
    remaining = limit - artifact_bytes(root)
    return run_learning_check(
        initialization_path=args.initialization,
        tokenizer_dir=args.tokenizer_dir,
        training_tokens=args.train_tokens,
        training_index=args.train_index,
        output_dir=output,
        artifact_root=root,
        steps=args.steps,
        sample_tokens=args.sample_tokens,
        minutes=args.minutes,
        device_name=args.device,
        storage_limit_bytes=remaining,
    )


def _pilot(args: argparse.Namespace) -> dict[str, Any]:
    from .pilot import run_pilot

    root = args.artifact_root.resolve()
    output = _under_artifact_root(args.output_dir, root)
    return run_pilot(
        bundle_dir=args.bundle_dir,
        initialization=args.initialization,
        output_dir=output,
        artifact_root=root,
        minutes=args.minutes,
        steps=args.steps,
        device_name=args.device,
        micro_batch=args.micro_batch,
        gradient_accumulation=args.gradient_accumulation,
        checkpoint_every_minutes=args.checkpoint_every_minutes,
        dataset_dir=args.dataset_dir,
        answer_weight=args.answer_weight,
        sampling_policy=args.sampling_policy,
    )


def _train(args: argparse.Namespace) -> dict[str, Any]:
    from .data import TokenCorpus
    from .runner import run_training

    if not 0 < args.minutes <= MAX_PILOT_MINUTES:
        raise ValueError("training duration must be greater than 0 and no more than the two-hour pilot")
    root = args.artifact_root.resolve()
    checkpoint = _under_artifact_root(args.checkpoint, root)
    metrics = checkpoint.with_suffix(checkpoint.suffix + ".metrics.jsonl")
    if args.train_tokens.resolve() == args.validation_tokens.resolve():
        raise ValueError("Training and validation token corpora must be separate files")
    with TokenCorpus(args.train_tokens) as train_corpus, TokenCorpus(args.validation_tokens) as validation:
        result = run_training(
            train_source=train_corpus,
            validation=validation,
            device_name=args.device,
            minutes=args.minutes,
            step_limit=args.steps,
            output_checkpoint=checkpoint,
            metrics_path=metrics,
            artifact_root=root,
            seed=args.seed,
            micro_batch=args.micro_batch,
            accumulation_steps=args.gradient_accumulation,
            checkpoint_interval_minutes=args.checkpoint_every_minutes,
            resume_from=args.resume,
        )
    return result


def _task_evaluate(args: argparse.Namespace) -> dict[str, Any]:
    from .benchmark import evaluate_files

    report = evaluate_files(
        args.task_set,
        args.responses,
        node_timeout_seconds=args.node_timeout_seconds,
        response_limit_bytes=args.response_limit_bytes,
    )
    if args.report is not None:
        if args.report.exists():
            raise FileExistsError(f"Evaluation report already exists: {args.report}")
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                              encoding="utf-8")
    return report


def _task_generate(args: argparse.Namespace) -> dict[str, Any]:
    from .task_run import generate_development_responses

    root = args.artifact_root.resolve()
    output_dir = _under_artifact_root(args.output_dir, root)
    return generate_development_responses(
        task_set_path=args.task_set,
        checkpoint_path=args.checkpoint,
        bundle_dir=args.bundle_dir,
        output_dir=output_dir,
        artifact_root=root,
        device_name=args.device,
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "environment":
            try:
                from .telemetry import environment_report, select_device
            except (ImportError, OSError) as exc:
                _json_print(
                    {
                        "pythonVersion": platform.python_version(),
                        "platform": sys.platform,
                        "torchVersion": "unavailable",
                        "torchImportError": f"{type(exc).__name__}: {exc}",
                        "cudaAvailable": "unavailable",
                        "selectedDevice": "unavailable",
                    }
                )
                return 2
            device = select_device(args.device)
            _json_print(environment_report(device))
        elif args.command == "prepare":
            _json_print(_prepare(args))
        elif args.command == "dataset-build":
            _json_print(_dataset_build(args))
        elif args.command == "web-dataset-build":
            _json_print(_web_dataset_build(args))
        elif args.command == "web-source-verify":
            _json_print(_web_source_verify(args))
        elif args.command == "web-contamination-check":
            _json_print(_web_contamination_check(args))
        elif args.command == "web-source-materialize":
            _json_print(_web_source_materialize(args))
        elif args.command == "tokenizer-train":
            _json_print(_tokenizer_train(args))
        elif args.command == "tokenizer-review":
            _json_print(_tokenizer_review(args))
        elif args.command == "task-finetune-repack":
            _json_print(_task_finetune_repack(args))
        elif args.command == "task-finetune-stage":
            _json_print(_task_finetune_stage(args))
        elif args.command == "task-finetune-run":
            _json_print(_task_finetune_run(args))
        elif args.command == "initialize":
            _json_print(_initialize(args))
        elif args.command == "learn-check":
            _json_print(_learn_check(args))
        elif args.command == "pilot":
            _json_print(_pilot(args))
        elif args.command == "pilot-evaluate":
            from .pilot import evaluate_pilot

            _json_print(evaluate_pilot(
                bundle_dir=args.bundle_dir, checkpoint_path=args.checkpoint,
                device_name=args.device, maximum_batches=args.max_batches,
            ))
        elif args.command == "pilot-resume":
            from .pilot import resume_pilot

            root = args.artifact_root.resolve()
            output = _under_artifact_root(args.output_dir, root)
            _json_print(resume_pilot(
                bundle_dir=args.bundle_dir, checkpoint_path=args.checkpoint,
                output_dir=output, artifact_root=root, minutes=args.minutes,
                steps=args.steps, device_name=args.device,
                micro_batch=args.micro_batch,
                gradient_accumulation=args.gradient_accumulation,
                checkpoint_every_minutes=args.checkpoint_every_minutes,
                dataset_dir=args.dataset_dir,
            ))
        elif args.command == "complete":
            from .completion import complete_pilot

            _json_print(complete_pilot(
                checkpoint_path=args.checkpoint, bundle_dir=args.bundle_dir,
                prompt=args.prompt, max_new_tokens=args.max_new_tokens,
                temperature=args.temperature, seed=args.seed,
                device_name=args.device,
            ))
        elif args.command == "smoke":
            _json_print(_smoke(args))
        elif args.command == "train":
            _json_print(_train(args))
        elif args.command == "evaluate":
            from .runner import evaluate_checkpoint

            _json_print(evaluate_checkpoint(
                args.checkpoint,
                args.tokens,
                device_name=args.device,
                maximum_batches=args.max_batches,
            ))
        elif args.command == "generate":
            from .runner import generate_bytes

            _json_print({"text": generate_bytes(
                args.checkpoint,
                args.prompt,
                device_name=args.device,
                max_new_tokens=args.max_new_tokens,
                temperature=args.temperature,
                seed=args.seed,
            )})
        elif args.command == "task-evaluate":
            _json_print(_task_evaluate(args))
        elif args.command == "task-generate":
            _json_print(_task_generate(args))
        return 0
    except (FileExistsError, ImportError, OSError, RuntimeError, ValueError) as exc:
        print(f"plex-train: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
