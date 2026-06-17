#!/usr/bin/env python3
"""
audit_pipeline.py - Standalone audit script for synthetic AI agent failure dataset.
Performs schema validation, duplicate detection, distribution checks, and diversity metrics.
"""
import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

SEVERITIES = ["low", "medium", "high", "critical"]
DIFFICULTIES = ["easy", "medium", "hard"]

REQUIRED_FIELDS = [
    "id", "task", "user_request", "agent_action", "failure_type",
    "failure_category", "root_cause", "why_it_failed", "impact",
    "severity", "correct_action", "recovery_plan", "expected_tools",
    "difficulty", "evaluation_criteria"
]

SEVERITY_TARGET = {"low": 20.0, "medium": 50.0, "high": 25.0, "critical": 5.0}
DIFFICULTY_TARGET = {"easy": 30.0, "medium": 50.0, "hard": 20.0}


def load_jsonl(filepath: str) -> List[Dict]:
    """Load a JSONL file into a list of dicts."""
    examples = []
    errors = []
    with open(filepath, "r") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                ex = json.loads(line)
                examples.append(ex)
            except json.JSONDecodeError as e:
                errors.append({"line": i, "error": str(e)})
    return examples, errors


def schema_validation(examples: List[Dict]) -> Dict:
    """Validate all required fields are present, correct types, no empty strings."""
    results = {
        "total": len(examples),
        "passed": 0,
        "failed": 0,
        "issues": [],
        "field_completeness": {},
    }
    
    field_counts = Counter()
    field_empty = Counter()
    
    for ex in examples:
        has_issues = False
        for field in REQUIRED_FIELDS:
            field_counts[field] += 1
            if field not in ex:
                results["issues"].append({
                    "id": ex.get("id", "unknown"),
                    "field": field,
                    "issue": "missing"
                })
                has_issues = True
            elif ex[field] is None:
                results["issues"].append({
                    "id": ex.get("id", "unknown"),
                    "field": field,
                    "issue": "is None"
                })
                has_issues = True
            elif isinstance(ex[field], str) and ex[field].strip() == "":
                field_empty[field] += 1
                results["issues"].append({
                    "id": ex.get("id", "unknown"),
                    "field": field,
                    "issue": "empty string"
                })
                has_issues = True
            elif isinstance(ex[field], (list, tuple)) and len(ex[field]) == 0:
                results["issues"].append({
                    "id": ex.get("id", "unknown"),
                    "field": field,
                    "issue": "empty list"
                })
                has_issues = True
        
        if not has_issues:
            results["passed"] += 1
        else:
            results["failed"] += 1
    
    # Check severity and difficulty values
    for ex in examples:
        if ex.get("severity") not in SEVERITIES:
            results["issues"].append({
                "id": ex.get("id", "unknown"),
                "field": "severity",
                "issue": f"invalid value: {ex.get('severity')}"
            })
        if ex.get("difficulty") not in DIFFICULTIES:
            results["issues"].append({
                "id": ex.get("id", "unknown"),
                "field": "difficulty",
                "issue": f"invalid value: {ex.get('difficulty')}"
            })
    
    # Recovery plan length checks
    for ex in examples:
        rp = ex.get("recovery_plan", [])
        if isinstance(rp, list) and len(rp) < 3:
            results["issues"].append({
                "id": ex.get("id", "unknown"),
                "field": "recovery_plan",
                "issue": f"too few steps ({len(rp)})"
            })
    
    results["field_completeness"] = {
        "total_fields": len(REQUIRED_FIELDS),
        "fields_with_empty": dict(field_empty),
    }
    
    return results


def exact_duplicates(examples: List[Dict]) -> Dict:
    """Detect exact duplicates by key text fields."""
    seen = {}
    duplicates = []
    
    for ex in examples:
        key_fields = (
            ex.get("user_request", ""),
            ex.get("agent_action", ""),
            ex.get("failure_type", ""),
            ex.get("root_cause", ""),
        )
        key = hash(key_fields)
        if key in seen:
            duplicates.append({
                "example_1": seen[key],
                "example_2": ex.get("id", "unknown"),
                "matched_fields": ["user_request", "agent_action", "failure_type", "root_cause"]
            })
        else:
            seen[key] = ex.get("id", "unknown")
    
    return {
        "total_exact_duplicates": len(duplicates),
        "exact_duplicate_rate": len(duplicates) / len(examples) if examples else 0,
        "duplicate_pairs": duplicates[:20],  # First 20 only
    }


