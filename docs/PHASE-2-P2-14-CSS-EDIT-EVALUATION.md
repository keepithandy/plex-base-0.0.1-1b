# P2-14 CSS edit development evaluation

Date: 2026-10-05

Status: **read-only development evaluation complete; 0/12 complete CSS edits at both checkpoints**

## Result

The existing P2-12 step-zero initialization and step-200 checkpoint were scored on a new hash-pinned 12-task development set. Each task supplied one existing flat CSS rule, requested a narrow edit, and required both requested declarations and exact preservation of the complete resulting rule. This is static development evidence only; the owner-authored final holdout remains unopened.

| Checkpoint | Complete edits | Partial checks | Truncated responses | Interpretation |
|---|---:|---:|---:|---|
| Step-zero initialization | 0/12 | 12/78 evaluator checks (only `noMarkdownFence`) | 12/12 | Outputs were largely malformed or repetitive token fragments; all reached the 128-token cap. |
| P2-12 step 200 | 0/12 | 12/68 evaluator checks (only `noMarkdownFence`) | 2/12 | Outputs were short continuations such as `.actions`, `.conactions`, or repeated `.actions`; none contained the requested complete CSS rule. |

The token-level response files are retained in ignored local experiment artifacts. The checkpoint metadata records tokenizer SHA-256 `a7f87c63ded6e6c1803d356a0e1a3899834426d6588ac3196f65c70510795573` for both checkpoints, matching the selected `p2-request-following-v3` bundle. This rules out a tokenizer-bundle mismatch as the cause of the observed fragments. The trained checkpoint was not fine-tuned on these requests, and no optimizer or runtime validation-loss path was used.

This result shows that the 95/96 selector-copy result does not transfer to these constrained code edits. It does not establish broad CSS ability or inability: this is a small, Codex-authored development set, and outputs were not executed in a browser. Do not train on this set or use it to claim a final benchmark result. A future training candidate requires its own review, candidate identity, and hash approval.

## Pinned identities

- Development task-set SHA-256: `0527d9c93321bd34a5c065b23e7551dc9a4a8cc55adec49f04168a68f7e7166e`
- Step-zero initialization checkpoint SHA-256: `0aa2153a3cb33a146fca91fda7c7c3c54ba5c7b94d7f1a43d2371547700724c7`
- Step-zero responses SHA-256: `bf4353fbddcec7a8ccfef0ec3a4e8ec3e19483c08f179a19608de520a6d6bf85`
- Step-200 checkpoint SHA-256: `e1e6821eaf5af2bfb9ddb0de7031790dc96e6d0e8f706bb4521d005219736065`
- Step-200 responses SHA-256: `7eabf3850df2bfee793079b3ccbee4edd00632bc8df92c9d0b83b9e4b087686d`
- Tasks: 12 single-rule CSS edits; exact whole-rule declaration maps checked
- Training and validation loss: not run
- Final holdout opened: **no**

The generated responses and score JSON files are ignored local artifacts under `training/artifacts/experiments/p2-14-css-edit-step0-v1/` and `training/artifacts/experiments/p2-14-css-edit-step200-v1/`.

## Next step

Do not extend or tune the step-200 checkpoint based on the 95/96 selector-copy result. Use this outcome to guide a new, separately reviewed request-to-code candidate if further model training is desired. Before any such run, inspect whether its examples teach complete request-to-code behavior, approve and hash-pin the candidate and tokenizer, and define a matched step-zero comparison. Keep the P2-14 development set disclosed, and retain a separately authored, owner-controlled final set outside training and iteration.
