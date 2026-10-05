"""Read-only greedy scoring of the hash-pinned P2-13 evaluation set."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from prepare_binding_candidate import sha256_file
from prepare_compositional_experiment import ARTIFACT_ROOT, TOKENIZER_BUNDLE, read_rows, write_json
from prepare_p2_13_step200_evaluation import (
    DEFAULT_OUTPUT as EVALUATION_DIR,
    EXPECTED_EVALUATION_SHA256,
    EXPERIMENT,
    build,
)
from run_p2_12_v2_experiment import _score
from plex_training.checkpoint import read_checkpoint
from plex_training.pilot import inspect_pilot_bundle

CHECKPOINT = ARTIFACT_ROOT / "experiments/p2-12-answer-start-transfer-v2-continuation-100step-v3/pilot/pilot-checkpoint.pt"
CHECKPOINT_SHA256 = "e1e6821eaf5af2bfb9ddb0de7031790dc96e6d0e8f706bb4521d005219736065"
SCORE_DIR = ARTIFACT_ROOT / "experiments/p2-13-step200-evaluation-v1"


def score(output: Path = SCORE_DIR, *, device: str = "cuda") -> dict:
    candidate = EVALUATION_DIR / "evaluation-only.jsonl"
    expected_rows = build()
    from prepare_p2_11_balanced_wording_candidate import _jsonl

    if sha256_file(candidate) != EXPECTED_EVALUATION_SHA256:
        raise ValueError("P2-13 evaluation-only file hash differs from the source-pinned hash")
    if candidate.read_bytes() != _jsonl(expected_rows):
        raise ValueError("P2-13 evaluation-only records differ from deterministic reconstruction")
    metadata = json.loads((EVALUATION_DIR / "review.json").read_text(encoding="utf-8"))
    if (metadata.get("evaluationJsonlSha256") != EXPECTED_EVALUATION_SHA256
            or metadata.get("checkpointSha256") != CHECKPOINT_SHA256
            or metadata.get("trainingUsed") is not False
            or metadata.get("runtimeValidationLossUsed") is not False
            or metadata.get("independentFinalHoldout") is not False):
        raise ValueError("P2-13 evaluation review record is incomplete or mismatched")
    if sha256_file(CHECKPOINT) != CHECKPOINT_SHA256:
        raise ValueError("Step-200 checkpoint hash differs from the pinned target")
    bundle = inspect_pilot_bundle(TOKENIZER_BUNDLE)
    model, payload = read_checkpoint(CHECKPOINT, "cpu")
    del model
    if payload.get("step") != 200 or payload.get("tokenizerRecord") != bundle["tokenizer"]:
        raise ValueError("Scoring checkpoint step or tokenizer identity is invalid")
    if payload.get("datasetRecord", {}).get("p212EvaluationUsedForValidation") is not False:
        raise ValueError("Scoring checkpoint includes the P2-12 evaluation set in validation")
    settings = json.loads((Path(__file__).resolve().parent / "evaluation/p2-01b-dev-v1.json").read_text(encoding="utf-8"))
    output = output.resolve()
    output.relative_to(ARTIFACT_ROOT.resolve())
    output.mkdir(parents=True, exist_ok=True)
    summary_path = output / "result.json"
    if summary_path.is_file():
        prior = json.loads(summary_path.read_text(encoding="utf-8"))
        if (prior.get("checkpointSha256") == CHECKPOINT_SHA256
                and prior.get("evaluationJsonlSha256") == EXPECTED_EVALUATION_SHA256
                and prior.get("finalHoldoutOpened") is False):
            return prior
        raise ValueError("Existing P2-13 summary does not match the pinned score request")
    raw_score = output / "completion-score.json"
    if raw_score.exists():
        # A prior invocation may have completed generation before report writing
        # failed. Reuse it only when checkpoint identity and every row ID match.
        scores = json.loads(raw_score.read_text(encoding="utf-8"))
        expected_ids = {row["id"] for row in expected_rows}
        actual_ids = {row.get("id") for row in scores.get("records", [])
                      if row.get("group") == "evaluation"}
        if (scores.get("checkpointSha256") != CHECKPOINT_SHA256
                or actual_ids != expected_ids
                or len(scores.get("records", [])) != len(expected_rows)):
            raise ValueError("Existing P2-13 generated score does not match pinned inputs")
    else:
        scores = _score(CHECKPOINT, [], expected_rows, settings, device, raw_score)
    scores.update({
        "experiment": EXPERIMENT,
        "evaluationJsonlSha256": EXPECTED_EVALUATION_SHA256,
        "evaluationSemantics": "Fresh development evaluation with six held-out wording templates crossed with two layouts and eight known selectors; not an independent final holdout.",
        "trainingUsed": False,
        "runtimeValidationLossUsed": False,
        "finalHoldoutOpened": False,
    })
    write_json(output / "labeled-completion-score.json", scores)
    summary = {
        "schemaVersion": 1,
        "experiment": EXPERIMENT,
        "checkpointSha256": CHECKPOINT_SHA256,
        "checkpointStep": 200,
        "evaluationJsonlSha256": EXPECTED_EVALUATION_SHA256,
        "evaluationRecords": len(expected_rows),
        "scores": scores["evaluation"],
        "conditionCells": scores["conditionCells"]["evaluation"],
        "trainingUsed": False,
        "runtimeValidationLossUsed": False,
        "independentFinalHoldout": False,
        "finalHoldoutOpened": False,
        "scoreArtifact": str(output / "labeled-completion-score.json"),
    }
    write_json(output / "result.json", summary)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=SCORE_DIR)
    parser.add_argument("--device", choices=("cuda",), default="cuda")
    args = parser.parse_args()
    try:
        print(json.dumps(score(args.output_dir, device=args.device), indent=2))
    except (OSError, ValueError, RuntimeError, ImportError, json.JSONDecodeError) as exc:
        print(f"plex-p2-13-evaluation-score: {exc}", file=sys.stderr)
        raise SystemExit(2)
