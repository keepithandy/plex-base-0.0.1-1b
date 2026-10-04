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

    tokenizer = subparsers.add_parser("tokenizer-train", help="Fit Plex byte-level BPE on reviewed training text only")
    tokenizer.add_argument("--dataset-dir", type=Path, required=True)
    tokenizer.add_argument("--output-dir", type=Path, default=Path("tokenizers/p1-15-starter-v1"))
    tokenizer.add_argument("--vocab-size", type=int, default=DEFAULT_CONFIG.vocab_size)
    tokenizer.add_argument("--min-frequency", type=int, default=2)
    tokenizer.add_argument("--storage-limit-gib", type=float, default=200.0)
    _add_artifact_root(tokenizer)

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
        elif args.command == "tokenizer-train":
            _json_print(_tokenizer_train(args))
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
        return 0
    except (FileExistsError, ImportError, OSError, RuntimeError, ValueError) as exc:
        print(f"plex-train: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
