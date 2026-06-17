#!/usr/bin/env python3
"""Generate the data-driven Markdown reports from the dataset + final_audit.json."""
import json
from collections import Counter

A = json.load(open("final_audit.json"))
EX = [json.loads(l) for l in open("agent_failure_dataset.jsonl")]
N = len(EX)

CATS = A["category_balance"]["counts"]
SEV = A["severity_distribution"]
DIF = A["difficulty_distribution"]
ND = A["near_duplicates"]
ED = A["exact_duplicates"]
TD = A["tool_diversity"]
RC = A["root_cause_diversity"]
RP = A["recovery_plan_diversity"]
QS = A["quality_score"]

# Cross-tabs.
sev_by_cat = Counter()
tool_failure_cats = {"Wrong Tool Selection", "Incorrect Parameters", "Missing Parameters"}
plan_failure_cats = {"Incorrect Planning", "Incomplete Workflow", "Multi-Step Execution Failure"}
tool_n = sum(1 for e in EX if e["failure_category"] in tool_failure_cats)
plan_n = sum(1 for e in EX if e["failure_category"] in plan_failure_cats)
crit_by_cat = Counter(e["failure_category"] for e in EX if e["severity"] == "critical")
high_by_cat = Counter(e["failure_category"] for e in EX if e["severity"] in ("high", "critical"))


def bar(pct, width=24):
    f = int(round(pct / 100 * width))
    return "█" * f + "·" * (width - f)


# ----------------------------------------------------------------- coverage
with open("coverage_report.md", "w") as f:
    f.write("# Coverage Report\n\n")
    f.write(f"Total examples: **{N}**\n\n")
    f.write("## Failure Category Coverage\n\n")
    f.write("| Category | Count | Share |\n|---|---|---|\n")
    for c, n in sorted(CATS.items()):
        f.write(f"| {c} | {n} | {n/N*100:.1f}% |\n")
    f.write(f"\nAll 10 categories at exactly {N//10} examples — perfectly balanced "
            f"(max deviation {A['category_balance']['max_deviation']:+.0f}).\n\n")

    f.write("## Severity Coverage\n\n| Severity | Count | Actual | Target |\n|---|---|---|---|\n")
    for s in ["low", "medium", "high", "critical"]:
        f.write(f"| {s} | {SEV['counts'][s]} | {SEV['actual_pcts'][s]}% | {SEV['target_pcts'][s]}% |\n")
    f.write(f"\nWithin ±5% tolerance: **{SEV['within_tolerance']}**\n\n")

    f.write("## Difficulty Coverage\n\n| Difficulty | Count | Actual | Target |\n|---|---|---|---|\n")
    for d in ["easy", "medium", "hard"]:
        f.write(f"| {d} | {DIF['counts'][d]} | {DIF['actual_pcts'][d]}% | {DIF['target_pcts'][d]}% |\n")
    f.write(f"\nWithin ±5% tolerance: **{DIF['within_tolerance']}**\n\n")

    f.write("## High-severity concentration by category\n\n")
    f.write("Count of high+critical examples per category (informational; severity is assigned "
            "independently of category so the spread is roughly uniform):\n\n")
    f.write("| Category | High+Critical |\n|---|---|\n")
    for c in sorted(CATS):
        f.write(f"| {c} | {high_by_cat.get(c,0)} |\n")

