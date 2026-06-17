# Dataset Summary

`agent_failure_dataset.jsonl` — a synthetic dataset of realistic AI agent failures for evaluation, training, and failure-recovery research.

## Dataset Overview

| Attribute | Value |
|---|---|
| Total examples | 1000 |
| Categories | 10 (100 each) |
| Domains | 12 (coding, DevOps/SRE, data, research, cloud, DB, ML, API, finance, support, security, MCP) |
| Schema fields | 15 |
| Composite quality | 98.4/100 |
| Near-dup rate | 1.60% |
| Exact-dup rate | 0.00% |

## Severity & Difficulty

- Severity low: 200 (20.0%)  `█████···················`
- Severity medium: 500 (50.0%)  `████████████············`
- Severity high: 250 (25.0%)  `██████··················`
- Severity critical: 50 (5.0%)  `█·······················`

- Difficulty easy: 300 (30.0%)  `███████·················`
- Difficulty medium: 500 (50.0%)  `████████████············`
- Difficulty hard: 200 (20.0%)  `█████···················`

## Failure Analysis

- Tool-related failures: 300 (30%)
- Planning-related failures: 300 (30%)
- Unique tools referenced: 110
- Avg recovery-plan length: 4.81 steps

## Schema

```json
{
  // id, task, user_request, agent_action, failure_type, failure_category,
  // root_cause, why_it_failed, impact, severity, correct_action,
  // recovery_plan[], expected_tools[], difficulty, evaluation_criteria[]
}
```

## Files

- `agent_failure_dataset.jsonl` — 1000 examples (merged)
- `batch_01.jsonl` … `batch_10.jsonl` — 100-example batches
- `final_audit.json`, `batch_NN_audit.json` — machine-readable audits
- `generate_dataset.py`, `audit_pipeline.py` — reproducible pipeline
- `coverage_report.md`, `audit_report.md`, `taxonomy_definition.md`, `generation_methodology.md`, `dataset_summary.md`
