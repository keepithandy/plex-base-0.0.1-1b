# P2-16 CSS Edit Generalization Curriculum candidate v1

**Status: ready for owner review; training is not authorized.**

## Motivation

P2-15 answered an important diagnostic question. The 27.6M-parameter scratch Plex model learned all 24 supplied CSS request-to-code records exactly, including EOS, but scored 0/12 on four withheld semantic property families. P2-14 remained 0/12 and P2-01b remained 0/30. The transferable behavior observed outside the supplied examples was bounded completion/EOS, not semantic coding-task success.

P2-16 therefore changes the **curriculum diversity**, not the architecture or parameter count. The candidate is designed to separate literal memorization from interpolation, wording robustness, composition, and entirely unseen-family transfer.

## Hypothesis

If Plex is beginning to learn the reusable operation

```text
existing single-rule CSS
+ requested bounded transformation
-> complete updated CSS rule
```

then performance should first appear on easier interpolation tiers before appearing on composition or unseen property families.

## Candidate identity and counts

- Candidate: `p2-16-css-generalization-candidate-v1`
- Candidate JSONL SHA-256: `639c743acba94d62dfb0060aa4c172439354157ea4e940cb7643c2f83f45a2fc`
- Total records: **180**
- Training records: **120**
- Evaluation records: **60**
- Approval status: **pending-owner-review**
- External source text included: **no**
- Tokenizer fitted: **no**
- Checkpoint initialized: **no**
- Training run created: **no**
- Final holdout opened: **no**

### Training operation balance

| Operation | Records |
|---|---:|
| replace | 72 |
| add | 24 |
| remove | 24 |
| **Total** | **120** |

Each of the 12 training property families contributes 10 records: six replace operations, two add operations, and two remove operations.

## Training families

The 12 seen training families are:

- `background-color`
- `border-radius`
- `box-shadow`
- `font-size`
- `letter-spacing`
- `line-height`
- `margin-block-start`
- `max-width`
- `opacity`
- `outline-offset`
- `padding`
- `width`

The curriculum varies selector names, property values, units, declaration ordering, edited declaration position, unrelated declarations, operation type, and instruction wording. Every selector is unique across the full 180-record candidate.

## Evaluation tiers

### Tier A — same operation, unseen selector/value

**24 records: two per seen property family.**

Tier A intentionally reuses instruction templates that occurred in training while holding out every selector and the tested literal value. It asks whether the model can apply a familiar transformation pattern to new surface forms rather than repeat a stored selector/value pair.

Representative record `p2-16-css-121`:

```text
Starting CSS:
.p216-tier-a-border-radius-01 { margin-inline: auto; display: block; border-radius: 0; }

Requested edit: Change border-radius to 0.25rem and preserve every other declaration.
Return the complete updated CSS rule with no explanation.
```

Expected:

```css
.p216-tier-a-border-radius-01 { margin-inline: auto; display: block; border-radius: 0.25rem; }
```

### Tier B — same semantic operation, unseen wording

**12 records: one per seen property family.**

Tier B keeps the property family/operation primitive in-distribution but uses held-out paraphrase templates and held-out tested literal values. No Tier B instruction template appears in training.

Representative record `p2-16-css-145` asks for the familiar border-radius replacement through a held-out phrase: “The rule should now use …; make no other edits.”

### Tier C — seen primitives, unseen combination

**12 records.**

Tier C combines two independently trained edit primitives in one bounded single-rule request. Training contains only one primitive per record, so no two-operation composition appears in training.

Representative record `p2-16-css-157`:

```text
Starting CSS:
.p216-tier-c-compose-01 { cursor: pointer; border-radius: 1px; text-align: left; }

Requested edit: Make two bounded edits: set border-radius to 6px, and add margin-block-start: 2rem. Preserve every other declaration.
Return the complete updated CSS rule with no explanation.
```

Expected:

```css
.p216-tier-c-compose-01 { cursor: pointer; border-radius: 6px; text-align: left; margin-block-start: 2rem; }
```

### Tier D — entirely unseen property family

**12 records: three operations each across four unseen families.**

Held-out property families:

- `aspect-ratio`
- `list-style-type`
- `text-transform`
- `white-space`

Each family receives one replace, one add, and one remove task. These properties never appear as edit families in P2-16 training.

Representative record `p2-16-css-169` changes `white-space` from `normal` to `pre-wrap` while preserving two unrelated declarations.

## Leakage controls

The grouping rules are tier-aware because different tiers intentionally share different abstractions with training.

- **Global:** 180/180 unique record IDs, selectors, and requests.
- **Global:** no exact duplicate input/expected-output pair.
- **Literal transformation groups:** no exact property/operation/source/target primitive tuple is reused from training in any evaluation tier.
- **Tier A:** family and wording template may cross by design; selector and tested literal value may not.
- **Tier B:** family/operation may cross; wording template and tested literal value may not.
- **Tier C:** only individually seen families/operations may be composed; no composition record exists in training.
- **Tier D:** edited property families are completely disjoint from training.
- **Development sets:** no exact request overlaps P2-14 or P2-01b.
- **Final holdout:** never read or opened.

