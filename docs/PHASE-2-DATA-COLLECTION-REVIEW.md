# Phase 2 data collection review

**Status: source collection and tokenizer preparation complete; the P2-01 development-only evaluator is now prepared; no P2 model training has started.** This record captures the approved small MDN selection, the exact previously approved Microsoft P1-14 subset re-split by project, and the resulting P2-02 data artifacts. P1 data, tokenizer, checkpoints, and experiment reports remain unchanged.

## Recorded decisions

For this collection, the owner approved:

- A path-by-path review of MDN's `learning-area` family and a small selection from the pinned snapshot below.
- Re-splitting the exact 34-content-file Microsoft P1-14 subset by project group into P2 training and development.
- Using 30 development tasks and 60 final tasks (10/20 each for HTML, CSS, and JavaScript), plus “majority of final tasks in every language and meaningful improvement over step-zero,” as the starting evaluation gate.
- Setting the numeric gate to at least 11/20 tasks passed per language and at least +10 percentage points overall over matching step-zero.

The 30-task static development set and response-generation/scoring commands are recorded in the [evaluation design](PHASE-2-EVALUATION-DESIGN.md). The final task set and a JavaScript behavior sandbox are not present yet.

## Source snapshots

The committed [P2 source lock](../training/phase2/dataset-source-lock.json) pins every selected path, byte length, and upstream Git blob SHA-1 (lock SHA-256 `4e211856af770cff42e62695edb11d6734b41963e6f561899024709958b3d74b`). The [P2 catalog](../training/phase2/dataset-sources.phase2-v1.json) records local source roots, license evidence, approval, source families, and split-group rules (catalog SHA-256 `a2ddb2b699925d84de13ccf2772e1fe61a8edd84d17d856746a77c3a92a35c3f`). The raw snapshots are ignored by Git and can be verified or restored with:

```powershell
uv run --project training python -m plex_training.source_fetch `
  --plan training\phase2\dataset-source-lock.json
