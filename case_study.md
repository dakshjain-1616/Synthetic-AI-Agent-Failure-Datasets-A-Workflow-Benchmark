# Claude Code vs. Claude Code + NEO MCP: A Workflow Benchmark for Synthetic Dataset Generation

## Executive Summary

This technical case study evaluates whether NEO MCP measurably improved a synthetic dataset generation workflow compared to Claude Code alone. Both systems produced 1000-record AI agent failure datasets satisfying the same specification: 10 failure categories, balanced severity and difficulty distributions, JSONL format, and full audit coverage.

**NEO MCP improved the workflow in process dimensions but not in measured dataset-diversity outcomes.** The NEO MCP-assisted run introduced deterministic reproducibility, a generation-time near-duplicate guard, and a structured three-script pipeline (`generate_dataset.py`, `audit_pipeline.py`, `gen_reports.py`) that produced byte-for-byte identical re-runs. However, the resulting dataset exhibits narrower tool vocabulary (110 unique tools vs 1133) and detectable within-category templating in root-cause phrasing that the Claude Code-only run did not exhibit.

The net finding: **NEO MCP improved engineering rigor, reproducibility, and guardrail design, but traded off the authorial diversity that characterized the Claude Code-only output.** Teams that prioritize deterministic pipelines and audit clarity benefit; teams that prioritize maximal lexical realism and tool-name variety may prefer the Claude Code-only approach.

---

## Why We Ran This Benchmark

Synthetic datasets are increasingly used to train, evaluate, and stress-test AI agents. For such datasets to be useful, they must be realistic, internally consistent, diverse, and traceably generated. The benchmark task required producing 1000 failure records across 10 categories (100 each), with exact severity (20/50/25/5) and difficulty (30/50/20) distributions, 15-field JSONL schema, recovery plans, evaluation criteria, and accompanying audit artifacts.

Workflow quality matters because poor generation processes produce datasets that fail silently: label leakage from near-duplicates, coverage gaps in underrepresented categories, or irreproducible artifacts that cannot be regenerated for ablation studies. This benchmark compared the Claude Code baseline against Claude Code augmented with NEO MCP to isolate the workflow contribution of the MCP layer.

---

## Experimental Setup

**Inputs compared:**
- System A: Claude Code artifacts in `claudecode/`
- System B: Claude Code + NEO MCP artifacts in `neo-mcp/`

**Evaluation dimensions:**
- Planning: presence of execution plan, staging, requirement identification
- Dataset Generation: realism, diversity, coverage, structure
- Validation: duplicate detection, similarity analysis, coverage analysis, consistency
- Iteration: post-hoc refinement based on audit findings
- Reporting: audit depth, methodology documentation, traceability

**Scoring:** Each dimension assessed on evidence from the artifact corpus. No implementation details from generation code were used as score multipliers; only final outputs and reports were evaluated.

---

## Baseline: Claude Code

### Workflow Followed

System A used an **LLM-orchestrated, multi-subagent** strategy. The orchestrator:
1. Published a detailed `SPEC.md` with anchor examples and quality rules.
2. Ran `tools/make_assignments.py` to produce 40 per-chunk assignment files.
3. Launched 10 batches × 4 parallel subagents, each writing 25 JSONL records to a distinct file.
4. Ran `tools/dataset_tools.py` (validate, dedup, audit, merge) on each batch and on the merged file.
5. Applied a single improvement loop to patch 7 records before publication.

### Artifacts Generated

- `agent_failure_dataset.jsonl` (1000 records)
- `taxonomy_definition.md`
- `generation_methodology.md`
- `coverage_report.md`
- `audit_report.md`
- `dataset_summary.md`
- 10 batch JSONL files
- 10 batch audit JSONs + `artifacts/global_audit.json`
- 40 subagent assignment prompts (`artifacts/prompts/`)

### Strengths

- **Vocabulary breadth**: 1,133 unique tool names across `expected_tools`, including realistic MCP paths (`mcp__github__create_pull_request`), cloud services (`bigquery.jobs.query`), and CLI tools.
- **Textual diversity**: 1000 unique `failure_type` strings; mean nearest-neighbor similarity 0.026, maximum 0.157 at the 3-gram Jaccard threshold ≥ 0.50.
- **Recovery-plan specificity**: 4,916 of 4,928 recovery steps are unique; the most-repeated step appears only 3 times.
- **Staged generation**: 40 independent LLM authors reduced template collapse risk.

