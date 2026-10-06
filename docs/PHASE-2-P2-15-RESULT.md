# P2-15 CSS edit diagnostic result

P2-15 completed the approved bounded CUDA run from a fresh seed-1337 initialization.

The local result artifact is:

`training/artifacts/experiments/p2-15-css-edit-run-v1/result.json`

The run reached the approved step limit and was not extended.

## Fixed experiment identity

- Experiment: `p2-15-promoted-css-edit-v1`
- Candidate: `p2-15-css-edit-candidate-v1`
- Candidate SHA-256: `e9ca83c92a40abd0575db708bd67d2e4ce6888d97bc31ef4a38938a050dfd6cf`
- Tokenizer SHA-256: `9af6bcda7b6087c0d17dd9ad85e7b2f8818633f78952335ca6d57b1081cec1f6`
- Initialization checkpoint SHA-256: `0ecc0aaf8e497509cf93d0c0043ef59360b09eabcfb8ba9e5f75e4561b54b94a`
- Initial model weights SHA-256: `ed64bae104034a8d219400f8d66819d3475a875e22f2c6dc86447661b48aa276`
- P2-14 development set SHA-256: `0527d9c93321bd34a5c065b23e7551dc9a4a8cc55adec49f04168a68f7e7166e`
- P2-01b development set SHA-256: `e229dce9c55de36246b93fc9a7b3f2261bb21e2de2851d186906c68a28950ff4`
- Maximum approved updates: 100
- Maximum approved duration: 10 minutes
- Sampling policy: `complete-record-v1`
- Loss objective: ordinary next-token loss over complete records
- Final owner-controlled holdout opened: **no**

## Supplied P2-15 training examples

| Measurement | Step zero | After training |
|---|---:|---:|
| Complete-task passes | 0/24 | **24/24** |
| Exact-string matches | 0/24 | **24/24** |
| EOS | 0/24 | **24/24** |
| No EOS | 24/24 | **0/24** |
| Generated tokens | 3072 | 544 |

The supplied training partition reached complete convergence under the experiment's scoring rule.

This demonstrates that the current 27.6M-parameter scratch Plex model can fit the supplied prompt-to-code mappings under this setup. It does **not** establish general CSS or coding ability.

## Withheld semantic-family validation

| Measurement | Step zero | After training |
|---|---:|---:|
| Complete-task passes | 0/12 | **0/12** |
| Exact-string matches | 0/12 | 0/12 |
| EOS | 0/12 | **12/12** |
| No EOS | 12/12 | **0/12** |
| Generated tokens | 1536 | 364 |

Because the supplied training partition reached 24/24, the 0/12 validation result is interpretable: P2-15 did not demonstrate semantic-family transfer to the four property families withheld from training.

## Existing development suites

### P2-14 constrained CSS edits

- Step zero: 0/12
- After P2-15: 0/12
- Delta: 0

The P2-15 curriculum therefore did not transfer to the existing P2-14 constrained CSS edit set.

### P2-01b 30-task development set

- Step zero: 0/30
- After P2-15: 0/30
- CSS EOS after training: 10/10
- HTML EOS after training: 10/10
- JavaScript EOS after training: 10/10

No P2-01b task became a complete pass. The transferable behavior was **bounded completion / EOS behavior across CSS, HTML, and JavaScript**. This is behavioral-format transfer, not coding-task generalization.

## Interpretation

P2-15 successfully establishes four narrow facts:

1. optimization works under the promoted setup;
2. the tiny model can fit these supplied prompt-to-code examples exactly;
3. it can learn correct answer termination on those examples;
4. EOS behavior can transfer beyond the supplied CSS records.

P2-15 does **not** establish:

- semantic edit generalization;
- unseen CSS property-family generalization;
- HTML editing ability;
- JavaScript editing ability;
- repository editing ability;
- general coding competence.

The immediate bottleneck is therefore more consistent with **curriculum diversity and abstraction** than with inability to fit the training examples. Training the same 24 examples for more steps is not justified by this result because those examples are already at 24/24 exact.

## Next experiment

Proceed to **P2-16 — CSS Edit Generalization Curriculum** at candidate/review stage. P2-16 should separate:

- interpolation to unseen selectors/values;
- robustness to unseen instruction wording;
- composition of seen edit primitives;
- transfer to entirely unseen property families.

Do not increase model size, change architecture, open the final holdout, or start P2-16 training before explicit owner approval.
