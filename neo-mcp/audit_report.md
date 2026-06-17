# Audit Report

Full reproducible audit of `agent_failure_dataset.jsonl` produced by `audit_pipeline.py`.

## Dataset Overview

- **Total examples:** 1000
- **Categories:** 10 (each at 100)
- **Severity distribution:** low 20.0%, medium 50.0%, high 25.0%, critical 5.0%
- **Difficulty distribution:** easy 30.0%, medium 50.0%, hard 20.0%

## Failure Analysis

**Most common failure types:** all ten categories are represented equally (100 each) by design, so no single failure type dominates.

**Most severe failure types:** critical-severity examples by category —

| Category | Critical |
|---|---|
| Incomplete Workflow | 8 |
| Missing Parameters | 7 |
| Context Loss | 7 |
| Hallucinated Information | 5 |
| Incorrect Parameters | 5 |
| Wrong Tool Selection | 5 |
| Insufficient Research | 5 |
| Recovery Failure | 4 |
| Incorrect Planning | 3 |
| Multi-Step Execution Failure | 1 |

**Tool-related failures** (Wrong Tool Selection + Incorrect/Missing Parameters): **300** examples (30%).

**Planning-related failures** (Incorrect Planning + Incomplete Workflow + Multi-Step Execution Failure): **300** examples (30%).

## Diversity Metrics

- **Failure / tool diversity:** 110 unique tools across 3518 occurrences (3.52 per example).
- **Root-cause diversity:** 194 unique root-cause opening patterns; entropy 6.0618 bits.
- **Recovery diversity:** 199 unique recovery first-step patterns; entropy 5.071 bits; avg 4.81 steps/plan.

## Quality Metrics

- **Schema validity:** 1000/1000 (100%).
- **Exact duplicate rate:** 0 (0.00%).
- **Near-duplicate rate (TF-IDF cosine > 0.85):** 16 pairs (1.60%) — target < 5%.
- **Composite quality score:** **98.4/100**.

Component scores:

| Component | Score |
|---|---|
| schema_score | 100.0 |
| exact_dup_score | 100.0 |
| near_dup_score | 84.0 |
| category_balance_score | 100.0 |
| severity_score | 100.0 |
| difficulty_score | 100.0 |
| diversity_score | 100.0 |

## Recommendations

- **Future expansions:** add adversarial/multi-failure examples (more than one root cause per trace), full multi-turn transcripts, and tool-call JSON payloads to support executable benchmarks.
- **Benchmark use cases:** failure-detection classifiers, recovery-plan generation/evaluation, root-cause attribution, severity triage, and tool-selection robustness tests.
- **Known limitations:** examples are single-failure, single-turn, and synthetic; impact text is tiered by severity rather than fully bespoke. See `generation_methodology.md`.
