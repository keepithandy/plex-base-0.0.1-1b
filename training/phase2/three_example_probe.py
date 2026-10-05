"""Bounded three-example Plex overfit probe using approved training records only.

This is a pipeline diagnostic, not a capability benchmark. Generated code is
parsed by existing static checks but never executed.
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
import time
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "training" / "src"))

from plex_training.artifacts import enforce_storage_limit, path_within_root
from plex_training.benchmark import _check_task
from plex_training.checkpoint import read_checkpoint, restore_optimizer, restore_random_states, save_checkpoint
from plex_training.completion import _completion_tokenizer, _generate_token_ids
from plex_training.config import DEFAULT_CONFIG
from plex_training.runner import ADAMW_BETAS, ADAMW_EPSILON, ADAMW_LEARNING_RATE, ADAMW_WEIGHT_DECAY, seed_everything
from plex_training.telemetry import peak_gpu_memory, reset_peak_gpu_memory, select_device
from plex_training.tokenizer import CODEC, sha256_file

from diagnose_saved_checkpoints import load_approved
from prepare_code_pair_candidate import prompt_text

SELECTED_IDS = (
    "gap-html-ruby-01",
    "gap-css-logical-border-01",
    "gap-javascript-division-01",
)
MAX_STEPS = 200
MAX_MINUTES = 10.0
SCORE_STEPS = (0, 25, 50, 100, 200)
ARTIFACT_ROOT = ROOT / "training" / "artifacts"


def prepare_examples(rows: list[dict], contracts: dict[str, str], tokenizer: object) -> list[dict]:
    by_id = {row["id"]: row for row in rows}
    selected = []
    for identifier in SELECTED_IDS:
        row = by_id[identifier]
        if row["candidateSplit"] != "train":
            raise ValueError(f"Probe example is not in the approved training split: {identifier}")
        prompt = prompt_text(row, contracts)
        prompt_ids = tokenizer.encode(prompt)
        full_ids = tokenizer.encode(prompt + "\n" + row["solution"])
        if full_ids[:len(prompt_ids)] != prompt_ids:
            raise ValueError(f"Tokenizer changed the prompt prefix: {identifier}")
        full_ids.append(3)  # EOS: the code answer ends here.
        if len(full_ids) < 3 or len(full_ids) - 1 > DEFAULT_CONFIG.context_length:
            raise ValueError(f"Probe example exceeds the model context: {identifier}")
        selected.append({"row": row, "prompt": prompt, "promptIds": prompt_ids,
                         "inputIds": full_ids[:-1], "targetIds": full_ids[1:]})
    if {item["row"]["language"] for item in selected} != {"html", "css", "javascript"}:
        raise ValueError("Probe needs one approved training example per language")
    return selected


def verify_built_train_split(bundle: Path, candidate_sha: str, examples: list[dict]) -> str:
    """Prove the selected source texts occur in the approved built training split."""
    dataset = ARTIFACT_ROOT / "datasets" / "p2-request-following-v3"
    manifest_path = dataset / "manifest.json"
    train_path = dataset / "train.jsonl"
    if any(path.is_symlink() or not path.is_file() or path.stat().st_size > 1024 * 1024
           for path in (manifest_path, train_path)):
        raise ValueError("Built v3 dataset files are missing, linked, or oversized")
    manifest_sha = sha256_file(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    bundle_manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    if (bundle_manifest.get("sourceDatasetManifestSha256") != manifest_sha
            or any(source.get("revision") != candidate_sha for source in manifest["sources"])
            or manifest["summary"].get("trainJsonlSha256") != sha256_file(train_path)
            or manifest["summary"].get("trainRecords") != 156):
        raise ValueError("Built training split does not match the approved candidate/tokenizer")
    actual_texts = {json.loads(line)["text"] for line in train_path.read_text(encoding="utf-8").splitlines()}
    for example in examples:
        if example["prompt"] + "\n" + example["row"]["solution"] not in actual_texts:
            raise ValueError(f"Selected example is absent from the built training split: {example['row']['id']}")
    return manifest_sha


def score(model: object, examples: list[dict], tokenizer: object, caps: dict[str, int],
          seed: int, device: torch.device, node: str | None, step: int) -> dict:
    model.eval()
    details = []
    for example in examples:
        row = example["row"]
        generated, stopped_at_eos = _generate_token_ids(
            model, example["promptIds"], actual_vocab=tokenizer.vocabulary_size,
            max_new_tokens=caps[row["language"]], temperature=0.0, seed=seed, device=device,
        )
        completion = tokenizer.decode(generated)
        static = _check_task({"id": row["id"], "language": row["language"],
                              "difficulty": "basic", "checks": row["checks"]},
                             completion, node, 5.0)
        details.append({
            "id": row["id"], "language": row["language"], "completion": completion,
            "expected": "\n" + row["solution"],
            "exactTarget": stopped_at_eos and completion == "\n" + row["solution"],
            "codeOnlyExact": stopped_at_eos and completion.strip() == row["solution"].strip(),
            "staticPass": static["passed"], "parseStatus": static["parseStatus"],
            "checksPassed": static["checksPassed"], "checksTotal": static["checksTotal"],
            "generatedTokens": len(generated), "stoppedAtEos": stopped_at_eos,
        })
    return {"step": step, "exactCount": sum(item["exactTarget"] for item in details),
            "staticPassCount": sum(item["staticPass"] for item in details),
            "examples": details}


def run(*, candidate: Path, approval: Path, task_set: Path, bundle: Path,
        initialization: Path, output: Path, device_name: str, steps: int = MAX_STEPS,
        minutes: float = MAX_MINUTES) -> dict:
    if type(steps) is not int or not 1 <= steps <= MAX_STEPS:
        raise ValueError("Probe steps must be from 1 through 200")
    if not 0 < minutes <= MAX_MINUTES:
        raise ValueError("Probe duration must be greater than zero and at most ten minutes")
    output = path_within_root(output, ARTIFACT_ROOT.resolve())
    if output.exists():
        raise FileExistsError("Probe output already exists; choose a fresh path")
    rows, candidate_sha = load_approved(candidate, approval)
    if task_set.is_symlink() or not task_set.is_file() or task_set.stat().st_size > 1024 * 1024:
        raise ValueError("Development settings file is missing, linked, or oversized")
    settings = json.loads(task_set.read_text(encoding="utf-8"))
    defaults = settings["inferenceDefaults"]
    if (settings.get("kind") != "development" or defaults.get("temperature") != 0.0
            or defaults.get("promptTemplateVersion") != "plex-coding-task-v1"):
        raise ValueError("Probe requires the fixed development prompt settings")
    tokenizer, tokenizer_record = _completion_tokenizer(bundle)
    examples = prepare_examples(rows, settings["outputContracts"], tokenizer)
    verify_built_train_split(bundle, candidate_sha, examples)
    if initialization.is_symlink() or not initialization.is_file():
        raise ValueError("Initialization checkpoint must be an existing regular file")
    seed = defaults["seed"]
    device = select_device(device_name)
    seed_everything(seed)
    rng = random.Random(seed)
    model, payload = read_checkpoint(initialization, device)
    initial_record = payload.get("initializationRecord")
    if (model.config != DEFAULT_CONFIG or payload.get("step") != 0
            or payload.get("codec") != CODEC
            or payload.get("tokenizerRecord") != tokenizer_record
            or payload.get("seed") != seed
            or not isinstance(initial_record, dict)
            or initial_record.get("pretrainedCheckpointLoaded") is not False
            or initial_record.get("pretrainedModelWeightsLoaded") is not False):
        raise ValueError("Probe requires the matching scratch-initialized step-zero checkpoint")
    optimizer = torch.optim.AdamW(model.parameters(), lr=ADAMW_LEARNING_RATE,
                                  betas=ADAMW_BETAS, weight_decay=ADAMW_WEIGHT_DECAY,
                                  eps=ADAMW_EPSILON)
    restore_optimizer(optimizer, payload)
    restore_random_states(payload, rng, torch.device("cpu"))
    if device.type == "cuda":
        torch.cuda.manual_seed_all(seed)
    node = shutil.which("node")
    enforce_storage_limit(ARTIFACT_ROOT, additional_bytes=350 * 1024**2,
                          limit_bytes=200 * 1024**3)
    inputs = [(torch.tensor(example["inputIds"], dtype=torch.long, device=device)[None, :],
               torch.tensor(example["targetIds"], dtype=torch.long, device=device)[None, :])
              for example in examples]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir(exist_ok=False)
    reset_peak_gpu_memory(device)
    started = time.perf_counter()
    deadline = started + minutes * 60
    scores = [score(model, examples, tokenizer, defaults["maxNewTokens"], seed,
                    device, node, 0)]
    losses = []
    step = 0
    for step_number in range(1, steps + 1):
        if time.perf_counter() >= deadline:
            break
        model.train()
        optimizer.zero_grad(set_to_none=True)
        step_losses = []
        for input_ids, target_ids in inputs:
            _, loss = model(input_ids, target_ids,
                            loss_vocabulary_size=tokenizer.vocabulary_size)
            if loss is None:
                raise RuntimeError("Probe produced no training loss")
            (loss / len(inputs)).backward()
            step_losses.append(float(loss.detach().item()))
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        step = step_number
        losses.append(sum(step_losses) / len(step_losses))
        if step in SCORE_STEPS:
            observation = score(model, examples, tokenizer, defaults["maxNewTokens"],
                                seed, device, node, step)
            scores.append(observation)
            print(json.dumps({"step": step, "loss": losses[-1],
                              "exactCount": observation["exactCount"],
                              "staticPassCount": observation["staticPassCount"]}), flush=True)
    if not scores or scores[-1]["step"] != step:
        scores.append(score(model, examples, tokenizer, defaults["maxNewTokens"],
                            seed, device, node, step))
    elapsed = time.perf_counter() - started
    dataset_record = {"kind": "three-approved-example-overfit-probe",
                      "candidateSha256": candidate_sha, "selectedIds": list(SELECTED_IDS)}
    training_settings = {"kind": "three-example-full-sequence-next-token-v1",
                         "optimizer": "AdamW", "learningRate": ADAMW_LEARNING_RATE,
                         "weightDecay": ADAMW_WEIGHT_DECAY, "betas": list(ADAMW_BETAS),
                         "epsilon": ADAMW_EPSILON, "maxSteps": steps, "maxMinutes": minutes,
                         "examplesPerStep": 3, "gradientClippingNorm": 1.0}
    checkpoint_path = output / "probe-checkpoint.pt"
    save_checkpoint(model, optimizer, step=step, seed=seed, codec=CODEC,
                    sampling_rng=rng, device=device, destination=checkpoint_path,
                    artifact_root=ARTIFACT_ROOT, initialization_record=initial_record,
                    tokenizer_record=tokenizer_record, dataset_record=dataset_record,
                    training_settings=training_settings,
                    tokens_processed_total=step * sum(len(x[1][0]) for x in inputs))
    report = {
        "schemaVersion": 1, "kind": "three-example-overfit-probe",
        "candidateSha256": candidate_sha, "selectedIds": list(SELECTED_IDS),
        "initializationCheckpointSha256": sha256_file(initialization),
        "checkpointSha256": sha256_file(checkpoint_path),
        "tokenizerSha256": tokenizer_record["tokenizerSha256"],
        "device": str(device), "nodeAvailableForSyntaxCheck": node is not None,
        "requestedSteps": steps, "requestedMinutes": minutes,
        "completedSteps": step, "elapsedSeconds": elapsed,
        "initialLoss": losses[0] if losses else None,
        "finalLoss": losses[-1] if losses else None,
        "peakGpuMemory": peak_gpu_memory(device),
        "objective": "ordinary full-sequence next-token loss on three approved records; equal per-example gradient weight",
        "scores": scores, "pretrainedCheckpointLoaded": False,
        "limits": "Pipeline overfit diagnostic only; no final-holdout evaluation or capability claim.",
    }
    (output / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                                        encoding="utf-8", newline="\n")
    enforce_storage_limit(ARTIFACT_ROOT, limit_bytes=200 * 1024**3)
    return {"report": str(output / "report.json"),
            "checkpointSha256": report["checkpointSha256"],
            "completedSteps": step, "elapsedSeconds": elapsed,
            "initialLoss": report["initialLoss"], "finalLoss": report["finalLoss"],
            "scores": [{key: result[key] for key in ("step", "exactCount", "staticPassCount")}
                       for result in scores]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--task-set", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--initialization", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--steps", type=int, default=MAX_STEPS)
    parser.add_argument("--minutes", type=float, default=MAX_MINUTES)
    args = parser.parse_args()
    print(json.dumps(run(candidate=args.candidate, approval=args.approval,
                         task_set=args.task_set, bundle=args.bundle,
                         initialization=args.initialization, output=args.output,
                         device_name=args.device, steps=args.steps, minutes=args.minutes),
                     indent=2))


if __name__ == "__main__":
    main()
