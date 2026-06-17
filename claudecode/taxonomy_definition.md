# Agent Failure Taxonomy Definition

This document defines the failure taxonomy used by the Synthetic AI Agent Failure
Dataset. It is the authoritative reference for the `failure_category`,
`failure_type`, `severity`, and `difficulty` fields in the schema.

The taxonomy is grounded in the task design of three reference datasets — **BFCL
v3** (tool/function-calling correctness, multi-turn, multi-step, relevance/
irrelevance detection), **xLAM Function-Calling 60K** (query → available-tools →
correct call mapping), and **GAIA** (multi-step, multi-tool real-world reasoning
with a single verifiable answer). We studied their *structure and task design*
(what a "correct" trajectory looks like and where it can break) and then defined
*original* failure modes. No examples are copied from those datasets.

---

## 1. Schema

Each record is a JSON object with the following fields:

| Field | Type | Description |
|---|---|---|
| `id` | string | Unique identifier, `afd_0001`..`afd_1000`. |
| `task` | string | Short description of the task/goal the agent was pursuing. |
| `user_request` | string | The user's natural-language request (verbatim style). |
| `agent_action` | string | What the agent actually did — the trajectory that failed. |
| `failure_type` | string | Specific failure mechanism (free-form, within a category). |
| `failure_category` | string | One of the 10 canonical categories (Section 2). |
| `root_cause` | string | The technical mechanism of the failure. |
| `why_it_failed` | string | Why it failed, the faulty assumption, and how it was avoidable. |
| `impact` | string | The downstream consequence of the failure. |
| `severity` | string | `Low` \| `Medium` \| `High` \| `Critical` (Section 3). |
| `correct_action` | string | What the agent should have done instead. |
| `recovery_plan` | array<string> | Ordered, realistic steps to detect and recover. |
| `expected_tools` | array<string> | Tools a correct trajectory would use. |
| `difficulty` | string | `Easy` \| `Medium` \| `Hard` (Section 4). |
| `evaluation_criteria` | array<string> | Checks an evaluator uses to score a trajectory. |

---

## 2. Failure Categories (10)

Target: **100 examples per category** (1000 total).

### 2.1 Wrong Tool Selection
The agent chooses a tool that is inappropriate for the task when a better-suited
tool was available. Includes: using a search tool when a write tool was needed,
calling a read-only API for a mutating action, picking a semantically similar but
wrong function from the toolset, or reaching for a general tool when a specialized
one exists. *Boundary:* the parameters may be fine — the **tool identity** is wrong.

### 2.2 Incorrect Parameters
The agent selects the right tool but supplies wrong argument **values**: wrong
units, wrong format, swapped positional arguments, wrong enum value, stale ID,
wrong path, off-by-one range, wrong timezone, incorrect type coercion. *Boundary:*
the parameter is *present* but *wrong* (contrast with 2.3).

### 2.3 Missing Parameters
The agent calls the right tool but omits a required argument, or omits an argument
that is optional-but-necessary for correctness (e.g., a filter, a pagination
cursor, an idempotency key, an auth scope). *Boundary:* the value is *absent*.

### 2.4 Incomplete Workflow
The agent stops before the task is actually done: it performs the main step but
skips a required finalization (commit, publish, confirm, clean up, notify), leaving
the system in a partial or inconsistent state. *Boundary:* steps were correct but
the **sequence terminated early**.

### 2.5 Incorrect Planning
The agent's high-level plan is flawed: wrong ordering of dependent steps, missing a
prerequisite, choosing an approach that cannot satisfy the constraints, or
decomposing the task incorrectly. *Boundary:* individual tool calls may each be
valid, but the **plan** is wrong.

### 2.6 Hallucinated Information
The agent fabricates content not grounded in any tool output or source: invented
API fields, made-up file paths, non-existent function names, fabricated citations,
imagined config keys, or asserted facts it never retrieved. *Boundary:* the failure
is **ungrounded assertion**, not a wrong-but-real value.

### 2.7 Insufficient Research
The agent acts on too little information: it skips reading the docs/code/data it
needed, does not verify an assumption it could have checked, or answers from priors
when a lookup was available and cheap. *Boundary:* the information **was reachable**
but the agent did not gather it.

### 2.8 Context Loss
The agent forgets or overwrites information established earlier in the
session/conversation: drops an earlier constraint, repeats a completed step, loses
a variable/ID it was given, or contradicts a prior decision. *Boundary:* the failure
is **state/memory** within a session, not external research.

### 2.9 Multi-Step Execution Failure
A multi-step trajectory breaks mid-execution: an intermediate step fails and the
agent proceeds as if it succeeded, ignores an error/non-200 response, passes a
malformed intermediate result downstream, or loses synchronization between steps.
*Boundary:* the plan was sound; **execution** of the chain broke.

### 2.10 Recovery Failure
After an error or failed attempt, the agent's *recovery* is wrong: it retries
verbatim without changing inputs, retries a non-idempotent action causing
duplication, gives up prematurely, or "recovers" into a worse state. *Boundary:*
there was an **error signal**, and the agent's response to it was the failure.

---

## 3. Severity Levels

| Level | Definition | Target |
|---|---|---|
| `Low` | Cosmetic or easily-caught; no data/state harm; trivial to correct. | 20% |
| `Medium` | Wrong/incomplete result requiring rework; no irreversible harm. | 50% |
| `High` | Significant wrong action, data exposure risk, broken deploy, or costly rework. | 25% |
| `Critical` | Irreversible or production-breaking: data loss, security breach, financial loss, outage. | 5% |

## 4. Difficulty Levels

Difficulty reflects how hard the failure is to **detect/diagnose**, not the task size.

| Level | Definition | Target |
|---|---|---|
| `Easy` | Obvious from the trajectory; a simple check catches it. | 30% |
| `Medium` | Needs comparing the action against intent or one external fact. | 50% |
| `Hard` | Subtle; requires deep domain knowledge, multi-step reasoning, or cross-referencing several signals to spot. | 20% |

---

## 5. Domains Covered

Examples span the agent settings named in the brief: AI coding assistants, research
agents, generic tool-using agents, workflow-automation agents, and MCP-enabled
systems. Concrete domain packs include: backend/API code, frontend/UI, CI/CD,
Kubernetes, Terraform/cloud, data warehouse/SQL, ETL/orchestration, ML training,
web research, document RAG/vector search, and MCP servers for GitHub, Slack, Google
Drive, Gmail, Calendar, and Notion, plus DB migrations, observability/logs,
security scanning, mobile, payments/billing, and CRM.
