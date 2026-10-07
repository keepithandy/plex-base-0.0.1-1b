# Plex Web pretraining workspace

This directory is the control surface for Plex's HTML/CSS/JavaScript domain-pretraining program.

## Current milestone

**P2-26 — Plex Web Corpus v1 (active).**

P2-25 is closed. The ingestion path now has source/license preflight, deterministic grouped corpus building, reproducibility evidence, and a mandatory contamination gate.

P2-26 expands the reviewed source pool toward the first meaningful corpus. No large corpus is stored in Git and no pretraining starts in this milestone.

## Pipeline

```text
approved source
    ↓
license/provenance gate
    ↓
HTML/CSS/JS file gate
    ↓
quality + secret/generated/minified filters
    ↓
hashing + deduplication
    ↓
repository-grouped train/validation split
    ↓
contamination check
    ↓
immutable corpus manifest/shards
    ↓
training-only tokenizer
    ↓
scratch domain pretraining
```

## Corpus ladder

- Plex Web 1M — pipeline validation
- Plex Web 10M — tokenizer/training behavior
- Plex Web 100M — meaningful pretraining experiment
- Plex Web Large — 500M+ candidate after earlier gates

## Important rules

- Publicly visible code is **not** automatically approved training data.
- Unknown or ambiguous licenses are rejected by default.
- Source provenance must survive every transformation.
- Repository families stay in one split.
- Protected Phase 2 development/evaluation content must not leak into pretraining.
- Gated dataset terms must be accepted by the repository owner directly, not by automation.
- The first pilot keeps the current 27.6M architecture.

See:

- [P2-24 specification](../../docs/PHASE-2-P2-24-WEB-PRETRAINING-SPEC.md)
- [source policy](source-policy.json)


## Verify reviewed local sources

Copy `source-manifest.example.json` to a working manifest beside your local source snapshots, replace the placeholders with pinned provenance/license information, then run:

```powershell
uv run --project training --no-sync python -m plex_training.cli web-source-verify `
  --source-manifest training\pretraining\sources.local.json
```

The verifier is read-only. It does not copy files or train the model.

It rejects sources outside the committed license allowlist and filters candidate HTML/CSS/JavaScript files for:

- disallowed paths such as `node_modules`, vendor/build output and caches
- minified suffixes
- generated-file markers
- binary/invalid UTF-8
- known credential/secret patterns
- exact normalized duplicates

At least two independent repository/source groups are required so later train/validation splitting can remain leak-resistant.

P2-25 is complete. See [the closeout](../../docs/PHASE-2-P2-25-CLOSEOUT.md).

## P2-26 — build the first larger corpus

The reviewed candidate pool lives at:

```text
training/pretraining/p2-26-source-candidates.json
```

Materialize the pinned sources and generate the local source manifest:

```powershell
uv run --project training --no-sync python -m plex_training.cli web-source-materialize
```

Then verify the materialized source set:

```powershell
uv run --project training --no-sync python -m plex_training.cli web-source-verify `
  --source-manifest training\pretraining\sources.p2-26.local.json
```

Build a fresh grouped corpus candidate:

```powershell
uv run --project training --no-sync python -m plex_training.cli dataset-build `
  --source-manifest training\pretraining\sources.p2-26.local.json `
  --output-dir datasets\p2-26-web-1m-candidate-v1 `
  --validation-percent 20 `
  --seed 1337
```

Before promotion, require a clean contamination report:

```powershell
uv run --project training --no-sync python -m plex_training.cli web-contamination-check `
  --dataset-dir training\artifacts\datasets\p2-26-web-1m-candidate-v1
```

A missing or failing contamination report blocks tokenizer fitting and pretraining.

The first byte-scale target is roughly **4–6 MiB of accepted normalized HTML/CSS/JavaScript**. Exact token count waits for P2-27 tokenizer review.

See [P2-26 Plex Web Corpus v1](../../docs/PHASE-2-P2-26-WEB-CORPUS-V1.md).

## P2-26 source batch #2

Batch #2 is recorded in:

```text
training/pretraining/p2-26-source-batch-2.json
```

It contains four CC0-1.0 MDN example repositories plus two MIT repositories. Pinned-tree screening estimates **5,849,962 eligible bytes / 3,322 eligible files** before Plex content filtering. The four MDN repositories share one source-family group to prevent related-example leakage across train/validation.

Materialize batch #2:

```powershell
uv run --project training --no-sync python -m plex_training.cli web-source-materialize `
  --registry training\pretraining\p2-26-source-batch-2.json `
  --manifest-output training\pretraining\sources.p2-26-batch-2.local.json
```

Verify it:

```powershell
uv run --project training --no-sync python -m plex_training.cli web-source-verify `
  --source-manifest training\pretraining\sources.p2-26-batch-2.local.json
```

