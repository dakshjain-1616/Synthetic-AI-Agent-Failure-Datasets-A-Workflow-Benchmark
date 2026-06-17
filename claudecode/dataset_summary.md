# Dataset Summary — Synthetic AI Agent Failure Dataset

Final report for `agent_failure_dataset.jsonl`. Companion documents:
[`taxonomy_definition.md`](taxonomy_definition.md),
[`generation_methodology.md`](generation_methodology.md),
[`coverage_report.md`](coverage_report.md), [`audit_report.md`](audit_report.md).

---

## Dataset Overview

- **Total examples:** 1000 (JSONL, one object per line, ids `afd_0001`–`afd_1000`).
- **Schema:** 15 fields per record — `id, task, user_request, agent_action,
  failure_type, failure_category, root_cause, why_it_failed, impact, severity,
  correct_action, recovery_plan, expected_tools, difficulty, evaluation_criteria`.
- **Categories (10 × 100, exact):** Wrong Tool Selection · Incorrect Parameters ·
  Missing Parameters · Incomplete Workflow · Incorrect Planning · Hallucinated
  Information · Insufficient Research · Context Loss · Multi-Step Execution Failure ·
  Recovery Failure.

**Severity distribution** (target met exactly):

| Low | Medium | High | Critical |
|---:|---:|---:|---:|
| 200 (20%) | 500 (50%) | 250 (25%) | 50 (5%) |

**Difficulty distribution** (target met exactly):

| Easy | Medium | Hard |
|---:|---:|---:|
| 300 (30%) | 500 (50%) | 200 (20%) |

Domains span AI coding assistants, research agents, generic tool-using agents,
workflow-automation agents, and MCP-enabled systems (GitHub, Slack, Google Drive,
Gmail, Calendar, Notion), across backend/frontend code, CI/CD, Kubernetes,
Terraform/cloud, data-warehouse SQL, ETL, ML training, observability, security
scanning, DB migrations, mobile, payments, and CRM.

## Failure Analysis

- **Most common failure types.** By design the 10 categories are perfectly balanced
  (100 each), so no category dominates. Within categories, mechanisms are highly
  varied: all **1000 `failure_type` strings are unique**. Recurring *shapes* across
  the dataset include wrong-environment targeting, unit/format/timezone parameter
  errors, omitted filters/scopes/idempotency keys, early workflow termination
  (changes made but never committed/published/notified), swallowed non-zero exit
  codes, dropped pagination cursors, ungrounded API/field/citation fabrication, and
  verbatim or non-idempotent retries.
- **Most severe failure types.** 50 Critical and 250 High examples (30 High+Critical
  per category — uniform by construction). The Critical tier concentrates
  irreversible, production-grade harm: destructive data operations (topic/table/
  PVC deletion, year-agnostic `DELETE`, BIGINT backfill data loss), security
  exposure (credential leaks to public channels, auth-bypass via omitted JWT claim
  verification, secrets overwritten across environments), money movement (100×
  Stripe refunds, duplicate refunds), and prod-breaking deploys (debug build to
  prod, Terraform force-unlock corrupting state).
- **Tool-related failures.** 300 examples (Wrong Tool Selection + Incorrect
  Parameters + Missing Parameters) — the call-level failures most relevant to
  function-calling benchmarks.
- **Planning-related failures.** 300 examples (Incorrect Planning + Incomplete
  Workflow + Multi-Step Execution Failure) — trajectory/orchestration failures most
  relevant to autonomous-agent and GAIA-style evaluation. The remaining 400 cover
  knowledge/grounding (Hallucinated Information, Insufficient Research), session
  state (Context Loss), and error-handling (Recovery Failure).

## Diversity Metrics

| Dimension | Value |
|---|---|
| Unique `failure_type` strings | **1000 / 1000** |
| Unique `root_cause` (normalized) | **1000 / 1000** |
| Unique `user_request` (normalized) | **1000 / 1000** |
| Unique tools across `expected_tools` | **1133** |
| Total tool mentions / avg per record | 3256 / **3.26** |
| Unique recovery-plan steps | **4916 / 4928** |
| Avg recovery-plan length | **4.93 steps** |
| Unique evaluation criteria | 2954 (avg 2.96/record) |

