# Synthetic AI Agent Failure Datasets — A Workflow Benchmark

Two independently generated **1,000-record synthetic datasets of realistic AI agent
failures**, plus the full analysis comparing the two workflows that produced them:

- **System A — `claudecode/`** — Claude Code alone (40 parallel LLM-authoring subagents).
- **System B — `neo-mcp/`** — Claude Code augmented with **NEO MCP** (a deterministic,
  guard-railed generation pipeline).

Both datasets satisfy the same specification — 10 failure categories (100 each), exact
severity (20/50/25/5) and difficulty (30/50/20) distributions, a 15-field JSONL schema,
recovery plans, evaluation criteria, and full audit artifacts. The interesting part is
*how differently* the two workflows got there, and what that says about **dataset
generation quality vs. dataset engineering quality**.

> **Use case.** Each dataset is suitable on its own for agent evaluation, agent training,
> failure-detection and recovery research, tool-calling benchmarks, and MCP-workflow
> evaluation. For high-stakes benchmark construction, consider combining both (dedup
> across them first) — see the recommendation in [`evaluation_report.md`](evaluation_report.md).

---

## TL;DR results

Independent evaluation scorecard (see [`evaluation_report.md`](evaluation_report.md) for
methodology and caveats):

| Dimension | System A (claudecode) | System B (neo-mcp) |
|---|---|---|
| Dataset Quality | 8 | 7 |
| Diversity | 9 | 6 |
| Schema Compliance | 9 | 9 |
| Dataset Utility | 8 | 8 |
| Audit Quality | 8 | 7 |
| Methodology Quality | 9 | 8 |
| Innovation | 7 | 6 |
| **Overall** | **8.3 / 10** | **7.3 / 10** |

Key quantitative differences (⚠️ the two systems use **different** similarity methods, so
diversity numbers are not directly comparable):

| Metric | System A | System B |
|---|---|---|
| Records | 1000 | 1000 |
| Schema errors | 0 | 0 |
| Category / severity / difficulty balance | exact | exact |
| Near-duplicate rate | 0.00% (Jaccard ≥ 0.50) | 1.60% (TF-IDF cosine ≥ 0.85) |
| Unique tools | 1133 | 110 |
| Avg recovery steps | 4.93 | 4.81 |
| Deterministic re-run from a seed | no (LLM-authored) | **yes (byte-for-byte)** |

**The takeaway:** System A optimized for *authorial diversity* (prose richness, tool-name
variety); System B optimized for *engineering rigor* (reproducibility, a generation-time
near-duplicate guard, a structured audit pipeline). Neither is an unqualified winner.

---

## Repository structure

```
.
├── README.md                  ← you are here
├── BLOG.md                    ← narrative write-up of the benchmark
├── case_study.md              ← technical case study (workflow comparison)
├── evaluation_report.md       ← objective head-to-head evaluation + scorecard
│
├── claudecode/                ← System A: Claude Code alone
│   ├── agent_failure_dataset.jsonl      (1000 records)
│   ├── SPEC.md                          generation spec read by every subagent
│   ├── taxonomy_definition.md
│   ├── generation_methodology.md
│   ├── coverage_report.md / audit_report.md / dataset_summary.md
│   ├── data/batches/                    40 per-category chunk files
│   ├── artifacts/                       per-batch + global audits, metrics, prompts
│   └── tools/                           dataset_tools.py, build_reports.py, make_assignments.py
│
└── neo-mcp/                    ← System B: Claude Code + NEO MCP
    ├── agent_failure_dataset.jsonl      (1000 records)
    ├── generate_dataset.py              compositional generator + near-dup guard
    ├── audit_pipeline.py                schema/dedup/distribution/diversity audit
    ├── gen_reports.py                   builds the markdown reports from the audit
    ├── batch_01..10.jsonl               100-record batches
    ├── final_audit.json / batch_NN_audit.json
    ├── taxonomy_definition.md
    ├── generation_methodology.md
    └── coverage_report.md / audit_report.md / dataset_summary.md
```

---

## The dataset

Both systems emit the same 15-field JSONL schema, one record per line:

| Field | Description |
|---|---|
| `id` | Stable identifier |
| `task` | What the agent was doing |
| `user_request` | The instruction the agent received |
| `agent_action` | What the agent actually did (the failure) |
| `failure_type` | Machine slug of the category |
| `failure_category` | One of the 10 categories |
| `root_cause` | What failed, mechanically |
| `why_it_failed` | The assumption/omission behind the failure |
| `impact` | Consequence |
| `severity` | `low` / `medium` / `high` / `critical` |
| `correct_action` | What the agent should have done |
| `recovery_plan` | Ordered steps to detect, contain, and fix |
| `expected_tools` | Tools relevant to doing it correctly |
| `difficulty` | `easy` / `medium` / `hard` |
| `evaluation_criteria` | Questions a grader uses to judge an agent |

**The 10 failure categories** (100 records each): Wrong Tool Selection · Incorrect
Parameters · Missing Parameters · Incomplete Workflow · Incorrect Planning · Hallucinated
Information · Insufficient Research · Context Loss · Multi-Step Execution Failure ·
Recovery Failure. Full definitions in each system's `taxonomy_definition.md`.

---

## Reproducing the datasets

### System B (`neo-mcp/`) — deterministic

```bash
cd neo-mcp
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

python3 generate_dataset.py --total 1000 --seed 42      # -> agent_failure_dataset.jsonl + batch_NN.jsonl
python3 audit_pipeline.py --input agent_failure_dataset.jsonl --output final_audit.json
python3 gen_reports.py                                   # -> coverage/audit/summary .md
```

Same seed → byte-for-byte identical output. The generator enforces diversity *at
generation time*: every candidate is screened against all accepted records (cosine
< 0.50 over the same text the audit scores) before being kept.

### System A (`claudecode/`) — LLM-authored

System A's records were authored by 40 parallel LLM subagents following
[`claudecode/SPEC.md`](claudecode/SPEC.md); the per-chunk prompts are preserved under
`claudecode/artifacts/prompts/`. Because generation is model-authored it is not strictly
reproducible, but the post-processing/audit tooling is in `claudecode/tools/`:

```bash
cd claudecode
python3 tools/dataset_tools.py    # validation / merge / dedup helpers
python3 tools/build_reports.py    # rebuild the markdown reports
```

---

## Read more

- **[BLOG.md](BLOG.md)** — *From Dataset Generation to Dataset Engineering: What Changed
  When We Added NEO MCP.*
- **[case_study.md](case_study.md)** — technical case study of the two workflows.
- **[evaluation_report.md](evaluation_report.md)** — objective, neutral head-to-head with
  the full scorecard, quantitative tables, and per-system strengths/weaknesses.

---

## License

Released under the [MIT License](LICENSE) (a permissive default — change it if your
intended distribution terms differ; datasets are sometimes released under CC-BY instead).
The data is **synthetic** — no real users, systems, or incidents are described.
