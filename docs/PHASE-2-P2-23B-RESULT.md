# P2-23b Target-Kind Continuation — Result

## Status

**Complete and closed at cumulative step 500.**

The approved P2-23b continuation resumed the existing P2-23 v1 step-100 checkpoint in four isolated +100-update CUDA increments and stopped at the authorized ceiling.

No automatic continuation beyond step 500 ran. The final project holdout remained closed.

## Preserved experiment identity

- training records: **144**
- evaluation records: **72**
- tokenizer SHA-256: `4a476b8671591da259fd0e7f5180c845726d22153e492b63b35cee445d88644a`
- parameters: **27,566,080**
- seed: **1337**
- objective: ordinary next-token complete-record training
- sampling policy: `complete-record-v1`
- micro-batch: **1**
- gradient accumulation: **16**
- optimizer, sampler, CPU/CUDA RNG continuation: preserved
- P2-14 excluded from gradients
- P2-01b excluded from gradients
- final project holdout: closed

## Learning curve

| Step | Supplied fit | Level A | Level B | Level C | Tier A | Tier B | Tier C | Held-out total | Validation loss | Recent loss |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 100 | 46/144 | 20/48 | 12/48 | 14/48 | 4/24 | 3/24 | 6/24 | 13/72 | 3.49394 | 0.33622 |
| 200 | 99/144 | 33/48 | 32/48 | 34/48 | 13/24 | 11/24 | 6/24 | 30/72 | 3.56998 | 0.11972 |
| 300 | 128/144 | 42/48 | 42/48 | 44/48 | 13/24 | 12/24 | 8/24 | 33/72 | 3.87601 | 0.08203 |
| 400 | 138/144 | 48/48 | 46/48 | 44/48 | 16/24 | 14/24 | 10/24 | 40/72 | 4.22473 | 0.06741 |
| 500 | **143/144** | **48/48** | **47/48** | **48/48** | **19/24** | **12/24** | **11/24** | **42/72** | **4.34508** | **0.06088** |

Six-way chance is **4/24 per tier**.

## Step-500 held-out target-kind results

Across the three 24-row held-out tiers, each target kind has 12 examples:

| Target kind | Exact /12 |
|---|---:|
| CSS_SELECTOR | **8** |
| CSS_PROPERTY | **5** |
| HTML_ELEMENT | **8** |
| HTML_ATTRIBUTE | **4** |
| JS_IDENTIFIER | **9** |
| JS_PROPERTY | **8** |

The remaining weakness is localized rather than uniform. **HTML_ATTRIBUTE** is the weakest class overall, and **CSS_PROPERTY** remains weak in repository-style Tier C language.

## Development sets

At step 500:

- P2-14: **0/12**
- P2-01b: **0/30**

These sets remained excluded from gradient training.

The result therefore establishes meaningful target-kind semantic transfer, not general coding-task completion.

## Optimization interpretation

Training continued to fit the supplied curriculum, reaching **143/144**, while recent training loss fell to about **0.06088**.

At the same time, validation loss rose from **3.49394** at step 100 to **4.34508** at step 500.

Held-out target-kind accuracy still improved over that interval, so the representation did learn useful semantics. However, the diverging loss curve and localized residual confusions do not justify simply extending the same run to step 600 or beyond.

## Architecture implication

P2-16 through P2-23b collectively support a narrower responsibility for the small Plex Base model:

**Plex Base should own**

- semantic normalization
- edit intent
- target kind
- target role
- language
- bounded search hints
- structured edit planning

**Deterministic Plex Code should own**

- repository search
- exact symbol / selector / property lookup
- current-state inspection
- INSERT / DELETE / REPLACE state transitions
- exact byte resolution
- file mutation
- validation
- unified diff generation

This boundary avoids forcing the 27.6M model to perform exact relational repository operations that the Phase 2 evidence has repeatedly shown to be unreliable.

## Decision

Close P2-23/P2-23b.

Do not continue the unchanged target-kind trajectory beyond step 500.

The final planned Phase 2 path is:

1. **P2-24 — Semantic Confusion Closure**
   - isolate the remaining CSS_PROPERTY and HTML_ATTRIBUTE confusions
   - test one bounded correction or representation change if evidence supports it
   - do not reopen deterministic exact-state responsibilities

2. **P2-25 — Structured Coding Bridge**
   - combine learned semantic fields into a compact structured edit plan
   - evaluate on unseen repository-style development requests
   - keep exact repository resolution deterministic

If P2-25 transfers well enough to support useful edit plans, close Phase 2 and begin P3-01.

The final project holdout remains closed.
