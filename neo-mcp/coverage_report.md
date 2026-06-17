# Coverage Report

Total examples: **1000**

## Failure Category Coverage

| Category | Count | Share |
|---|---|---|
| Context Loss | 100 | 10.0% |
| Hallucinated Information | 100 | 10.0% |
| Incomplete Workflow | 100 | 10.0% |
| Incorrect Parameters | 100 | 10.0% |
| Incorrect Planning | 100 | 10.0% |
| Insufficient Research | 100 | 10.0% |
| Missing Parameters | 100 | 10.0% |
| Multi-Step Execution Failure | 100 | 10.0% |
| Recovery Failure | 100 | 10.0% |
| Wrong Tool Selection | 100 | 10.0% |

All 10 categories at exactly 100 examples — perfectly balanced (max deviation +0).

## Severity Coverage

| Severity | Count | Actual | Target |
|---|---|---|---|
| low | 200 | 20.0% | 20.0% |
| medium | 500 | 50.0% | 50.0% |
| high | 250 | 25.0% | 25.0% |
| critical | 50 | 5.0% | 5.0% |

Within ±5% tolerance: **True**

## Difficulty Coverage

| Difficulty | Count | Actual | Target |
|---|---|---|---|
| easy | 300 | 30.0% | 30.0% |
| medium | 500 | 50.0% | 50.0% |
| hard | 200 | 20.0% | 20.0% |

Within ±5% tolerance: **True**

## High-severity concentration by category

Count of high+critical examples per category (informational; severity is assigned independently of category so the spread is roughly uniform):

| Category | High+Critical |
|---|---|
| Context Loss | 34 |
| Hallucinated Information | 26 |
| Incomplete Workflow | 34 |
| Incorrect Parameters | 24 |
| Incorrect Planning | 24 |
| Insufficient Research | 31 |
| Missing Parameters | 37 |
| Multi-Step Execution Failure | 25 |
| Recovery Failure | 31 |
| Wrong Tool Selection | 34 |