def near_duplicates(examples: List[Dict], threshold: float = 0.85) -> Dict:
    """Detect near-duplicates using TF-IDF + cosine similarity."""
    if len(examples) < 2:
        return {"total_near_duplicates": 0, "near_duplicate_rate": 0, "pairs": []}
    
    # Build corpus: concatenate user_request + agent_action + failure_type
    corpus = []
    ids = []
    for ex in examples:
        text = f"{ex.get('user_request', '')} {ex.get('agent_action', '')} {ex.get('failure_type', '')}"
        corpus.append(text)
        ids.append(ex.get("id", "unknown"))
    
    try:
        vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
        tfidf_matrix = vectorizer.fit_transform(corpus)
        similarity_matrix = cosine_similarity(tfidf_matrix)
    except ValueError as e:
        return {"total_near_duplicates": 0, "near_duplicate_rate": 0, "pairs": [], "error": str(e)}
    
    pairs = []
    seen_pairs = set()
    for i in range(len(examples)):
        for j in range(i + 1, len(examples)):
            sim = similarity_matrix[i][j]
            if sim > threshold:
                pair_key = (ids[i], ids[j])
                if pair_key not in seen_pairs:
                    seen_pairs.add(pair_key)
                    pairs.append({
                        "id_1": ids[i],
                        "id_2": ids[j],
                        "similarity": round(float(sim), 4),
                    })
    
    pairs.sort(key=lambda x: x["similarity"], reverse=True)
    
    return {
        "total_near_duplicates": len(pairs),
        "near_duplicate_rate": len(pairs) / len(examples) if examples else 0,
        "threshold_used": threshold,
        "pairs": pairs[:30],
    }


def category_balance(examples: List[Dict]) -> Dict:
    """Count per category and report deviation from target (100 per category)."""
    counts = Counter()
    for ex in examples:
        cat = ex.get("failure_category", "unknown")
        counts[cat] += 1
    
    total = len(examples)
    num_categories = 10
    
    results = {
        "counts": dict(counts.most_common()),
        "expected_per_category": total / num_categories if total else 0,
        "deviations": {},
        "max_deviation": 0,
        "min_category": None,
        "max_category": None,
    }
    
    for cat, count in sorted(counts.items()):
        expected = total / num_categories
        deviation = count - expected
        pct_dev = (deviation / expected * 100) if expected else 0
        results["deviations"][cat] = {
            "count": count,
            "expected": round(expected, 1),
            "deviation": round(deviation, 1),
            "deviation_pct": round(pct_dev, 1),
        }
        if abs(deviation) > abs(results["max_deviation"]):
            results["max_deviation"] = deviation
            results["max_category"] = cat
    
    # Find min
    min_cat = min(counts.items(), key=lambda x: x[1])
    results["min_category"] = min_cat[0]
    
    return results


def severity_distribution(examples: List[Dict]) -> Dict:
    """Check severity distribution against target."""
    counts = Counter()
    for ex in examples:
        counts[ex.get("severity", "unknown")] += 1
    
    total = len(examples)
    results = {"counts": {}, "target_pcts": SEVERITY_TARGET, "actual_pcts": {}, "deviations": {}}
    
    for sev in SEVERITIES:
        count = counts.get(sev, 0)
        actual_pct = (count / total * 100) if total else 0
        target_pct = SEVERITY_TARGET[sev]
        results["counts"][sev] = count
        results["actual_pcts"][sev] = round(actual_pct, 1)
        results["deviations"][sev] = round(actual_pct - target_pct, 1)
    
    # Chi-square-like statistic
    chi2 = 0
    for sev in SEVERITIES:
        observed = counts.get(sev, 0)
        expected = total * SEVERITY_TARGET[sev] / 100
        if expected > 0:
            chi2 += (observed - expected) ** 2 / expected
    
    results["chi_square_stat"] = round(chi2, 4)
    results["within_tolerance"] = all(
        abs(results["deviations"][sev]) <= 5.0 for sev in SEVERITIES
    )
    
    return results


