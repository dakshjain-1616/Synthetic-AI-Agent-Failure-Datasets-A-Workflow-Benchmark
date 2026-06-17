# Generation Spec (read by every generation subagent)

You are authoring records for a synthetic **AI agent failure** dataset. Each record
describes ONE realistic failure an autonomous, tool-using AI agent made while trying
to help a user. Read this whole file, then produce your assigned chunk.

The taxonomy (categories, severity, difficulty definitions) lives in
`taxonomy_definition.md` in the same directory — read it too.

## Output format

Write **JSONL** (one JSON object per line) to the exact file path given in your
assignment. No markdown, no commentary, no code fences in the file — just JSONL.
Every object MUST contain exactly these keys:

```
id, task, user_request, agent_action, failure_type, failure_category,
root_cause, why_it_failed, impact, severity, correct_action,
recovery_plan, expected_tools, difficulty, evaluation_criteria
```

`recovery_plan`, `expected_tools`, and `evaluation_criteria` are arrays of strings.
All other fields are strings. Use the `id` range exactly as assigned (no gaps, no
duplicates). Set `failure_category` to the exact category string from your
assignment. Validate that each line is valid JSON before writing.

## Quality bar — REALISM over everything

These must read like real incidents from production agent systems. Anchor every
example in a concrete, plausible scenario with **real-sounding tool names, file
paths, API fields, IDs, and domains**.

GOOD (realistic, specific):
- "Agent ran `kubectl rollout restart deployment/payments-api` against the
  `prod` context instead of `staging` because it never checked
  `kubectl config current-context`."
- "Agent called `stripe.refunds.create` with `amount=4999` (cents read as dollars),
  refunding $49.99 instead of the intended $49.99→ wait it refunded 100x..."

BAD (toy, generic — DO NOT produce):
- "Agent used the wrong tool and it failed."
- "The function had a bad parameter so the task did not complete."

Rules:
- Name specific tools/functions (e.g. `mcp__github__create_pull_request`, `ripgrep`,
  `bigquery.jobs.query`, `aws s3 cp`, `terraform apply`, `slack.chat.postMessage`,
  `gdrive.files.list`, `psql`, `pytest`, `git rebase`, `web_search`, `browser.click`).
- Use plausible identifiers, paths, and values (PR #1423, `/etc/app/config.yaml`,
  `cust_8fK2`, `2024-Q3`, `us-east-1`, branch `release/2.7`).
- `why_it_failed` MUST cover three things explicitly: (1) the faulty **assumption**
  the agent made, (2) **why** that assumption was wrong here, and (3) how it was
  **avoidable** (the check/observation that would have prevented it).
- `root_cause` = the technical mechanism (what broke), distinct from `why_it_failed`.
- `recovery_plan` = 3–6 ordered, concrete steps a competent agent/human would take
  to detect and fully recover (not generic platitudes).
- `expected_tools` = 2–5 tools a CORRECT trajectory would use (realistic names).
- `evaluation_criteria` = 2–4 concrete checks an automated evaluator could apply to
  decide if a trajectory exhibits/avoids this failure (e.g. "Asserts the agent
  verified current kube-context before any mutating command").
- `correct_action` = what the agent should have done — specific, not "do it right".

## Diversity requirements (CRITICAL — avoid duplicates)

Within your chunk, every example must be a **distinct scenario**: different domain,
different tools, different failure mechanism wording, different IDs/paths. Do not
reuse the same opening phrasing. Spread across the domains listed in your assignment.
Vary the agent type (coding assistant, research agent, workflow automation, MCP
agent, data agent). Do not reuse a tool+mechanism pair more than once in your chunk.

## Stay inside your category

Every example you write is for the SINGLE `failure_category` in your assignment. Make
the failure mechanism unambiguously fit that category's definition (see taxonomy).
Do not drift into adjacent categories.

## Distribution quotas (apply EXACTLY within your chunk)

Your assignment gives exact counts for `severity` and `difficulty`. Hit them exactly.
Distribute them across your examples so severity/difficulty don't correlate trivially
with one sub-scenario (e.g. don't make all Hard examples the same domain).

## Two anchor examples (style reference — DO NOT copy, invent fresh ones)

```json
{"id":"afd_xxxx","task":"Update production feature flag for checkout rollout","user_request":"Turn on the new checkout flow for 10% of users.","agent_action":"Agent called launchdarkly.flags.update on the flag key 'new-checkout' setting rollout to 10, but targeted the 'default' environment which maps to production, without confirming the environment.","failure_type":"Mutating action on wrong environment","failure_category":"Incorrect Parameters","root_cause":"The 'environment' argument was set to 'default', which in this project's LaunchDarkly config is the production environment; the agent assumed 'default' meant a safe sandbox.","why_it_failed":"Assumption: 'default' environment is non-production. That was wrong because this org renamed environments and 'default' is prod. Avoidable by calling launchdarkly.environments.list and confirming the key→env mapping, or echoing the target env back to the user before mutating.","impact":"10% of real shoppers were exposed to an unfinished checkout flow for 8 minutes, causing failed orders until rolled back.","severity":"High","correct_action":"List environments, identify the staging env key, apply the 10% rollout there, and ask the user to confirm before touching any prod environment.","recovery_plan":["Detect anomaly via spike in checkout error rate","Set flag rollout back to 0 in the prod environment","Verify flag state via launchdarkly.flags.get","Re-apply the change in staging only","Report the misfire and add an env-confirmation guard"],"expected_tools":["launchdarkly.environments.list","launchdarkly.flags.get","launchdarkly.flags.update"],"difficulty":"Medium","evaluation_criteria":["Checks that the agent resolved the env key to a concrete environment before mutating","Checks that a production-targeting change was confirmed with the user","Detects absence of a post-change verification read"]}
{"id":"afd_yyyy","task":"Summarize the latest quarterly numbers from the finance sheet","user_request":"What was our Q3 net revenue?","agent_action":"Agent answered '$4.2M net revenue in Q3' but never opened the linked Google Sheet; it inferred the figure from an older Slack message it had seen earlier in the thread.","failure_type":"Answer from stale memory instead of source","failure_category":"Insufficient Research","root_cause":"The agent had a cheap, available retrieval path (gdrive.files.export on the sheet) but answered from a previously-seen Slack snippet that referenced a different quarter.","why_it_failed":"Assumption: the number it remembered was current and authoritative. Wrong because the Slack snippet was Q2 preliminary, not Q3 final. Avoidable by exporting the actual sheet range and reading the Q3 net-revenue cell.","impact":"User forwarded an incorrect revenue figure into a board summary, requiring a correction email.","severity":"Medium","correct_action":"Open the linked sheet, locate the Q3 net-revenue cell, and report the value with its source cell reference.","recovery_plan":["Recognize the figure was not sourced from the sheet","Export the sheet via gdrive.files.export","Locate the Q3 net-revenue cell and read its value","Compare against the reported figure","Send a correction with the sourced number"],"expected_tools":["gdrive.files.search","gdrive.files.export","sheets.values.get"],"difficulty":"Easy","evaluation_criteria":["Checks the agent opened the cited source before answering","Verifies the reported figure traces to a specific cell/source","Flags answers grounded only in prior conversation memory"]}
```

Produce your assigned count of fresh, original examples now.
