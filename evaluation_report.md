# Synthetic Dataset Generation Evaluation Report

## Executive Summary

This report objectively evaluates two 1000-record synthetic AI agent failure datasets produced for the same task specification. **System A** (`claudecode`) and **System B** (`neo-mcp`) both produced 1000-example JSONL datasets covering 10 failure categories, with balanced severity and difficulty distributions.

Both systems produce datasets that are fit for the stated purpose, but they differ significantly in their measured diversity characteristics. System A reports substantially higher diversity metrics on most dimensions, while System B reports a modest near-duplicate rate (1.6%) and a much smaller tool vocabulary (110 vs 1133 unique tools). Neither system's reports include embedding-based semantic similarity checks, so conclusions about uniqueness are bounded by the applicable lexical methods.

No declared winner is warranted; the datasets are structurally comparable, and System B's near-duplicate rate is below a 5% intervention threshold without any reported post-hoc fixes.

---

## Scorecard

| Category | System A | System B |
| -------- | -------- | -------- |
| Dataset Quality | 8 | 7 |
| Diversity | 9 | 6 |
| Schema Compliance | 9 | 9 |
| Dataset Utility | 8 | 8 |
| Audit Quality | 8 | 7 |
| Methodology Quality | 9 | 8 |
| Innovation | 7 | 6 |
| **Overall** | **8.3 / 10** | **7.3 / 10** |

---

## Quantitative Analysis

| Metric | System A | System B |
|--------|----------|----------|
| Record count | 1000 | 1000 |
| Unique `failure_type` strings | 1000 / 1000 | reported 1000 |
| Unique `root_cause` (normalized) | 1000 / 1000 | 194 patterns |
| Near-duplicate rate | 0.00% (Jaccard ≥ 0.50) | 1.60% (cosine ≥ 0.85) |
| Max pair similarity | 0.157 | 1.000 (threshold 0.85) |
| Unique tools | 1133 | 110 |
| Avg tools per record | 3.26 | 3.52 |
| Avg recovery steps | 4.93 | 4.81 |
| Schema errors | 0 | 0 |
| Field completeness | 15 / 15 | 15 / 15 |
| Category balance | exact ±0 | exact ±0 |
| Severity balance | exact | exact |
| Difficulty balance | exact | exact |

> Note: similarity methods differ between systems (Jaccard ≥ 0.50 for System A, TF-IDF cosine ≥ 0.85 for System B), so the metrics are not directly comparable.

---

## Strengths of System A

- **Authoring model**: 40 parallel LLM subagents produced original prose, yielding 1133 distinct tool names and 2000 unique user-request / root-cause strings at the token level.
- **Literal uniqueness**: 100% unique `failure_type` strings and 100% unique `root_cause` strings at the reported threshold, with mean nearest-neighbour similarity of 0.026 and a maximum of 0.157.
- **Tool vocabulary breadth**: 1133 distinct tools vs System B's 110, reflecting richer domain variation across MCP, cloud, data, DevOps, and mobile.
- **Domain coverage**: 22 named domain packs and a rotating domain-assignment scheme across categories and chunks.
- **Improvement loop**: One documented verification-and-patch pass corrected 7 records before publication.
- **Anchor examples**: The spec included two full example records, raising the prose quality bar for all subagents.

## Weaknesses of System A

- **Methodology limitation**: Near-duplicate detection is lexical (Jaccard 3-gram shingles); similarity thresholds between 0.50 and 0.85 are not reported, so near-duplicate rate is sensitive to the chosen threshold. It is unclear how many additional pairs exist between 0.157 (System A's max) and 0.85 (System B's threshold), making cross-system comparison unreliable.
- **Category labeling**: Rather than an independent judge re-verification, category labels were enforced at assignment time and spot-checked only.
- **Impact text**: The methodology states that impact text is tiered by severity rather than bespoke per scenario, which may create surface-level similarity within severity bands.
- **No deterministic seed**: Generation depends on LLM subagents; strict byte-for-byte reproducibility is not claimed.

## Strengths of System B

