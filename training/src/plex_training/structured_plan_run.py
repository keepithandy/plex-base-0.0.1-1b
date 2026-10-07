"""Deterministic development-only generation for the P2-31 structured bridge."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from .artifacts import enforce_storage_limit
from .checkpoint import read_checkpoint
from .completion import _completion_tokenizer, _generate_token_ids
from .structured_plan import (
    MAX_PLAN_TASK_SET_BYTES,
    PLAN_SCHEMA_VERSION,
    PROMPT_TEMPLATE_VERSION,
    render_plan_prompt,
    validate_plan_task_set,
)
from .telemetry import select_device
from .tokenizer import CODEC, sha256_file

DEFAULT_CONTRACT = Path("training/pretraining/p2-31-structured-bridge-contract.json")


def _contract(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise ValueError("P2-31 contract must be a regular local file under 1 MiB")
    value = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(value, dict)
            or value.get("schemaVersion") != 1
            or value.get("milestone") != "P2-31"
            or value.get("kind") != "plex-p2-31-structured-bridge-contract-v1"
            or value.get("status") != "evaluation-authorized"
            or value.get("modelTrainingAuthorized") is not False):
        raise ValueError("P2-31 evaluation contract is missing or does not block training")
    protected = value.get("protectedEvaluation")
    if (not isinstance(protected, dict)
            or protected.get("finalProjectHoldoutMustRemainClosed") is not True
            or protected.get("noGradientUpdates") is not True):
        raise ValueError("P2-31 protected-evaluation boundary is invalid")
    development = value.get("developmentEvaluation")
    if (not isinstance(development, dict)
            or development.get("planSchemaVersion") != PLAN_SCHEMA_VERSION
            or development.get("promptTemplateVersion") != PROMPT_TEMPLATE_VERSION
            or development.get("temperature") != 0.0
            or development.get("seed") != 1337
            or development.get("maxNewTokens") != 256):
        raise ValueError("P2-31 deterministic evaluation settings changed")
    return value


def generate_structured_plans(
    *,
    task_set_path: Path,
    checkpoint_path: Path,
    bundle_dir: Path,
    output_dir: Path,
    artifact_root: Path,
    contract_path: Path = DEFAULT_CONTRACT,
    device_name: str = "auto",
) -> dict[str, Any]:
    """Generate raw structured-plan responses without parsing, scoring, or training."""
    contract = _contract(contract_path)
    if task_set_path.is_symlink() or not task_set_path.is_file():
        raise ValueError("P2-31 task set must be a regular local file")
    if task_set_path.stat().st_size > MAX_PLAN_TASK_SET_BYTES:
        raise ValueError("P2-31 task set exceeds the 1 MiB limit")
    raw_task_set = task_set_path.read_bytes()
    task_set_sha = hashlib.sha256(raw_task_set).hexdigest()
    development = contract["developmentEvaluation"]
    if task_set_sha != development.get("taskSetSha256"):
        raise ValueError("P2-31 task set hash differs from the authorized development set")
    task_set = validate_plan_task_set(json.loads(raw_task_set.decode("utf-8")))
    if task_set["kind"] != "development":
        raise ValueError("P2-31 generation is development-only; final holdouts stay sealed")
    if (task_set["setId"] != development.get("setId")
            or len(task_set["tasks"]) != development.get("tasks")
            or task_set["inferenceDefaults"]["temperature"] != development.get("temperature")
            or task_set["inferenceDefaults"]["seed"] != development.get("seed")
            or task_set["inferenceDefaults"]["maxNewTokens"] != development.get("maxNewTokens")):
        raise ValueError("P2-31 task-set metadata differs from the authorization")

    checkpoint = contract.get("checkpoint")
    if (not isinstance(checkpoint, dict)
            or checkpoint_path.is_symlink() or not checkpoint_path.is_file()
            or sha256_file(checkpoint_path) != checkpoint.get("sha256")):
        raise ValueError("P2-31 requires the exact fixed P2-30 step-100 checkpoint")

    vocabulary, tokenizer_record = _completion_tokenizer(bundle_dir)
    tokenizer = contract.get("tokenizer")
    if (not isinstance(tokenizer, dict)
            or tokenizer_record.get("tokenizerSha256") != tokenizer.get("sha256")
            or tokenizer_record.get("bundleManifestSha256") != tokenizer.get("bundleManifestSha256")
            or tokenizer_record.get("actualVocabularySize") != tokenizer.get("vocabularySize")):
        raise ValueError("P2-31 requires the exact frozen P2-30 tokenizer bundle")

    device = select_device(device_name)
    model, payload = read_checkpoint(checkpoint_path, device)
    initialization = payload.get("initializationRecord")
    stage = payload.get("stageTransitionRecord")
    if (payload.get("codec") != CODEC
            or payload.get("tokenizerRecord") != tokenizer_record
            or payload.get("step") != checkpoint.get("step")
            or not isinstance(initialization, dict)
            or initialization.get("pretrainedCheckpointLoaded") is not False
            or initialization.get("pretrainedModelWeightsLoaded") is not False
            or not isinstance(stage, dict)
            or stage.get("kind") != "plex-task-finetune-stage-transition-v1"):
        raise ValueError("P2-31 checkpoint provenance does not match the fixed Plex lineage")
    if vocabulary.vocabulary_size != tokenizer.get("vocabularySize"):
        raise ValueError("P2-31 tokenizer vocabulary size changed")

    artifact_root = artifact_root.resolve()
    output_dir = output_dir.resolve(strict=False)
    try:
        output_dir.relative_to(artifact_root)
    except ValueError as exc:
        raise ValueError("P2-31 outputs must stay under the configured artifact root") from exc
    if output_dir.exists():
        raise FileExistsError("P2-31 output directory already exists; choose a fresh path")
    output_dir.parent.mkdir(parents=True, exist_ok=True)

    defaults = task_set["inferenceDefaults"]
    responses: list[dict[str, Any]] = []
    for task in task_set["tasks"]:
        prompt = render_plan_prompt(task_set, task)
        prompt_ids = vocabulary.encode(prompt)
        if len(prompt_ids) >= model.config.context_length:
            raise ValueError(f"P2-31 prompt for {task['id']} exceeds the model context")
        generated_ids, stopped_at_eos = _generate_token_ids(
            model,
            prompt_ids,
            actual_vocab=vocabulary.vocabulary_size,
            max_new_tokens=defaults["maxNewTokens"],
            temperature=defaults["temperature"],
            seed=defaults["seed"],
            device=device,
        )
        responses.append({
            "taskId": task["id"],
            "text": vocabulary.decode(generated_ids),
            "truncated": not stopped_at_eos,
        })

    staging = Path(tempfile.mkdtemp(prefix=".plex-p2-31-", dir=output_dir.parent)).resolve()
    try:
        responses_path = staging / "responses.jsonl"
        with responses_path.open("x", encoding="utf-8", newline="\n") as stream:
            for response in responses:
                stream.write(json.dumps(response, ensure_ascii=False, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        manifest = {
            "schemaVersion": 1,
            "runKind": "p2-31-structured-plan-development-generation",
            "trainingPerformed": False,
            "researchOptimizerUpdates": 0,
            "finalHoldoutOpened": False,
            "taskSetId": task_set["setId"],
            "taskSetSha256": task_set_sha,
            "taskCount": len(responses),
            "checkpointSha256": sha256_file(checkpoint_path),
            "checkpointStep": payload["step"],
            "tokenizerSha256": tokenizer_record["tokenizerSha256"],
            "tokenizerBundleManifestSha256": tokenizer_record["bundleManifestSha256"],
            "planSchemaVersion": task_set["planSchemaVersion"],
            "promptTemplateVersion": defaults["promptTemplateVersion"],
            "temperature": defaults["temperature"],
            "seed": defaults["seed"],
            "maxNewTokens": defaults["maxNewTokens"],
            "device": str(device),
            "responsesSha256": sha256_file(responses_path),
            "contractSha256": sha256_file(contract_path),
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
        "planSchemaVersion": task_set["planSchemaVersion"],
        "device": str(device),
        "trainingPerformed": False,
        "researchOptimizerUpdates": 0,
        "finalHoldoutOpened": False,
    }
