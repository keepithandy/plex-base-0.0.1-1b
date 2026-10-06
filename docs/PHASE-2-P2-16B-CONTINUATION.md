# P2-16b Optimization Continuation

## Approval

The repository owner approved continuation of the existing P2-16 step-100 checkpoint through cumulative step 500.

P2-16b changes **cumulative optimization only**.

It preserves:

- the same 120 P2-16 training records;
- the same 60 P2-16 evaluation records;
- tokenizer SHA-256 \`1b0494e0e56bc904dfc94c1d9a571eefca82e20f78276632191514b69421b7a0\`;
- the 27,566,080-parameter architecture;
- the existing AdamW optimizer state;
- the existing seed/RNG trajectory;
- ordinary next-token loss;
- \`complete-record-v1\`;
- micro-batch 1;
- gradient accumulation 16;
- CUDA;
- the existing P2-16 A-D, P2-14 and P2-01b scoring rules.

The continuation schedule is fixed:

\`\`\`text
step 100 source checkpoint
  -> +100 -> score step 200
  -> +100 -> score step 300
  -> +100 -> score step 400
  -> +100 -> score step 500
\`\`\`

No automatic continuation beyond cumulative step 500 is authorized. P2-14 and P2-01b remain excluded from gradient training. The final holdout remains closed.

## Runtime source gate

The step-100 model checkpoint is a local artifact, so the committed runner verifies it at runtime rather than pretending GitHub stores its bytes.

Before any continuation update, the runner requires:

- the prepared P2-16 bundle still passes \`verify_prepared\`;
- the local source run is the completed P2-16 approved experiment;
- the source result is step 100 and was not interrupted;
- candidate, tokenizer, dataset and parameter-count identities match the approved values;
- the actual checkpoint SHA-256 matches the checkpoint hash stored in \`trained-candidate-score.json\`;
- the checkpoint retains optimizer state;
- the checkpoint retains sampling, CPU and CUDA RNG state;
- its sampler is still \`complete-record-v1\`;
- its seed remains 1337.

Each +100 increment uses the repository's existing isolated \`resume_pilot\` path. That path verifies resume compatibility before performing an optimizer update and preserves the prior source checkpoint unchanged.

## Run command

After pulling the merged P2-16b continuation changes:

\`\`\`powershell
uv run --project training --no-sync python training\phase2\run_p2_16b_continuation.py \`
  --prepared training\artifacts\experiments\p2-16-css-generalization-prepared-v1 \`
  --source-run training\artifacts\experiments\p2-16-css-generalization-run-v1 \`
  --output-dir training\artifacts\experiments\p2-16b-optimization-continuation-v1
\`\`\`

The runner has no CLI option to request more than the four approved increments.

## Scoring

At cumulative steps 200, 300, 400 and 500 the runner records:

- supplied training complete-task passes;
- training syntax-valid count;
- Tier A-D complete-task passes;
- Tier A-D syntax-valid counts;
- P2-14 complete passes;
- P2-01b complete passes and language breakdown;
- validation loss before/after each increment;
- mean recent training loss;
- token progress;
- checkpoint SHA-256.

The step-100 source result is included as the first point in the final learning curve.

## Decision rule after step 500

Do not automatically continue.

Use the measured learning curve to decide whether:

1. exact supplied-task fit is still rising and additional optimization is scientifically justified;
2. Tier A/B exact passes begin to emerge, supporting interpolation/wording transfer;
3. training converges while A-D remain zero, supporting a curriculum/representation change rather than more compute;
4. optimization stalls or validation loss reverses, supporting an earlier stop or revised objective.

The final holdout remains reserved for a later frozen-model evaluation.
