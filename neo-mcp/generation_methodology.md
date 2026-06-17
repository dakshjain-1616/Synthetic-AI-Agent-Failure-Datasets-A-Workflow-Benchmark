# Generation Methodology

## Overview

The dataset is produced by a single reproducible pipeline:

```
generate_dataset.py  →  agent_failure_dataset.jsonl (+ batch_NN.jsonl)
audit_pipeline.py    →  final_audit.json (+ batch_NN_audit.json)
gen_reports.py       →  coverage_report.md, audit_report.md, dataset_summary.md
```

Everything is deterministic from `--seed` (default 42). Re-running reproduces the dataset
and every metric byte-for-byte.

## Reference datasets

We analyzed the **structure and task design** of BFCL v3, xLAM Function-Calling 60K, and
GAIA — how they frame tools, parameters, multi-step tasks, and graded answers — and used
those conventions to shape our schema (explicit `expected_tools`, `evaluation_criteria`,
difficulty tiers). No examples were copied; all 1000 failures are original.

## Compositional generation (not slot templates)

Each example is assembled by **joining already-resolved string fragments** drawn
independently from many pools:

- **12 domains** (coding, DevOps/SRE, data pipelines, web research, cloud infra, DB admin,
  ML training, API integration, finance ops, support automation, security audit, MCP
  workflows). Each domain supplies concrete tools, file paths/artifacts, entities, and
  realistic error strings.
- **Per-category builders** encode the *mechanism* of each failure and select among many
  phrasings for `user_request`, `agent_action`, `root_cause`, `why_it_failed`,
  `correct_action`, and a category-specific ordered `recovery_plan`.
- **Severity-tiered impact** text so consequences match the assigned severity.

Because there is no brace/slot substitution anywhere, unfilled `{placeholder}` output is
structurally impossible; a final `assert_no_placeholder` check rejects any field still
containing `{` or `}`.

## Diversity by construction

Rather than deduplicating after the fact, diversity is enforced at generation time:

- A streaming **near-duplicate guard** vectorizes each candidate with a stateless
  `HashingVectorizer` over the *same* text the audit scores (`user_request +
  agent_action + failure_type`) and rejects any candidate whose cosine similarity to an
  already-accepted example exceeds **0.50** — well below the audit's 0.85 flag threshold.
- An **exact-key guard** rejects any candidate whose `(user_request, agent_action,
  failure_type, root_cause)` tuple was already used.

In the final run ~44k candidates were rejected to land 1000 highly-distinct examples.

## Distribution control

Severity and difficulty labels are pre-allocated to **exact quotas**
(severity 20/50/25/5; difficulty 30/50/20) and shuffled, so the realized distribution
hits target with zero deviation. Categories are planned at exactly 100 each and
interleaved across the ten batch files, so every batch is itself category-balanced.

## Validation & audit loop

After generation, `audit_pipeline.py` runs schema validation, exact + TF-IDF near-dup
detection, category/severity/difficulty balance, and tool/root-cause/recovery diversity,
emitting a composite quality score. Each batch is audited individually and the merged
dataset is audited as a whole.

## Provenance note

An initial template-based generator produced a complete but low-diversity dataset
(~293% near-duplicate pairs). That approach was discarded and replaced with the
compositional generator and generation-time diversity guard described here, which brought
the near-duplicate rate to ~1.6% while keeping schema validity at 100% and all
distributions on target.

## Known limitations

- Examples are **single-failure** and **single-turn**; real traces often chain multiple
  faults across many turns.
- `impact` is tiered by severity rather than fully bespoke per scenario.
- Text is synthetic and English-only. See `audit_report.md` → Recommendations for
  proposed expansions (multi-turn transcripts, executable tool-call payloads,
  multi-root-cause traces).