def difficulty_distribution(examples: List[Dict]) -> Dict:
    """Check difficulty distribution against target."""
    counts = Counter()
    for ex in examples:
        counts[ex.get("difficulty", "unknown")] += 1
    
    total = len(examples)
    results = {"counts": {}, "target_pcts": DIFFICULTY_TARGET, "actual_pcts": {}, "deviations": {}}
    
    for diff in DIFFICULTIES:
        count = counts.get(diff, 0)
        actual_pct = (count / total * 100) if total else 0
        target_pct = DIFFICULTY_TARGET[diff]
        results["counts"][diff] = count
        results["actual_pcts"][diff] = round(actual_pct, 1)
        results["deviations"][diff] = round(actual_pct - target_pct, 1)
    
    chi2 = 0
    for diff in DIFFICULTIES:
        observed = counts.get(diff, 0)
        expected = total * DIFFICULTY_TARGET[diff] / 100
        if expected > 0:
            chi2 += (observed - expected) ** 2 / expected
    
    results["chi_square_stat"] = round(chi2, 4)
    results["within_tolerance"] = all(
        abs(results["deviations"][diff]) <= 5.0 for diff in DIFFICULTIES
    )
    
    return results


def recovery_plan_diversity(examples: List[Dict]) -> Dict:
    """Analyze recovery plan diversity."""
    first_step_patterns = Counter()
    all_steps = []
    avg_steps = 0
    
    for ex in examples:
        rp = ex.get("recovery_plan", [])
        if isinstance(rp, list) and len(rp) > 0:
            # Extract first step pattern: first 4 words
            first_step = rp[0]
            words = first_step.split()[:4]
            pattern = " ".join(words)
            first_step_patterns[pattern] += 1
            all_steps.extend(rp)
            avg_steps += len(rp)
    
    avg_steps = avg_steps / len(examples) if examples else 0
    
    # Shannon entropy of first-step patterns
    total_patterns = sum(first_step_patterns.values())
    entropy = 0
    for count in first_step_patterns.values():
        p = count / total_patterns
        entropy -= p * math.log2(p) if p > 0 else 0
    
    # Count unique first-step patterns
    unique_patterns = len(first_step_patterns)
    
    return {
        "unique_first_step_patterns": unique_patterns,
        "first_step_pattern_entropy": round(entropy, 4),
        "avg_steps_per_plan": round(avg_steps, 2),
        "total_unique_recovery_texts": len(set(" ".join(ex.get("recovery_plan", [])) for ex in examples)),
        "top_first_step_patterns": dict(first_step_patterns.most_common(15)),
    }


def tool_diversity(examples: List[Dict]) -> Dict:
    """Count unique tools across all examples."""
    all_tools = []
    tool_counts = Counter()
    
    for ex in examples:
        tools = ex.get("expected_tools", [])
        if isinstance(tools, list):
            for tool in tools:
                all_tools.append(tool)
                tool_counts[tool] += 1
    
    unique_tools = len(set(all_tools))
    
    return {
        "unique_tools": unique_tools,
        "total_tool_occurrences": len(all_tools),
        "avg_tools_per_example": round(len(all_tools) / len(examples), 2) if examples else 0,
        "top_tools": dict(tool_counts.most_common(20)),
    }


def root_cause_diversity(examples: List[Dict]) -> Dict:
    """Analyze root cause diversity by clustering first few words."""
    patterns = Counter()
    
    for ex in examples:
        rc = ex.get("root_cause", "")
        words = rc.split()[:6]
        pattern = " ".join(words)
        patterns[pattern] += 1
    
    total = sum(patterns.values())
    
    # Shannon entropy
    entropy = 0
    for count in patterns.values():
        p = count / total
        entropy -= p * math.log2(p) if p > 0 else 0
    
    # Count patterns that appear more than once
    repeated = {k: v for k, v in patterns.items() if v > 1}
    
    return {
        "unique_root_cause_patterns": len(patterns),
        "root_cause_entropy": round(entropy, 4),
        "repeated_patterns": len(repeated),
        "top_root_cause_patterns": dict(patterns.most_common(15)),
    }