# ----------------------------------------------------------------- audit
with open("audit_report.md", "w") as f:
    f.write("# Audit Report\n\n")
    f.write("Full reproducible audit of `agent_failure_dataset.jsonl` produced by `audit_pipeline.py`.\n\n")

    f.write("## Dataset Overview\n\n")
    f.write(f"- **Total examples:** {N}\n")
    f.write(f"- **Categories:** {len(CATS)} (each at {N//10})\n")
    f.write("- **Severity distribution:** "
            + ", ".join(f"{s} {SEV['actual_pcts'][s]}%" for s in ['low','medium','high','critical']) + "\n")
    f.write("- **Difficulty distribution:** "
            + ", ".join(f"{d} {DIF['actual_pcts'][d]}%" for d in ['easy','medium','hard']) + "\n\n")

    f.write("## Failure Analysis\n\n")
    f.write("**Most common failure types:** all ten categories are represented equally "
            f"({N//10} each) by design, so no single failure type dominates.\n\n")
    f.write("**Most severe failure types:** critical-severity examples by category —\n\n")
    f.write("| Category | Critical |\n|---|---|\n")
    for c, n in crit_by_cat.most_common():
        f.write(f"| {c} | {n} |\n")
    f.write(f"\n**Tool-related failures** (Wrong Tool Selection + Incorrect/Missing Parameters): "
            f"**{tool_n}** examples ({tool_n/N*100:.0f}%).\n\n")
    f.write(f"**Planning-related failures** (Incorrect Planning + Incomplete Workflow + "
            f"Multi-Step Execution Failure): **{plan_n}** examples ({plan_n/N*100:.0f}%).\n\n")

    f.write("## Diversity Metrics\n\n")
    f.write(f"- **Failure / tool diversity:** {TD['unique_tools']} unique tools across "
            f"{TD['total_tool_occurrences']} occurrences ({TD['avg_tools_per_example']} per example).\n")
    f.write(f"- **Root-cause diversity:** {RC['unique_root_cause_patterns']} unique root-cause "
            f"opening patterns; entropy {RC['root_cause_entropy']} bits.\n")
    f.write(f"- **Recovery diversity:** {RP['unique_first_step_patterns']} unique recovery first-step "
            f"patterns; entropy {RP['first_step_pattern_entropy']} bits; avg {RP['avg_steps_per_plan']} steps/plan.\n\n")

    f.write("## Quality Metrics\n\n")
    f.write(f"- **Schema validity:** {A['schema_validation']['passed']}/{N} "
            f"({A['schema_validation']['passed']/N*100:.0f}%).\n")
    f.write(f"- **Exact duplicate rate:** {ED['total_exact_duplicates']} ({ED['exact_duplicate_rate']*100:.2f}%).\n")
    f.write(f"- **Near-duplicate rate (TF-IDF cosine > {ND['threshold_used']}):** "
            f"{ND['total_near_duplicates']} pairs ({ND['near_duplicate_rate']*100:.2f}%) — target < 5%.\n")
    f.write(f"- **Composite quality score:** **{QS['composite_quality_score']}/100**.\n\n")
    f.write("Component scores:\n\n| Component | Score |\n|---|---|\n")
    for k in ["schema_score","exact_dup_score","near_dup_score","category_balance_score",
              "severity_score","difficulty_score","diversity_score"]:
        f.write(f"| {k} | {QS[k]} |\n")

    f.write("\n## Recommendations\n\n")
    f.write("- **Future expansions:** add adversarial/multi-failure examples (more than one root cause per "
            "trace), full multi-turn transcripts, and tool-call JSON payloads to support executable benchmarks.\n")
    f.write("- **Benchmark use cases:** failure-detection classifiers, recovery-plan generation/evaluation, "
            "root-cause attribution, severity triage, and tool-selection robustness tests.\n")
    f.write("- **Known limitations:** examples are single-failure, single-turn, and synthetic; impact text is "
            "tiered by severity rather than fully bespoke. See `generation_methodology.md`.\n")

# ----------------------------------------------------------------- summary
with open("dataset_summary.md", "w") as f:
    f.write("# Dataset Summary\n\n")
    f.write("`agent_failure_dataset.jsonl` — a synthetic dataset of realistic AI agent failures for "
            "evaluation, training, and failure-recovery research.\n\n")
    f.write("## Dataset Overview\n\n")
    f.write(f"| Attribute | Value |\n|---|---|\n")
    f.write(f"| Total examples | {N} |\n")
    f.write(f"| Categories | {len(CATS)} (100 each) |\n")
    f.write(f"| Domains | 12 (coding, DevOps/SRE, data, research, cloud, DB, ML, API, finance, support, security, MCP) |\n")
    f.write(f"| Schema fields | 15 |\n")
    f.write(f"| Composite quality | {QS['composite_quality_score']}/100 |\n")
    f.write(f"| Near-dup rate | {ND['near_duplicate_rate']*100:.2f}% |\n")
    f.write(f"| Exact-dup rate | {ED['exact_duplicate_rate']*100:.2f}% |\n\n")

    f.write("## Severity & Difficulty\n\n")
    for s in ["low","medium","high","critical"]:
        f.write(f"- Severity {s}: {SEV['counts'][s]} ({SEV['actual_pcts'][s]}%)  `{bar(SEV['actual_pcts'][s])}`\n")
    f.write("\n")
    for d in ["easy","medium","hard"]:
        f.write(f"- Difficulty {d}: {DIF['counts'][d]} ({DIF['actual_pcts'][d]}%)  `{bar(DIF['actual_pcts'][d])}`\n")

    f.write("\n## Failure Analysis\n\n")
    f.write(f"- Tool-related failures: {tool_n} ({tool_n/N*100:.0f}%)\n")
    f.write(f"- Planning-related failures: {plan_n} ({plan_n/N*100:.0f}%)\n")
    f.write(f"- Unique tools referenced: {TD['unique_tools']}\n")
    f.write(f"- Avg recovery-plan length: {RP['avg_steps_per_plan']} steps\n\n")

    f.write("## Schema\n\n```json\n")
    f.write(json.dumps({k: EX[0][k] for k in EX[0]}, indent=2)[:1] + "\n")
    f.write("  // id, task, user_request, agent_action, failure_type, failure_category,\n")
    f.write("  // root_cause, why_it_failed, impact, severity, correct_action,\n")
    f.write("  // recovery_plan[], expected_tools[], difficulty, evaluation_criteria[]\n}\n```\n\n")
    f.write("## Files\n\n")
    f.write("- `agent_failure_dataset.jsonl` — 1000 examples (merged)\n")
    f.write("- `batch_01.jsonl` … `batch_10.jsonl` — 100-example batches\n")
    f.write("- `final_audit.json`, `batch_NN_audit.json` — machine-readable audits\n")
    f.write("- `generate_dataset.py`, `audit_pipeline.py` — reproducible pipeline\n")
    f.write("- `coverage_report.md`, `audit_report.md`, `taxonomy_definition.md`, "
            "`generation_methodology.md`, `dataset_summary.md`\n")

print("wrote coverage_report.md, audit_report.md, dataset_summary.md")
