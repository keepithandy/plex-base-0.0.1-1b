# P1-20 — First scratch-training experiment report

**Status: complete.** This report records Plex's first bounded real-data training run, the one-step checkpoint continuation, and the first independently loaded CPU completion. Plex began from random weights; no pretrained model was loaded. The experiment validates the local training and checkpoint path. It does not show that Plex can reliably write working code.

## Result at a glance

The 27.6-million-parameter Plex model trained for the full two-hour limit on 34 training records. It processed 357,433,344 sampled token positions over 43,632 optimizer updates. Held-out next-token loss fell from **9.33937** before training to **6.53100** afterward, a 30.07% reduction in that loss value. A separate evaluation reproduced the final loss.

The training loss reached 0.02910, far below the held-out loss. The small training set and different source types make memorization and weak transfer likely explanations, though this experiment cannot separate those effects. On CPU, Plex generated a short continuation from a JavaScript prompt, but the result was incomplete and did not implement the requested function correctly. Plex has not passed a coding benchmark or functional code test.

## Data and tokenizer

The experiment used the owner-approved, local starter corpus built in P1-14. The two source groups remained separate between training and validation.

| Split | Source group and content | Records | Packed tokens |
|---|---|---:|---:|
| Training | Microsoft Web Dev for Beginners: mostly lessons and explanations, with HTML, CSS, and JavaScript examples | 34 | 147,948 |
| Held-out validation | Brad Traversy's 50 Projects in 50 Days: HTML, CSS, and JavaScript project code | 54 | 18,394 |

The corpus package occupies 746,848 bytes. Plex's byte-level BPE tokenizer was fitted on training text only. It has 9,976 learned token IDs within the model's 16,384-ID capacity. The tokenizer package occupies 1,039,201 bytes. Original MIT notices and source provenance are retained. See the [source review](DATASET-SOURCE-REVIEW.md) and [tokenizer report](PLEX-TOKENIZER.md) for selected files, hashes, and scope.

The 357 million training positions count repeated, randomly sampled context windows. They are not 357 million unique source tokens. The model saw the same small set of material many times. The validation file contains 18,394 tokens; the recorded loss used 35 full batches, or 17,920 target positions.

## Model and training settings

P1-16 created the initial checkpoint from random weights with seed 1337 and scheme `plex-normal-0.02-v1`. The model is a decoder-only Transformer with six layers, width 512, eight attention heads, a 2,048-wide feed-forward layer, 512-token context, and 0.1 dropout. It has 27,566,080 parameters. Training used FP32 AdamW with learning rate 0.0003, betas (0.9, 0.95), weight decay 0.1, micro-batch one, and gradient accumulation 16. The P1-18 run used a constant learning rate and stopped at its 120-minute limit.

The initial checkpoint SHA-256 is `7a06c575ba229cfbdf758cad6ae7d0c4e504236eeba1dd90c9d531ca4689c7b4`. Its initialization record says `pretrainedCheckpointLoaded: false`. Qwen was not used; it remains only a possible future evaluation baseline.

## Hardware and software

The owner-provided Windows hardware inventory lists an Intel Core i9-14900KF with 32 logical processors, 31.7 GiB of RAM, and an NVIDIA GeForce RTX 4080 SUPER with 16,376 MiB of VRAM. The collection snapshot showed 14,532 MiB free; that value changes as applications use the GPU. At pilot start, the runner reported 15,540,944,896 bytes free on the GPU.

The run used Python 3.12.10, PyTorch 2.14.0+cu126, and CUDA 12.6 on Windows. Peak GPU allocation was 801,311,232 bytes (about 764.5 MiB), and peak reservation was 878,706,688 bytes (about 838 MiB). Peak process working set was 1,397,129,216 bytes (about 1.30 GiB). The original training checkpoint is 330,897,883 bytes. The owner allocated 200 GiB for Plex artifacts; this run remained within that limit. CPU model inference was checked later in P1-19, but CPU latency and memory targets have not been measured.

## P1-18 two-hour pilot