def compute_quality_score(results: Dict) -> Dict:
    """Compute a composite quality score from all audit metrics."""
    scores = {}
    
    # Schema validation (0-100)
    schema = results.get("schema_validation", {})
    passed = schema.get("passed", 0)
    total = schema.get("total", 1)
    scores["schema_score"] = (passed / total * 100) if total else 0
    
    # Exact dup rate (score: 100 - dup_rate * 100)
    exact_dup_rate = results.get("exact_duplicates", {}).get("exact_duplicate_rate", 0)
    scores["exact_dup_score"] = max(0, 100 - exact_dup_rate * 1000)
    
    # Near dup rate (score: 100 - near_dup_rate * 1000)
    near_dup_rate = results.get("near_duplicates", {}).get("near_duplicate_rate", 0)
    scores["near_dup_score"] = max(0, 100 - near_dup_rate * 1000)
    
    # Category balance (0-100): avg deviation from 10%
    cat_balance = results.get("category_balance", {})
    if cat_balance:
        devs = [abs(d["deviation_pct"]) for d in cat_balance.get("deviations", {}).values()]
        avg_dev = sum(devs) / len(devs) if devs else 0
        scores["category_balance_score"] = max(0, 100 - avg_dev * 2)
    else:
        scores["category_balance_score"] = 0
    
    # Severity distribution (0-100)
    sev = results.get("severity_distribution", {})
    if sev:
        avg_sev_dev = sum(abs(v) for v in sev.get("deviations", {}).values()) / 4
        scores["severity_score"] = max(0, 100 - avg_sev_dev * 5)
    else:
        scores["severity_score"] = 0
    
    # Difficulty distribution (0-100)
    diff = results.get("difficulty_distribution", {})
    if diff:
        avg_diff_dev = sum(abs(v) for v in diff.get("deviations", {}).values()) / 3
        scores["difficulty_score"] = max(0, 100 - avg_diff_dev * 5)
    else:
        scores["difficulty_score"] = 0
    
    # Diversity (0-100): min of tool diversity, root cause diversity, recovery diversity
    tool_div = results.get("tool_diversity", {})
    rc_div = results.get("root_cause_diversity", {})
    rp_div = results.get("recovery_plan_diversity", {})
    
    tool_entropy = min(tool_div.get("unique_tools", 0) / 50 * 100, 100)
    rc_entropy = min(rc_div.get("root_cause_entropy", 0) / 5 * 100, 100)
    rp_entropy = min(rp_div.get("first_step_pattern_entropy", 0) / 5 * 100, 100)
    scores["tool_diversity_score"] = round(tool_entropy, 1)
    scores["root_cause_diversity_score"] = round(rc_entropy, 1)
    scores["recovery_diversity_score"] = round(rp_entropy, 1)
    
    diversity_score = (tool_entropy + rc_entropy + rp_entropy) / 3
    scores["diversity_score"] = round(diversity_score, 1)
    
    # Composite: weighted average
    weights = {
        "schema_score": 0.20,
        "exact_dup_score": 0.15,
        "near_dup_score": 0.10,
        "category_balance_score": 0.15,
        "severity_score": 0.10,
        "difficulty_score": 0.10,
        "diversity_score": 0.20,
    }
    
    composite = sum(scores.get(k, 0) * w for k, w in weights.items())
    scores["composite_quality_score"] = round(composite, 1)
    
    return scores


def run_audit(jsonl_path: str) -> Dict:
    """Run full audit on a JSONL file and return results."""
    print(f"Loading {jsonl_path}...", file=sys.stderr)
    examples, parse_errors = load_jsonl(jsonl_path)
    print(f"  Loaded {len(examples)} examples, {len(parse_errors)} parse errors", file=sys.stderr)
    
    results = {
        "file": jsonl_path,
        "total_examples": len(examples),
        "parse_errors": parse_errors,
    }
    
    # Run all checks
    print("  Schema validation...", file=sys.stderr)
    results["schema_validation"] = schema_validation(examples)
    
    print("  Exact duplicate detection...", file=sys.stderr)
    results["exact_duplicates"] = exact_duplicates(examples)
    
    print("  Near-duplicate detection (TF-IDF)...", file=sys.stderr)
    results["near_duplicates"] = near_duplicates(examples, threshold=0.85)
    
    print("  Category balance...", file=sys.stderr)
    results["category_balance"] = category_balance(examples)
    
    print("  Severity distribution...", file=sys.stderr)
    results["severity_distribution"] = severity_distribution(examples)
    
    print("  Difficulty distribution...", file=sys.stderr)
    results["difficulty_distribution"] = difficulty_distribution(examples)
    
    print("  Recovery plan diversity...", file=sys.stderr)
    results["recovery_plan_diversity"] = recovery_plan_diversity(examples)
    
    print("  Tool diversity...", file=sys.stderr)
    results["tool_diversity"] = tool_diversity(examples)
    
    print("  Root cause diversity...", file=sys.stderr)
    results["root_cause_diversity"] = root_cause_diversity(examples)
    
    # Quality score
    print("  Computing quality score...", file=sys.stderr)
    results["quality_score"] = compute_quality_score(results)
    
    return results


