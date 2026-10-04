"""Run the fixed development prompts on one local, scratch-initialized Plex checkpoint."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

import torch

from .benchmark import MAX_TASK_SET_BYTES, render_task_prompt, validate_task_set
from .artifacts import enforce_storage_limit
from .checkpoint import read_checkpoint
from .completion import _completion_tokenizer, _generate_token_ids
from .tokenizer import CODEC, sha256_file
from .telemetry import select_device


def generate_development_responses(
    *,
    task_set_path: Path,
    checkpoint_path: Path,
    bundle_dir: Path,
    output_dir: Path,
    artifact_root: Path,
    device_name: str = "auto",
) -> dict[str, Any]:
    """Generate one deterministic response per development task without executing it."""
    if task_set_path.is_symlink() or not task_set_path.is_file():
        raise ValueError("Task set must be a regular local file")
    if task_set_path.stat().st_size > MAX_TASK_SET_BYTES:
        raise ValueError("Task set file exceeds the 1 MiB limit")
    if checkpoint_path.is_symlink() or not checkpoint_path.is_file():
        raise ValueError("Evaluation checkpoint must be a regular file")
    raw_task_set = task_set_path.read_bytes()
    task_set = validate_task_set(json.loads(raw_task_set.decode("utf-8")))
    if task_set["kind"] != "development":
        raise ValueError("This command runs development task sets only; final holdouts stay sealed")

    defaults = task_set["inferenceDefaults"]
    vocabulary, tokenizer_record = _completion_tokenizer(bundle_dir)
    device = select_device(device_name)
    model, payload = read_checkpoint(checkpoint_path, device)
    initialization = payload.get("initializationRecord")
    if (payload.get("codec") != CODEC
            or payload.get("tokenizerRecord") != tokenizer_record
            or type(payload.get("step")) is not int
            or payload["step"] < 0
            or not isinstance(initialization, dict)
            or initialization.get("pretrainedCheckpointLoaded") is not False
            or initialization.get("pretrainedModelWeightsLoaded") is not False):
        raise ValueError("Evaluation checkpoint must be a matching scratch-initialized Plex checkpoint")
    if not 4 <= vocabulary.vocabulary_size <= model.config.vocab_size:
        raise ValueError("Development tokenizer vocabulary does not fit the checkpoint")

    artifact_root = artifact_root.resolve()
    output_dir = output_dir.resolve(strict=False)
    try:
        output_dir.relative_to(artifact_root)
    except ValueError as exc:
        raise ValueError("Evaluation outputs must stay under the configured artifact root") from exc
    if output_dir.exists():
        raise FileExistsError("Evaluation output directory already exists; choose a fresh path")
    output_dir.parent.mkdir(parents=True, exist_ok=True)

    responses: list[dict[str, Any]] = []
    for task in task_set["tasks"]:
        prompt = render_task_prompt(task_set, task)
        prompt_ids = vocabulary.encode(prompt)
        if len(prompt_ids) >= model.config.context_length:
            raise ValueError(f"Prompt for {task['id']} exceeds the model context after tokenization")
        generated_ids, stopped_at_eos = _generate_token_ids(
            model,
            prompt_ids,
            actual_vocab=vocabulary.vocabulary_size,
            max_new_tokens=defaults["maxNewTokens"][task["language"]],
            temperature=defaults["temperature"],
            seed=defaults["seed"],
            device=device,
        )
        responses.append({
            "taskId": task["id"],
            "text": vocabulary.decode(generated_ids),
            "truncated": not stopped_at_eos,
        })

    staging = Path(tempfile.mkdtemp(prefix=".plex-task-eval-", dir=output_dir.parent)).resolve()
    try:
        responses_path = staging / "responses.jsonl"
        with responses_path.open("x", encoding="utf-8", newline="\n") as stream:
            for response in responses:
                stream.write(json.dumps(response, ensure_ascii=False, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        manifest = {
            "schemaVersion": 1,
            "runKind": "development-task-generation",
            "taskSetId": task_set["setId"],
            "taskSetSha256": hashlib.sha256(raw_task_set).hexdigest(),
            "taskCount": len(responses),
            "checkpointSha256": sha256_file(checkpoint_path),
            "checkpointStep": payload["step"],
            "initialModelWeightsSha256": initialization.get("initialModelWeightsSha256"),
            "tokenizer": tokenizer_record,
            "modelConfig": model.config.to_dict(),
            "promptTemplateVersion": defaults["promptTemplateVersion"],
            "temperature": defaults["temperature"],
            "seed": defaults["seed"],
            "maxNewTokens": defaults["maxNewTokens"],
            "device": str(device),
            "pretrainedCheckpointLoaded": False,
            "responsesSha256": sha256_file(responses_path),
        }
        with (staging / "run-manifest.json").open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(manifest, stream, indent=2, ensure_ascii=False, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        enforce_storage_limit(artifact_root, limit_bytes=200 * 1024**3)
        os.rename(staging, output_dir)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise

    return {
        "outputDirectory": str(output_dir.relative_to(artifact_root)),
        "responses": str((output_dir / "responses.jsonl").relative_to(artifact_root)),
        "manifest": str((output_dir / "run-manifest.json").relative_to(artifact_root)),
        "taskCount": len(responses),
        "checkpointStep": payload["step"],
        "checkpointSha256": manifest["checkpointSha256"],
        "responsesSha256": manifest["responsesSha256"],
        "device": str(device),
        "pretrainedCheckpointLoaded": False,
    }
