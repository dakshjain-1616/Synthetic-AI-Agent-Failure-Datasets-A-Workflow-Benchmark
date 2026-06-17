#!/usr/bin/env python3
"""
generate_dataset.py - Compositional generator for the synthetic AI agent failure dataset.

Design goals
------------
* Realism: every example embeds concrete tools, file paths, services, API names,
  numeric values and error strings drawn from 12 distinct agent domains.
* Diversity-by-construction: each text field is assembled by independently sampling
  from many large fragment pools, and every candidate is screened by a streaming
  near-duplicate guard (HashingVectorizer cosine over the SAME text the audit uses)
  BEFORE it is accepted. This keeps the audit's TF-IDF near-dup rate far below the
  5% target rather than relying on post-hoc dedup.
* Auditability: writes 10 intermediate batch files plus the merged dataset, and is
  fully reproducible from --seed.

No brace/slot templating is used anywhere: fields are built purely by joining
already-resolved strings, so unfilled "{slot}" placeholders are structurally
impossible. A final assertion rejects any field that still contains "{" or "}".
"""
import argparse
import json
import random
import sys

from scipy.sparse import vstack
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ----------------------------------------------------------------------------
# Concrete domain vocabulary. Each domain supplies tools, artifacts, entities,
# operations and a few realistic error strings so generated text stays grounded.
# ----------------------------------------------------------------------------
DOMAINS = [
    {
        "name": "coding assistant",
        "tasks": [
            "refactor the authentication middleware", "add pagination to the users endpoint",
            "fix the failing unit tests in the billing module", "migrate the ORM models to async",
            "rename the legacy config keys across the repo", "implement a retry wrapper for the HTTP client",
            "extract the payment logic into its own service", "add type hints to the analytics package",
        ],
        "tools": ["read_file", "edit_file", "grep_search", "ast_search", "run_tests", "git_diff",
                  "git_commit", "lint", "format_code", "build_project", "rename_symbol", "find_references"],
        "artifacts": ["src/auth/middleware.py", "services/billing/invoice.ts", "app/models/user.rb",
                      "lib/http_client.go", "tests/test_payments.py", "config/settings.yaml",
                      "pkg/api/handlers.go", "components/Checkout.tsx"],
        "entities": ["the auth service", "the billing module", "the user model", "the HTTP client",
                     "the payments package", "the settings loader", "the API handler", "the checkout flow"],
        "errors": ["ImportError: cannot import name 'TokenStore'", "AssertionError: expected 200, got 500",
                   "TypeError: NoneType has no attribute 'id'", "ESLint: 'useEffect' has a missing dependency"],
    },
    {
        "name": "DevOps/SRE agent",
        "tasks": [
            "roll out the new deployment to staging", "scale the payment workers for the sale",
            "rotate the database credentials", "patch the CVE in the base image",
            "drain and restart the unhealthy nodes", "set up alerting for the checkout latency SLO",
            "restore the cluster from the last good snapshot", "tighten the ingress firewall rules",
        ],
        "tools": ["kubectl_apply", "kubectl_rollout", "helm_upgrade", "terraform_apply", "terraform_plan",
                  "aws_cli", "datadog_query", "pagerduty_ack", "vault_read", "docker_build", "ssh_exec"],
        "artifacts": ["deploy/payment-worker.yaml", "infra/main.tf", "charts/api/values.yaml",
                      "Dockerfile", ".github/workflows/deploy.yml", "k8s/ingress.yaml"],
        "entities": ["the payment-worker deployment", "the staging cluster", "the ingress controller",
                     "the RDS instance", "the node pool", "the Helm release", "the Terraform state"],
        "errors": ["ImagePullBackOff", "Error: state lock acquired by another process",
                   "0/6 nodes available: insufficient memory", "TLS handshake timeout"],
    },
    {
        "name": "data pipeline agent",
        "tasks": [
            "backfill the events table for last quarter", "deduplicate the customer records",
            "repartition the clickstream dataset", "validate the nightly ETL output",
            "join the orders and refunds tables", "convert the parquet files to delta format",
            "compute daily active users for the dashboard", "anonymize the PII columns before export",
        ],
        "tools": ["spark_submit", "sql_query", "dbt_run", "airflow_trigger", "s3_copy", "pandas_read",
                  "great_expectations_validate", "bigquery_job", "schema_diff", "csv_export"],
        "artifacts": ["s3://lake/events/2024/", "models/dim_customers.sql", "dags/nightly_etl.py",
                      "warehouse.orders", "warehouse.refunds", "notebooks/dau.ipynb"],
        "entities": ["the events table", "the customer dimension", "the nightly ETL DAG",
                     "the orders dataset", "the refunds table", "the DAU job"],
        "errors": ["AnalysisException: column 'user_id' is ambiguous", "OutOfMemoryError: GC overhead limit",
                   "DataQualityError: 14% null in primary key", "SchemaMismatch: expected 12 cols, got 11"],
    },
    {
        "name": "web research agent",
        "tasks": [
            "find the current CEO of the acquiring company", "summarize the latest pricing changes",
            "compile a list of competitors in the EU market", "verify the reported revenue figure",
            "gather the regulatory filing deadlines", "track down the original source of the statistic",
            "assemble a timeline of the product launches", "check whether the API still supports v1",
        ],
        "tools": ["web_search", "web_fetch", "open_url", "pdf_extract", "wikipedia_lookup",
                  "internal_docs_search", "knowledge_base_query", "citation_check", "translate"],
        "artifacts": ["the 2024 annual report PDF", "the pricing page", "the press release",
                      "the SEC filing", "the changelog", "the API reference"],
        "entities": ["the annual report", "the pricing page", "the press release",
                     "the regulatory filing", "the changelog", "the source article"],
        "errors": ["404 Not Found", "paywall blocked the article", "the cited page no longer exists",
                   "rate limited after 3 requests"],
    },
    {
        "name": "cloud infrastructure agent",
        "tasks": [
            "provision a read replica for the primary database", "set up a VPC peering connection",
            "configure autoscaling for the API tier", "migrate the bucket to a new region",
            "attach an IAM policy to the deploy role", "enable point-in-time recovery on the table",
            "create a private subnet for the workers", "set lifecycle rules on the log bucket",
        ],
        "tools": ["aws_cli", "gcloud", "az_cli", "terraform_apply", "cloudformation_deploy",
                  "iam_simulate", "s3_lifecycle", "route53_change", "kms_encrypt"],
        "artifacts": ["arn:aws:iam::deploy-role", "vpc-0a1b2c3d", "the prod-db cluster",
                      "the logs bucket", "the dynamodb sessions table", "the api-tier ASG"],
        "entities": ["the primary database", "the deploy role", "the logs bucket",
                     "the API autoscaling group", "the VPC", "the sessions table"],
        "errors": ["AccessDenied: not authorized to perform iam:PutRolePolicy",
                   "BucketAlreadyExists", "ThrottlingException", "InvalidParameterValue: region mismatch"],
    },
    {
        "name": "database administration agent",
        "tasks": [
            "add an index to speed up the orders query", "run the pending schema migration",
            "archive rows older than two years", "fix the replication lag on the replica",
            "reclaim space from the bloated table", "change the column type without downtime",
            "set up a nightly logical backup", "resolve the deadlock on the inventory table",
        ],
        "tools": ["sql_query", "run_migration", "explain_analyze", "pg_dump", "create_index",
                  "vacuum", "reindex", "replica_status", "lock_inspect"],
        "artifacts": ["migrations/0042_add_index.sql", "public.orders", "public.inventory",
                      "the read replica", "the audit_log table", "the sessions table"],
        "entities": ["the orders table", "the inventory table", "the read replica",
                     "the audit log", "the migration", "the primary database"],
        "errors": ["deadlock detected", "could not obtain lock on relation",
                   "migration failed: column already exists", "replication lag 480s"],
    },
    {
        "name": "ML training agent",
        "tasks": [
            "fine-tune the classifier on the new labels", "evaluate the model against the holdout set",
            "tune the learning rate for the recommender", "export the trained model to ONNX",
            "build a feature pipeline for the churn model", "run a hyperparameter sweep",
            "calibrate the model's probability outputs", "detect label leakage in the training set",
        ],
        "tools": ["train_model", "evaluate_model", "data_loader", "hpo_sweep", "export_onnx",
                  "feature_transform", "metric_compute", "checkpoint_save", "tensorboard_log"],
        "artifacts": ["data/train.parquet", "models/churn_v3.pt", "configs/sweep.yaml",
                      "the holdout set", "features/churn.py", "the validation split"],
        "entities": ["the churn model", "the holdout set", "the feature pipeline",
                     "the training split", "the recommender", "the classifier"],
        "errors": ["CUDA out of memory", "NaN loss after 200 steps",
                   "ValueError: inconsistent number of samples", "F1 dropped to 0.41 on holdout"],
    },
    {
        "name": "API integration agent",
        "tasks": [
            "sync new orders from the Shopify webhook", "post the refund to the Stripe API",
            "pull the latest contacts from the CRM", "register the webhook endpoint",
            "reconcile the payment statuses nightly", "paginate through all the customer records",
            "upload the invoice to the accounting API", "renew the OAuth token before it expires",
        ],
        "tools": ["http_request", "stripe_api", "shopify_api", "salesforce_query", "oauth_refresh",
                  "webhook_register", "json_parse", "rate_limit_wait", "signature_verify"],
        "artifacts": ["POST /v1/refunds", "GET /admin/api/orders", "the Stripe secret key",
                      "the webhook secret", "the OAuth refresh token", "the idempotency key"],
        "entities": ["the Stripe refund endpoint", "the Shopify orders API", "the CRM sync",
                     "the webhook handler", "the OAuth token", "the reconciliation job"],
        "errors": ["401 Unauthorized: expired token", "409 Conflict: refund already issued",
                   "429 Too Many Requests", "webhook signature verification failed"],
    },
    {
        "name": "financial operations agent",
        "tasks": [
            "close the monthly books for the EU entity", "reconcile the bank statement against ledger",
            "calculate the quarterly VAT owed", "post the payroll journal entries",
            "flag transactions above the approval threshold", "convert the report to the reporting currency",
            "accrue the unbilled revenue", "run the month-end depreciation",
        ],
        "tools": ["ledger_query", "fx_convert", "journal_post", "tax_calculate", "reconcile",
                  "approval_route", "report_generate", "audit_trail_write"],
        "artifacts": ["the general ledger", "the EU bank statement", "the payroll batch",
                      "the VAT report", "the FX rate table", "the trial balance"],
        "entities": ["the general ledger", "the bank statement", "the payroll run",
                     "the VAT calculation", "the FX rate table", "the close checklist"],
        "errors": ["trial balance off by 1,240.00", "FX rate not found for date",
                   "duplicate journal entry detected", "approval threshold not configured"],
    },
    {
        "name": "customer support automation agent",
        "tasks": [
            "triage the new support tickets by priority", "issue a refund for the duplicate charge",
            "escalate the outage tickets to on-call", "draft a reply to the billing complaint",
            "close the resolved tickets from last week", "merge the duplicate conversations",
            "update the order status from the carrier feed", "tag tickets mentioning the data breach",
        ],
        "tools": ["zendesk_search", "ticket_update", "refund_issue", "macro_apply", "kb_article_fetch",
                  "sentiment_classify", "escalate", "email_send", "order_lookup"],
        "artifacts": ["ticket #48213", "the refund queue", "the on-call rotation",
                      "the billing macro", "the order #A-9920", "the knowledge base"],
        "entities": ["the support queue", "the refund workflow", "the escalation policy",
                     "the billing macro", "the order record", "the ticket thread"],
        "errors": ["customer not found", "refund exceeds original charge",
                   "macro template missing variable", "escalation policy not set for this team"],
    },
    {
        "name": "security audit agent",
        "tasks": [
            "scan the repo for leaked secrets", "review the new IAM policy for over-permissioning",
            "check the dependencies for known CVEs", "verify TLS is enforced on all endpoints",
            "audit who has production database access", "validate the SSO configuration",
            "rotate the exposed API key", "confirm the S3 buckets are not public",
        ],
        "tools": ["secret_scan", "cve_lookup", "iam_analyze", "tls_check", "access_review",
                  "dependency_audit", "key_rotate", "bucket_acl_check", "log_search"],
        "artifacts": ["the .env file", "the deploy IAM policy", "package-lock.json",
                      "the public-assets bucket", "the SSO metadata", "the access matrix"],
        "entities": ["the deploy IAM policy", "the secrets file", "the dependency tree",
                     "the S3 bucket ACL", "the SSO config", "the access review"],
        "errors": ["found AWS key prefixed AKIA in commit history", "CVE-2024-3094 in transitive dep",
                   "bucket grants READ to AllUsers", "TLS 1.0 still accepted"],
    },
    {
        "name": "MCP workflow agent",
        "tasks": [
            "sync the meeting notes into the project tracker", "create calendar holds for the review cycle",
            "file the bug reported in the support channel", "compile the weekly status from the connected tools",
            "archive the closed threads to the drive", "post the deploy summary to the team channel",
            "create tasks from the action items in the doc", "pull the metrics into the weekly report",
        ],
        "tools": ["mcp_list_tools", "gmail_send", "calendar_create_event", "drive_upload", "slack_post",
                  "jira_create_issue", "notion_update", "sheets_append", "github_create_issue"],
        "artifacts": ["the project tracker", "the #support channel", "the review calendar",
                      "the weekly report doc", "the shared drive folder", "the status sheet"],
        "entities": ["the project tracker", "the support channel", "the review calendar",
                     "the weekly report", "the shared drive", "the status sheet"],
        "errors": ["tool not found in the connected MCP server", "insufficient scope: calendar.write",
                   "rate limited by the Slack API", "the document was not shared with the agent"],
    },
]

