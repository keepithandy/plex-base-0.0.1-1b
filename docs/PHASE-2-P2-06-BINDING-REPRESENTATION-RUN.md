# P2-06: binding-representation run

Status: approved bounded diagnostic.

## Why this exists

P2-05 showed that Plex can perfectly fit the six supplied selector-gap combinations in every fold, yet only 1/9 fold-local held-out combinations composed correctly. Syntax remained 9/9, selector binding was more stable than gap binding, and six held-out outputs replayed a training solution.

P2-06 separates three capabilities that P2-05 mixed together:

1. preserve one requested binding under alternate wording,
2. preserve two requested bindings simultaneously,
3. compose those same two bindings into CSS.

Each level uses a fresh seed-1337 scratch model. No level continues training from another.

## Exact approved identities

### Level 1 — single-copy

- train SHA-256: `13452867b30a38b9ffc3e42ef440d3ac560c3103d5d479d014525eae10a12727`
- evaluation SHA-256: `9cf9777c431de134f880eb152d84794af9f848e69f25a36420c605bcc6a144c8`
- 6 training records
- 6 evaluation records

The same three selectors and three gaps appear in training and evaluation, but evaluation uses alternate request wording. This is a basic prompt-bound copying/instruction-transfer probe, not a novel-value holdout.

### Level 2 — dual-binding

- train SHA-256: `856f20637a3bd42e0b6838964503a3aaf74a86af3a0d464128194f9ab3c6aabb`
- evaluation SHA-256: `e3afa59441365fd2a88089704755f5b9fbb9b27f88804416616272283c5d5399`
- 6 training records
- 3 held-out selector-gap combinations

Output is exactly two labeled lines. CSS generation is intentionally absent.

### Level 3 — CSS composition

- train SHA-256: `a84de00032d543a4b2bc9e9d67ef0bea5ef2cc94b080ea862f37179253b1ec6b`
- evaluation SHA-256: `969ca23edf91ff9175e9ac502395a5aa850b541c3392843e20aa82b38eb56dee`
- 6 training records
- 3 held-out selector-gap combinations

The binding split is identical to Level 2. Only the answer task changes from labeled binding preservation to full CSS composition.

## Controlled settings

All three levels use:

- fresh random Plex initialization,
- seed `1337`,
- frozen P2 tokenizer,
- answer/EOS-only complete-record supervision,
- microbatch `1`,
- gradient accumulation `16`,
- at most `100` optimizer updates,
- at most `10` minutes,
- existing P2 request-following validation data for runtime loss telemetry,
- no P2-06 evaluation rows in gradient training or runtime validation loss,
- no automatic extension,
- final project holdout closed.

Total authorized ceiling is 300 updates / 30 minutes across the three fresh models.

## Interpretation gate

A level is interpretable only if it first gets all six supplied training examples correct under its representation-pass measure.

After all three levels converge on their supplied examples:

- Level 1 evaluation < 6/6 → basic single-binding copy or wording-transfer bottleneck.
- Level 1 = 6/6, Level 2 < 3/3 → simultaneous independent-binding bottleneck.
- Levels 1 and 2 pass, Level 3 < 3/3 → code-composition bottleneck after bindings were preserved.
- All three pass → representation ladder passed; investigate broader distribution/capacity effects rather than basic binding representation alone.

## Local commands

Prepare immutable experiment inputs:

```powershell
uv run --project training --no-sync python training\phase2\prepare_binding_representation_experiment.py `
  --output training\artifacts\experiments\p2-06-binding-representation-inputs-v1
```

Run all three fresh-model levels:

```powershell
uv run --project training --no-sync python training\phase2\run_binding_representation_experiment.py `
  --prepared training\artifacts\experiments\p2-06-binding-representation-inputs-v1 `
  --output-dir training\artifacts\experiments\p2-06-binding-representation-run-v1 `
  --steps 100 --minutes 10 --device cuda
```

The final summary is written to:

`training/artifacts/experiments/p2-06-binding-representation-run-v1/result.json`

Record-level completions for each level are also written under that level's output directory.

## Scope

This remains a tiny CSS-domain diagnostic. It is not evidence of broad HTML/CSS/JavaScript generalization and does not authorize a larger model, longer training schedule, or final-holdout access.
