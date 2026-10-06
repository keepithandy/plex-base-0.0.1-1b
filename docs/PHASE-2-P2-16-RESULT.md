# P2-16 CSS Generalization Result

## Status

The first owner-approved P2-16 run completed on CUDA at the authorized 100-update ceiling.

This was a fresh seed-1337, 27,566,080-parameter Plex model trained from scratch on the approved 120-record P2-16 training partition with a tokenizer fitted on training only. The 60 P2-16 evaluation records, P2-14, P2-01b and the final holdout were excluded from gradient training.

## Source identity

- Candidate: \`p2-16-css-generalization-candidate-v1\`
- Candidate SHA-256: \`639c743acba94d62dfb0060aa4c172439354157ea4e940cb7643c2f83f45a2fc\`
- Tokenizer SHA-256: \`1b0494e0e56bc904dfc94c1d9a571eefca82e20f78276632191514b69421b7a0\`
- Actual tokenizer vocabulary: 717
- Train records: 120
- Evaluation records: 60
- Train JSONL SHA-256: \`ac48d07ab0b39edd1e810fa551be571e6f0d1d653cccce9120fc6121d4ee7ea1\`
- Validation JSONL SHA-256: \`c92d6248fc954e23fb7c22e364864656ea73185b91296245fa888420e7a5e540\`

## Step-100 task result

| Set | Complete passes | Syntax-valid | EOS |
|---|---:|---:|---:|
| Training | 3/120 | 45/120 | 120/120 |
| Tier A | 0/24 | 19/24 | 24/24 |
| Tier B | 0/12 | 6/12 | 12/12 |
| Tier C | 0/12 | 4/12 | 12/12 |
| Tier D | 0/12 | 3/12 | 12/12 |
| P2-14 | 0/12 | — | — |
| P2-01b | 0/30 | — | 30/30 |

The step-zero checkpoint passed 0 complete tasks in every set and produced malformed CSS throughout P2-16. The trained checkpoint therefore learned bounded output behavior and materially increased CSS syntax validity, but it did not yet produce a complete held-out edit.

## Optimization state

- Step: 100
- Steps in run: 100
- Interrupted: false
- Elapsed training time: 15.710425399942324 seconds
- Tokens processed: 225,764
- Mean recent training loss: 0.32886304398998617
- Validation loss before: 6.716460253063001
- Validation loss after: 3.3871124669125208
- Learning rate: 0.0003, constant-v1
- Sampling: complete-record-v1
- Micro-batch: 1
- Gradient accumulation: 16

Validation loss fell by about 49.6%, while complete training-task fit reached only 3/120. That combination means the 100-update run stopped while the larger P2-16 curriculum was still underfit.

## Interpretation

P2-16 does **not** establish semantic generalization at step 100 because Tier A-D complete-task passes remained zero.

It also does **not** support the stronger conclusion that the curriculum cannot generalize. Unlike P2-15, the supplied training set did not converge. The correct interpretation is that the first 100 updates produced substantial format/syntax learning and lower held-out next-token loss, but were insufficient to determine whether exact edit behavior emerges later in the same optimization trajectory.

The owner therefore approved P2-16b: a controlled continuation of this exact step-100 checkpoint through cumulative step 500 in four isolated +100-update increments, with matched scoring at steps 200, 300, 400 and 500.

The final owner-controlled holdout remains closed.
