# P2-23 Target-Kind Classification Candidate Review

## Status

**Candidate only. Pending owner review.**

No tokenizer fitting, checkpoint initialization, training run, or model training is authorized by this candidate.

Candidate:

`p2-23-target-kind-classification-candidate-v1`

Candidate SHA-256:

`3625f43419c185b567ae0d6849860f3e310016fc9dcc5bf6bc53afa6363d1d08`

Training rows SHA-256:

`f51cf7808a8b37a9fe60513401117efd81d0c28c10fe1a0ab154dc5724af45e7`

## Research question

Can the existing 27.6M Plex Base learn another **flat semantic normalization primitive**:

> Given a repository-edit request, what kind of source construct is being acted on?

P2-23 deliberately avoids exact repository strings, before/after state reasoning, byte lookup, patch generation, and deterministic resolution.

Those remain outside this candidate.

## Legal model outputs

```text
CSS_SELECTOR
CSS_PROPERTY
HTML_ELEMENT
HTML_ATTRIBUTE
JS_IDENTIFIER
JS_PROPERTY
```

The simple six-way chance expectation is **4/24 = 16.7% per held-out tier**.

## Dataset

216 total records:

- 144 training
- 72 evaluation-only

Each semantic band contains:

- 48 training
- 24 evaluation-only

Every target kind appears:

- 8 times in training per level
- 4 times in evaluation per tier
- 24 times in training overall
- 12 times in evaluation overall

### Level / Tier A — direct target-kind paraphrases

Clean semantic descriptions of one source-construct category.

The model classifies whether the target is a CSS matcher, CSS declaration field, HTML node type, HTML field, JavaScript declaration-level symbol, or JavaScript object member.

### Level / Tier B — minimal contrasts

Matched six-way contrasts under a shared semantic context.

The group context is held constant while the described target kind changes.

- 8 training contrast groups
- 4 evaluation contrast groups
- no train/evaluation context reuse

### Level / Tier C — repository-style target language

Repository-flavored CSS/HTML/JavaScript requests without requiring exact source literals.

The model still outputs only one canonical target-kind label.

- 8 training contrast groups
- 4 evaluation contrast groups
- no train/evaluation context reuse

## Integrity audit

- 216 unique requests
- train/evaluation exact request overlap: **0**
- B/C train/evaluation context overlap: **0**
- same-target-kind train/evaluation near-duplicates at word-Jaccard >= 0.65: **0**

### Prior-task audit

| Prior set | Exact overlap | Max word-Jaccard |
|---|---:|---:|
| P2-22c | 0 | 0.264151 |
| P2-22 | 0 | 0.375000 |
| P2-21 | 0 | 0.433333 |
| P2-20 | 0 | 0.222222 |
| P2-19 | 0 | 0.156863 |
| P2-18 | 0 | 0.151515 |
| P2-17 | 0 | 0.131148 |
| P2-14 | 0 | 0.118644 |
| P2-01b | 0 | 0.128205 |

The highest prior-task similarity is P2-21 at 0.433333, well below the candidate's 0.65 near-duplicate threshold.

## Why these six labels

The split is intentionally language- and structure-specific enough to be useful to Plex Code while remaining a flat classification problem:

```text
CSS_SELECTOR   -> stylesheet rule matcher
CSS_PROPERTY   -> stylesheet declaration field name
HTML_ELEMENT   -> markup tag / node type
HTML_ATTRIBUTE -> named field attached to a markup element
JS_IDENTIFIER  -> declaration-level JavaScript symbol name
JS_PROPERTY    -> JavaScript object/member key
```

This directly tests three important pairwise distinctions:

- CSS_SELECTOR vs CSS_PROPERTY
- HTML_ELEMENT vs HTML_ATTRIBUTE
- JS_IDENTIFIER vs JS_PROPERTY

Those are structurally useful distinctions for later deterministic repository resolution.

## Relation to P2-22c

P2-22c showed that explicit presence transitions did not solve INSERT/DELETE directionality in the current model.

P2-23 therefore does **not** ask Plex to reason over relational before/after state.

It returns to the kind of flat semantic category task where Plex has shown useful transfer.

## Candidate hashes

```text
candidate:
3625f43419c185b567ae0d6849860f3e310016fc9dcc5bf6bc53afa6363d1d08

training:
f51cf7808a8b37a9fe60513401117efd81d0c28c10fe1a0ab154dc5724af45e7

Tier A:
6157b1e41f98a9e2b30a660deae8ae712a7a910fe1d991f0653c8918e00ce3d6

Tier B:
1d194209d6813a4ff58876ee2103194985fa973eb925992ae1b45599d67678f8

Tier C:
bf1a195e2bbbd0b0325cc1de31fdb7a1d817045abdbda07d107082500129a01a
```

## Approval gate

Do not:

- fit a P2-23 tokenizer;
- initialize a P2-23 checkpoint;
- train P2-23;
- reuse P2-23 evaluation records for tokenizer fitting;
- use P2-23 evaluation records for gradients;
- open the final project holdout;

until the repository owner reviews the candidate and explicitly authorizes a bounded run policy.