- **Deterministic pipeline**: Reproducible from a fixed seed (default 42) with no external dependencies; re-running produces byte-for-byte identical files and reports.
- **Generation-time near-dup guard**: Streaming HashingVectorizer rejects any candidate whose cosine similarity to an already-accepted example exceeds 0.50 during *generation*, not only after, keeping 16 of ~44k candidates in ~44k rejected.
- **Plain schema, straightforward tooling**: Single-file merged `agent_failure_dataset.jsonl`, JSON audit logs, and a 3-script pipeline (`generate_dataset.py`, `audit_pipeline.py`, `gen_reports.py`) built on scikit-learn without auxiliary orchestration.
- **Explicit near-dup rate at audit threshold**: Reports 1.60% near-duplicate pairs at TF-IDF cosine 0.85, well under a typical 5% intervention threshold; no post-hoc fixes were needed.

## Weaknesses of System B

- **Narrow tool vocabulary**: 110 unique tools vs 1133 — the `expected_tools` field appears repetitive. The top tool (`terraform_apply`) appears 59 times in a 1000-record dataset, suggesting limited domain variation.
- **Root-cause templating**: 194 root-cause opening patterns across 1000 records; the audit shows categories share identical prefixes (e.g. "Workflow terminated early: the agent treated" × 100, "Tool selected by surface-level name matching" × 100, "Flawed plan structure: the ordering/strategy was" × 100), indicating high within-category formatting similarity.
- **Recovery diversity**: First-step patterns show category-uniform prefixes (199 unique patterns, but top six each recur exactly 100 times), reducing trajectory diversity.
- **Less detailed methodology documentation**: No explicit domain-pack list, no documented per-batch subagent provenance, and no description of the template-replacement semantics.

## Key Differences

1. **Diversity mechanism**: System A achieves high diversity via many independent LLM subagents; System B achieves moderate diversity via a streaming vectorizer guard plus per-category builder templates. System A reports stronger diversity metrics wherever the methods allow comparison.

2. **Tool vocabulary realism**: System A cites realistic, differentiated tools (1133 unique names including MCP paths like `mcp__github__create_pull_request`, `gdrive.files.export`, `bigquery.jobs.query`). System B cites 110 generic tool names (`open_file`, `search_web`, `run_query`, `terraform_apply`) repeated many times.

3. **Reproducibility**: System B's output is deterministic from a seed; System A's LLM-authored subagent output is not strictly reproducible without re-running the same generation tasks.

4. **Audit depth**: System A reports 11 numeric metrics in `artifacts/metrics.json` plus per-batch audit JSON; System B reports 20 component scores in `final_audit.json` plus root-cause entropy and recovery first-step entropy. System A covers more text-level statistics; System B provides more usable per-dimension scoring.

5. **Correction history**: System A had a single documented improvement cycle (7 records patched); System B reports zero corrections and states no errors or warnings at generation time.

6. **Category uniformity risk**: System B's root-cause audit reveals top patterns repeated 100 times within a category. This structure is detectably mechanical to a human annotator.

---

## Recommendation

Neither dataset is meaningfully superior in all dimensions.

- If the priority is **maximal lexical diversity and tool-name realism for model training**, System A is superior.
- If the priority is **deterministic reproducibility and a verifiable near-duplicate guard at generation time**, System B is superior.
- For end-use as an **LLM-judge or failure-detection benchmark**, both datasets are suitable. System A's more unique tool names and lower measured similarity may slightly reduce label leakage, while System B's tighter audit scaffolding makes it easier to re-run validation.
- Recommend **combining the datasets** (duplicate-checking across them first) to maximize coverage before using either for high-stakes benchmark construction.

---

## Overall Assessment

The difference is **not insignificant** but is not large enough to declare an unqualified winner. On the evaluated criteria, System A (claudecode) outperforms System B (neo-mcp) by approximately 1 point overall, primarily on diversity and tool-vocabulary breadth. System B compensates with superior reproducibility and cleaner generation-time anti-duplication. Both datasets are structurally valid, category-balanced, and suitable for the original task. Benchmark builders using either dataset should run their own semantic-embedding dedup pass as a final safeguard before commitment.
