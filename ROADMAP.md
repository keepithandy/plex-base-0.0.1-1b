# Plex v0.1 engineering roadmap

Prepared October 3, 2026. This is a development plan, not an implementation or a claim that any model has passed Plex benchmarks. Model and runtime recommendations use the primary sources linked below; engineering limits are proposed starting values to revise using measurements.

Plex v0.1 should ship as a local, preview-first implementation CLI for small HTML, CSS, and JavaScript projects. The first deliverable is a real local-model run of:

```powershell
plex "change the page title to DungeonDex"
```

It must select `index.html`, propose exactly the title change, validate the proposed HTML, display the diff, and leave the original project untouched. A fixture response proves orchestration; it does not prove local inference or model capability.

## 1. Implementation language and stack

Use **TypeScript for Plex tooling**, compiled to JavaScript, on **Node.js 24 LTS**. The target repositories still support only HTML, CSS, and JavaScript; using TypeScript internally does not expand that scope. Node 24 is an LTS release in the current official release table. [Node.js releases](https://nodejs.org/en/about/previous-releases)

This choice keeps CLI packaging, source inspection, and web-language validation in one ecosystem. TypeScript makes interfaces explicit; compilation avoids relying on runtime TypeScript features. Python is a reasonable alternative for later model experiments, but is unnecessary for the shipped workflow. Rust would add build and distribution work before a demonstrated need.

| Concern | Initial choice | Purpose |
|---|---|---|
| CLI | Node built-in argument parsing; npm `bin` entry | A plain `plex` command with Windows command shim |
| Files, processes, HTTP | Node built-ins | Bounded reads, explicit process arguments, loopback inference |
| Contracts | JSON Schema with Ajv; TypeScript interfaces | Reject malformed model and configuration output |
| Diff | A small maintained unified-diff library, pinned | Tool-generated diffs from verified edits |
| Ignore fallback | `ignore` package, pinned | Git-style ignore rules in non-Git projects |
| HTML | `parse5` with source locations and parse diagnostics | Inspect structure without reserializing whole files |
| CSS | `css-tree` | Parse styles and inspect declarations |
| JavaScript | Acorn with explicit script/module mode | Parse code without executing it |
| Tooling tests | `node:test` and assertions | Unit and integration tests without a test framework |
| Behavioral benchmarks | Small fixture checks; later Playwright | Verify DOM, CSS layout, and browser events |
| Persistence | JSON configuration and JSONL benchmark results | No database |

Parser capabilities are documented by their maintainers: [parse5](https://github.com/inikulin/parse5), [CSS Tree](https://github.com/csstree/csstree), [Acorn](https://github.com/acornjs/acorn). Pin exact dependency versions at implementation time after compatibility checks. Install development dependencies and model assets during setup; Plex must never install packages or download weights while processing a task.

## 2. Local inference architecture

Use **one `llama-server.exe` process from a pinned llama.cpp release**, loading one local GGUF model. CPU is the required baseline; optional GPU offload uses the same adapter. llama.cpp documents quantized inference, CPU/GPU backends, and Windows operation. [llama.cpp](https://github.com/ggml-org/llama.cpp)

```text
Plex CLI -> deterministic orchestrator -> Plex Runtime adapter
                                         -> loopback llama-server
                                         -> local Plex Code weights
         <- verified edits <- schema-checked model response
         -> in-memory validation -> proposed diff + result
```

Initially the developer starts the server separately and supplies its endpoint. Keep it warm across CLI invocations. The official server supports a health endpoint, Windows startup, and schema-constrained JSON responses. [llama.cpp server documentation](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)

Example CPU launch, after obtaining the binary and weights during setup:

```powershell
llama-server.exe -m C:\Models\plex-code-0.5b-q4_k_m.gguf -c 4096 -ngl 0 --host 127.0.0.1 --port 8080
```

The filename is a local naming example, not a download identifier. Verify flags against the pinned binary. The adapter must reject non-loopback endpoints and HTTP redirects, enforce timeouts and response-size limits, and report loading/unavailable states clearly. There is no cloud fallback.

Use the model's native chat template. Start with greedy decoding where supported, a fixed seed, one request at a time, and a bounded output allowance. Record exact runtime, model hash, template, and generation settings. Low-temperature output is not a promise of bit-for-bit reproducibility across hardware.

Begin with a 4,096-token runtime context for Qwen candidates. Reserve roughly 768 tokens for output and 256 for uncertainty/template overhead; account for instructions, schema, metadata, task, and source in the remaining budget. Use runtime tokenization where available, including template overhead, before sending. A character estimate is only a preliminary filter. Models with smaller supported windows need smaller budgets.

Start with Q4_K_M. Compare Q8_0 on the same tasks before blaming model size for failures. Weight-file size is not peak RAM: measure server working set, KV cache, CLI overhead, and optional VRAM separately. Do not publish consumer-hardware latency or memory claims until measured.

Do not add embedded native bindings, a second model server, automatic server management, Docker, or WSL as initial requirements.

## 3. Base-model candidates

Evaluate existing weights; no Plex training or fine-tuning is part of this roadmap. This is a practical shortlist, not an exhaustive ranking of every available small model.

| Candidate | Published size / context | Role in evaluation | Important limitation |
|---|---|---|---|
| Qwen2.5-Coder-0.5B-Instruct | 0.49B / 32,768 tokens | First baseline; smallest coding-specific instruct option here | Repository editing and JSON reliability remain unproven for Plex |
| Qwen3-0.6B | 0.6B / 32,768 tokens | Small general-purpose challenger | Start with thinking disabled; test template and structured output compatibility |
| Maincoder-1B | 1B / 2,048 tokens | Coding challenger after the baseline | Emphasizes Python generation/completion; smaller context and instruction-following risk |
| Qwen2.5-Coder-1.5B-Instruct | 1.54B / 32,768 tokens | Upper-range comparator | Higher memory cost; adopt only if measured gains justify it |

The Qwen coder cards identify instruction tuning, coding specialization, Apache-2.0 licensing, and the published parameter/context sizes. [0.5B model card](https://huggingface.co/Qwen/Qwen2.5-Coder-0.5B-Instruct), [1.5B model card](https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct). Official Qwen 0.5B GGUF weights are available, including the Q4_K_M option. [Qwen GGUF repository](https://huggingface.co/Qwen/Qwen2.5-Coder-0.5B-Instruct-GGUF)

Qwen3-0.6B publishes Apache-2.0 licensing and a thinking/non-thinking switch. It is a challenger, not an assumed coding upgrade. [Qwen3-0.6B model card](https://huggingface.co/Qwen/Qwen3-0.6B)

Maincoder publishes Apache-2.0 licensing, a 2,048-token context, and Python-oriented examples; its publisher also supplies GGUF quantizations. Verify that the pinned Windows runtime loads its architecture and handles the required output contract before including it in comparative results. Its reported Python benchmark scores do not establish web-repository editing ability. [Maincoder model card](https://huggingface.co/Maincode/Maincoder-1B), [publisher GGUF repository](https://huggingface.co/Maincode/Maincoder-1B-GGUF)

Two optional probes should not delay Phase 1:

- **Gemma 3 1B IT:** a general instruction model with a published 32K window for the 1B variant and Gemma-specific access/license terms. Evaluate only if the initial shortlist leaves a clear gap. [Official model card](https://huggingface.co/google/gemma-3-1b-it)
- **Atlas-Coder-2-0.5B:** an existing Qwen coder derivative. Its card states Python emphasis and training sequences up to 1,024 tokens, making it a lower-priority probe for this workflow. Confirm artifact provenance and license files before use. [Publisher model card](https://huggingface.co/Pluto-AI-Labs/Atlas-Coder-2-0.5B)

Keep Qwen3-1.7B and SmolLM2-1.7B outside the initial approximate 0.5B–1.5B envelope. Do not broaden the envelope simply because a model is newer.

Select the smallest candidate meeting the measured release gate. Verify original and quantized artifact licenses, attribution requirements, hashes, and chat templates before distribution. Preserve upstream model identity: “Plex Code 0.5B” initially describes a configured model role, not newly trained weights.

## 4. Module boundaries and contracts

| Module | Owns | Output |
|---|---|---|
| `cli` | Arguments, configuration, printing, exit codes | Task request |
| `repo` | Root discovery, enumeration, bounded inspection, ranking | Manifest and scored candidates |
| `context` | Selected source, related references, budget accounting, prompt assembly | Context bundle and permitted edit spans |
| `model` | Plex Runtime HTTP adapter, native template settings, schema request | Untrusted structured response |
| `patch` | Response validation, scope/path checks, exact replacements, diff | Proposed file buffers |
| `validation` | Parsing and explicitly configured checks | Diagnostics and coverage report |
| `core` | State transitions, one repair budget, timings, final outcome | Run result |
| `benchmarks` | Fixture reset, behavior assertions, scoring | Reproducible results |

Use plain functions and data objects. Inject one `ModelClient` interface for live inference or deterministic test responses. Do not create a general plugin system.

### Repository discovery and selection

1. An explicit `--repo` wins. Otherwise use the Git top-level root when available; for non-Git projects, use the requested/current directory and say so. Never silently widen to an unrelated ancestor.
2. In Git projects, combine tracked and untracked nonignored paths using `git ls-files --cached --others --exclude-standard -z`; deduplicate and verify paths on disk. Git documents these enumeration options. [git-ls-files](https://git-scm.com/docs/git-ls-files)
3. Gitignore does not exclude already tracked files. Apply Plex's hard exclusions and size/extension filters regardless. Skip submodules and do not follow symlinks or Windows junctions.
4. For non-Git projects, traverse deterministically with nested ignore rules, hard exclusions, and limits. Document unsupported ignore semantics rather than pretending perfect Git parity.
5. Initially allow `.html`, `.css`, `.js`, `.mjs`, and `.cjs`; exclude dependencies, `.git`, build output, coverage, minified files, maps, binaries, and sensitive configuration. Do not load `.env` contents into model context.
6. Proposed limits: 1,000 eligible files, 128 KiB per file, and 4 MiB total content inspected for ranking. List metadata first; inspect bounded text sequentially and discard it after extracting signals. Exceeding limits yields a clear unsupported/insufficient-context outcome, not a silently incomplete successful scan.

Rank using explicit filename/path matches, task tokens, language intent, symbols/selectors, and references. Define weights in a small table, stabilize ties lexically, and expose ranking reasons. In the title fixture, `<title>` and `index.html` must outrank CSS and JavaScript. Ambiguous multiple pages require a target hint or an insufficient-context result.

Phase 1 reads a complete small selected HTML file. Later, use parser source ranges around matched symbols and deterministic local imports/references. Never cut a function, selector, or tag arbitrarily to fit. Remove low-ranked files first; if critical context cannot fit, stop. A missing required file or unseen dependency must not be invented.

### Model response and patch safety

Prefer exact search/replacement edits over model-authored unified diffs:

```json
{
  "status": "patch",
  "reason": "Updated the existing page title.",
  "edits": [
    {
      "path": "index.html",
      "old": "<title>Example</title>",
      "new": "<title>DungeonDex</title>"
    }
  ]
}
```

Model statuses: `patch`, `no_change`, `insufficient_context`, `unsupported`. Other statuses require an empty edit list. The orchestrator owns outcomes such as `invalid_output`, `validation_failed`, `repair_failed`, and `runtime_unavailable`; the model cannot declare validation success.

Use one canonical schema with required fields, enums, bounded strings/arrays, and no unknown properties. Keep the runtime constraint schema simple and test it against the pinned runtime; Ajv remains authoritative. Do not extract plausible JSON from surrounding prose or accept truncated output.

Before constructing a proposal:

- Require existing regular files from the supplied selection. Reject creation, deletion, absolute paths, traversal, Windows drive/UNC paths, alternate data streams, case aliases, and paths escaping the canonical root.
- Require each nonempty `old` string to occur exactly once in its original file and entirely inside a supplied editable source span. Reject overlaps and apply multiple edits against the original snapshot in reverse position order.
- Reject file-level deletion, oversized replacements, and excessive changed lines/files. Start with at most three files, ten edits, and 100 changed lines; these limits do not prove semantic scope correctness.
- Preserve original encoding, BOM, newline style, and unchanged bytes. Phase 1 supports validated UTF-8 only; refuse unknown encodings.
- Snapshot hashes and recheck selected files before the final report. If the project changed during inference, reject the stale proposal.

The tooling computes unified diffs from original/proposed buffers. The model cannot invoke a shell, access Git, or name validation commands. Repository comments and validation logs are data, never instructions.

Preview is the full v0.1 default: built-in checks inspect proposed buffers, and original files remain untouched. Applying proposals can wait until later measured reliability warrants it.

### Validation and one repair

HTML parsing alone is too permissive to prove correctness. Capture parser diagnostics and explicit invariants; in the title fixture require one title inside the head, the expected title text, preserved script/style references, and no other byte changes. Report existing diagnostics separately from introduced failures.

CSS parsing must reject parser recovery/raw nodes or errors where applicable. JavaScript parsing must use known script/module mode. Later inspect inline scripts/styles and relative references. Syntax checks cannot prove visual layout, event behavior, or arbitrary task completion.

Detect available `test`, `lint`, and `build` scripts as metadata. Run only checks explicitly enabled in local configuration; the model never chooses a command. In Phase 3, execute them against a bounded disposable project copy containing the proposed changes. Preserve required project configuration and dependency resolution; if faithful staging is unavailable, report that check as unavailable. Never claim tests on original files validated a proposal.

Configured project scripts are arbitrary local code, not sandboxed merely because they run in a temporary directory. Use only developer-trusted repositories, explicit executable/argument arrays, fixed working directories, timeouts, capped output, and Windows process-tree cleanup. No package installation, implicit `npx` fetching, or model-generated command strings.

On a repairable parse/check failure, send bounded concrete diagnostics plus the original selected context and rejected edits back to Plex Code once. The repair generates replacements against the original snapshot. Validate the entire repaired proposal again. Unsafe paths, unsupported operations, insufficient context, and stale snapshots stop immediately; malformed structured output stops with `invalid_output`. No hidden retries or selection expansion.

The CLI distinguishes `PROPOSAL VALIDATED — NOT APPLIED`, `NO CHANGE`, `INSUFFICIENT CONTEXT`, and failures. List which checks passed, failed, or were unavailable. Print the final diff and file count, not a generic claim that the requested behavior is proven.

## 5. Proposed repository structure

Create directories as their first implementation tasks need them:

```text
plex/
  src/
    cli/main.ts
    repo/{detect,scan,rank}.ts
    context/{build,budget}.ts
    model/{client,llama}.ts
    patch/{contract,check,diff}.ts
    validation/{html,css,javascript,commands}.ts
    core/{run,result,config}.ts
  tests/{unit,integration}/
  fixtures/simple-web-project/{index.html,style.css,app.js}
  prompts/implementation.txt
  benchmarks/{cases,assertions,run.ts}
  docs/{architecture,setup,limitations,model-evaluation}.md
  scripts/benchmark.ps1
  package.json
  package-lock.json
  tsconfig.json
  plex.config.example.json
  README.md
  CHANGELOG.md
```

Keep weights outside source control, configured by local paths. Ignore generated output and benchmark artifacts containing source. All Plex components remain in one repository.

## 6. Development phases and milestone gates

| Phase | Deliverable | Exit gate |
|---|---|---|
| 1 — Title-change proof | CLI, scanner/ranker, focused prompt, real inference, safe proposal, HTML validation, one repair, basic benchmark | On CPU, the exact title command produces only the expected diff on repeated clean fixture runs; no source writes; negative cases stop safely |
| 2 — Web-language coverage | CSS/JS parsing, bounded source sections, local-reference selection, single-file tasks then three-file edits | Automated behavior checks cover every requested benchmark category; targeting and scope results are recorded |
| 3 — Project validation | Explicit command configuration, staged lint/test/build, baseline diagnostics, failure reporting | Passing and deliberately failing project checks inspect proposed code; timeout and cleanup work on Windows |
| 4 — Model evaluation and release | Comparative CPU runs, quantization comparison, held-out evaluation, reproducible setup/docs | Smallest qualifying model selected from evidence; release thresholds frozen and met; limitations published |

Phase 1 is a vertical slice, not a complete v0.1 release. Advance only after its real-model gate; implement Phase 2 categories incrementally so failures identify the subsystem needing work. No calendar estimate is reliable before measuring model latency and the developer's hardware/setup.

## 7. Phase 1 independently testable tasks

Each task should be one small change with the acceptance evidence below. Dependencies are explicit; fixture responses allow tooling tests before live inference is connected.

| ID | Task | Depends on | Independent acceptance test |
|---|---|---|---|
| P1-01 | Initialize TypeScript build, npm bin, test command | — | Compile and run `plex --help` from a Windows path containing spaces |
| P1-02 | Define request, manifest, response schema, and result contracts | 01 | Accept valid statuses; reject unknown fields, missing keys, and edits on non-patch statuses |
| P1-03 | Add three-file fixture and title assertion | 01 | Assert original title is Example and hash all three files |
| P1-04 | Detect explicit, Git, and non-Git project roots | 02 | Nested Git cwd resolves correctly; explicit fixture root remains the requested boundary |
| P1-05 | Enumerate paths with exclusions, limits, and safe traversal | 04 | Test ignored/untracked files, missing tracked paths, oversized files, symlinks/junctions, and deterministic ordering |
| P1-06 | Rank candidates with inspectable scores | 03,05 | Title task ranks index.html first; ambiguous pages do not produce a confident target |
| P1-07 | Build bounded prompt and selection snapshot | 02,06 | Only selected HTML enters source context; hashes/spans recorded; critical oversized context stops |
| P1-08 | Implement strict response parsing | 02 | Accept exact JSON; reject prose, invalid types, incomplete JSON, empty anchors, and excessive edits |
| P1-09 | Validate edit paths and unique anchors | 07,08 | Reject unselected files, creation/deletion, traversal, case aliases, repeated anchors, and overlapping edits |
| P1-10 | Build proposed buffers and unified diff | 09 | Expected title diff only; UTF-8/BOM/CRLF preservation; originals remain byte-identical |
| P1-11 | Validate proposed HTML and title fixture behavior | 03,10 | Correct title passes; wrong title and introduced structural errors fail despite parse recovery |
| P1-12 | Compose pipeline using an injected fixture ModelClient | 04–11 | Success, no-change, missing-context, unsafe-output, and stale-file paths produce correct outcomes |
| P1-13 | Add loopback HTTP adapter with a fake local server | 02,07,08 | Health/loading state, timeout, redirect rejection, response cap, and schema request tested without weights |
| P1-14 | Record local CPU runtime/model setup | 13 | Pinned binary loads hashed Qwen 0.5B GGUF and accepts a constrained response; record hardware and template |
| P1-15 | Wire real local inference into the CLI | 12–14 | Title request uses actual model output; unavailable runtime fails clearly with no fixture fallback |
| P1-16 | Add the single repair transition | 11,12,15 | Inject a validation failure then valid repair; assert at most two model calls and repaired edits use original source |
| P1-17 | Print diff, checks, preview status, timings, and exit code | 12,16 | stdout/result contract distinguish valid proposal from applied work, runtime error, and repair failure |
| P1-18 | Add repeatable title benchmark and safety regression run | 03,15–17 | Ten CPU title runs on reset copies, plus already-correct and ambiguous fixtures; record targeting, scope, validity, behavior, and latency |

P1-14 is a real runtime smoke test; P1-15 and P1-18 are model capability evidence. Neither can be replaced by mocked tests. If the title gate fails, inspect selection, prompting, output format, quantization, and validation diagnostics before considering a larger model.

## 8. Benchmark strategy

Start a versioned benchmark manifest in Phase 1. Expand to all requested categories in Phase 2:

| Category | Required cases | Behavioral oracle |
|---|---|---|
| HTML | Title, element addition, attribute change, element move | Parsed DOM/text/attribute/order assertions |
| CSS | Spacing, layout rule, selector, responsive behavior | Parsed rule checks plus browser computed styles at fixed viewports |
| JavaScript | Constant, event handler, conditional bug, helper reuse, validation rule | Controlled fixture execution/events and positive/negative inputs |
| Multi-file | Add control, style it, wire existing JS | DOM presence, computed style, event outcome; only expected files changed |
| Conservative outcomes | Already correct, missing target, ambiguous target, unsupported request | Correct no-change/refusal and unchanged source |

Each case records task, fixture revision, expected/forbidden files, expected behavior, validator/command, allowed edit scope, and pass/fail. Expected files are ground truth for the harness and must not be leaked as privileged hints to the production selector. Permit alternative minimal correct patches unless a case explicitly tests exact byte preservation.

Run each task from a clean temporary fixture copy with pinned inputs. Compare candidates on identical tasks, templates appropriate to each model, and total context/output limits supported by each candidate. Record actual supplied context so short-window results remain interpretable.

Maintain development and held-out variants: different titles, file names, formatting, distractor pages, selectors, and function names. Tune prompts only on development tasks. Start with at least one case per category, then add multiple variants before choosing a model. Repeated runs of one fixture measure stability, not generalization.

Record:

- **Task success:** correct behavior, permitted scope, valid output, and validation pass together; refusal on a solvable task counts as failure.
- **Targeting:** selected-file precision/recall against ground truth, separately from modified-file accuracy.
- **Scope:** forbidden/unexpected edits and unrelated changes within allowed files.
- **First attempt / repair:** initial pass rate; recovery rate among repair-eligible failures, with denominators.
- **Hallucination indicators:** rejected nonexistent paths, unresolved references, and explicit oracle failures. Do not claim a complete hallucination detector.
- **Context efficiency:** supplied source tokens/eligible source tokens, critical-context coverage, and budget failures. Small context alone is not success.
- **Patch size:** files, edits, changed lines, and ratio to a reference minimal patch when meaningful.
- **Performance:** cold start separately from warm inference; end-to-end p50/p95, input/output tokens, prompt and generation time, sampled peak RAM and available VRAM.

Publish run counts and uncertainty alongside rates. Capture local artifacts with source retention opt-in. Select on the correctness/latency/memory tradeoff, not a single chatbot score.

After initial baseline runs, set achievable quantitative goals using observed failure categories and hardware performance. Freeze goals before held-out evaluation; do not change them to fit the winning result.

## 9. Testing strategy

Keep tooling correctness separate from model quality:

1. Unit tests cover ranking ties, budget accounting, schema parsing, edit anchors, canonical paths, source-byte preservation, and retry limits.
2. Pipeline integration tests use injected responses for all outcomes and failure stages; fake HTTP tests exercise the actual transport contract.
3. Windows integration tests cover paths with spaces/non-ASCII text, CRLF, drive-case behavior, junctions, command shims, Git worktrees, and interrupted processes.
4. Parser regressions verify new diagnostics against baseline and prevent recovered malformed HTML/CSS being treated as sufficient evidence.
5. Live-model tests run separately and explicitly require a local runtime. An absent model is “not run,” never a passing test.
6. Behavioral benchmark tests verify actual fixture outcomes. Browser tooling is a development dependency with assets prepared ahead of offline runs.
7. Phase 3 tests verify staged commands see proposed code, missing dependencies are reported, failing checks trigger only one repair, and process cleanup preserves originals.

No test suite should execute arbitrary generated JavaScript in the Plex process. Behavioral execution belongs in controlled fixtures or developer-configured project checks.

## 10. Technical risks and mitigations

| Risk | Mitigation / measurement |
|---|---|
| Tiny model misunderstands edits | Small scopes, exact anchors, behavior checks, conservative outcomes |
| File selection omits necessary code | Ranking reasons, reference signals, targeting recall, ambiguity/context refusal |
| Structured output fails | Constrained decoding plus authoritative schema validation; format-error metric |
| Valid JSON contains unsafe edits | Canonical path allowlist, supplied-span enforcement, unique anchors, edit caps |
| Selected-file edit changes unrelated behavior | Minimal-patch policy and behavior/scope oracles; acknowledge production limits |
| Context budget drops critical code | Runtime token counts, whole logical sections, fail-safe budget policy |
| Multi-file reasoning is weak | Graduate from single-file cases and measure separately |
| Quantization removes useful capability | Paired Q4/Q8 evaluation before model-size escalation |
| CPU is too slow / RAM too high | Small context/output caps, warm server, hardware profiling |
| Windows/runtime incompatibility | Pin artifacts; CPU load/transport/template smoke gates for every candidate |
| Source comments influence instructions | Delimit source as data; no model-controlled tools, paths, or commands |
| Existing errors confuse validation | Baseline diagnostics; report unchanged failures separately |
| Parser pass is mistaken for correctness | Explicit check coverage and separate behavioral benchmarks |
| Project scripts cause side effects | Explicit trusted checks; no automatic discovery-to-execution; document lack of sandbox |
| User edits race with inference | Snapshot hashes; reject stale proposals |
| License/provenance mismatch | Verify upstream and quantized artifacts, attribution, and hashes |
| Prompt brittleness / benchmark overfitting | Version prompts; held-out layouts/names; frozen release gate |

## 11. Definition of done

Plex v0.1 is releasable only when all of the following are evidenced:

- A documented Windows setup runs the CLI with preinstalled local assets, CPU-only, offline after setup.
- The real-model title milestone passes ten repeated clean-fixture runs with exactly the intended diff and no original-file writes.
- Scanning, ranking, context budgeting, strict output parsing, scoped proposals, and diff display have deterministic automated coverage.
- HTML/CSS/JS validation reports concrete checks and limitations; configured project checks operate on proposed code when faithfully stageable.
- One repair attempt works under a deliberate repairable failure, and no code path exceeds that limit.
- All requested benchmark categories and conservative outcomes execute automatically; results include source/model/runtime revisions and core metrics.
- A quantitative benchmark gate established after development baselines is frozen and met on held-out cases. No unsupported overall reliability percentage is advertised.
- Safety regressions reject malformed output, unexpected paths/files, stale snapshots, over-budget context, and unsupported operations.
- The chosen model is the smallest tested candidate meeting the gate; CPU latency/RAM and any tested GPU results are documented.
- Setup, limitations, preview semantics, exit codes, configuration, model provenance/license requirements, and changelog are complete.

Passing syntax checks alone, loading weights, or producing the title edit once does not meet the full definition of done.

## 12. Deferred v0.2+ work

Consider explicit application of validated proposals only after measured reliability, with backup/recovery and hash checks. Then consider improved reference analysis, larger-project support, more languages, and richer validation as evidence demands.

Keep autonomous Plex Agent loops, multiple repairs, training/fine-tuning, model variants, embeddings/vector databases, persistent memory, plugins, IDE/GUI integration, remote/cloud execution, model-driven browsing/installations, automatic commits/pushes, and GitHub/PR integration deferred. A future specialization proposal must first show that deterministic tooling is reliable and identify repeatable model errors worth training against.

The next implementation task is **P1-01**. The next capability proof is **P1-15 through P1-18**, using the smallest coding baseline and the exact DungeonDex title request.