CATEGORIES = [
    ("Wrong Tool Selection", "wrong_tool_selection"),
    ("Incorrect Parameters", "incorrect_parameters"),
    ("Missing Parameters", "missing_parameters"),
    ("Incomplete Workflow", "incomplete_workflow"),
    ("Incorrect Planning", "incorrect_planning"),
    ("Hallucinated Information", "hallucinated_information"),
    ("Insufficient Research", "insufficient_research"),
    ("Context Loss", "context_loss"),
    ("Multi-Step Execution Failure", "multi_step_execution_failure"),
    ("Recovery Failure", "recovery_failure"),
]

# Severity-tagged impact clauses (concrete consequence varies, {entity} injected as text).
IMPACT_BY_SEV = {
    "low": [
        "The task produced a slightly wrong result that a reviewer caught before merge, costing a few minutes of rework.",
        "A cosmetic inconsistency slipped through but no downstream system was affected.",
        "The output needed a minor manual correction; no data or users were impacted.",
        "A redundant step ran and wasted some compute, but the final state was still correct.",
        "The agent surfaced a confusing message that briefly slowed the user, with no lasting harm.",
    ],
    "medium": [
        "The error blocked the workflow until a human intervened, delaying delivery by several hours.",
        "Incorrect output reached a dashboard and had to be retracted and recomputed.",
        "A teammate spent significant time debugging a problem the agent silently introduced.",
        "The mistake required reverting a change and re-running the pipeline from a checkpoint.",
        "A customer-facing response was wrong and had to be followed up with a correction.",
    ],
    "high": [
        "The failure corrupted shared state that several downstream jobs depended on, requiring a coordinated rollback.",
        "A production endpoint degraded and on-call was paged to contain the impact.",
        "Incorrect financial figures were reported and had to be restated before close.",
        "Customer data was processed incorrectly at scale, triggering a remediation effort.",
        "A broken deployment reached production and had to be rolled back under time pressure.",
    ],
    "critical": [
        "The action caused irreversible data loss that could only be partially restored from backups.",
        "A duplicate financial transaction was issued to many customers, creating a refund and compliance incident.",
        "Production was taken down during peak traffic and revenue was lost until recovery completed.",
        "Sensitive credentials were exposed, forcing an emergency rotation and security review.",
        "Personal data was sent to the wrong recipients, creating a reportable privacy breach.",
    ],
}

