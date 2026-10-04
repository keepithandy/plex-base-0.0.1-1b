# P1-15 — Plex tokenizer report

P1-15 is complete for the approved starter corpus. Plex's tokenizer was fitted locally from scratch using only the `text` fields in the 34 training records. Validation text, source paths, provenance fields, and external tokenizer checkpoints were excluded from fitting. Both splits were encoded afterward; encoding validation text does not fit or update the tokenizer.

The implementation uses the pinned [Tokenizers 0.23.2 library](https://pypi.org/project/tokenizers/0.23.2/) and its [BPE trainer API](https://github.com/huggingface/tokenizers/tree/v0.23.2). This is a tokenizer implementation dependency, not pretrained data or model weights. Its installation and lock file are part of this milestone. No model training, paid service, new dataset download, or pretrained checkpoint loading took place.

## Settings

| Setting | Value |
|---|---|
| Codec | `plex-byte-bpe-v1` |
| Algorithm | Byte-level BPE |
| Requested vocabulary limit | 16,384 |
| Actual vocabulary, including special tokens | **9,976** |
| Model vocabulary capacity | **16,384**, unchanged |
| Minimum merge frequency | 2 |
| Initial byte alphabet | All 256 byte values |
| Normalization | None; preserve input exactly |
| Prefix space | Disabled |
| Byte-level regex splitting | Enabled |
| PAD / UNK / BOS / EOS IDs | 0 / 1 / 2 / 3 |
| Automatic BOS/PAD/EOS | None |
| Packed record boundary | Append one EOS (ID 3) per record |
| Literal control marker strings | Encode as ordinary text, never as control IDs |

The starter training split does not supply enough repeated pairs to reach the requested vocabulary limit at frequency 2. A smaller learned vocabulary is valid; it does not change the 27,566,080-parameter model configuration. Later model integration must mask unused vocabulary IDs during generation. The complete byte alphabet represents unseen valid Unicode text without UNK. Tokenization performs no new text normalization; the curated dataset's earlier normalization remains documented in its source manifest.

## Results

| Split | Records | UTF-8 text bytes | Packed tokens, including EOS | Bytes per text token, excluding EOS |
|---|---:|---:|---:|---:|
| Training | 34 | 638,548 | **147,948** | 4.3170 |
| Validation | 54 | 53,373 | **18,394** | 2.9102 |

All 88 complete records decoded exactly. Seven additional samples covered HTML, CSS, JavaScript, ordinary prose, indentation/tabs/trailing spaces, CRLF/newlines, emoji and several scripts, combining characters, escaped strings, empty text, and literal control marker spellings. The saved tokenizer was reopened and checked. A second build in a separate Python process produced all **11 bundle files byte-identically**.

The primary local bundle is `training/artifacts/tokenizers/p1-15-starter-v1/`. It occupies **1,039,201 bytes** (about 0.99 MiB), including both original MIT notices and the source manifest. A separate verification bundle is in `p1-15-starter-v1-repro/`. Both count against the 200 GiB allocation. Generated bundles are ignored by Git; implementation, pinned dependencies, instructions, and this result record are tracked.

The bundle contains:

- `tokenizer.json`: learned vocabulary, merges, byte pretokenizer, and decoder.
- `tokenizer-config.json`: vocabulary sizes, settings, special IDs, fitting input hash, library version, and tokenizer hash.
- `model-config.json`: the unchanged P1-12 model configuration.
- `manifest.json`: codec, split token counts/hashes, roundtrip counts, source and model hashes.
- `train.tokens.u16le` and `validation.tokens.u16le`: little-endian unsigned 16-bit IDs, one EOS after each record.
- `train.index.json` and `validation.index.json`: record IDs and token offsets/counts, including EOS.
- `source-dataset-manifest.json` and `licenses/`: reviewed provenance and the original notices.

| Artifact/input | SHA-256 |
|---|---|
| Training JSONL | `40996f243ec7fa786db49effd92cbebea441bdf7be9de59dacec335f517070dd` |
| Validation JSONL | `2348e634efd165e3151a604f3180e09236be9510659a76e70f13e7717813d2f2` |
| Source dataset manifest | `58845cbc9251c0c33d5f2980d8b47d28dccb05638d68ac572a5841cdf96c8fcc` |
| Tokenizer JSON | `76491cb4fb4e452ece1808159126ac78dc154901bd49b1d95870c0ba57ad503e` |
| Model configuration | `0179591365be51ddac2feebb8767c19916084629e9a3a51b553d1bb0d62d00b0` |
| Training token file | `008a1633b15bc27882fdbc5917d644299cabfdd439f4c0f03dee2f34c36cad4e` |
| Validation token file | `9c55bfc7ff2afe049c87e191a516cae4820e7b3e588048ffea11cc9ec0435c38` |
| Tokenizer bundle manifest | `cb69621fcebd585f79d48207cecb1306a45c7418080d31c6c76e308956647e70` |

## Reproduce in PowerShell

From the repository root, sync the pinned environment and select a fresh output directory. The existing primary bundle is already built; it will not be overwritten.

```powershell
uv sync --project training --locked
uv run --project training --no-sync python -m plex_training.cli tokenizer-train `
  --dataset-dir training\artifacts\datasets\p1-14-starter-v1 `
  --output-dir tokenizers\p1-15-my-rebuild
```

Use another fresh output name if that directory already exists. The input dataset must first exist; its [source/build review](DATASET-SOURCE-REVIEW.md) explains how to reconstruct the approved corpus. This command does not fetch sources. Optional `--vocab-size` (260–16,384) and `--min-frequency` settings change the experiment; retain the defaults to reproduce these hashes.

Output stays beneath `training/artifacts` by default. The command validates reviewed sources, original license hashes, record content hashes, complete split hashes/counts, and separate groups/content. It refuses existing outputs and publishes the bundle only after all checks pass. It streams records with bounded line/sample sizes and enforces remaining storage across the artifact root, with a maximum 200 GiB allocation.

```powershell
uv run --project training --no-sync python -m unittest discover -s training/tests -v
```

All **35 training-workspace tests pass**, including deterministic builds, changed validation text leaving the learned vocabulary unchanged, code/Unicode/control-marker roundtrips, packed EOS/index checks, source and license integrity, group leakage rejection, storage cleanup, no overwrite, local reload hashes, and protection against mixing BPE tokens with the bootstrap runner. Independent checks reopened the primary bundle, decoded all 88 indexed packed records with the saved tokenizer, and verified adjacent next-token pairs and valid IDs in 512-token windows from both splits. Python compilation, offline dependency-lock consistency, and `git diff --check` passed. The existing missing-NumPy warning remains nonfatal.

## Next milestone and limits

P1-16 has since created fresh step-zero random weights linked to this tokenizer; see the [initialization report](PLEX-INITIALIZATION.md). The current `train`, `evaluate`, and `generate` runner still uses the earlier `byte-v1` checkpoint format. It rejects these BPE corpora rather than saving a misleading byte checkpoint. Keep the synthetic smoke checkpoint as a historical resource test; it cannot resume into this tokenizer's different token meanings.

P1-17's tiny real-text learning check is complete; see the [learning report](PLEX-LEARNING-CHECK.md). The two-hour pilot remains P1-18 and needs a general bounded BPE training/evaluation path using the held-out validation split. Complete tokenizer-aware checkpoint/resume/generation in P1-19 before longer runs. The tokenizer milestone proves faithful encoding and reproducibility, not coding ability. Training is mostly explanations and validation mostly web code, so the different compression rates reflect a small, uneven starter mixture. Broader reviewed data and model quality remain future work.
