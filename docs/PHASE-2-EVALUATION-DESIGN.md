# Phase 2 coding evaluation — P2-01

**Status: P2-01a and the development-only portion of P2-01b are complete.** The 30-task development set is versioned at [`training/phase2/evaluation/p2-01b-dev-v1.json`](../training/phase2/evaluation/p2-01b-dev-v1.json). No 60-task final holdout, P2 checkpoint, or model score exists.

## Owner-approved decision rule

For the eventual 60-task final holdout, Plex must pass at least **11 of 20 tasks in each of HTML, CSS, and JavaScript**, and its overall complete-task pass rate must be at least **10 percentage points above the matching step-zero checkpoint**. With 60 tasks, that margin is at least six net additional passed tasks. Report raw counts and uncertainty intervals as context; this small set is an early signal, not a claim of statistical certainty.

The step-zero and trained checkpoints must use the same fresh random initialization, model configuration, tokenizer, prompts, decoding settings, and task set. A trivial baseline may be reported separately. Qwen is optional only if a suitable model is already available locally; it is not a Plex initialization source, and this milestone downloads none.

## Task format and fixed development defaults

The development set has ten owner-authored tasks per language, split between basic and edge cases. It asks for one semantic HTML fragment, one CSS stylesheet, or one JavaScript function. Each task has a stable ID, request, language, difficulty, output contract, and visible structural checks. The prompts and checks are benchmark files, outside the source catalog and training manifest. The final 60 prompts and checks have not been authored or frozen.

The task-set manifest records the initial deterministic decode defaults: temperature 0 (greedy), seed 1337, a versioned common prompt template, and maximum output lengths of 192 HTML tokens, 128 CSS tokens, and 192 JavaScript tokens. These are development settings for later model comparisons; no model was invoked here. Do not silently change them between compared checkpoints. Any revised benchmark or prompt settings need a new version.

## What the evaluator checks

`plex_training.benchmark` consumes newline-delimited JSON responses with `taskId` and `text` (plus `truncated` when generation metadata is available), and reports per-language and overall counts, pass rates, descriptive 95% Wilson intervals, assertion totals, partial assertion counts, parse outcomes, missing/empty/truncated/over-limit outputs, timeouts, Node.js parser version, and input SHA-256 hashes. The interval denominator includes every task; unavailable checks are never counted as passes and are also reported separately. These small-set intervals are descriptive context, not a significance test. The evaluator rejects duplicate or unknown response IDs, caps each response at 65,536 UTF-8 bytes, and limits each JavaScript syntax check to five seconds.

- HTML is parsed with Python's standard-library `HTMLParser`. The current subset checks balanced and properly nested tags, duplicate attributes, requested element/attribute presence, and requested text. It is a structural fragment check, not a browser or accessibility audit.
- CSS checks flat selector blocks, balanced braces, and requested declarations. Nested rules and at-rules are not supported. This is a bounded syntax/structure check, not computed-style validation.
- JavaScript is written to a temporary directory and passed to an installed `node --check` command. The code is never executed. If Node is missing, syntax status is marked unavailable and that task cannot pass.
- Markdown fences are rejected. Output and reports contain score details, not source paths or environment secrets.

The JS tasks include required source fragments in addition to syntax. Those fragments can be present in incorrect or unreachable code, so the evaluator does **not** establish JavaScript behavior. Before a final benchmark can claim complete-task behavior, confirm a safe local execution boundary for deterministic JS tests with strict timeouts and output limits. If a suitable isolation mechanism is unavailable, keep JavaScript behavior marked unavailable and do not use static results as the P2-03 or P2-04 coding-quality gate. Browser-backed HTML/CSS behavior is also not implemented here.

## Reproduce a development evaluation

Once a matching scratch-initialized step-zero or trained checkpoint and tokenizer bundle are available, generate only the development responses into a fresh output directory:

```powershell
uv run --project training --locked python -m plex_training.cli task-generate `
  --checkpoint training\artifacts\initializations\p2-step-zero\initialization.pt `
  --bundle-dir training\artifacts\tokenizers\p2-02-data-v2 `
  --output-dir evaluation\p2-dev-step-zero-v1 `
  --device cuda
```

The command applies the task-set prompt template and greedy decode limits, checks that the checkpoint is scratch-initialized and matches the tokenizer, and writes `responses.jsonl` plus a hash-bound `run-manifest.json`. It refuses an existing output directory and cannot generate from a final task set. It does not train.

For a manually supplied response, create a local response JSONL file with one object per task, for example:

```jsonl
{"taskId":"p2dev-js-01-clamp","text":"function clamp(value, minimum, maximum) { return Math.min(maximum, Math.max(minimum, value)); }","truncated":false}
```

Score the generated response file from the repository root in PowerShell, choosing a report path that does not already exist. For a manually supplied response, replace the `--responses` path with your JSONL file:

```powershell
uv run --project training --locked python -m plex_training.cli task-evaluate `
  --task-set training\phase2\evaluation\p2-01b-dev-v1.json `
  --responses training\artifacts\evaluation\p2-dev-step-zero-v1\responses.jsonl `
  --report training\artifacts\evaluation\p2-dev-step-zero-v1\score.json
```

`truncated` should be set from the generator's stop reason; true marks an output that reached the token limit and forces that task to fail. The byte limit is a separate safety bound. No model was invoked, no training checkpoint or score was created, and no dependency installation or external download occurred as part of P2-01.

## Stop gates that remain

1. Do not create or inspect the final holdout until its full oracle is tested with known-good, deliberately broken, malformed, empty, timeout, and output-limit cases. The current unit suite covers those failure classes for the static evaluator and checks a known-good output for every development task; it does not provide a safe JavaScript behavior sandbox.
2. Review the P2-02 corpus before P2-03. The collected split is documentation-heavy and below the proposed code share; do not train on it as the preferred coding corpus without a reviewed data-mix decision.
3. Keep all training runs capped at 120 minutes, retain scratch initialization, and compare step-zero with trained Plex on the same versioned development tasks before any final-set decision.

The current environment detected Node.js on `PATH` and no browser executable by the names `msedge`, `chrome`, or `firefox`. This records only what the implementation environment could resolve; it is not an inventory of the owner's Windows installation.
