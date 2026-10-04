# P1-19 — Save, resume, and complete

**Status: technical gate complete.** A bounded CUDA continuation resumed the completed P1-18 scratch-trained checkpoint by one optimizer update, preserved the original pilot, and saved a new checkpoint with its tokenizer bundle. Independent held-out evaluation matched the resumed checkpoint's report. A separate CPU process loaded that checkpoint and generated text with Plex's own BPE tokenizer. This proves the save/resume/completion path, not useful coding ability.

## Verified continuation

The source is the completed [P1-18 pilot](PLEX-PILOT.md) at `training/artifacts/pilot/p1-18-full-v2/pilot-checkpoint.pt`. `pilot-resume` verifies the reviewed tokenizer and separate train/validation corpus identities, the scratch initialization record, the saved optimizer and random-generator state, and the fixed training policy. The original P1-18 checkpoint predates explicit `trainingSettings` and `scheduleState` fields; the resume path accepts it only with that pilot's known batch, validation, and AdamW settings. New checkpoints record those fields explicitly. The continuation writes to a fresh directory and does not modify its source checkpoint.

| Measurement | Verified result |
|---|---:|
| Source step | 43,632 |
| Source checkpoint SHA-256 | `8f00c895637a4062037f7a49fb7fdaf1193771243c3727bdd9b9059da93a1298` |
| Additional CUDA optimizer updates | 1 |
| New checkpoint step | 43,633 |
| Token positions in the continuation | 8,192 |
| Total sampled training token positions | 357,441,536 |
| Held-out loss before continuation | 6.530996513366699 |
| Held-out loss after continuation | 6.530651337759835 |
| Independent held-out evaluation | 6.530651337759835 |
| New checkpoint size | 330,899,291 bytes |
| New checkpoint SHA-256 | `f0313ffd8a1c8c68066057a97cac062de9e641b185f9bbdb02bffc03d29f489f` |

The ignored output is `training/artifacts/pilot/p1-19-resume-v2/`. It contains `resumed-checkpoint.pt`, `resume-report.json`, `metrics.jsonl`, and a copied `tokenizer/` bundle. The new checkpoint records Plex model weights, AdamW state, CPU/CUDA and sampling RNG states, the constant `3e-4` learning-rate schedule (`constant-v1`), immutable training settings, step and total token positions, scratch-initialization provenance, and tokenizer/dataset identities. The tokenizer files accompany the checkpoint as a checked sidecar bundle; they are not model weights. The original P1-18 pilot checkpoint remains intact, with its SHA-256 unchanged at `8f00c895637a4062037f7a49fb7fdaf1193771243c3727bdd9b9059da93a1298`.

The small reduction in held-out loss is a one-update continuity observation, not a new quality result. The tiny, uneven starter corpus still shows a large training/validation gap and needs broader reviewed data and stronger coding evaluations.

## Independent completion

`complete` loads the saved model and matching tokenizer bundle in a new process. It encodes a nonempty prompt with Plex's BPE tokenizer, limits each generation context to 512 tokens, masks PAD/UNK/BOS and all IDs outside the learned 9,976-token vocabulary, stops at EOS, and decodes the result. Generation is bounded to at most 256 new tokens. Temperature `0` uses greedy decoding; positive temperatures use a seeded local generator. A supplied `--bundle-dir` must match the checkpoint's tokenizer identity; otherwise the command defaults to the `tokenizer/` sidecar next to the checkpoint.

The separate CPU command generated 32 tokens from `function add(a, b) {`. Its completion began:

```text
 return Math.max(a, Math.min(b, v)); }
  function clamp01(v) { return clamp(v, 0, 1
```

This is incomplete and does not correctly implement the requested function. It demonstrates loading and decoding saved Plex weights on CPU; it does not establish useful code generation or measured CPU latency and memory requirements.

## Reproduce from the repository root

The verified resume directory already exists. Use a **new** output path to repeat the bounded check; the command refuses to overwrite existing results. It adds at most 100 steps and is capped at ten minutes. These commands use the already locked local environment and download nothing:

```powershell
uv run --project training --no-sync python -m plex_training.cli pilot-resume `
  --checkpoint training\artifacts\pilot\p1-18-full-v2\pilot-checkpoint.pt `
  --output-dir pilot\p1-19-my-resume `
  --minutes 10 --steps 1 --device cuda
```

To independently recheck the existing resumed checkpoint on CUDA using its packaged tokenizer, then generate with that checkpoint on CPU:

```powershell
uv run --project training --no-sync python -m plex_training.cli pilot-evaluate `
  --bundle-dir training\artifacts\pilot\p1-19-resume-v2\tokenizer `
  --checkpoint training\artifacts\pilot\p1-19-resume-v2\resumed-checkpoint.pt `
  --device cuda
uv run --project training --no-sync python -m plex_training.cli complete `
  --checkpoint training\artifacts\pilot\p1-19-resume-v2\resumed-checkpoint.pt `
  --prompt 'function add(a, b) {' `
  --max-new-tokens 32 --temperature 0 --device cpu
```

The existing tokenizer corpus and checkpoint remain under the owner's 200 GiB artifact allocation. The general `train`, `evaluate`, and `generate` commands still serve the older `byte-v1` plumbing path. P1-19 adds `pilot-resume` and `complete` for the reviewed BPE pilot.

## Verification and next step

The P1-19 training-workspace suite passed **46 tests**, including an exact CPU comparison of uninterrupted two-step BPE training with a one-step run followed by one-step resumption, rejection of changed batch/accumulation and schedule settings, output-overwrite checks, and deterministic generation with masking/EOS behavior. The real one-step CUDA continuation passed its report checks, the new checkpoint hash matched, and independent held-out evaluation reproduced the final loss. The CUDA RNG restoration path was corrected so a checkpoint loaded onto CUDA can restore saved device RNG state.

The technical P1-19 gate has passed, but uncapped longer training remains unavailable in the CLI and is not recommended on this small corpus. The [P1-20 experiment report](PLEX-EXPERIMENT-REPORT-P1-20.md) now records the data, training history, held-out results, sample output, and failure analysis. Plan broader reviewed data and functional evaluation before considering a longer run.