| Measurement | Result |
|---|---:|
| Run duration | 7,200.018 seconds |
| Optimizer updates | 43,632 |
| Sampled training token positions | 357,433,344 |
| Reported throughput | 49,643.40 positions/second |
| Recent mean training loss | 0.0291038 |
| Held-out loss before training | 9.3393699 |
| Held-out loss after training | 6.5309965 |
| Independent held-out evaluation | 6.5309965 over 35 batches / 17,920 targets |
| Interrupted | No |
| Checkpoint SHA-256 | `8f00c895637a4062037f7a49fb7fdaf1193771243c3727bdd9b9059da93a1298` |

The held-out loss fell by 2.80837. This shows the trained checkpoint predicted this particular held-out split better than the untrained initialization under the same evaluation procedure. It does not mean Plex is 30% more accurate: cross-entropy loss is not an accuracy percentage. The training/validation difference is large, and the validation set comes from a separate source group with a different content mix.

An earlier `p1-18-full-v1` attempt stopped after about 393 seconds and 1,400 updates without producing a final report. Its cause was not identified. The completed `p1-18-full-v2` run is the result reported here. See the [P1-18 run record](PLEX-PILOT.md).

## P1-19 resume and CPU completion

P1-19 resumed the completed pilot for one CUDA optimizer update. The new checkpoint advanced from step 43,632 to 43,633, processed 8,192 more positions, and preserved the original checkpoint. Its held-out loss changed from 6.5309965 to 6.5306513; independent evaluation matched. One update is only a checkpoint-continuity check, not a meaningful quality improvement.

The new checkpoint is 330,899,291 bytes, with SHA-256 `f0313ffd8a1c8c68066057a97cac062de9e641b185f9bbdb02bffc03d29f489f`. It records model weights, AdamW state, CPU/CUDA and sampling RNG states, the constant learning-rate schedule, training settings, step and token progress, tokenizer and dataset identities, and scratch-initialization provenance. A verified tokenizer bundle is copied beside it. The original P1-18 checkpoint's hash remains unchanged.

A separate CPU process loaded this checkpoint and tokenizer and generated 32 tokens from `function add(a, b) {`:

```javascript
function add(a, b) { return Math.max(a, Math.min(b, v)); }
  function clamp01(v) { return clamp(v, 0, 1
```

This is a plausible-looking continuation assembled from familiar web-code patterns, but it references the wrong variables and ends mid-expression. It is not a correct implementation of `add`. The sample confirms that the saved weights and tokenizer can generate locally on CPU; it also shows that the model does not yet reliably follow the prompt or produce complete, correct code. See the [P1-19 resume and completion report](PLEX-RESUME-AND-COMPLETION.md).

## Failures and limits

- The first P1-18 attempt ended early without a final report; the reason is unknown. The second attempt completed the full bound and supplies the reported results.
- The first real P1-19 continuation exposed a CUDA RNG restore error: `torch.load(..., map_location="cuda")` moved RNG state tensors to the GPU, while PyTorch's CUDA generator requires CPU byte tensors. The runner now returns these states to CPU before restoring them. A CUDA regression check and the successful real continuation cover the fix.
- PyTorch printed a warning that NumPy is not installed. It did not prevent training, evaluation, checkpointing, or generation; no dependency was installed for this experiment.
- The corpus contains only 34 training and 54 held-out records. Training is mostly explanatory text, while validation is code from a different source group. This makes the measured loss useful for checking the pipeline but weak evidence about performance on new coding tasks.
- No generated sample was run through unit tests, a browser, or a functional correctness benchmark. No CPU speed or memory target was set. No longer or uncapped training run was started.

## Conclusion and next decision

P1-20 records that Plex can train from random initialization, lower next-token loss on the approved held-out split, save a full training state, resume it for an additional update, and load the resulting checkpoint for CPU text generation. The completion sample is incorrect, so the experiment does not demonstrate useful coding ability.

The next quality decision should be based on broader reviewed training and validation sources, with multiple source groups represented on both sides and functional checks for generated HTML, CSS, and JavaScript. Keep the current 120-minute training cap until the data mixture and evaluation plan are reviewed. The P1-19 gate passed technically, but the present results do not justify scaling training on this same small corpus.