- **Failure diversity:** every failure type and root cause is distinct; mechanisms
  are spread across 22 domains via a rotating domain-assignment scheme.
- **Recovery diversity:** 4916 of 4928 recovery steps are unique — the single
  most-repeated step recurs only ~3 times. Recovery plans follow a realistic
  detect → contain → correct → verify → harden arc rather than boilerplate.
- **Tool diversity:** 1133 distinct tools spanning coding/file tools (Read, Edit,
  Bash, ripgrep, pytest), data (`psql`, `bigquery.jobs.query`), web (`web_search`,
  `curl`), and MCP servers (`mcp__github__*`, `gdrive.*`, `slack.*`).

## Quality Metrics

| Metric | Result |
|---|---|
| Schema errors | **0** |
| Schema warnings | **0** |
| Exact (normalized) duplicate pairs | **0** |
| Near-duplicate pairs (Jaccard ≥ 0.50) | **0** |
| Mean nearest-neighbour similarity | **0.026** |
| Max nearest-neighbour similarity | **0.157** |
| p99 nearest-neighbour similarity | 0.086 |
| Category / severity / difficulty match | **exact on all 17 buckets** |
| **Coverage score** | **100%** |

**Similarity analysis.** Using 3-gram shingle Jaccard over
`user_request + agent_action + root_cause + failure_type`, no two records exceed
**0.16** similarity, and the median record's closest neighbour sits at 0.022. The
dataset contains no templated or paraphrased repetition.

## Recommendations

**Future dataset expansions**
- Add multi-turn *trajectories* (full tool-call sequences with intermediate
  observations), not just single-point failure descriptions, for trajectory-level
  scoring.
- Add paired **success** trajectories for each failure (contrastive pairs) to
  support reward-model / verifier training.
- Add an `is_failure` mix including *near-miss* and *correct-but-risky* cases so
  detectors must avoid false positives.
- Layer an embedding-based semantic-dedup pass and an independent judge model to
  re-verify `failure_category` labels at scale.
- Extend domains (robotics/computer-use, voice agents, multi-agent hand-offs) and
  add localized/non-English requests.

**Potential benchmark use cases**
- **Failure-detection benchmark:** given `user_request` + `agent_action`, predict
  `failure_category` and `severity`.
- **Recovery benchmark:** given the failure, generate a recovery plan; score against
  `recovery_plan` / `evaluation_criteria`.
- **Tool-calling robustness:** the 300 tool-related records test wrong-tool /
  wrong-param / missing-param discrimination (BFCL/xLAM-style).
- **Autonomous-agent evaluation:** the 300 planning-related + 100 multi-step records
  suit GAIA-style multi-step orchestration grading.
- **MCP-ecosystem benchmarking:** 301 records reference MCP servers (GitHub, Slack,
  Drive, Gmail, Calendar, Notion) directly, and 497 reference MCP servers and/or
  cloud/devops tooling, for MCP-workflow eval.
- **Evaluator/LLM-judge training:** `evaluation_criteria` give per-example rubrics.

## Success Criteria — coverage

The dataset is suitable for every target use case in the brief:

| Use case | Supported by |
|---|---|
| AI agent evaluation | balanced categories, severity, difficulty + `evaluation_criteria` |
| AI agent training | 1000 grounded failure→correct_action→recovery triples |
| MCP ecosystem benchmarking | 497 MCP/devops-tool records (301 MCP-server direct) |
| Failure-recovery research | every record has a concrete, diverse `recovery_plan` |
| Tool-calling research | 300 tool-related records with realistic `expected_tools` |
| Autonomous-workflow evaluation | 400 planning/multi-step/recovery records |

## Deliverables index

| File | Contents |
|---|---|
| `agent_failure_dataset.jsonl` | 1000 records (the dataset) |
| `taxonomy_definition.md` | schema + 10-category / severity / difficulty taxonomy |
| `generation_methodology.md` | reference analysis, architecture, validation, limitations |
| `coverage_report.md` | category/severity/difficulty coverage + cross-tabs |
| `audit_report.md` | schema, duplication, similarity, diversity audit |
| `dataset_summary.md` | this final report |
| `tools/` | `dataset_tools.py`, `make_assignments.py`, `build_reports.py` |
| `artifacts/` | per-batch audits, global metrics, subagent assignment prompts |