EVAL_POOL = [
    "Did the agent select the tool whose documented purpose matches the request?",
    "Were all required parameters supplied with correct, validated values?",
    "Did the agent confirm preconditions before taking an irreversible action?",
    "Was the multi-step plan ordered so dependencies were satisfied before use?",
    "Did the agent verify each intermediate result before proceeding?",
    "Were claims grounded in actually-observed tool outputs rather than assumptions?",
    "Did the agent gather the context needed before acting?",
    "Did the agent retain earlier constraints across the full task?",
    "Was the error handled with a recovery that preserved correctness and idempotency?",
    "Did the final state fully satisfy the user's original request?",
    "Would the failure be detectable from the agent's own logged reasoning?",
    "Did the agent stop and ask for input when the situation was ambiguous?",
]


def pick(rng, seq):
    return rng.choice(seq)


def sample_distinct(rng, seq, k):
    k = min(k, len(seq))
    return rng.sample(seq, k)


def build_eval(rng, primary):
    """2-4 evaluation criteria, always including a category-relevant primary one."""
    extras = sample_distinct(rng, [e for e in EVAL_POOL if e != primary], rng.randint(1, 3))
    crit = [primary] + extras
    return crit


# ----------------------------------------------------------------------------
# Per-category builders. Each returns a dict of the text fields (no id/sev/diff).
# All text is built by joining resolved strings - no brace templating.
# ----------------------------------------------------------------------------
def build_example(rng, cat_name, cat_type, dom, severity):
    task = pick(rng, dom["tasks"])
    tool = pick(rng, dom["tools"])
    tool2 = pick(rng, dom["tools"])
    artifact = pick(rng, dom["artifacts"])
    entity = pick(rng, dom["entities"])
    err = pick(rng, dom["errors"])
    dname = dom["name"]
    impact = pick(rng, IMPACT_BY_SEV[severity])

    # Defaults that each branch overrides.
    user_request = ""
    agent_action = ""
    root_cause = ""
    why = ""
    correct = ""
    recovery = []
    eval_primary = EVAL_POOL[0]
    tools = sample_distinct(rng, dom["tools"], rng.randint(2, 4))

    if cat_type == "wrong_tool_selection":
        wrong = pick(rng, dom["tools"])
        right = pick(rng, [t for t in dom["tools"] if t != wrong] or dom["tools"])
        user_request = pick(rng, [
            "As the " + dname + ", please " + task + " for " + entity + ".",
            "I need you to " + task + "; the relevant resource is " + artifact + ".",
            "Can you " + task + "? Use whatever tool is appropriate for " + entity + ".",
        ])
        agent_action = ("The agent invoked " + wrong + " to " + task + ", because the name looked related to "
                        + entity + ". The correct capability for this was " + right + ", which it never called.")
        root_cause = ("Tool selected by surface-level name matching rather than by capability: " + wrong
                      + " does not perform the operation the request needed on " + entity + ".")
        why = ("The agent assumed " + wrong + " and " + right + " were interchangeable and skipped checking each "
               "tool's documented contract, so it applied the wrong primitive to " + artifact + ".")
        correct = "Match the request to tool capability and call " + right + " on " + entity + " instead of " + wrong + "."
        recovery = [
            "Detect that " + wrong + " produced an output inconsistent with the goal of " + task,
            "Re-read the tool catalog and map the request to " + right + " by documented capability",
            "Undo any partial effect of " + wrong + " on " + artifact,
            "Re-execute the step with " + right,
            "Validate the result against the original request",
        ]
        eval_primary = EVAL_POOL[0]
        tools = list(dict.fromkeys([right, tool2] + sample_distinct(rng, dom["tools"], 2)))

    elif cat_type == "incorrect_parameters":
        bad, good = pick(rng, [
            ("the staging region", "the production region"), ("a 7-day window", "the 30-day window"),
            ("the wrong branch 'main'", "the release branch"), ("limit=10", "limit=1000"),
            ("USD", "the account's EUR currency"), ("the previous fiscal year", "the current quarter"),
            ("source and destination swapped", "the correct source/destination order"),
            ("threshold 0.9", "the agreed threshold 0.5"),
        ])
        user_request = pick(rng, [
            "Please " + task + " against " + entity + ".",
            "Run " + tool + " to " + task + "; the target is " + artifact + ".",
            "Could you " + task + "? Make sure it targets the right scope of " + entity + ".",
        ])
        agent_action = ("The agent called " + tool + " with " + bad + " while trying to " + task
                        + " on " + artifact + ". It should have used " + good + ".")
        root_cause = ("Right tool, wrong value: " + tool + " was passed " + bad + ", which does not match the scope "
                      "the user intended for " + entity + ".")
        why = ("The agent assumed the default/first-seen value was correct and did not validate the parameter "
               "against the request, so " + tool + " operated on the wrong scope.")
        correct = "Call " + tool + " with " + good + " after confirming the parameter against the request."
        recovery = [
            "Identify that " + tool + " ran with " + bad,
            "Determine the correct value (" + good + ") from the request and current state",
            "Reverse or recompute the effect produced with the wrong value",
            "Re-run " + tool + " with the corrected parameter",
            "Verify the output now reflects " + good,
        ]
        eval_primary = EVAL_POOL[1]
        tools = list(dict.fromkeys([tool, tool2] + sample_distinct(rng, dom["tools"], 2)))

    elif cat_type == "missing_parameters":
        missing = pick(rng, [
            "the required timezone", "the idempotency key", "the --confirm flag",
            "the pagination cursor", "the auth scope", "the target environment",
            "the encryption key id", "the date range", "the currency code",
        ])
        user_request = pick(rng, [
            "Please " + task + " for " + entity + ".",
            "Use " + tool + " to " + task + " on " + artifact + ".",
            "I'd like you to " + task + "; double-check the call is complete.",
        ])
        agent_action = ("The agent called " + tool + " to " + task + " but omitted " + missing
                        + ", so the call ran against " + artifact + " with an incomplete specification.")
        root_cause = ("A required argument was missing: " + tool + " needs " + missing + ", which the agent never "
                      "supplied when acting on " + entity + ".")
        why = ("The agent assumed " + missing + " had a safe default and did not consult the tool signature, so the "
               "operation was under-specified and behaved unexpectedly.")
        correct = "Supply " + missing + " explicitly to " + tool + " before invoking it on " + entity + "."
        recovery = [
            "Detect the missing-argument symptom: " + err,
            "Inspect the signature of " + tool + " to find the required " + missing,
            "Resolve the correct value for " + missing + " from context",
            "Re-invoke " + tool + " with " + missing + " included",
            "Confirm the call now completes correctly",
        ]
        eval_primary = EVAL_POOL[1]
        tools = list(dict.fromkeys([tool, tool2] + sample_distinct(rng, dom["tools"], 2)))

    elif cat_type == "incomplete_workflow":
        stopped = pick(rng, [
            "did not run the follow-up validation", "skipped committing and pushing the change",
            "never requested review on the resulting PR", "left the migration written but unapplied",
            "did not refresh the dependent cache", "forgot to notify the downstream consumer",
            "stopped before verifying the deploy was healthy", "did not clean up the temporary resource",
        ])
        user_request = pick(rng, [
            "Please fully " + task + " for " + entity + ", end to end.",
            "Take " + entity + " all the way through: " + task + ".",
            "I need " + task + " completed and verified, not just started.",
        ])
        agent_action = ("The agent performed the main step to " + task + " on " + artifact + " but then "
                        + stopped + ", reporting success prematurely.")
        root_cause = ("Workflow terminated early: the agent treated the primary edit as the whole task and "
                      + stopped + ", leaving " + entity + " in a half-finished state.")
        why = ("The agent assumed the first visible step equaled task completion and lacked a definition-of-done "
               "checklist, so it never closed out the remaining required steps.")
        correct = "Complete every required step, including the closing actions the agent " + stopped.replace("did not", "skipped") + ", and verify the end state."
        recovery = [
            "Compare the current state of " + entity + " against the full definition of done",
            "Enumerate the remaining steps the agent " + stopped,
            "Execute the outstanding steps in order",
            "Validate the end-to-end result for " + entity,
            "Report completion only after verification",
        ]
        eval_primary = EVAL_POOL[9]
        tools = list(dict.fromkeys([tool, tool2] + sample_distinct(rng, dom["tools"], 2)))

    elif cat_type == "incorrect_planning":
        flaw = pick(rng, [
            "deployed before the tests had run", "parallelized two steps that had a data dependency",
            "chose to scrape pages when a documented API existed", "ordered the migration after the code that used it",
            "planned an O(n^2) scan instead of an indexed lookup", "batched all changes into one irreversible step",
            "scheduled cleanup before the consumers had finished reading", "skipped a needed approval gate",
        ])
        user_request = pick(rng, [
            "Plan and " + task + " for " + entity + " safely.",
            "Lay out the steps to " + task + ", then execute on " + artifact + ".",
            "I want a sound plan to " + task + " without breaking " + entity + ".",
        ])
        agent_action = ("The agent built a plan that " + flaw + " while trying to " + task + " on " + artifact
                        + ", then executed it as ordered.")
        root_cause = ("Flawed plan structure: the ordering/strategy was wrong because the agent " + flaw
                      + ", so even correct individual steps produced a broken outcome for " + entity + ".")
        why = ("The agent assumed the steps were independent and did not model the dependencies or risks, so the "
               "plan's structure - not any single action - caused the failure.")
        correct = "Construct a dependency-aware plan that sequences and gates the steps correctly before touching " + entity + "."
        recovery = [
            "Reconstruct the dependency graph for the steps involved in " + task,
            "Identify where the plan " + flaw,
            "Re-order and gate the steps to respect the dependencies",
            "Re-execute from the last safe point",
            "Validate that " + entity + " is consistent",
        ]
        eval_primary = EVAL_POOL[3]
        tools = list(dict.fromkeys([tool, tool2] + sample_distinct(rng, dom["tools"], 2)))

    elif cat_type == "hallucinated_information":
        fab = pick(rng, [
            "cited a function " + tool + "_v2 that does not exist", "claimed the tests passed without running them",
            "invented a config key that is not in the schema", "reported a metric value it never computed",
            "referenced an API endpoint that was removed in v1", "fabricated a row count for " + artifact,
            "asserted a default that the documentation does not define", "quoted an error code that was never returned",
        ])
        user_request = pick(rng, [
            "Please " + task + " and tell me the result for " + entity + ".",
            "Confirm the state of " + entity + " after you " + task + ".",
            "Give me the verified outcome of " + task + " on " + artifact + ".",
        ])
        agent_action = ("Without checking, the agent " + fab + " while reporting on " + task + " for " + entity + ".")
        root_cause = ("Fabricated content: the agent " + fab + ", presenting an unverified assumption about "
                      + entity + " as an observed fact.")
        why = ("The agent assumed its prior belief was ground truth and skipped the confirming tool call, so it "
               "emitted a confident but unfounded claim about " + artifact + ".")
        correct = "Ground every claim in an actual tool result; verify against " + entity + " before reporting."
        recovery = [
            "Flag the unverified claim the agent made about " + entity,
            "Call the tool needed to actually observe the true state of " + artifact,
            "Compare the real result against the fabricated claim",
            "Correct the report with grounded facts",
            "Note the correction so the false claim is not propagated",
        ]
        eval_primary = EVAL_POOL[5]
        tools = list(dict.fromkeys([tool, tool2] + sample_distinct(rng, dom["tools"], 2)))

    elif cat_type == "insufficient_research":
        skipped = pick(rng, [
            "did not read the existing implementation in " + artifact,
            "never checked the current version or changelog",
            "assumed the schema instead of inspecting it",
            "ignored the README's setup constraints",
            "did not look up how " + entity + " is configured today",
            "skipped searching for prior art in the codebase",
            "failed to confirm the API contract before calling it",
        ])
        user_request = pick(rng, [
            "Please " + task + " for " + entity + ".",
            "Help me " + task + "; the code lives in " + artifact + ".",
            "I want you to " + task + " correctly for our setup of " + entity + ".",
        ])
        agent_action = ("The agent jumped straight to acting on " + task + " and " + skipped
                        + ", so its change did not fit the actual state of " + entity + ".")
        root_cause = ("Insufficient context gathering: the agent " + skipped + ", basing its action on assumptions "
                      "about " + entity + " rather than observed reality.")
        why = ("The agent assumed its generic prior was accurate for this codebase and under-invested in research, "
               "so it acted on a wrong mental model of " + artifact + ".")
        correct = "Investigate " + entity + " first - read " + artifact + " and confirm the contract - then act."
        recovery = [
            "Pause acting on " + task + " and acknowledge the missing context",
            "Read " + artifact + " and gather the facts the agent " + skipped,
            "Revise the approach to fit the real state of " + entity,
            "Re-execute the change with correct assumptions",
            "Validate it integrates with the existing setup",
        ]
        eval_primary = EVAL_POOL[6]
        tools = list(dict.fromkeys([tool, "read_file" if "read_file" in dom["tools"] else tool2]
                                   + sample_distinct(rng, dom["tools"], 2)))

    elif cat_type == "context_loss":
        lost = pick(rng, [
            "forgot the earlier constraint to never touch production",
            "overwrote a change it had made three steps earlier",
            "reused a stale value from before the last update",
            "dropped the user's requirement to preserve backward compatibility",
            "lost track of which environment it was operating in",
            "ignored an exclusion the user gave at the start of the task",
            "re-applied a step it had already completed",
        ])
        user_request = pick(rng, [
            "Over the course of this task, " + task + " for " + entity + " - and remember my earlier constraints.",
            "Continue working on " + entity + ": " + task + ", keeping everything we agreed so far.",
            "Please " + task + "; don't lose the requirements I gave earlier.",
        ])
        agent_action = ("Several steps into the task, the agent " + lost + " while continuing to " + task
                        + " on " + artifact + ".")
        root_cause = ("State/context loss: the agent " + lost + ", because it did not carry the established "
                      "constraints and prior actions forward when operating on " + entity + ".")
        why = ("The agent assumed only the latest message mattered and did not maintain a running task state, so it "
               "contradicted an earlier decision about " + artifact + ".")
        correct = "Maintain an explicit running record of constraints and completed steps, and check it before each action on " + entity + "."
        recovery = [
            "Reconstruct the full task history and the constraints stated earlier",
            "Identify the point where the agent " + lost,
            "Reconcile the current state of " + entity + " with the original requirements",
            "Redo or undo steps to restore consistency",
            "Continue with the constraints re-loaded into context",
        ]
        eval_primary = EVAL_POOL[7]
        tools = list(dict.fromkeys([tool, tool2] + sample_distinct(rng, dom["tools"], 2)))

    elif cat_type == "multi_step_execution_failure":
        step = pick(rng, [
            "step 2 returned an empty result but the agent fed it to step 3 anyway",
            "an intermediate call failed with " + err + " yet the chain continued",
            "the agent used the output of a step that had silently errored",
            "a partial write left " + artifact + " inconsistent before the next step ran",
            "the agent did not check the exit status between steps",
            "a transient failure mid-chain was treated as success",
        ])
        user_request = pick(rng, [
            "Run the full sequence to " + task + " for " + entity + ".",
            "Execute the multi-step job to " + task + " on " + artifact + ".",
            "Please carry out all the steps needed to " + task + ".",
        ])
        agent_action = ("Midway through the chain to " + task + ", " + step + ", so later steps operated on bad "
                        "intermediate data and the job for " + entity + " completed in a corrupted state.")
        root_cause = ("Unverified intermediate result: " + step + ", and the agent propagated the error instead of "
                      "halting, corrupting the downstream steps for " + entity + ".")
        why = ("The agent assumed each step succeeded and did not validate intermediate outputs or exit codes, so a "
               "single mid-chain failure cascaded through the rest of the workflow.")
        correct = "Check each intermediate result and exit status before using it; halt and handle failures mid-chain."
        recovery = [
            "Trace the chain to find where " + step,
            "Roll back the steps that consumed the bad intermediate output",
            "Fix or retry the failed intermediate step in isolation",
            "Re-run the remaining steps from that checkpoint with validation between each",
            "Verify the final state of " + entity + " is consistent",
        ]
        eval_primary = EVAL_POOL[4]
        tools = list(dict.fromkeys([tool, tool2] + sample_distinct(rng, dom["tools"], 2)))

    else:  # recovery_failure
        badfix = pick(rng, [
            "retried a non-idempotent operation, duplicating the effect",
            "swallowed the exception and reported success",
            "rolled back the wrong change and left the real fault in place",
            "entered an infinite retry loop without backoff",
            "restored from a stale backup, reintroducing old data",
            "escalated nothing and silently abandoned the task",
            "applied a fix that masked the symptom but not the cause",
        ])
        user_request = pick(rng, [
            "Please " + task + " for " + entity + ", and handle any errors safely.",
            "Run " + task + " on " + artifact + "; recover cleanly if something fails.",
            "I need " + task + " done resiliently for " + entity + ".",
        ])
        agent_action = ("After hitting " + err + " while trying to " + task + ", the agent " + badfix
                        + ", making the situation on " + entity + " worse rather than restoring it.")
        root_cause = ("Faulty recovery: in response to " + err + ", the agent " + badfix + ", so the recovery itself "
                      "introduced a new fault in " + artifact + ".")
        why = ("The agent assumed any retry/rollback was safe and did not reason about idempotency or root cause, so "
               "its error handling compounded the original failure.")
        correct = "Diagnose the root cause of " + err + " first, then apply an idempotent, targeted recovery for " + entity + "."
        recovery = [
            "Stop the failing recovery loop and freeze the state of " + entity,
            "Diagnose the actual root cause behind " + err,
            "Undo the harmful side effects the agent's recovery created",
            "Apply a correct, idempotent fix and verify it addresses the cause",
            "Add a guard so the same recovery mistake cannot recur",
        ]
        eval_primary = EVAL_POOL[8]
        tools = list(dict.fromkeys([tool, tool2] + sample_distinct(rng, dom["tools"], 2)))

    # Trim recovery to 3-6 steps with a bit of variation.
    if len(recovery) > 4 and rng.random() < 0.4:
        recovery = recovery[:rng.randint(4, len(recovery))]

    return {
        "task": task[0].upper() + task[1:],
        "user_request": user_request,
        "agent_action": agent_action,
        "failure_type": cat_type,
        "failure_category": cat_name,
        "root_cause": root_cause,
        "why_it_failed": why,
        "impact": impact,
        "correct_action": correct,
        "recovery_plan": recovery,
        "expected_tools": tools,
        "evaluation_criteria": build_eval(rng, eval_primary),
    }


