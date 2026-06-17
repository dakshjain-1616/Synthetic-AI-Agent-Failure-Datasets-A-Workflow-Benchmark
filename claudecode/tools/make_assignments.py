#!/usr/bin/env python3
"""Generate per-chunk assignment files for generation subagents."""
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "artifacts", "prompts")
os.makedirs(OUT, exist_ok=True)

CATS = [
    ("Wrong Tool Selection", "wrong_tool_selection"),
    ("Incorrect Parameters", "incorrect_parameters"),
    ("Missing Parameters", "missing_parameters"),
    ("Incomplete Workflow", "incomplete_workflow"),
    ("Incorrect Planning", "incorrect_planning"),
    ("Hallucinated Information", "hallucinated_information"),
    ("Insufficient Research", "insufficient_research"),
    ("Context Loss", "context_loss"),
    ("Multi-Step Execution Failure", "multistep_execution_failure"),
    ("Recovery Failure", "recovery_failure"),
]

GROUPS = {
    "G1": "backend/API service code, CI/CD pipelines (GitHub Actions/Jenkins), Terraform/cloud infra (AWS/GCP), ETL & workflow orchestration (Airflow/dbt), the GitHub MCP server, and database schema migrations",
    "G2": "frontend/UI code (React/TypeScript), Kubernetes operations (kubectl/helm), data warehouse SQL (BigQuery/Snowflake), ML model training pipelines, the Slack MCP server, and observability/logs (Datadog/Grafana/Prometheus)",
    "G3": "open-web research & browsing, document RAG / vector search (embeddings/retrieval), the Google Drive MCP server, the Gmail MCP server, security scanning (SAST & dependency CVEs), and payments/billing (Stripe)",
    "G4": "the Google Calendar MCP server, the Notion MCP server, mobile app builds (iOS/Android, Fastlane), CRM automation (Salesforce/HubSpot), API gateway / reverse-proxy config (Kong/nginx), and data warehouse SQL",
}

# chunk letter -> (severity dict, difficulty dict)
CHUNK_QUOTAS = {
    "A": ({"Low": 5, "Medium": 13, "High": 6, "Critical": 1}, {"Easy": 8, "Medium": 12, "Hard": 5}),
    "B": ({"Low": 5, "Medium": 13, "High": 6, "Critical": 1}, {"Easy": 8, "Medium": 12, "Hard": 5}),
    "C": ({"Low": 5, "Medium": 12, "High": 6, "Critical": 2}, {"Easy": 7, "Medium": 13, "Hard": 5}),
    "D": ({"Low": 5, "Medium": 12, "High": 7, "Critical": 1}, {"Easy": 7, "Medium": 13, "Hard": 5}),
}
LETTERS = ["A", "B", "C", "D"]


def grp_for(cat_idx, chunk_idx):
    return GROUPS[f"G{((cat_idx + chunk_idx) % 4) + 1}"]


manifest = []
for ci, (cat_name, slug) in enumerate(CATS):
    base = ci * 100 + 1
    for li, letter in enumerate(LETTERS):
        start = base + li * 25
        end = start + 24
        sev, diff = CHUNK_QUOTAS[letter]
        domains = grp_for(ci, li)
        out_file = f"data/batches/cat{ci+1:02d}_{slug}_{letter}.jsonl"
        ids = f"afd_{start:04d} .. afd_{end:04d}"
        sev_s = ", ".join(f"{k}={v}" for k, v in sev.items())
        diff_s = ", ".join(f"{k}={v}" for k, v in diff.items())
        text = f"""# CHUNK ASSIGNMENT — {cat_name} [{letter}]

You are a generation subagent for a synthetic AI-agent-failure dataset.
Working directory: /home/azureuser/AGENTFailureDatasetGeneration/claudecode

STEP 1 — Read these two files IN FULL before writing anything:
  - SPEC.md  (output format, realism bar, diversity rules, anchor examples)
  - taxonomy_definition.md  (category/severity/difficulty definitions)

STEP 2 — Produce EXACTLY 25 examples for this single category:
  failure_category = "{cat_name}"   (every one of your 25 examples is THIS category)

ID range (assign sequentially, no gaps, no duplicates):
  {ids}

Write the 25 examples as JSONL (one JSON object per line, nothing else in the file) to:
  {out_file}

DOMAINS — spread your 25 examples across these, roughly evenly, each example a
distinct concrete scenario with real tool names / paths / IDs:
  {domains}

EXACT severity counts (must sum to 25): {sev_s}
EXACT difficulty counts (must sum to 25): {diff_s}

Spread severity and difficulty across different domains — do not let all the Hard
or all the Critical examples fall in one domain or share one mechanism.

STEP 3 — Self-check before finishing:
  - Exactly 25 lines, each valid JSON with all 15 required keys.
  - IDs exactly {ids}.
  - Severity tally matches the quota above EXACTLY.
  - Difficulty tally matches the quota above EXACTLY.
  - Every failure_category value is "{cat_name}".
  - No two examples share the same tool+mechanism or opening phrasing.
  - Each `why_it_failed` states the faulty assumption, why it was wrong, and how it was avoidable.

Return ONLY a short summary (count written, severity tally, difficulty tally,
domains used, and the output file path). Do NOT paste the examples back to me.
"""
        path = os.path.join(OUT, f"cat{ci+1:02d}_{letter}.txt")
        with open(path, "w") as f:
            f.write(text)
        manifest.append((f"cat{ci+1:02d}_{letter}", cat_name, ids, out_file, path))

print(f"Wrote {len(manifest)} assignment files to {OUT}")
for m in manifest:
    print(" ", m[0], "->", m[4])
