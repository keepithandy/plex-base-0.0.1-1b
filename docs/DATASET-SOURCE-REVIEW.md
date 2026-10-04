# First Plex corpus: source review

Prepared October 3, 2026. Status: **both source groups explicitly approved by the owner; starter corpus built and verified; P1-14 complete for this corpus**.

The recommendation is a small corpus focused on HTML, CSS, JavaScript, and programming explanations. A source group keeps material from one repository family together. Training material is what Plex studies; validation material is withheld so we can check it on unfamiliar examples.

## Approved sources

| Source group | Purpose | Declared license | Selected snapshot | Eligible corpus records |
|---|---|---|---:|---:|
| [Microsoft Web Dev for Beginners](https://github.com/microsoft/Web-Dev-For-Beginners/tree/78085398be0dea7abaaf5eda914817f46f6ddbbc) | Training: English lessons plus completed HTML/CSS/JavaScript projects | [MIT; Microsoft Corporation](https://github.com/microsoft/Web-Dev-For-Beginners/blob/78085398be0dea7abaaf5eda914817f46f6ddbbc/LICENSE) | 35 files / 639,710 bytes, including LICENSE | 34 |
| [Brad Traversy's 50 Projects in 50 Days](https://github.com/bradtraversy/50projects50days/tree/c92b0bc3a87fc95d44b89552b7b6a2eeb36ca481) | Validation: small HTML/CSS/JavaScript interface examples | [MIT; copyright 2022 Brad Traversy](https://github.com/bradtraversy/50projects50days/blob/c92b0bc3a87fc95d44b89552b7b6a2eeb36ca481/LICENSE) | 55 files / 54,583 bytes, including LICENSE | 54 |

Both inspected root licenses cover software and associated documentation under MIT terms. Preserve their copyright and permission notices with the corpus copies. The downloader retains each original LICENSE byte-for-byte; the dataset builder packages local license evidence under its output's `licenses/` directory and records its SHA-256 hash. Linked websites, course videos, images, and external assets are not included.

The owner explicitly chose **"Approve both and build the corpus"** in this chat. The approval was recorded at `2026-10-04T00:51:40Z` (October 3, 2026, 8:51:40 PM America/New_York) for these specific subsets with their notices retained. The approved catalog, containing public metadata and relative paths only, is [training/dataset-sources.starter-v1.json](../training/dataset-sources.starter-v1.json).

Original in-file attribution comments and links are retained, including references to W3Schools and MDN in Microsoft's terrarium example. No content was fetched from those external sites. The inspected upstream repository MIT declaration is the recorded license evidence.

## Exact scope

The immutable revisions and selected file paths, byte sizes, and upstream Git blob hashes are in [training/dataset-source-lock.json](../training/dataset-source-lock.json).

Microsoft's subset contains the main English README lessons from `2-js-basics`, `3-terrarium`, `4-typing-game`, `6-space-game`, and `7-bank-project`, plus the top-level completed `solution` HTML/CSS/JavaScript files in those projects. It excludes translations, assignments, `your-work` starter files, intermediate solution variants, server/API implementations, newer AI projects, images, dependencies, and Git history.

Traversy's subset contains only HTML/CSS/JavaScript files from these 18 completed projects:

```text
animated-navigation       auto-text-effect          button-ripple-effect
custom-range-slider       drawing-app               drink-water
event-keycodes            faq-collapse              good-cheap-fast
hidden-search             incrementing-counter      notes-app
progress-steps            random-choice-picker      simple-timer
theme-clock               toast-notification        todo-list
```

The public source snapshots total **694,293 bytes (about 0.66 MiB)**. No paid course material, API access, package installation, or source execution is needed. Every downloaded file matched its recorded upstream Git blob hash.

## Preflight results and split

The preflight ran the pipeline's normalization, secret-pattern, exact-duplicate, and JavaScript syntax checks without creating a corpus or changing the approval status:

| Split | Eligible files | Normalized UTF-8 text bytes | Composition |
|---|---:|---:|---|
| Training | 34 | 638,548 | 23 Markdown lessons, 4 HTML, 3 CSS, 4 JavaScript |
| Validation | 54 | 53,373 | 18 HTML, 18 CSS, 18 JavaScript |

No selected file was skipped by these checks, and no exact duplicate crossed the groups. This does not establish that every example works: JavaScript received a syntax check, while HTML/CSS and Markdown received text/credential checks rather than browser or behavior tests. Lessons can contain intentionally partial teaching snippets. The source programs were not executed.

Use the default seed **1337** and **10 percent of groups** setting. With two groups, the pipeline must hold out one whole group: 50 percent of groups, but approximately **7.7 percent of normalized text bytes** in this selection. Seed 1337 assigns Microsoft to training and Traversy to validation. The assignment is fixed before training or evaluation.

This is a starter corpus for the tokenizer, learning checks, and first pilot. Training text is mostly explanations; validation is code from separate projects. Results must describe that difference. This amount of data does not support a claim of general coding ability, and larger later experiments need broader reviewed sources.

## Reproduce the approved build

The approved source catalog records both exact revisions, paths, licenses, group IDs, and the owner's rights-review timestamp. On a fresh checkout with the local source snapshots missing, run from the repository root:

```powershell
uv run --project training python -m plex_training.source_fetch
uv run --project training python -m plex_training.cli dataset-build `
  --source-manifest training\dataset-sources.starter-v1.json `
  --output-dir datasets\p1-14-starter-v1 `
  --validation-percent 10 `
  --seed 1337
```

The first command verifies existing snapshots or downloads only the locked files if missing. It refuses changed snapshots and caps total selected downloads at 20 MiB. The second command produces the corpus under `training/artifacts/datasets/p1-14-starter-v1`. This directory already exists in the owner's current workspace; choose a fresh `--output-dir` when repeating the build there. Existing datasets are never overwritten.

## Verified corpus

The local build contains **88 records**: 34 training records and 54 validation records. Total packaged size is **746,848 bytes (about 0.71 MiB)**.

| Output | Bytes |
|---|---:|
| `train.jsonl` | 669,287 |
| `validation.jsonl` | 71,967 |
| `manifest.json` | 3,362 |
| `licenses/microsoft-web-dev.txt` | 1,162 |
| `licenses/traversy-web-projects.txt` | 1,070 |

SHA-256 verification:

```text
train.jsonl:
40996f243ec7fa786db49effd92cbebea441bdf7be9de59dacec335f517070dd
validation.jsonl:
2348e634efd165e3151a604f3180e09236be9510659a76e70f13e7717813d2f2
manifest.json:
58845cbc9251c0c33d5f2980d8b47d28dccb05638d68ac572a5841cdf96c8fcc
source catalog:
d5fd4043b08eed001b4b2c3e9ed2f0e572cbcc61b7001342ce8d14df8116861c
```

Verification confirmed pinned source blob hashes, source approvals, every record's content/identity hashes, separate repository groups, separate normalized content hashes, exact original license copies, and an identical second build of every packaged file. The temporary reproduction was removed after comparison. No selected file was skipped; this is a filtering result, not a claim that undetected secrets or behavior defects are impossible.

All **25 training-workspace tests passed** in the owner's installed Python/PyTorch environment. No dependencies were installed and no real-data training was started. Raw source snapshots and corpus outputs remain ignored by Git; the approved catalog, source lock, pipeline, and this report are reviewable repository files.

P1-15 has trained the tokenizer using the training split only; its [report](PLEX-TOKENIZER.md) records settings, exact-text checks, token counts, hashes, and reproduction. Keep the validation group withheld from tokenizer fitting and model training.
