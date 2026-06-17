# Generation Methodology

How the 1000-example synthetic AI-agent-failure dataset
(`agent_failure_dataset.jsonl`) was designed, generated, validated, and audited.

---

## 1. Goal

Produce a high-quality, original, **synthetic** dataset of realistic AI-agent
failures that helps researchers and benchmark builders understand why agents fail,
how failures occur, how they can be detected, and how they can be recovered from —
suitable for agent evaluation, training, failure analysis, tool-calling benchmarks,
MCP-workflow evaluation, and autonomous-agent research.

The design priority, per the brief, was **realism, diversity, auditability, and
quality over raw size**.

## 2. Analysis of reference datasets

We studied the *structure and task design* of three references and used them to
shape the taxonomy and schema. **No examples were copied**; every record is original.

- **BFCL v3** (Berkeley Function-Calling Leaderboard). Its value is the taxonomy of
  *calling* situations: simple/multiple/parallel calls, **multi-turn** and
  **multi-step** trajectories, and explicit **relevance/irrelevance** detection
  (knowing when *not* to call, or when a tool is missing). This directly motivated
  our `Wrong Tool Selection`, `Incorrect Parameters`, `Missing Parameters`, and
  `Multi-Step Execution Failure` categories, and the idea that a record should pin
  down *which* part of a call is wrong (tool identity vs. argument value vs. missing
  argument).
- **xLAM Function-Calling 60K**. Its value is the clean `query → available tools →
  correct call` mapping. This motivated our use of concrete tool inventories
  (`expected_tools`) and the framing of each failure as a divergence from the
  correct call given a realistic toolset.
- **GAIA**. Its value is *real-world, multi-step, multi-tool* tasks with a single
  verifiable answer, where success depends on planning, research, and tool
  orchestration. This motivated `Incorrect Planning`, `Insufficient Research`,
  `Hallucinated Information`, `Incomplete Workflow`, `Context Loss`, and `Recovery
  Failure`, plus the verifiable `evaluation_criteria` field.

The resulting **10-category taxonomy** is defined authoritatively in
[`taxonomy_definition.md`](taxonomy_definition.md), along with the severity and
difficulty rubrics.

## 3. Schema

A flat 15-field JSON object per record (see `taxonomy_definition.md` §1). Beyond the
brief's required fields we enforced that `root_cause` and `why_it_failed` are
*distinct*: `root_cause` states the technical mechanism, while `why_it_failed`
must spell out (1) the agent's faulty **assumption**, (2) **why** it was wrong in
that situation, and (3) how it was **avoidable**. This makes the root-cause analysis
required by the brief checkable.

## 4. Generation architecture

The user selected an **LLM-authored, multi-subagent** generation strategy. We
orchestrated it deterministically to keep coverage and distributions exact:

```
orchestrator (main agent)
 ├─ taxonomy_definition.md + SPEC.md   ← shared, read by every subagent
 ├─ tools/make_assignments.py          ← emits 40 per-chunk assignment files
 └─ 10 batches × 4 chunks = 40 subagents
        each: reads SPEC + taxonomy + its assignment
              writes 25 JSONL records to its own file
              returns only a short summary (keeps orchestrator context lean)
```

**Batching.** Each of the 10 categories is one *batch* of 100 examples, split into
4 *chunks* of 25 authored by 4 independent subagents. 40 subagents total, run in
parallel waves.

**ID space.** Categories occupy contiguous blocks (`afd_0001`–`afd_0100` for
category 1, etc.); each chunk owns a 25-id sub-range, so ids never collide and the
merged file is gap-free `afd_0001`–`afd_1000`.

**Anti-duplication by construction.** The 22 domains (coding, CI/CD, IaC, data
warehouse, ETL, ML, web research, RAG, MCP servers for GitHub/Slack/Drive/Gmail/
Calendar/Notion, DB migrations, observability, security, mobile, payments, CRM) are
partitioned into 4 groups. A rotating assignment (`group = (category_idx +
chunk_idx) mod 4`) guarantees each category's four chunks cover all four groups, and
that the same domain pairs with a different chunk position across categories.
Subagents were also instructed never to reuse a tool+mechanism pair or opening
phrasing within their chunk.

