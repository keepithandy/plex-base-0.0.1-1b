# P2-03: approved binding-diversity comparison

Recorded October 5, 2026. **Both bounded runs are complete. The varied arm reproduced 20/24 supplied answers, but both arms passed 0/12 new binding requests, 0/12 previously reserved transfer requests, and 0/30 development tasks.** Adding these variations improved learning of the supplied examples without demonstrating successful completion on new requests at 100 updates. P2-03 remains active; a two-hour run remains deferred.

## Approval and prepared inputs

The owner approved: “Approve the 24 binding-diversity examples for local diagnostic training.” The [approval record](../training/phase2/approvals/p2-03-binding-diversity-v1.json) pins the exact candidate and evaluation hashes and permits the reviewed original-only/varied comparison, capped at 100 updates and ten minutes per arm. Its scope is local diagnostic training, with no public license grant. The twelve new evaluation examples remain excluded from training.

The [review](PHASE-2-BINDING-CANDIDATE-REVIEW.md) describes six original anchors plus eighteen variations: words in HTML `bdi`, progress values, CSS selectors and gaps, and JavaScript function names. They contain no external source text. The original draft files retain their historical pending-review labels and unchanged bytes; the separate approval record authorizes their exact content.

The [preparer](../training/phase2/prepare_binding_experiment.py) built distinct, verified datasets and tokenizer bundles under [p2-binding-v1](../training/artifacts/experiments/p2-binding-v1/experiment.json):

| Prepared input | Original-only | Varied |
|---|---:|---:|
| Training records | 6 | 24 |
| Records per operation | 1 | 4 |
| Packed training tokens, including record EOS | 520 | 2,162 |
| Same-family evaluation records | 12 | 12 |
| Packed evaluation tokens | 1,113 | 1,113 |

Both arms use byte-identical evaluation text and tokens. Their tokenizer/model/config assets were copied unchanged from the approved broad v3 bundle: 1,509 learned entries within capacity 16,384. No tokenizer was fitted on the new examples or evaluation text. Bundle metadata explicitly records the original tokenizer fitting corpus and the distinct current dataset identities. Standard dataset/checkpoint compatibility checks remain enforced. Each complete record fits the unchanged 512-token context.

## Matched run and accounting

The [runner](../training/phase2/run_binding_experiment.py) completed both arms on CUDA. Both started at step zero with seed 1337, the 27,566,080-parameter model, and exactly equal parameter tensors. The original scratch checkpoint and both new initializations were loaded safely on CPU and compared with `torch.equal` before training and again during independent verification. No pretrained checkpoint or pretrained model weights were loaded. Checkpoint file hashes differ because arm metadata differs; file hashes are not evidence of tensor equality.

Both used ordinary complete-record next-token loss over prompt, answer and EOS, AdamW with constant learning rate 0.0003, betas 0.9/0.95, epsilon 1e-8, weight decay 0.1, gradient clipping 1, dropout 0.1, microbatch 1 and accumulation 16. Greedy inference retained the development prompt template, seed 1337 and language-specific generation caps. Only installed tools were used; there were no downloads, installations, paid services, security-setting changes or automatic run extensions.

| Training measure | Original-only | Varied |
|---|---:|---:|
| Optimizer updates | 100 | 100 |
| Sampled complete records | 1,600 | 1,600 |
| Real next-token targets | 137,283 | 142,741 |
| Elapsed training seconds | 14.31 | 14.11 |
| Mean recent training loss | 0.02977 | 0.06636 |
| New-binding packed text loss before | 7.45870 | 7.45870 |
| New-binding packed text loss after | 2.46776 | 2.26458 |
| Peak GPU reserved bytes | 819,986,432 | 822,083,584 |

Uniform record sampling gives each of the six operations equal probability in both arms because each operation has the same number of records within its arm. Sampler replay independently matched the real target totals. The realized operation counts were identical: HTML word 249, HTML progress 272, CSS border 276, CSS layout 247, JavaScript division 275 and array copy 281. Every varied record was selected 55–83 times. Nevertheless, token lengths, per-record exposure and dropout draws differ. The varied arm processed 5,458 more real targets, about 4%; this is a fixed-update diagnostic rather than a perfectly equal token-budget experiment.

Packed text loss is a secondary next-token measure on the twelve same-family new bindings, including their prompts. It is neither the earlier family-separated corpus validation nor a complete-task capability score.

## Completion results

| Evaluated requests | Original-only | Varied |
|---|---:|---:|
| Six original anchors: exact/static complete passes | 6/6 | 6/6 |
| Eighteen added variations: exact/static complete passes | 0/18, unseen in this arm | 14/18, trained in this arm |
| Twelve reserved transfer requests: complete passes | 0/12 | 0/12 |
| Twelve new evaluation bindings: complete passes | 0/12 | 0/12 |
| Thirty development tasks: complete passes | 0/30 | 0/30 |
| Development static assertions passed | 41/151 | 50/151 |

