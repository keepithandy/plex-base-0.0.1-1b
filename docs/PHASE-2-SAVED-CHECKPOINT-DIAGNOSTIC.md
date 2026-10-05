# P2-02: saved-checkpoint prompt-to-answer diagnostic

This is a read-only inference check of the two existing 100-step Plex checkpoints against the **owner-approved 234-example v3 candidate**. It uses the same prompt construction, greedy decoding, seed, and per-language token caps as the development-task generator. It separates the 156 examples included in training from the 78 held-out corpus validation examples. It does **not** score the owner-authored 30-task development set again, open the final holdout, train, download data, or execute generated JavaScript.

The [diagnostic script](../training/phase2/diagnose_saved_checkpoints.py) verifies the candidate's approval and SHA-256, dataset manifest provenance, tokenizer compatibility, scratch initialization, and checkpoint identity. [The local report](../training/artifacts/diagnostics/p2-v3-saved-checkpoints-v2/report.json) contains the response text and per-example result. Exact target means the generated text equals the training target (leading newline and code) and stops at EOS. Code-only exact ignores surrounding whitespace but still requires EOS. Static pass means language syntax, no Markdown fence, and every example-specific assertion pass; JavaScript receives Node `--check` syntax parsing only. Those static assertions are narrower than behavioral correctness.

| Saved checkpoint, 100 steps | Approved training examples: exact / static / syntax | Corpus validation examples: exact / static / syntax | Truncated |
|---|---:|---:|---:|
| Ordinary next-token loss | 0 / 0 / 11 of 156 | 0 / 0 / 6 of 78 | 0 of 234 |
| Answer-weight 4 | 0 / 0 / 42 of 156 | 0 / 0 / 18 of 78 | 0 of 234 |

None of the reference answers exceeds its language's generation cap. The weighted checkpoint increased syntax passes, especially on CSS, but did not produce a complete static pass even on a training prompt. For example, the ordinary model's **training** prompt asking for `<ruby>Kyoto<rt>Kyo-to</rt></ruby>` produced `<ruby>Kyoto</rt>Kyoto</rt>Kyoto</rt>`. A **validation** request for an abbreviation produced a ruby fragment instead. The weighted model generated a similarly malformed ruby fragment for the training prompt, and its CSS outputs often repeated unrelated selectors or declarations. These are representative examples, not a substitute for the full counts above.

The candidates are not owner-authored benchmark tasks. Zero exact matches alone would be a stringent text-match result, but zero full static passes and the inspected responses show that these 100-step checkpoints have **not yet reliably learned even supplied answers** under greedy prompting. There is therefore no evidence here of a separately measurable generalization gap. Falling held-out next-token loss and correct EOS timing did not establish usable request-to-code behavior. A two-hour continuation remains unjustified.

## One bounded next change

Prepare a **three-example overfit probe**, one already-approved training example per language, with the existing tokenizer and the same scratch initialization. Cap it at 200 optimizer steps and ten minutes, save a separate checkpoint, and check exact completion and the existing static assertions on each of those three prompts after the run. This is a pipeline diagnostic, not a capability benchmark: if it cannot learn three seen examples, inspect loss targeting, prompt boundaries, and generation before expanding data or runtime. If it can, resume planning broader data and a measured training schedule, while continuing to evaluate on the development set and keeping the final holdout closed. The [completed follow-up probe](PHASE-2-THREE-EXAMPLE-PROBE-REPORT.md) learned all three supplied answers exactly; the larger-corpus question remains open.

The approved candidate SHA-256 is `555fc619d041b3f5138207c1513ca2169b4d704d35daba2f1e1cc800360c0016`; the dataset manifest is `bc3725297473733c69fa6c87546f22dc843eacb0879a486f3e307dc391c760ea`. Ordinary and weighted checkpoint SHA-256 values are `b2d4b7a3e35affe398b2e269f7b2dd7f1d9d86e528f2d2d8148d7a887e2620eb` and `6e7542cc1d68abe55ee510e8ca443b55a115c9a4b68fa86fba2bda8e288401e3`. CUDA ran on the user's local GPU; the familiar missing-NumPy PyTorch warning did not prevent inference. The saved JSON report is an ignored local artifact, so reproduce it with the command below if it is absent in another checkout:

```powershell
uv run --project training --no-sync python training\phase2\diagnose_saved_checkpoints.py `
  --candidate training\phase2\drafts\p2-02-request-following-v3\candidate.jsonl `
  --approval training\phase2\approvals\p2-02-request-following-v3.json `
  --task-set training\phase2\evaluation\p2-01b-dev-v1.json `
  --bundle training\artifacts\tokenizers\p2-request-following-v3 `
  --checkpoint training\artifacts\pilot\p2-request-following-100step-v3\pilot-checkpoint.pt `
  --checkpoint training\artifacts\pilot\p2-request-following-answer4-100step-v1\pilot-checkpoint.pt `
  --output training\artifacts\diagnostics\p2-v3-saved-checkpoints-recheck `
  --device cuda
```

Choose a fresh `--output` directory for each run; overwrite is refused. Use `--device cpu` if CUDA is unavailable.