The lexical audit intentionally excludes Tier A from the unexpected-near-duplicate rejection threshold because Tier A is the deliberate same-wording interpolation test. Maximum normalized instruction Jaccard against training is:

| Tier | Maximum |
|---|---:|
| A | 1.000000 — intentional |
| B | 0.384615 |
| C | 0.500000 |
| D | 0.285714 |

The verifier rejects Tier B/C/D if maximum instruction Jaccard reaches 0.70.

Against the disclosed development prompts, the highest request-level word Jaccard is 0.394737 for P2-14 and 0.111111 for P2-01b, with zero exact request overlaps.

## Candidate verification

Run the read-only verifier from the repository root:

```powershell
uv run --project training --no-sync python training\phase2\verify_p2_16_css_generalization_candidate.py
```

The verifier is designed to fail if any of the following drift:

- candidate, training, tier, P2-14, or P2-01b SHA-256 identities;
- expected 120/60 split or A/B/C/D counts;
- training family or operation balance;
- record IDs, selectors, requests, or source/target uniqueness;
- tier-specific family/value/template separation;
- unexpected near-duplicate leakage;
- P2-14/P2-01b exact prompt overlap or excessive lexical similarity;
- deterministic application of add/replace/remove primitives;
- preservation of unrelated declarations;
- repository CSS static checker success for every authored expected output;
- pending approval metadata;
- no-tokenizer/no-checkpoint/no-training/no-final-holdout state inside the candidate package.

Passing this verifier is **not owner approval**.

## Scoring rules for a future approved run

Report every tier separately. Do not collapse A-D into one generalization score.

For each generated response:

1. **Syntax-valid** — the repository CSS parser reports `parseStatus == "pass"`.
2. **Complete-task pass** — syntax is valid, no Markdown fence is present, and `css_stylesheet_exact` matches the expected selector/declaration map exactly.
3. **Exact-string match** — `completion.strip() == expected.strip()`.
4. **EOS** — generation terminated by EOS before the generation budget.
5. **Generated token count** — count emitted completion tokens.

Also derive deterministic, non-exclusive failure flags:

- requested edit not applied;
- correct property but wrong value;
- unrelated declaration changed or removed;
- unexpected selector/declaration added;
- incomplete rule;
- malformed CSS;
- repeated fragment/declaration;
- copied input without applying the edit;
- premature EOS;
- no EOS.

A preservation failure means an input declaration not named by an edit primitive differs in the output. An unrelated-change failure means the output contains a selector or declaration not required by the expected complete rule.

## Existing development suites

Continue matched scoring against the unchanged development suites only:

- P2-14 constrained CSS edits: current baseline **0/12**.
- P2-01b HTML/CSS/JavaScript development set: current baseline **0/30**.

Do not train on either set. Do not place their prompts or trivial mutations into P2-16 training. The final owner-controlled holdout remains closed.

## Proposed first run — not authorized

The cleanest first comparison changes one major variable: **curriculum diversity**.

Proposed post-approval preparation/run policy:

- fresh tokenizer fitted on approved **training rows only**;
- no evaluation/development text used for tokenizer fitting;
- fresh random initialization, seed 1337;
- unchanged model architecture and parameter count;
- ordinary next-token loss over complete records;
- `complete-record-v1` sampling;
- micro batch 1;
- gradient accumulation 16;
- CUDA;
- matched step-zero evaluation;
- first ceiling: **100 updates / 10 minutes**;
- no automatic extension.

This intentionally keeps the P2-15 objective and first-run ceiling stable so the curriculum is the main experimental change. Before any run, the approved training rows still need a fresh tokenizer, context/generation budget inspection, and a prepared experiment bundle. If the larger curriculum cannot reach interpretable training performance within the proposed bound, report that rather than automatically extending it.

## Limitations

This is still a narrow single-rule CSS curriculum. Even strong Tier A-C performance would not establish HTML ability, JavaScript ability, repository editing, or general coding competence. Tier D is intentionally difficult and can remain at zero while easier tiers show meaningful reusable edit behavior.

The candidate is deliberately diagnostic. It is not designed to maximize a benchmark by contaminating P2-14 or P2-01b.

## Pinned hashes

- Candidate JSONL: `639c743acba94d62dfb0060aa4c172439354157ea4e940cb7643c2f83f45a2fc`
- Training rows: `50b3ccd2e7fad9e2b67d8886adb04dc15e76e5de06952b1df9870ae639ae6e59`
- Tier A: `1e1baa18bbe5ae0415ad3b57dccef40cdee56845469135d468048671f3f2c024`
- Tier B: `a096e1c0f837e7473355cb921ba8fbfd2c281ae10b95fa87f6fa0eace2f984b0`
- Tier C: `3c01756e11244cf68c3b1c6c765b4480daf248689c3e4181308e6f863a3cc515`
- Tier D: `f8f696f1213d83d0b45aea9a6cddd19a822363e6c8ef4b680b11aacf1d8ea460`
- P2-14 development set: `0527d9c93321bd34a5c065b23e7551dc9a4a8cc55adec49f04168a68f7e7166e`
- P2-01b development set: `e229dce9c55de36246b93fc9a7b3f2261bb21e2de2851d186906c68a28950ff4`

**Training remains blocked until the repository owner explicitly approves this exact candidate and a prepared run policy.**