```

Both snapshots were fetched and then re-verified against the lock. The fetcher reported `alreadyVerified: true` for each on the second pass. Their combined pinned download size is 657,484 bytes, including both license files.

### Microsoft Web Dev for Beginners

- Repository: [microsoft/Web-Dev-For-Beginners](https://github.com/microsoft/Web-Dev-For-Beginners)
- Commit: `78085398be0dea7abaaf5eda914817f46f6ddbbc`
- License: the pinned [MIT license file](https://github.com/microsoft/Web-Dev-For-Beginners/blob/78085398be0dea7abaaf5eda914817f46f6ddbbc/LICENSE) (1,162 bytes; Git blob `3d8b93bc7987d14c848448c089e2ae15311380d7`) is retained.
- Selection: the exact 34 content files already approved for P1-14, plus that license file. No P1 file or historical output was edited.
- Project groups: `2-js-basics`, `3-terrarium`, `4-typing-game`, `6-space-game`, and `7-bank-project`.

### MDN `learning-area`

- Repository: [mdn/learning-area](https://github.com/mdn/learning-area)
- Commit: `dbed6bcb8284634c7549c4da596ec30b0cfc6e7e`
- License: the pinned [CC0 1.0 license file](https://github.com/mdn/learning-area/blob/dbed6bcb8284634c7549c4da596ec30b0cfc6e7e/LICENSE) (6,555 bytes; Git blob `670154e3538863b2d9891fd5483160fbdfc89164`) is retained with the corpus.
- Selection: 13 code-example files, 11,219 bytes of upstream source text, across five related project groups:

| Group | Selected paths |
|---|---|
| `mdn-html-navigation` | `html/introduction-to-html/navigation-menu-marked-up/{index,pictures,projects,social}.html` |
| `mdn-html-form` | `html/forms/your-first-HTML-form/{first-form,first-form-styled}.html` |
| `mdn-css-positioning` | `css/css-layout/practical-positioning-examples/{hidden-info-panel-start,hidden-info-panel}.html` |
| `mdn-html-head` | `html/introduction-to-html/the-html-head/{script.js,style.css,title-example.html}` |
| `mdn-css-web-font-starter` | `css/web-fonts/{web-font-start.html,web-font-start.css}` |

The path review excluded the punk-table styling group because its examples referenced unselected images and a Google Fonts resource. It excluded the tabbed-info-box example because `tabs-manual.js` identifies separately licensed W3C code. The web-storage example was incomplete when reduced to selected files because its JavaScript expected page elements absent from its selected HTML. The MDN font group is limited to its starter HTML/CSS; no font binaries, generated font examples, or Google Fonts files are retained. The final MDN snapshot contains only the 13 listed files plus its license; no full repository was cloned.

## Split and corpus

The new `family-stratified-groups-v1` pipeline keeps related project files together and places both approved source families in each split. It preserves the P1 whole-source-group behavior for old catalogs. For P2, the deterministic split uses seed `51` and holds out 30% of eligible project groups within each family: three groups per family for training and two per family for development.

| Split | Microsoft groups | MDN groups | Records | Text bytes | BPE tokens including one end marker per record |
|---|---|---|---:|---:|---:|
| Training | typing-game, space-game, bank-project | HTML navigation, HTML form, CSS positioning | 30 | 443,606 | 103,195 |
| Development | JS basics, terrarium | CSS web-font starter, HTML head | 17 | 206,161 | 56,646 |

All 47 selected content files passed curation; there were no skipped records or exact-content duplicates. The output is [training/artifacts/datasets/p2-02-data-v2](../training/artifacts/datasets/p2-02-data-v2), with a 688,458-byte pair of JSONL splits. Its manifest SHA-256 is `f600bcf7cc21dd941ea4ae7b84cad9a3f0edb20eba4dfb68d900d634a7a102ee`; training JSONL SHA-256 is `479181ded02e3b3cbb34d0e8d86312e215ebfbbb088d72dfcf5cb364b4c5ca5c`; development JSONL SHA-256 is `29505d9c92faf2f2f8e56760e7fe01b1e5c2d4066fe0e8533467fe15fff46140`.

The data is small but documentation-heavy. These tokenizer counts are grouped by record extension and include one end marker per record:

| Record type | Training records | Training tokens | Development records | Development tokens |
|---|---:|---:|---:|---:|
| Markdown (prose, diagrams, and code fences) | 14 | 78,579 | 9 | 51,695 |
| HTML | 11 | 10,423 | 3 | 2,406 |
| JavaScript | 3 | 9,687 | 2 | 983 |
| CSS | 2 | 4,506 | 3 | 1,562 |

Markdown includes prose, diagrams, and fenced code; HTML can contain inline CSS/JavaScript, so extension buckets are not an exact syntax-level language count. In the training Markdown, the audit found about 8,800 tokens in labeled or unlabelled source-code fences, compared with about 57,200 tokens of unfenced Markdown and 11,200 tokens in Mermaid diagrams. Those are approximate because BPE token counts do not add exactly across separately tokenized spans. The identifiable source-code share remains well below the proposal's rough 70–80% code target. Keep this as a traceable pipeline baseline; review a larger code-focused selection or an approved authored-code supplement before treating it as the preferred Phase 2 training mix.

## Tokenizer

A new byte-level BPE tokenizer was fitted from the 30 training records only. It learned 8,143 entries within the 16,384 model capacity, encoded both splits, and round-tripped all 47 records. The bundle is [training/artifacts/tokenizers/p2-02-data-v2](../training/artifacts/tokenizers/p2-02-data-v2); `tokenizer.json` SHA-256 is `1f39127c1567031df51a8d8ba84e8c3a0a6549ff3bb080c92c9f9e94fd6cf0ac`, and the bundle manifest SHA-256 is `83ed9daec7eceffde20544183c69344c0c39ca46d24d9e479bc896c62a16651a`. This is a tokenizer artifact, not a pretrained model. No model weights were initialized or trained for P2.

The 30/60 task sizes and per-language majority rule are accepted as a starting design, not a final benchmark. The owner has since approved a 10-percentage-point overall improvement margin and a minimum of 11/20 tasks in each language; the 30-task development set and static evaluator are recorded in the [evaluation design](PHASE-2-EVALUATION-DESIGN.md). The final holdout remains unbuilt, and a safe JavaScript behavior boundary is not confirmed. The [data-mix review](PHASE-2-DATA-MIX-REVIEW.md) records the v2 baseline and the v3 candidate; a matching step-zero score now exists, and a trained comparison remains. Qwen remains only an optional evaluation baseline if already present locally; Plex stays scratch-initialized.