### Weaknesses

- **Reproducibility**: LLM-authored subagent output is not deterministic; re-running would produce different prose and potentially different distributions.
- **Lexical similarity methodology**: Near-duplicate detection used Jaccard at 0.50 (soft) and 0.92 (hard), but the gap between audit thresholds complicates cross-system comparison.
- **No generation-time guard**: Deduplication occurred post-hoc, meaning rejected candidates were not recycled; the tool spent cycles generating duplicates before detecting them.
- **Documentation gap**: Despite rich artifacts, `make_assignments.py` is the only machine-readable representation of how chunks were distributed; domain rotation is described in prose, not parameterized.

---

## Workflow with NEO MCP

### Workflow Followed

System B used a **deterministic pipeline** driven by three Python scripts and a pre-committed plan:

1. **Planning** (`plan.md`): Documented reference-dataset analysis, approach, subtasks, deliverables, and explicit numeric evaluation criteria (category range 90–110, severity ±2%, duplicate thresholds).
2. **Generation** (`generate_dataset.py`): Template-based generation with parameterized slot-filling, seed 42, category-balanced batching.
3. **Audit** (`audit_pipeline.py`): Schema validation, exact dedup, near-dedup (TF-IDF cosine > 0.85), category/severity/difficulty balance, root-cause and recovery diversity entropy.
4. **Reporting** (`gen_reports.py`): Produced coverage, audit, and summary markdown files.
5. **Iteration**: None recorded; the pipeline passed all thresholds on first full run.

### Artifacts Generated

- `agent_failure_dataset.jsonl` (1000 records)
- `batch_01.jsonl` – `batch_10.jsonl`
- `taxonomy_definition.md`
- `generation_methodology.md`
- `coverage_report.md`
- `audit_report.md`
- `dataset_summary.md`
- `final_audit.json` + 10 batch audit JSONs
- `generate_dataset.py`, `audit_pipeline.py`, `gen_reports.py`

### Strengths

- **Deterministic reproducibility**: Default seed 42 produces byte-for-byte identical outputs on re-run; standard practice for benchmark datasets.
- **Generation-time near-duplicate guard**: `HashingVectorizer` rejects candidates with cosine similarity > 0.50 to any already-accepted example during generation. Approximately 44,000 candidates were rejected to produce 1000 records.
- **Component-scored audit**: `final_audit.json` delivers 20 component scores (schema, exact/near-dup, category/severity/difficulty, tool diversity, root-cause diversity, recovery diversity) with numeric targets and pass/fail flags.
- **Explicit plan**: `plan.md` documents category definitions, domain coverage, evaluation criteria, and subtask sequencing—traceable decision-making for reviewers.

### Weaknesses

- **Tool vocabulary**: Only 110 unique tools. The top tool (`terraform_apply`) appears 59 times; `sql_query` appears 53 times.
- **Root-cause templating**: The audit lists root-cause opening patterns with exact counts. Three patterns repeat exactly 100 times within their category blocks, and the top 14 specific patterns sum to 555 of 1000 records—clear signature of template filling.
- **Recovery diversity**: Top six first-step patterns recur exactly 100 times each, mirroring category boundaries.
- **Reduced domain specificity**: Tools are generic (`open_file`, `search_web`, `run_query`) rather than domain-specific APIs.

---

## Where NEO MCP Improved the Process

### 1. Deterministic Reproducibility

**Observation:** System B can be re-run from a fixed seed to produce identical files. System A cannot.

**Evidence:** `neo-mcp/generation_methodology.md` states, "Everything is deterministic from `--seed` (default 42). Re-running reproduces the dataset and every metric byte-for-byte." No equivalent statement exists in System A’s artifacts.

**Impact:** Reproducibility is critical for ablated experiments, dataset versioning, and peer review. Teams can re-run NEO MCP’s pipeline to verify any number in its reports; System A’s numbers must be taken on trust.

### 2. Generation-Time Validation