Do not assume the 5.85 MB estimate survives filtering. `web-source-verify` is authoritative.

See [P2-26 source batch #2](../../docs/PHASE-2-P2-26-SOURCE-BATCH-2.md).

## Plex Web build parity

Use `web-dataset-build` for P2-26 and later Plex Web corpora. The older generic `dataset-build` command is retained for non-Web training workflows, but it does not apply the full Plex Web minified/disallowed-suffix policy.

```powershell
uv run --project training --no-sync python -m plex_training.cli web-dataset-build `
  --source-manifest training\pretraining\sources.p2-26-batch-2.local.json `
  --output-dir datasets\p2-26-web-batch-2-v2 `
  --validation-percent 20 `
  --seed 1337
```

The Web builder first runs the normal source verifier, captures its exact accepted paths, and then permits the dataset builder to read only those paths. The dataset builder may still reject a verified JavaScript file if Node syntax validation fails; it may never reintroduce a path rejected by the Web verifier.


## P2-26 closeout and P2-27 tokenizer review

P2-26 is complete. The corrected verifier-locked batch #2 corpus contains **3,140 records** (**3,071 train / 69 validation**) from **5,463,479 accepted normalized source bytes**. Its dataset manifest SHA-256 is:

```text
2f02f199d101050c9939df6d389851e46bbd858157cb68d7cb8cc75863178a91
```

The contamination report passed with zero blocked origins, zero exact protected matches, and zero long-substring matches. The final project holdout remained closed.

P2-27 is now active. Run the fresh train-only tokenizer comparison with:

```powershell
uv run --project training --no-sync python -m plex_training.cli tokenizer-review `
  --dataset-dir training\artifacts\datasets\p2-26-web-batch-2-v2 `
  --output-dir tokenizer-reviews\p2-27-web-v1 `
  --vocab-sizes 4096 8192 12288 16384 `
  --min-frequency 2
```

This command fits tokenizer candidates only. It does **not** initialize or train model weights, and it does not open the final holdout.

See [P2-26 closeout](../../docs/PHASE-2-P2-26-CLOSEOUT.md) and [P2-27 tokenizer review](../../docs/PHASE-2-P2-27-TOKENIZER-REVIEW.md).


## P2-27 closeout and P2-28 initialization gate

P2-27 is complete. The owner selected the **16,384-token** candidate.

Frozen identities:

```text
dataset manifest:
2f02f199d101050c9939df6d389851e46bbd858157cb68d7cb8cc75863178a91

tokenizer:
2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697

tokenizer review:
3d462afedf7ae2bae33407f4db4f7ab6b53c2dc46c70bec891c95707a4046db8
```

Machine-readable selection:

`training/pretraining/p2-27-tokenizer-selection.json`

P2-28 is active at the fresh-random-initialization gate. The exact machine-readable contract is:

`training/pretraining/p2-28-scratch-pilot-contract.json`

Authorized initialization command:

```powershell
uv run --project training --no-sync python -m plex_training.cli initialize `
  --tokenizer-dir training\artifacts\tokenizer-reviews\p2-27-web-v1\candidates\vocab-16384 `
  --output-dir initializations\p2-28-web-v1-step0 `
  --seed 1337
```

This creates a step-zero checkpoint only. **Do not start training yet.** First verify the initialization output reports 27,566,080 parameters, vocabulary 16,384, seed 1337, `pretrainedCheckpointLoaded: false`, and both checkpoint/initial-weight hashes.

See [P2-27 result](../../docs/PHASE-2-P2-27-RESULT.md) and [P2-28 contract](../../docs/PHASE-2-P2-28-SCRATCH-PRETRAINING-PILOT.md).


## P2-28 verified initialization and first training authorization

The step-zero initialization passed:

```text
checkpoint:
06c27a452e2a62ed069729d2080b1d2fddb84d41bd336bbda489c066c23f8a86

initial weights:
98785d70ee7f68fcfde35ad6136bb3be05ff562374f0bdede2faae93cb80a193

tokenizer:
2d5102623cf8e8e51925ab5e6ea05716221013538c5b661476aa1ea765af2697
```

One bounded training run is now authorized:

```powershell
uv run --project training --no-sync python -m plex_training.cli pilot `
  --bundle-dir training\artifacts\tokenizer-reviews\p2-27-web-v1\candidates\vocab-16384 `
  --initialization training\artifacts\initializations\p2-28-web-v1-step0\initialization.pt `
  --output-dir pilot\p2-28-web-v1-100step `
  --minutes 10 `
  --steps 100 `
  --device cuda `
  --micro-batch 1 `
  --gradient-accumulation 16 `
  --checkpoint-every-minutes 5
```

Do not resume or extend this run until its report is reviewed.

Machine-readable records:

- `p2-28-initialization-result.json`
- `p2-28-training-contract.json`