The varied arm learned 20/24 training answers exactly: HTML 7/8, CSS 5/8 and JavaScript 8/8. Its four incorrect seen answers substituted another taught detail:

- Progress value 18 produced value 47.
- Selector `.notice-edge` produced `.banner-edge`.
- Toolbar gap 6px produced the original 12px.
- Toolbar gap 14px produced 28px.

On new requests, Riga produced Seoul, Tallinn produced Lisbon, and progress value 27 produced 47. Neither arm passed a requested-binding check on either transfer set. Syntax passes rose from 4/12 to 9/12 on reserved transfer and from 3/12 to 9/12 on new transfer. These partial improvements do not establish correct answers. Both arms had zero empty or truncated diagnostic/development outputs.

The varied arm has not learned all its supplied answers, so its transfer failure cannot establish that diversity is ineffective after convergence. The small, selected six-operation scope also cannot establish general model limitations. HTML/CSS checks are static; installed Node parses JavaScript with `--check`, and generated code is never executed. Safe JavaScript behavior and browser-backed checks remain outstanding. The final 60-task holdout is unbuilt and was not used.

## Artifacts and verification

The saved [comparison.json](../training/artifacts/experiments/p2-binding-run-v1/comparison.json) contains both run reports, source identities, sampler exposure and aggregate scores. Each arm has its own saved initialization, checkpoint, metrics, completion score, development responses, manifest and score:

- Original-only: [diagnostic completions](../training/artifacts/experiments/p2-binding-run-v1/original-only/completion-score.json), [development score](../training/artifacts/experiments/p2-binding-run-v1/original-only/development/score.json).
- Varied: [diagnostic completions](../training/artifacts/experiments/p2-binding-run-v1/varied/completion-score.json), [development score](../training/artifacts/experiments/p2-binding-run-v1/varied/development/score.json).

| Identity | SHA-256 |
|---|---|
| Approved 24-record candidate | `8f3fc7dfc21c4ebb5ce5b40391e9b123521d13df50b2d349e5d6b7c3faf37c2f` |
| Twelve evaluation-only records | `ea8699efc997c0b4a5cdeb55c0da1d5be1b0d27a8ae9ad6b5164476c0d82ca7c` |
| Frozen tokenizer | `a7f87c63ded6e6c1803d356a0e1a3899834426d6588ac3196f65c70510795573` |
| Preserved original scratch initialization | `d0294311bbc852dbc882017e0426274b379af4ece73caa612c9ed9e23c56c4d5` |
| Prepared experiment manifest | `9517826e5938a98eff32080e9614dac574f9ae2e0b82455c07a27aa935bf0140` |
| Original-only trained checkpoint | `1495681ae1c5b882a9087b657836033618e0dab4d98e10e68c9f27a5705121e2` |
| Varied trained checkpoint | `4d185752e0c08bb647bb1e8bcb5174816a606ea5f0520113f8edb12585bd69b7` |

Three focused experiment tests passed: hard bounds, rejection of trained/pretrained/different starting parameters, and exact two-arm preparation with identical held-out inputs, tamper rejection and overwrite protection. The real CUDA run verified the full preparation/initialization/training/inference/scoring path. Independent verification checked all prepared texts and token IDs against approved records, rechecked initial tensor equality and checkpoint hashes, rescored all 96 diagnostic completions consistently, and matched provenance for both 30-response development runs. Python syntax, documentation links and Git whitespace were also checked. The older 116-test full-suite result belongs to the prior continuation; it is not a new result for this experiment.

The existing environment emitted the missing-NumPy warning, but both runs completed and their checkpoints were independently loaded. Windows Application Control had blocked an earlier attempt in the project history; no such block prevented this run.

## Reproduction and next step

The owner does not need to repeat these completed runs. If reproducing, choose unused paths under `training/artifacts`; both scripts refuse overwrite. From the repository root:

```powershell
uv run --project training --no-sync python training\phase2\prepare_binding_experiment.py --output training\artifacts\experiments\p2-binding-my-inputs
uv run --project training --no-sync python training\phase2\run_binding_experiment.py `
  --prepared training\artifacts\experiments\p2-binding-my-inputs `
  --output-dir training\artifacts\experiments\p2-binding-my-run `
  --steps 100 --minutes 10 --device cuda
```

**Next: prepare an answer-focused loss comparison using these same approved 24 examples and complete-record context.** Keep prompt tokens available to the model, but compare the ordinary objective with loss applied to answer/EOS targets only. Retain the scratch starting weights, tokenizer, optimizer, update cap and unchanged evaluation sets. This is a proposed configuration investigation, not an implemented command or a scheduled run. The earlier four-times-answer-weight experiment used packed windows on the broad corpus, so it does not answer this complete-record, small-corpus question. Check supplied-answer learning before interpreting future transfer failures; record objective and real/supervised target accounting explicitly.

This recommendation follows the observed substitutions and incomplete learning; it does not promise that a different loss will solve them. No extra examples or new source approval are needed to prepare that comparison. P2-02 remains complete at pilot scope, P2-03 remains active, and P2-04 longer training remains deferred.