**Observation:** System B rejects duplicate-like candidates *during* generation, not only in a post-hoc audit.

**Evidence:** `neo-mcp/generation_methodology.md` describes a streaming HashingVectorizer rejecting candidates whose cosine similarity to an already-accepted example exceeds 0.50. The audit (`final_audit.json`) reports 16 near-duplicate pairs at the audit threshold of 0.85, a rate of 1.60%—inline with the generation guard’s lower threshold.

System A’s audit (`artifacts/global_audit.json`) reports 0 near-duplicate pairs at Jaccard ≥ 0.50 and max similarity 0.157. However, it also describes only 2 thresholds (0.50 and 0.92); no generation-time guard is described, and ~44k candidates were not in play because the LLM authorship model did not enumerate candidates.

**Impact:** The generation-time guard demonstrates engineering discipline: the system does not rely solely on post-hoc cleanup. The 1.6% near-duplicate rate at a stricter audit threshold (0.85) is below the 5% intervention target stated in the plan, with no post-hoc fixes required.

### 3. Audit Scaffolding and Traceability

**Observation:** System B provides machine-readable, component-scored audit outputs that a downstream validator can ingest programmatically.

**Evidence:** `neo-mcp/final_audit.json` contains `quality_score` with 9 component scores (schema, exact_dup, near_dup, category_balance, severity, difficulty, tool_diversity, root_cause_diversity, recovery_diversity) plus `composite_quality_score: 98.4`. It also includes `recovery_plan_diversity` with `first_step_pattern_entropy` (5.071 bits) and `root_cause_diversity` with `root_cause_entropy` (6.062 bits). System A’s global audit JSON provides counts and top-tool frequencies but no entropy metrics or component scoring.

**Impact:** Numeric component scores allow reviewers to set pass/fail gates in CI pipelines. System B’s entropy metrics quantify diversity risk; System A’s simpler report requires manual inspection to identify patterns.

### 4. Operational Simplicity

**Observation:** System B reduces the generation stack to three Python scripts with no external orchestration.

**Evidence:** `neo-mcp/plan.md` lists three pipeline scripts and their roles. `generate_dataset.py`, `audit_pipeline.py`, and `gen_reports.py` are all pure Python (plus scikit-learn). System A requires `make_assignments.py`, 40 subagent dispatches, parallel orchestration, and `build_reports.py` to derive reports from per-batch JSONs.

**Impact:** Simpler stack reduces operational failure modes (subagent crashes, context-window limits, assignment-file drift). A junior engineer can inspect `generate_dataset.py` to understand generation logic; System A’s logic is distributed across 40 authored prompts and a multi-step orchestrator.

---

## What Did Not Improve

### Dataset Diversity

NEO MCP did not improve diversity relative to the baseline. The Claude Code dataset reports:
- 1,133 unique tools (System B: 110)
- Mean nearest-neighbor similarity 0.026 (System B: not reported for its own corpus at soft thresholds)
- Root-cause diversification via 40 independent LLM authors (System B: 194 opening patterns, many recurring at block boundaries)

The NEO MCP dataset has a nominal near-duplicate rate of 1.6% at cosine ≥ 0.85, but its template-based generation introduces structural repetition: categories share `failure_type` prefixes, and root-cause sentences begin with category-fixed phrases. This would be masked by a cosine threshold of 0.85 because the templates are low-similarity at the sentence level when prefixes are short.

### Authoring Depth

System A used 40 parallel LLM authors, each prompt-engineered with anchor examples, domain packs, and diversity constraints. System B used parameterized templates. The resulting prose in System A is more varied at the phrase level; System B reads more predictably.

### Iteration Artifacts

System A documents an explicit improvement phase (7 records patched) and preserves patchable per-batch files. System B reports zero corrections and no improvement phase artifacts. While this may indicate first-pass quality, it also means there is no documented recovery or regeneration process to audit.

---

## Quantitative Comparison

