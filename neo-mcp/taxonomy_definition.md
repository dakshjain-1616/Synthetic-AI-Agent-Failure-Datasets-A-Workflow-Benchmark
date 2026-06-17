# AI Agent Failure Taxonomy

This dataset classifies agent failures into ten mutually-distinct categories. Each
category captures a different *mechanism* of failure — where in the perceive → plan →
act → verify loop the agent went wrong — rather than a surface symptom. Examples are
balanced at 100 per category.

The schema for every example:

| Field | Meaning |
|---|---|
| `id` | Stable identifier (`agent-failure-NNNN`) |
| `task` | Short description of what the agent was doing |
| `user_request` | The instruction the agent received |
| `agent_action` | What the agent actually did (the failure) |
| `failure_type` | Machine slug of the category |
| `failure_category` | Human-readable category |
| `root_cause` | What failed, mechanically |
| `why_it_failed` | The assumption/omission behind the failure |
| `impact` | Consequence, tiered to severity |
| `severity` | low / medium / high / critical |
| `correct_action` | What the agent should have done |
| `recovery_plan` | Ordered steps to detect, contain, and fix the failure |
| `expected_tools` | Tools relevant to doing the task correctly |
| `difficulty` | easy / medium / hard |
| `evaluation_criteria` | Questions a grader uses to judge an agent on this case |

## Categories

1. **Wrong Tool Selection** — The agent calls a plausible-but-incorrect tool, usually
   by matching on the tool's *name* rather than its documented *capability*. The right
   tool existed and was never called.

2. **Incorrect Parameters** — The correct tool is chosen but invoked with wrong values
   (wrong region, wrong scope, swapped arguments, wrong threshold/units/date range).

3. **Missing Parameters** — A required argument is omitted, leaving the call
   under-specified (no timezone, no idempotency key, no confirm flag, missing scope).

4. **Incomplete Workflow** — The agent performs the headline step and stops, treating a
   partial action as task completion (code written but not committed, migration written
   but not applied, deploy started but not verified).

5. **Incorrect Planning** — Individual steps may be correct but the plan's *structure* is
   wrong: bad ordering, ignored dependencies, unsafe parallelism, or a strategy that
   never should have been chosen (scraping when an API exists).

6. **Hallucinated Information** — The agent presents unverified belief as observed fact:
   fabricated tool outputs, nonexistent functions/endpoints, invented config keys, or
   claimed test results it never ran.

7. **Insufficient Research** — The agent acts before gathering the context it needed:
   doesn't read existing code, check versions, or inspect the real schema, so its action
   is built on a wrong mental model.

8. **Context Loss** — Over a longer task the agent drops earlier constraints, overwrites
   its own prior work, or loses track of state/environment because it does not maintain a
   running task record.

9. **Multi-Step Execution Failure** — A chained workflow fails because an intermediate
   step errored or returned bad data and the agent propagated it instead of halting,
   corrupting downstream steps.

10. **Recovery Failure** — Given an error, the agent's *recovery* is the fault: a
    non-idempotent retry that duplicates effects, a swallowed exception, the wrong
    rollback, an infinite retry loop, or a symptom-masking fix.

## Severity scale

- **low** — caught easily; minor rework, no data/user impact.
- **medium** — blocks a workflow or reaches a dashboard/customer; hours of delay or rework.
- **high** — corrupts shared state, degrades production, or misreports financials; needs a
  coordinated rollback or remediation.
- **critical** — irreversible data loss, duplicate financial transactions, production
  outage at peak, credential exposure, or a privacy breach.

## Difficulty scale

Reflects how hard the failure is for an evaluator/agent to **detect and avoid**:
**easy** (obvious from the action), **medium** (needs cross-checking against context),
**hard** (only visible with full task history or downstream effects).
