#!/usr/bin/env python3
"""Validation, dedup, audit, and merge tooling for the agent-failure dataset.

Subcommands:
  validate <files...>   Schema + enum + integrity validation. Exit 1 on errors.
  dedup    <files...>   Exact + near-duplicate detection (Jaccard on token shingles).
  audit    <files...>   Distribution + diversity audit; prints JSON metrics.
  merge    <files...> --out FILE   Concatenate, sort by id, validate, write.

All subcommands accept multiple file paths or globs.
"""
import argparse, json, glob, re, sys, hashlib
from collections import Counter, defaultdict
from itertools import combinations

REQUIRED_KEYS = [
    "id", "task", "user_request", "agent_action", "failure_type",
    "failure_category", "root_cause", "why_it_failed", "impact", "severity",
    "correct_action", "recovery_plan", "expected_tools", "difficulty",
    "evaluation_criteria",
]
STR_KEYS = [
    "id", "task", "user_request", "agent_action", "failure_type",
    "failure_category", "root_cause", "why_it_failed", "impact", "severity",
    "correct_action", "difficulty",
]
LIST_KEYS = ["recovery_plan", "expected_tools", "evaluation_criteria"]

CATEGORIES = [
    "Wrong Tool Selection", "Incorrect Parameters", "Missing Parameters",
    "Incomplete Workflow", "Incorrect Planning", "Hallucinated Information",
    "Insufficient Research", "Context Loss", "Multi-Step Execution Failure",
    "Recovery Failure",
]
SEVERITIES = ["Low", "Medium", "High", "Critical"]
DIFFICULTIES = ["Easy", "Medium", "Hard"]
ID_RE = re.compile(r"^afd_\d{4}$")

# Target distributions (fractions of the whole dataset)
SEV_TARGET = {"Low": 0.20, "Medium": 0.50, "High": 0.25, "Critical": 0.05}
DIFF_TARGET = {"Easy": 0.30, "Medium": 0.50, "Hard": 0.20}


def expand(paths):
    out = []
    for p in paths:
        g = sorted(glob.glob(p))
        out.extend(g if g else [p])
    return out


def load(paths):
    records, errors = [], []
    for path in expand(paths):
        try:
            with open(path) as f:
                for ln, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        records.append((path, ln, json.loads(line)))
                    except json.JSONDecodeError as e:
                        errors.append(f"{path}:{ln} invalid JSON: {e}")
        except FileNotFoundError:
            errors.append(f"{path}: file not found")
    return records, errors


def validate(records):
    errors, warnings = [], []
    seen_ids = {}
    for path, ln, r in records:
        loc = f"{path}:{ln}"
        if not isinstance(r, dict):
            errors.append(f"{loc}: not an object")
            continue
        keys = set(r.keys())
        missing = set(REQUIRED_KEYS) - keys
        extra = keys - set(REQUIRED_KEYS)
        if missing:
            errors.append(f"{loc}: missing keys {sorted(missing)}")
        if extra:
            errors.append(f"{loc}: unexpected keys {sorted(extra)}")
        for k in STR_KEYS:
            v = r.get(k)
            if not isinstance(v, str) or not v.strip():
                errors.append(f"{loc}: field '{k}' must be a non-empty string")
        for k in LIST_KEYS:
            v = r.get(k)
            if not isinstance(v, list) or not v or not all(isinstance(x, str) and x.strip() for x in v):
                errors.append(f"{loc}: field '{k}' must be a non-empty list of non-empty strings")
        if isinstance(r.get("id"), str):
            if not ID_RE.match(r["id"]):
                errors.append(f"{loc}: id '{r['id']}' not in afd_NNNN form")
            if r["id"] in seen_ids:
                errors.append(f"{loc}: duplicate id '{r['id']}' (also {seen_ids[r['id']]})")
            seen_ids[r["id"]] = loc
        if r.get("failure_category") not in CATEGORIES:
            errors.append(f"{loc}: bad failure_category '{r.get('failure_category')}'")
        if r.get("severity") not in SEVERITIES:
            errors.append(f"{loc}: bad severity '{r.get('severity')}'")
        if r.get("difficulty") not in DIFFICULTIES:
            errors.append(f"{loc}: bad difficulty '{r.get('difficulty')}'")
        # soft quality warnings
        if isinstance(r.get("recovery_plan"), list) and len(r["recovery_plan"]) < 3:
            warnings.append(f"{loc}: recovery_plan has <3 steps")
        if isinstance(r.get("expected_tools"), list) and len(r["expected_tools"]) < 2:
            warnings.append(f"{loc}: expected_tools has <2 tools")
        wf = r.get("why_it_failed", "")
        if isinstance(wf, str) and len(wf.split()) < 12:
            warnings.append(f"{loc}: why_it_failed looks thin (<12 words)")
    return errors, warnings


_word = re.compile(r"[a-z0-9_]+")


def tokens(text):
    return _word.findall(text.lower())


def sig_text(r):
    return " ".join(str(r.get(k, "")) for k in
                     ["user_request", "agent_action", "root_cause", "failure_type"])