| Dimension | System A (Claude Code) | System B (Claude Code + NEO MCP) | Winner (process) |
|-----------|------------------------|----------------------------------|------------------|
| Records | 1000 | 1000 | Tie |
| Unique tools | 1,133 | 110 | System A |
| Unique failure types | 1,000 / 1,000 | 1,000 (reported) | Tie (unverified) |
| Near-duplicate rate | 0.00% (Jaccard ≥ 0.50) | 1.60% (cosine ≥ 0.85) | System B (guardrail) |
| Max pair similarity | 0.157 | 1.000 (at audit threshold) | System A (textual diversity) |
| Root-cause entropy | 0.026 mean NN sim | 6.062 bits | System B (quantified) |
| Recovery entropy | Implicitly high | 5.071 bits | System B (quantified) |
| Audit component scores | 11 metrics + batch JSONs | 9 scored components + final JSON | System B (gated scoring) |
| Schema errors | 0 | 0 | Tie |
| Deterministic reproduction | No | Yes (seed 42) | System B |
| Generation-time guard | No | Yes (cosine > 0.50) | System B |
| Improvement loop | Yes (7 patches) | No recorded fixes | Tie (complementary) |
| Artifact count | 40+ files | 22 files | Tie |
| Pipeline complexity | High (subagents + orchestrator) | Low (3 scripts) | System B (simplicity) |

---

## Key Findings

1. **NEO MCP improved three process dimensions: determinism, generation-time validation, and audit scoring.** These are structural workflow improvements that make the system more maintainable and auditable.

2. **NEO MCP did not improve dataset-diversity metrics.** The template-based generator produced a dataset with narrower tool vocabulary and detectable structural repetition. Whether this matters depends on the downstream use case (training vs. benchmark).

3. **The Claude Code baseline traded reproducibility for richness.** Its 40-author LLM approach produced more varied tool names and prose but cannot be reliably re-run, and post-hoc dedup is weaker than a generation-time guard.

4. **Similarity-method differences are significant.** System A reports at Jaccard 0.50; System B reports at TF-IDF cosine 0.85. A direct cross-system comparison of duplicate rates is not possible without a common embedding space.

5. **Both systems met all hard numeric targets** (1000 records, exact category balance, exact severity/difficulty distributions, 0 schema errors). On these dimensions, neither workflow produced a better dataset.

---

## Limitations

- **Benchmark scope**: Only two artifacts were compared; both were produced by Claude Code in some configuration. The evaluation cannot isolate NEO MCP from the LLM authoring environment that produced it.
- **Metric asymmetry**: Different similarity thresholds and metrics (Jaccard vs. TF-IDF cosine) make duplicate-rate comparison noise rather than signal.
- **No human evaluation**: No domain experts rated realism or annotation quality; conclusions rely on self-reported automation metrics.
- **Single evaluation**: Only one run of each system was audited; variance across multiple runs is unknown, especially for System A.

---

## Practical Takeaways

**When Claude Code is sufficient:**
- When the team values prose richness and tool-name realism over repeatability.
- When the dataset will be used primarily for model training and every record needs to read as a unique incident.
- When one-shot generation with a post-hoc audit loop is operationally acceptable.

**When NEO MCP provides meaningful value:**
- When the dataset must be regenerated identically for ablation or reversion (benchmarking, CI-pinned artifacts).
- When the team needs auditable generation-time guardrails and machine-readable component scores.
- When operational simplicity (3 scripts vs. K-subagent orchestration) is a priority.
- When near-duplicate rate must be controlled during generation, not detected after.

**Tradeoff:** NEO MCP shifted the system from a *creative* LLM-authoring model to a *deterministic* template-and-guard model. This traded surface-level diversity for engineering rigor.

---

## Conclusion

NEO MCP improved the synthetic data generation workflow on evidence-based, process-level criteria: determinism, generation-time validation, audit scaffolding, and operational simplicity. It did not improve the measured diversity or textual realism of the generated dataset; on those dimensions, the Claude Code baseline remained ahead.

The benchmark does not support a universal verdict that NEO MCP is strictly better or worse. It supports a conditional verdict: **NEO MCP adds value for teams that treat the dataset as an artifact requiring verifiable lineage, and adds less value for teams that treat the dataset as a pure training corpus where prose variety is the highest priority.**

Future work should adopt a common similarity embedding space, add human-rated realism checks, and test whether a hybrid approach—NEO MCP determinism with a richer template vocabulary—can capture both workflow improvements.
