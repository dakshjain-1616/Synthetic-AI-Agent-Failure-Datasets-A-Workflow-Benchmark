# Audit Report

Automated audit of `agent_failure_dataset.jsonl` (1000 records). Produced by `tools/dataset_tools.py` (validate/dedup/audit) and `tools/build_reports.py`.

## 1. Schema validation

- **Errors: 0.** Every record has exactly the 15 required keys with correct types.
- All `id` values match `afd_NNNN`, are unique, and run contiguously afd_0001–afd_1000.
- All `failure_category`, `severity`, `difficulty` values are in-vocabulary.
- All list fields (`recovery_plan`, `expected_tools`, `evaluation_criteria`) are non-empty lists of non-empty strings.

## 2. Duplicate & near-duplicate analysis

- **Exact (normalized) duplicate pairs: 0.**
- **Pairs above 0.92 Jaccard similarity: 0.**
- **Pairs above 0.50 Jaccard similarity: 0.**
- Signature = `user_request + agent_action + root_cause + failure_type`, 3-gram shingles.

### Nearest-neighbour similarity (each record vs its most similar peer)

| Metric | Value |
|---|---:|
| Mean nearest-neighbour similarity | 0.026 |
| Median (p50) | 0.022 |
| p90 | 0.044 |
| p99 | 0.086 |
| Max | 0.157 |
| Pairs with similarity ≥ 0.40 | 0 |

No pair reached 0.40 similarity — the dataset is highly diverse.

## 3. Diversity metrics

| Metric | Value |
|---|---:|
| Unique `failure_type` strings | 1000 / 1000 |
| Unique `root_cause` (normalized) | 1000 / 1000 |
| Unique `user_request` (normalized) | 1000 / 1000 |
| Unique tools in `expected_tools` | 1133 |
| Total tool mentions | 3256 |
| Avg tools per record | 3.26 |
| Unique recovery-plan steps | 4916 / 4928 |
| Avg recovery-plan length | 4.93 steps (range 4–6) |
| Unique evaluation criteria | 2954 |
| Avg evaluation criteria per record | 2.96 |

Most-repeated recovery step (max repetition is tiny relative to 1000 records):

- `run nginx t and reload` ×3
- `cancel the blocking statement if still running` ×2
- `re run ci to confirm green` ×2
- `confirm pods reach ready` ×2
- `kill the diverging run` ×2

## 4. Tool diversity — top tools

| Tool | Mentions |
|---|---:|
| `Read` | 184 |
| `Bash` | 99 |
| `Edit` | 76 |
| `psql` | 57 |
| `ripgrep` | 46 |
| `curl` | 44 |
| `web_search` | 44 |
| `bigquery.jobs.query` | 34 |
| `gdrive.files.list` | 30 |
| `Grep` | 29 |
| `gdrive.files.get` | 28 |
| `pytest` | 28 |
| `terraform plan` | 27 |
| `WebFetch` | 24 |
| `terraform apply` | 21 |
| `grep` | 20 |
| `dbt run` | 19 |
| `embeddings.create` | 19 |
| `gmail.messages.list` | 18 |
| `fastlane` | 18 |

## 5. Severity-weighted findings

Severity score = mean severity weight per category (Low=1 … Critical=4).

| Category | High+Critical | Severity score |
|---|---:|---:|
| Wrong Tool Selection | 30 | 2.15 |
| Incorrect Parameters | 30 | 2.15 |
| Missing Parameters | 30 | 2.15 |
| Incomplete Workflow | 30 | 2.15 |
| Incorrect Planning | 30 | 2.15 |
| Hallucinated Information | 30 | 2.15 |
| Insufficient Research | 30 | 2.15 |
| Context Loss | 30 | 2.15 |
| Multi-Step Execution Failure | 30 | 2.15 |
| Recovery Failure | 30 | 2.15 |

## 6. Findings & quality gate

| Gate | Target | Result | Status |
|---|---|---|---|
| Category balance | 100 each | 100 each | ✅ |
| Severity distribution | 20/50/25/5 | 20/50/25/5 | ✅ |
| Difficulty distribution | 30/50/20 | 30/50/20 | ✅ |
| Schema errors | 0 | 0 | ✅ |
| Exact duplicates | 0 | 0 | ✅ |
| Near-dup pairs (≥0.5) | 0 | 0 | ✅ |
| Unique failure types | ≥ 950 | 1000 | ✅ |
| Unique tools | ≥ 300 | 1133 | ✅ |

All quality gates pass. No further improvement rounds required.
