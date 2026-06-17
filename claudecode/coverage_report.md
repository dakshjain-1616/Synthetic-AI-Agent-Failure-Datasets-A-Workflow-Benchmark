# Coverage Report

**Dataset:** `agent_failure_dataset.jsonl`  
**Total examples:** 1000

## 1. Failure-category coverage

Target: 100 per category (10% each). **Result: exact.**

| # | Failure category | Count | Share | |
|---|---|---:|---:|---|
| 1 | Wrong Tool Selection | 100 | 10% | ██·················· |
| 2 | Incorrect Parameters | 100 | 10% | ██·················· |
| 3 | Missing Parameters | 100 | 10% | ██·················· |
| 4 | Incomplete Workflow | 100 | 10% | ██·················· |
| 5 | Incorrect Planning | 100 | 10% | ██·················· |
| 6 | Hallucinated Information | 100 | 10% | ██·················· |
| 7 | Insufficient Research | 100 | 10% | ██·················· |
| 8 | Context Loss | 100 | 10% | ██·················· |
| 9 | Multi-Step Execution Failure | 100 | 10% | ██·················· |
| 10 | Recovery Failure | 100 | 10% | ██·················· |

## 2. Severity distribution

| Severity | Target | Count | Actual | |
|---|---:|---:|---:|---|
| Low | 20% | 200 | 20.0% | ████················ |
| Medium | 50% | 500 | 50.0% | ██████████·········· |
| High | 25% | 250 | 25.0% | █████··············· |
| Critical | 5% | 50 | 5.0% | █··················· |

## 3. Difficulty distribution

| Difficulty | Target | Count | Actual | |
|---|---:|---:|---:|---|
| Easy | 30% | 300 | 30.0% | ██████·············· |
| Medium | 50% | 500 | 50.0% | ██████████·········· |
| Hard | 20% | 200 | 20.0% | ████················ |

## 4. Severity × Category cross-tab

| Category | Low | Medium | High | Critical |
|---|---:|---:|---:|---:|
| Wrong Tool Selection | 20 | 50 | 25 | 5 |
| Incorrect Parameters | 20 | 50 | 25 | 5 |
| Missing Parameters | 20 | 50 | 25 | 5 |
| Incomplete Workflow | 20 | 50 | 25 | 5 |
| Incorrect Planning | 20 | 50 | 25 | 5 |
| Hallucinated Information | 20 | 50 | 25 | 5 |
| Insufficient Research | 20 | 50 | 25 | 5 |
| Context Loss | 20 | 50 | 25 | 5 |
| Multi-Step Execution Failure | 20 | 50 | 25 | 5 |
| Recovery Failure | 20 | 50 | 25 | 5 |

## 5. Difficulty × Category cross-tab

| Category | Easy | Medium | Hard |
|---|---:|---:|---:|
| Wrong Tool Selection | 30 | 50 | 20 |
| Incorrect Parameters | 30 | 50 | 20 |
| Missing Parameters | 30 | 50 | 20 |
| Incomplete Workflow | 30 | 50 | 20 |
| Incorrect Planning | 30 | 50 | 20 |
| Hallucinated Information | 30 | 50 | 20 |
| Insufficient Research | 30 | 50 | 20 |
| Context Loss | 30 | 50 | 20 |
| Multi-Step Execution Failure | 30 | 50 | 20 |
| Recovery Failure | 30 | 50 | 20 |

## 6. Domain coverage (by expected-tool bucket)

Tool mentions classified into ecosystem buckets (a proxy for domain spread).

| Domain bucket | Tool mentions |
|---|---:|
| other | 1194 |
| comms/crm | 357 |
| data/sql | 353 |
| git/github | 238 |
| mcp | 224 |
| web/research | 194 |
| cloud/iac | 152 |
| kubernetes | 133 |
| rag/vector | 133 |
| payments | 84 |
| ci/cd | 67 |
| observability | 64 |
| ml | 36 |
| security | 27 |

## 7. Coverage score

All three target distributions (category, severity, difficulty) match their targets exactly, so the **coverage score = 100%** (sum of absolute deviations from target = 0 across all 17 buckets).