**Distribution control.** Each chunk carries an *exact* severity and difficulty
quota. The four chunk quotas per category sum to the global targets, so hitting
every chunk quota guarantees the global distribution exactly:

| Chunk | Low | Med | High | Crit | Easy | Med | Hard |
|---|---:|---:|---:|---:|---:|---:|---:|
| A | 5 | 13 | 6 | 1 | 8 | 12 | 5 |
| B | 5 | 13 | 6 | 1 | 8 | 12 | 5 |
| C | 5 | 12 | 6 | 2 | 7 | 13 | 5 |
| D | 5 | 12 | 7 | 1 | 7 | 13 | 5 |
| **×10 cats** | **200** | **500** | **250** | **50** | **300** | **500** | **200** |

**Realism enforcement.** `SPEC.md` sets the realism bar with explicit
good/bad contrasts, requires named real tools/paths/IDs, requires the three-part
`why_it_failed`, requires 3–6 concrete recovery steps and 2–4 verifiable evaluation
criteria, and includes two full anchor examples for style (with an instruction not
to copy them).

## 5. Validation pipeline (per batch and global)

`tools/dataset_tools.py` provides four subcommands, run after every batch and again
on the merged file:

1. **validate** — exact 15-key schema, type checks, enum checks (`failure_category`,
   `severity`, `difficulty`), `id` format + uniqueness + contiguity, non-empty list
   fields, plus soft quality warnings (e.g. `expected_tools` < 2).
2. **dedup** — exact normalized-text duplicates (md5 of tokenized signature) **and**
   near-duplicates via **Jaccard similarity on 3-gram shingles** of
   `user_request + agent_action + root_cause + failure_type`, at thresholds 0.92
   (hard) and 0.50–0.55 (near).
3. **audit** — category/severity/difficulty counts and diversity counters.
4. **merge** — re-validates, sorts by id, writes the canonical JSONL.

Per-batch audit artifacts are saved under `artifacts/batchNN_audit.json`; the global
metrics under `artifacts/metrics.json`. `tools/build_reports.py` computes the richer
metrics (cross-tabs, nearest-neighbour similarity distribution, tool-domain
buckets) and renders `coverage_report.md` and `audit_report.md`.

## 6. Improvement phase

The brief's improvement loop ran once. The only weaknesses the audit surfaced were
cosmetic: 5 records carried a single `expected_tool` (spec asks for ≥2) and 3
records shared the `failure_type` string "Omitted pagination cursor". These 7
records were patched in place (a second in-context tool added; two failure-type
strings specialized), after which re-validation showed **0 errors, 0 warnings, and
1000 unique `failure_type` values**. No category needed regeneration — category,
severity, and difficulty distributions were already exact and duplication was zero.

## 7. Reproducibility & auditability

- The taxonomy, spec, and all 40 assignment files are committed under
  `artifacts/prompts/`, so the exact instructions given to every subagent are
  inspectable.
- All tooling is deterministic Python with no external dependencies; rerunning
  validate/dedup/audit on the published file reproduces every number in the reports.
- Per-batch audit artifacts preserve the intermediate state of each batch.

## 8. Limitations

- Examples are **synthetic**: scenarios are plausible and internally consistent but
  are not transcripts of real incidents. Tool names and APIs are realistic but some
  parameter/field details are illustrative.
- Severity and difficulty are uniform *across categories* by construction (identical
  per-category quotas). Severity differentiation therefore lives at the
  example level, not between categories — intentional, to keep every category
  usable across the full severity range.
- Near-duplicate detection is lexical (shingle Jaccard), not embedding-based; it
  reliably catches templated repetition but a semantic-embedding pass could be added
  for an even stronger guarantee.
- `failure_category` correctness was enforced via per-chunk single-category
  assignments and the taxonomy boundaries in `SPEC.md`, plus spot review; it was not
  re-classified by an independent judge model.
