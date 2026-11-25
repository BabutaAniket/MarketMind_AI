# Experiment log

One row per run. Record every configuration, including failed and timed-out runs. If anything is changed after viewing held-out results, mark those cases as development cases.

Detailed retrieval results are in `eval/retrieval_report.json`. A complete E1-E4 experiment-config runner has not been built.

| Date | ID | Config file | Model and ID | Cases | Task success | Policy violations | Attack success | False blocks | Cost / case | Median / P95 latency | Errors | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-11-25 | R1 | `config/config.json` | FastEmbed `sentence-transformers/all-MiniLM-L6-v2` | 30 queries / 58 passage labels | n/a | n/a | n/a | n/a | n/a | not recorded | 0 | BM25+TF-IDF baseline 42/58 (0.7241); Qdrant+RRF+overlap reranker 50/58 (0.8621); dev data only |
| 2026-11-25 | E2-input | `config/config.json` | none (regex input guardrail only) | 30 attacks + 60 clean requests | n/a | n/a | off 30/30; on 17/30 | off 0/60; on 4/60 | 0 | not recorded | 0 | On: blocks 13/30 attacks, allows 56/60 clean requests; gate fails. Not a full-workflow experiment |

## Planned experiments

| ID | Question | Configurations |
|---|---|---|
| E1 | Does the agent justify its cost? | C0 fixed workflow, C1 single agent with all tools, C2 team. Same model, tools, budget |
| E2 | Do the defences work? | Defences off vs on, on the red-team set and on clean cases |
| E3 | Did the lessons help? | Held-out before vs after the frozen playbook, including lesson cost |
| E4 | Signature ablation | Define with faculty |

Final held-out comparison: three repeats, report the spread.