def shingles(toks, n=3):
    if len(toks) < n:
        return set(toks)
    return {" ".join(toks[i:i + n]) for i in range(len(toks) - n + 1)}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def dedup(records, near=0.55, exact=0.92):
    recs = [r for _, _, r in records]
    norm_hash = {}
    exact_dups = []
    for i, r in enumerate(recs):
        h = hashlib.md5(" ".join(tokens(sig_text(r))).encode()).hexdigest()
        if h in norm_hash:
            exact_dups.append((norm_hash[h], i))
        else:
            norm_hash[h] = i
    sh = [shingles(tokens(sig_text(r))) for r in recs]
    # bucket by shared tokens to avoid full O(n^2) where possible, but n is small enough
    near_dups, hard_dups = [], []
    for i, j in combinations(range(len(recs)), 2):
        s = jaccard(sh[i], sh[j])
        if s >= exact:
            hard_dups.append((i, j, round(s, 3)))
        elif s >= near:
            near_dups.append((i, j, round(s, 3)))
    return recs, exact_dups, hard_dups, sorted(near_dups, key=lambda x: -x[2])


def audit(records):
    recs = [r for _, _, r in records]
    n = len(recs)
    cat = Counter(r.get("failure_category") for r in recs)
    sev = Counter(r.get("severity") for r in recs)
    diff = Counter(r.get("difficulty") for r in recs)
    ftype = Counter(r.get("failure_type") for r in recs)
    tools = Counter()
    for r in recs:
        for t in r.get("expected_tools", []):
            tools[t] += 1
    rc_norm = Counter(" ".join(tokens(r.get("root_cause", "")))[:80] for r in recs)
    recovery_steps = Counter()
    rp_lens = []
    for r in recs:
        rp = r.get("recovery_plan", [])
        rp_lens.append(len(rp))
        for s in rp:
            recovery_steps[" ".join(tokens(s))] += 1
    eval_steps = Counter()
    for r in recs:
        for s in r.get("evaluation_criteria", []):
            eval_steps[" ".join(tokens(s))] += 1
    uniq_users = len(set(" ".join(tokens(r.get("user_request", ""))) for r in recs))
    return {
        "total": n,
        "by_category": dict(cat),
        "by_severity": dict(sev),
        "by_difficulty": dict(diff),
        "severity_pct": {k: round(100 * v / n, 1) for k, v in sev.items()} if n else {},
        "difficulty_pct": {k: round(100 * v / n, 1) for k, v in diff.items()} if n else {},
        "unique_failure_types": len(ftype),
        "unique_tools": len(tools),
        "top_tools": tools.most_common(15),
        "unique_root_cause_prefixes": len(rc_norm),
        "unique_user_requests": uniq_users,
        "unique_recovery_steps": len(recovery_steps),
        "avg_recovery_steps": round(sum(rp_lens) / n, 2) if n else 0,
        "most_repeated_recovery_step": recovery_steps.most_common(3),
        "unique_eval_criteria": len(eval_steps),
    }


def cmd_validate(args):
    records, load_errs = load(args.files)
    errors, warnings = validate(records)
    errors = load_errs + errors
    print(f"Loaded {len(records)} records from {len(expand(args.files))} file(s)")
    for e in errors:
        print("  ERROR:", e)
    for w in warnings[:40]:
        print("  warn :", w)
    if len(warnings) > 40:
        print(f"  ...and {len(warnings)-40} more warnings")
    print(f"\n{len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


def cmd_dedup(args):
    records, load_errs = load(args.files)
    for e in load_errs:
        print("  LOAD ERROR:", e)
    recs, exact_dups, hard_dups, near_dups = dedup(records, near=args.near, exact=args.exact)
    print(f"{len(recs)} records | exact-norm dup pairs: {len(exact_dups)} | "
          f">= {args.exact} sim: {len(hard_dups)} | >= {args.near} sim: {len(near_dups)}")
    for i, j in exact_dups[:20]:
        print(f"  EXACT  {recs[i]['id']} == {recs[j]['id']}")
    for i, j, s in hard_dups[:20]:
        print(f"  HIGH   {recs[i]['id']} ~ {recs[j]['id']}  sim={s}")
    for i, j, s in near_dups[:20]:
        print(f"  near   {recs[i]['id']} ~ {recs[j]['id']}  sim={s}")
    return 1 if (exact_dups or hard_dups) else 0


def cmd_audit(args):
    records, load_errs = load(args.files)
    for e in load_errs:
        print("  LOAD ERROR:", e)
    print(json.dumps(audit(records), indent=2))
    return 0


def cmd_merge(args):
    records, load_errs = load(args.files)
    errors, _ = validate(records)
    errors = load_errs + errors
    if errors:
        print(f"Refusing to merge: {len(errors)} validation errors")
        for e in errors[:20]:
            print("  ERROR:", e)
        return 1
    recs = sorted((r for _, _, r in records), key=lambda r: r["id"])
    with open(args.out, "w") as f:
        for r in recs:
            f.write(json.dumps({k: r[k] for k in REQUIRED_KEYS}, ensure_ascii=False) + "\n")
    print(f"Merged {len(recs)} records -> {args.out}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ["validate", "dedup", "audit", "merge"]:
        p = sub.add_parser(name)
        p.add_argument("files", nargs="+")
        if name == "dedup":
            p.add_argument("--near", type=float, default=0.55)
            p.add_argument("--exact", type=float, default=0.92)
        if name == "merge":
            p.add_argument("--out", required=True)
    args = ap.parse_args()
    sys.exit({"validate": cmd_validate, "dedup": cmd_dedup,
              "audit": cmd_audit, "merge": cmd_merge}[args.cmd](args))


if __name__ == "__main__":
    main()
