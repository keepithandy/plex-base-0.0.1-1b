"""Prepare the pending P2-07 instruction-invariance candidate; never train or approve."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

from prepare_binding_candidate import ROOT, sha256_file
from prepare_code_pair_candidate import prompt_text, source_text
from prepare_compositional_experiment import DEV_SHA, TOKENIZER_BUNDLE, TOKENIZER_SHA
from plex_training.tokenizer import PlexTokenizer

PHASE2 = ROOT / "training/phase2"
DEFAULT_OUTPUT = PHASE2 / "drafts/p2-07-instruction-invariance-v1"
SELECTORS = (".actions", ".filters", ".controls")
GAPS = ("6px", "14px", "28px")
FAMILIES = {
    "selector-copy": {
        "values": SELECTORS,
        "slot": "selector",
        "phrases": (
            ("return-exactly", "Return this selector exactly: {value}"),
            ("copy-unchanged", "Copy this selector unchanged: {value}"),
            ("repeat-as-shown", "Repeat the selector exactly as shown: {value}"),
            ("output-only", "Output only the selector shown here: {value}"),
        ),
        "heldOutPhrase": ("give-back-no-changes", "Give back this selector with no changes: {value}"),
    },
    "gap-copy": {
        "values": GAPS,
        "slot": "gap",
        "phrases": (
            ("return-exactly", "Return this gap exactly: {value}"),
            ("copy-unchanged", "Copy this gap value unchanged: {value}"),
            ("repeat-as-shown", "Repeat the gap value exactly as shown: {value}"),
            ("output-only", "Output only the gap value shown here: {value}"),
        ),
        "heldOutPhrase": ("give-back-no-changes", "Give back this gap value with no changes: {value}"),
    },
}
PROVENANCE = "codex-authored-p2-07-instruction-invariance-probe"


def _row(family: str, value: str, phrase_id: str, template: str, evaluation: bool) -> dict:
    slot = FAMILIES[family]["slot"]
    split = "evaluation" if evaluation else "train"
    return {
        "schemaVersion": 1,
        "id": f"p2-07-{family}-{phrase_id}-{value.replace('.', 'dot').replace('px', '')}-{split}",
        "operationFamily": family,
        "language": "css",
        "request": template.format(value=value),
        "solution": value,
        "contract": "Return exactly the requested value and nothing else.",
        "checks": [{"kind": "exact_text", "value": value}],
        "bindings": {slot: value},
        "value": value,
        "phrasingId": phrase_id,
        "phrasingGroup": "held-out" if evaluation else "training",
        "splitGroupId": f"p2-07-{family}",
        "sourceId": "p2-07-instruction-invariance",
        "use": "evaluation-only-never-train" if evaluation else "training-candidate",
        "approvalStatus": "evaluation-only" if evaluation else "pending-owner-review",
        "provenance": PROVENANCE,
    }


def build() -> tuple[list[dict], list[dict]]:
    train, evaluation = [], []
    for family, spec in FAMILIES.items():
        for phrase_id, template in spec["phrases"]:
            train.extend(_row(family, value, phrase_id, template, False) for value in spec["values"])
        phrase_id, template = spec["heldOutPhrase"]
        evaluation.extend(_row(family, value, phrase_id, template, True) for value in spec["values"])
    validate(train, evaluation)
    return train, evaluation


def validate(train: list[dict], evaluation: list[dict]) -> None:
    if len(train) != 24 or len(evaluation) != 6:
        raise ValueError("P2-07 requires exactly 24 training and six evaluation records")
    train_requests = {row["request"] for row in train}
    eval_requests = {row["request"] for row in evaluation}
    if len(train_requests) != len(train) or len(eval_requests) != len(evaluation):
        raise ValueError("P2-07 requests must be unique within each split")
    if train_requests & eval_requests:
        raise ValueError("P2-07 training and evaluation requests overlap")
    all_rows = train + evaluation
    if any(row.get("operationFamily") not in FAMILIES for row in all_rows):
        raise ValueError("P2-07 contains an unknown operation family")
    ids = [row["id"] for row in all_rows]
    if len(ids) != len(set(ids)):
        raise ValueError("P2-07 record IDs must be unique")
    for family, spec in FAMILIES.items():
        family_train = [row for row in train if row["operationFamily"] == family]
        family_eval = [row for row in evaluation if row["operationFamily"] == family]
        if len(family_train) != 12 or len(family_eval) != 3:
            raise ValueError(f"{family} requires twelve training and three evaluation records")
        expected_cross = {(phrase_id, value) for phrase_id, _ in spec["phrases"] for value in spec["values"]}
        actual_cross = {(row["phrasingId"], row["value"]) for row in family_train}
        if actual_cross != expected_cross:
            raise ValueError(f"{family} training phrase/value matrix is not fully crossed")
        phrase_templates = dict(spec["phrases"])
        for row in family_train:
            if (row["phrasingId"] not in phrase_templates
                    or row["request"] != phrase_templates[row["phrasingId"]].format(value=row["value"])):
                raise ValueError(f"{family} training request differs from its declared phrase/value")
        if Counter(row["value"] for row in family_train) != Counter({v: 4 for v in spec["values"]}):
            raise ValueError(f"{family} training values must each appear four times")
        held_id, held_template = spec["heldOutPhrase"]
        if any(row["phrasingId"] != held_id or row["request"] != held_template.format(value=row["value"])
               for row in family_eval):
            raise ValueError(f"{family} evaluation must use only its designated held-out phrasing")
        if {row["value"] for row in family_eval} != set(spec["values"]):
            raise ValueError(f"{family} evaluation must use only already-seen values")
        if {row["phrasingId"] for row in family_train} & {row["phrasingId"] for row in family_eval}:
            raise ValueError(f"{family} held-out phrasing appears in training")
    for row in all_rows:
        slot = FAMILIES[row["operationFamily"]]["slot"]
        if (row["language"] != "css" or row["sourceId"] != "p2-07-instruction-invariance"
                or row["solution"] != row["value"] or row["bindings"] != {slot: row["value"]}
                or row["checks"] != [{"kind": "exact_text", "value": row["value"]}]):
            raise ValueError("P2-07 row content does not match its declared single-copy binding")
    for row in train:
        if row["use"] != "training-candidate" or row["approvalStatus"] != "pending-owner-review":
            raise ValueError("All training rows must remain pending owner review")
    for row in evaluation:
        if row["use"] != "evaluation-only-never-train" or row["approvalStatus"] != "evaluation-only":
            raise ValueError("Evaluation rows must remain evaluation-only")


def _write_jsonl(path: Path, rows: list[dict]) -> str:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8", newline="\n")
    return sha256_file(path)


def _review_markdown(train: list[dict], evaluation: list[dict], review: dict) -> str:
    sections = [
        "# P2-07: instruction invariance / paraphrase generalization\n",
        "Status: **pending owner review**. This preparer creates candidates and review metadata only; it does not train a model or create an approval artifact.\n",
        "## Why this probe exists\n",
        "P2-06 learned all six supplied single-copy examples but scored 0/6 when the same known selectors and gaps were requested with alternate wording. The dual-binding and CSS-composition levels also learned 6/6 supplied examples and scored 0/3 held out. P2-07 isolates the earlier single-value wording question before reintroducing multi-binding or code composition.\n",
        "## Controlled design\n",
        "Training contains 24 records: four instruction phrasings crossed with all three values for each of selector-copy and gap-copy. Evaluation contains six records: one never-trained phrasing per family applied to the same three known values. No new values, CSS generation, or multiple bindings are introduced; the only intended novelty is instruction wording.\n",
        "This tiny probe is not evidence of broad language understanding. A transfer score applies only to these operation families and phrasings. Exact training convergence is required before interpreting evaluation failures.\n",
        "## Training phrasing matrix\n",
    ]
    for family, spec in FAMILIES.items():
        sections.append(f"### {family}\n\nValues: {', '.join(spec['values'])}\n\n")
        sections.extend(f"- `{phrase_id}`: `{template}`\n" for phrase_id, template in spec["phrases"])
        sections.append("\n")
        phrase_id, template = spec["heldOutPhrase"]
        sections.append(f"Held out: `{phrase_id}` — `{template}`\n\n")
    sections.extend([
        "## Interpretation criteria\n",
        "Interpret held-out wording only after all 24 training rows pass. If training does not converge, report `inconclusive-instruction-invariance: supplied paraphrase matrix did not fully converge`. At 6/6, report `instruction-invariance-demonstrated-within-single-copy-probe`; at 4–5/6, partial; at 1–3/6, limited; at 0/6, no held-out paraphrase transfer after supplied convergence. Do not generalize beyond this probe.\n",
        "## Safeguards and approval boundary\n",
        "The frozen reference tokenizer must match the expected SHA-256; it is not refitted. The final project holdout is not opened, generated, imported, or scored. Candidate records remain pending owner review, evaluation records are evaluation-only, `modelTrained` is false, and `finalHoldoutOpened` is false. No training is authorized until the owner approves the exact generated candidate hashes.\n",
        "## Candidate files\n\n",
        f"- Training records: {len(train)} (`{review['candidateJsonlSha256']}`)\n",
        f"- Evaluation-only records: {len(evaluation)} (`{review['evaluationJsonlSha256']}`)\n",
        f"- Frozen tokenizer: `{review['tokenizerSha256']}`\n",
        "\nRun the focused preparation tests with:\n\n```powershell\nuv run --project training --no-sync python -m unittest discover -s training\\tests -p test_p2_07_instruction_invariance_probe.py -v\n```\n",
    ])
    return "".join(sections)


def prepare(output: Path = DEFAULT_OUTPUT) -> dict:
    output = output.resolve()
    if output.exists():
        raise FileExistsError("P2-07 candidate directory exists; choose a fresh path")
    dev_path = PHASE2 / "evaluation/p2-01b-dev-v1.json"
    if sha256_file(dev_path) != DEV_SHA:
        raise ValueError("Development output-contract settings changed")
    tokenizer_path = TOKENIZER_BUNDLE / "tokenizer.json"
    if sha256_file(tokenizer_path) != TOKENIZER_SHA:
        raise ValueError("Frozen reference tokenizer changed; refusing candidate preparation")
    settings = json.loads(dev_path.read_text(encoding="utf-8"))
    tokenizer = PlexTokenizer.load(TOKENIZER_BUNDLE)
    train, evaluation = build()
    maxima = {"prompt": 0, "recordIncludingEos": 0, "answerIncludingEos": 0}
    for row in train + evaluation:
        prefix = tokenizer.encode(prompt_text(row, settings["outputContracts"]))
        whole = tokenizer.encode(source_text(row, settings["outputContracts"]))
        answer = len(whole) - len(prefix) + 1
        if whole[:len(prefix)] != prefix or len(whole) + 1 > 512:
            raise ValueError(f"P2-07 token/context budget failed for {row['id']}")
        if answer > settings["inferenceDefaults"]["maxNewTokens"]["css"]:
            raise ValueError(f"P2-07 answer budget failed for {row['id']}")
        maxima["prompt"] = max(maxima["prompt"], len(prefix))
        maxima["recordIncludingEos"] = max(maxima["recordIncludingEos"], len(whole) + 1)
        maxima["answerIncludingEos"] = max(maxima["answerIncludingEos"], answer)
    output.mkdir(parents=True, exist_ok=False)
    candidate_sha = _write_jsonl(output / "candidate.jsonl", train)
    evaluation_sha = _write_jsonl(output / "evaluation-only.jsonl", evaluation)
    review = {
        "schemaVersion": 1,
        "candidate": "p2-07-instruction-invariance-v1",
        "approvalStatus": "pending-owner-review",
        "trainingRecords": len(train),
        "evaluationOnlyRecords": len(evaluation),
        "operationFamilies": {name: {"values": list(spec["values"]),
                                     "trainingPhrases": [{"id": pid, "template": text} for pid, text in spec["phrases"]],
                                     "heldOutPhrase": {"id": spec["heldOutPhrase"][0], "template": spec["heldOutPhrase"][1]}}
                              for name, spec in FAMILIES.items()},
        "candidateJsonlSha256": candidate_sha,
        "evaluationJsonlSha256": evaluation_sha,
        "reviewMarkdownSha256": None,
        "tokenizerSha256": TOKENIZER_SHA,
        "tokenizerRefitted": False,
        "allEvaluationValuesSeenInTraining": True,
        "evaluationWordingAbsentFromTraining": True,
        "fullyCrossedTrainingMatrix": True,
        "tokenMaxima": maxima,
        "modelTrained": False,
        "finalHoldoutOpened": False,
    }
    markdown_path = output / "REVIEW.md"
    markdown_path.write_text(_review_markdown(train, evaluation, review), encoding="utf-8", newline="\n")
    review["reviewMarkdownSha256"] = sha256_file(markdown_path)
    (output / "review.json").write_text(json.dumps(review, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    review["reviewJsonSha256"] = sha256_file(output / "review.json")
    return review


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.output), indent=2, sort_keys=True))
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"plex-p2-07-prepare: {exc}", file=sys.stderr)
        sys.exit(2)