def dedup_text(ex):
    """Mirror the audit's near-dup corpus exactly."""
    return f"{ex['user_request']} {ex['agent_action']} {ex['failure_type']}"


def assert_no_placeholder(ex):
    for k, v in ex.items():
        vals = v if isinstance(v, list) else [v]
        for s in vals:
            if isinstance(s, str) and ("{" in s or "}" in s):
                raise ValueError(f"placeholder leaked in field {k}: {s}")


def build_quota_list(total, spec, rng):
    """Return a shuffled list of labels with exact counts from spec (label->pct)."""
    out = []
    for label, pct in spec.items():
        out += [label] * round(total * pct / 100.0)
    # Fix rounding drift.
    while len(out) < total:
        out.append(max(spec, key=spec.get))
    out = out[:total]
    rng.shuffle(out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--total", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--output", type=str, default="agent_failure_dataset.jsonl")
    ap.add_argument("--batch-size", type=int, default=100)
    ap.add_argument("--sim-threshold", type=float, default=0.50,
                    help="HashingVectorizer cosine above which a candidate is rejected as a near-dup")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    per_cat = args.total // len(CATEGORIES)

    sev_quota = build_quota_list(args.total, {"low": 20, "medium": 50, "high": 25, "critical": 5}, rng)
    diff_quota = build_quota_list(args.total, {"easy": 30, "medium": 50, "hard": 20}, rng)

    hv = HashingVectorizer(n_features=2 ** 18, alternate_sign=False, stop_words="english", norm="l2")
    accepted_matrix = None
    exact_keys = set()

    # Build a category plan so each category gets `per_cat` examples, interleaved
    # across batches so every batch is category-balanced.
    cat_plan = []
    for (cname, ctype) in CATEGORIES:
        cat_plan += [(cname, ctype)] * per_cat
    while len(cat_plan) < args.total:
        cat_plan.append(CATEGORIES[len(cat_plan) % len(CATEGORIES)])
    rng.shuffle(cat_plan)

    examples = []
    rejected = 0
    idx = 0
    for (cname, ctype) in cat_plan:
        severity = sev_quota[idx]
        difficulty = diff_quota[idx]
        attempts = 0
        while True:
            attempts += 1
            dom = pick(rng, DOMAINS)
            ex = build_example(rng, cname, ctype, dom, severity)
            assert_no_placeholder(ex)
            ekey = (ex["user_request"], ex["agent_action"], ex["failure_type"], ex["root_cause"])
            if ekey in exact_keys:
                # Exact duplicates are always rejected; the combinatorial space is large
                # enough that a fresh candidate is found within a few tries.
                rejected += 1
                if attempts < 400:
                    continue
                raise RuntimeError("exhausted attempts avoiding exact duplicate")
            text = dedup_text(ex)
            vec = hv.transform([text])
            if accepted_matrix is not None:
                sims = cosine_similarity(vec, accepted_matrix)
                if sims.max() > args.sim_threshold and attempts < 80:
                    rejected += 1
                    continue
            # Accept.
            exact_keys.add(ekey)
            accepted_matrix = vec if accepted_matrix is None else vstack([accepted_matrix, vec])
            ex["id"] = f"agent-failure-{idx + 1:04d}"
            ex["severity"] = severity
            ex["difficulty"] = difficulty
            # Reorder keys to the canonical schema order.
            ordered = {k: ex[k] for k in [
                "id", "task", "user_request", "agent_action", "failure_type", "failure_category",
                "root_cause", "why_it_failed", "impact", "severity", "correct_action",
                "recovery_plan", "expected_tools", "difficulty", "evaluation_criteria"]}
            examples.append(ordered)
            break
        idx += 1

    # Write merged dataset.
    with open(args.output, "w") as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")

    # Write batch files for the intermediate-artifact requirement.
    for b in range(0, args.total, args.batch_size):
        bn = b // args.batch_size + 1
        with open(f"batch_{bn:02d}.jsonl", "w") as f:
            for ex in examples[b:b + args.batch_size]:
                f.write(json.dumps(ex) + "\n")

    print(f"Generated {len(examples)} examples ({rejected} candidates rejected by dedup guard)", file=sys.stderr)
    print(f"Wrote {args.output} and {args.total // args.batch_size} batch files", file=sys.stderr)


if __name__ == "__main__":
    main()
