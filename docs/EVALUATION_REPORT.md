# Evaluation report (draft)

This is a prototype evaluation, not the final capstone report. It reports measured results and keeps the remaining required experiments explicit.

## 1. Scope and users

User: a marketer at a small company who needs channel drafts and lead follow-up grounded in approved company information. Proposed impact measures are editing time per approved draft and the proportion of factual claims supported by cited passages. Neither has been measured with human users.

## 2. Data and method

| Set | File | Cases | Notes |
|---|---|---:|---|
| Campaign golden set | `eval/golden_set.jsonl` | 60 | 40 development / 20 held-out; this does not meet the guide's roughly 20 dev / 40+ held-out split |
| Red-team set | `eval/red_team_cases.jsonl` | 30 | Natural-language unsafe requests |
| Retrieval labels | `eval/retrieval_golden.jsonl` | 30 queries / 58 relevant passage labels | Hand-labeled against the included synthetic Cedarline profile; development data only |

The campaign set has a repeated four-point expected checklist and is not yet a strong independent benchmark. The retrieval set is specific to one synthetic company, not representative of a broad corpus.

## 3. Retrieval Recall@5

Run: `python scripts/retrieval_eval.py`. Exact per-query results are saved in `eval/retrieval_report.json`.

| Method | Relevant passages retrieved | Recall@5 |
|---|---:|---:|
| Previous weighted BM25 + TF-IDF cosine baseline | 42 / 58 | 0.7241 |
| FastEmbed MiniLM vectors in in-memory Qdrant + BM25 RRF + overlap reranker | 50 / 58 | 0.8621 |
| Change | +8 passages | +0.1380 |

This is a reproducible before/after comparison on the current 30-query development set. The previous method is reimplemented from prior code rather than taken from a saved historical run. Qdrant rebuilds an in-memory collection per query; the overlap reranker is not a cross-encoder.

## 4. Input guardrail evaluation

Run: `python scripts/eval_gate.py`. Scope is the **input regex guardrail only**, not the complete agent workflow or generated output.

| Configuration | Attack success | False blocks on legitimate requests |
|---|---:|---:|
| Defences off | 30 / 30 (100%) | 0 / 60 (0%) |
| Defences on | 17 / 30 (56.7%) | 4 / 60 (6.7%) |
| Required gate | at most 15% attack success and at most 15% false blocks | **Fails:** attack success is too high |

With defences on, 13 of 30 attacks were blocked and 56 of 60 ordinary requests were allowed. The misses include natural-language promises and unsupported commercial claims; the false blocks include benign mentions of guarantees. Do not tune against this set and then call it held-out.

## 5. Workflow verification

The LangGraph demo workflow was exercised over HTTP. It produced research, planning, specialist, review and action-preparation events; called knowledge, checks and action FastMCP tools; and paused for approval. Tests edited the payload, confirmed its hash changed, rejected approval with the old hash, then resumed and approved the current hash. The action remained mock-only.

This verifies the local prototype mechanics. It is not a campaign-quality evaluation and does not prove process kill/restart recovery in a live demonstration.

## 6. Required results still missing

| Item | Status |
|---|---|
| 60+ independent campaign cases with about 20 development / 40+ protected held-out | **TODO** |
| Outcomes, trajectories and tool-use scoring over the full workflow | **TODO** |
| Different-family judge, 20+ human labels and Cohen's kappa | **TODO** |
| E1 fixed vs single agent vs team | **TODO** |
| E2 full workflow defences off vs on | **TODO** |
| E3 held-out playbook off vs on, including lesson cost | **TODO** |
| E4 signature ablation | **TODO** |
| Cost, median/P95 latency, errors and three final repeats | **TODO** |
| Human editing-time study and claim-support evaluation | **TODO** |

## 7. Limits

The specialists are deterministic functions, not independent LLM agents. No real Ollama or OpenRouter generation was run in the current environment. The app has no authentication, supports one active company, and stores records in local JSON. No external actions occur. Before a supervised pilot, add authentication and roles, perform a privacy review, strengthen output claim verification, and test deployment on a clean machine.