def print_summary(results: Dict):
    """Print a human-readable summary of audit results."""
    total = results["total_examples"]
    print(f"\n{'='*70}")
    print(f"AUDIT SUMMARY: {results['file']}")
    print(f"{'='*70}")
    print(f"Total examples: {total}")
    
    # Schema
    sv = results["schema_validation"]
    print(f"\n📋 Schema Validation:")
    print(f"  Passed: {sv['passed']}/{sv['total']} ({sv['passed']/sv['total']*100:.1f}%)")
    print(f"  Failed: {sv['failed']}")
    if sv['issues']:
        print(f"  Issues: {len(sv['issues'])} total")
        for iss in sv['issues'][:5]:
            print(f"    - {iss['id']}: {iss['field']} - {iss['issue']}")
    
    # Duplicates
    ed = results["exact_duplicates"]
    nd = results["near_duplicates"]
    print(f"\n🔍 Duplicate Analysis:")
    print(f"  Exact duplicates: {ed['total_exact_duplicates']} ({ed['exact_duplicate_rate']*100:.2f}%)")
    print(f"  Near-duplicates (>{nd.get('threshold_used', 0.85)}): {nd['total_near_duplicates']} ({nd['near_duplicate_rate']*100:.2f}%)")
    
    # Category balance
    cb = results["category_balance"]
    print(f"\n📊 Category Balance:")
    for cat, info in sorted(cb.get("deviations", {}).items()):
        marker = " ⚠️" if abs(info["deviation"]) > 10 else ""
        print(f"  {cat}: {info['count']} (expected {info['expected']}, dev: {info['deviation']:+.1f}){marker}")
    
    # Severity
    sd = results["severity_distribution"]
    print(f"\n📈 Severity Distribution:")
    for sev in SEVERITIES:
        actual = sd.get("actual_pcts", {}).get(sev, 0)
        target = sd.get("target_pcts", {}).get(sev, 0)
        dev = sd.get("deviations", {}).get(sev, 0)
        marker = " ⚠️" if abs(dev) > 5 else ""
        print(f"  {sev}: {sd['counts'].get(sev, 0)} ({actual}%) target {target}% (dev: {dev:+.1f}){marker}")
    print(f"  Within ±5% tolerance: {sd.get('within_tolerance', False)}")
    
    # Difficulty
    dd = results["difficulty_distribution"]
    print(f"\n📈 Difficulty Distribution:")
    for diff in DIFFICULTIES:
        actual = dd.get("actual_pcts", {}).get(diff, 0)
        target = dd.get("target_pcts", {}).get(diff, 0)
        dev = dd.get("deviations", {}).get(diff, 0)
        marker = " ⚠️" if abs(dev) > 5 else ""
        print(f"  {diff}: {dd['counts'].get(diff, 0)} ({actual}%) target {target}% (dev: {dev:+.1f}){marker}")
    print(f"  Within ±5% tolerance: {dd.get('within_tolerance', False)}")
    
    # Diversity
    td = results["tool_diversity"]
    rd = results["root_cause_diversity"]
    rp = results["recovery_plan_diversity"]
    print(f"\n🎯 Diversity Metrics:")
    print(f"  Unique tools: {td.get('unique_tools', 0)}")
    print(f"  Unique root cause patterns: {rd.get('unique_root_cause_patterns', 0)}")
    print(f"  Unique recovery first-step patterns: {rp.get('unique_first_step_patterns', 0)}")
    print(f"  Root cause entropy: {rd.get('root_cause_entropy', 0)}")
    print(f"  Recovery pattern entropy: {rp.get('first_step_pattern_entropy', 0)}")
    print(f"  Avg steps per plan: {rp.get('avg_steps_per_plan', 0)}")
    
    # Quality score
    qs = results.get("quality_score", {})
    print(f"\n⭐ Quality Score:")
    for k, v in qs.items():
        print(f"  {k}: {v}")
    
    print(f"\n{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(description="Audit AI agent failure dataset")
    parser.add_argument("--input", type=str, required=True, help="Input JSONL file path")
    parser.add_argument("--output", type=str, default=None, help="Output audit JSON file path (optional)")
    args = parser.parse_args()
    
    results = run_audit(args.input)
    print_summary(results)
    
    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"Audit written to {args.output}", file=sys.stderr)
    
    return results


if __name__ == "__main__":
    main()