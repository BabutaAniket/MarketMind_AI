# Guideline status

Checked against `capstone_fullstack_projects.pdf` (the minimum bar on page 3 and the evaluation protocol on pages 5-6). Status is based on what runs in this folder.

**Verified** means exercised on the build machine (tests, live server, browser). **Written, unverified** means the files exist but could not be run there (no Docker).

| Area | Minimum bar | Status | Evidence / gap |
|---|---|---|---|
| Retrieval | Source and date metadata; hybrid BM25 + vectors with RRF; reranker; one query-side technique; passage IDs; Recall@5 on 30+ queries before and after a change | **Partial** | Verified: metadata, passage IDs, BM25 + TF-IDF weighted hybrid, rule-based query expansion. Missing: embeddings, RRF, reranker, labelled queries, Recall@5 |
| Tools and MCP | 3+ FastMCP servers, typed I/O, structured errors, read/write marks, one test per tool | **Partial** | Three tool modules with structured errors and tests; not FastMCP servers, no schemas exposed |
| Orchestration | LangGraph, typed state, conditional edges, self-correction loop, persistent checkpointer, stop and resume | **Not done** | Sequential Python orchestrator only |
| Memory | Short-term trimming; long-term store; written policy; memory on/off comparison | **Partial** | Approved-lesson store and written policy ([MEMORY_POLICY.md](MEMORY_POLICY.md)); no trimming, no comparison |
| Planning | Plan object; replan on contradiction; ReAct in specialists | **Partial** | Plan object shown; no replan or ReAct |
| Multi-agent | Supervisor + 3 specialists with own tools, typed hand-offs, single-agent baseline | **Partial** | Four rule-based specialist functions; no per-agent tools, no baseline comparison |
| Improvement | Reflexion loop, human-reviewed lessons, frozen playbook, held-out before/after | **Not done** | Manual feedback store only |
| Evaluation | 60+ cases (about 20 dev / 40+ held-out), outcomes, trajectories, tool use, different-family judge, 20+ human labels, kappa | **Partial** | 60 cases (split is 40 dev / 20 held-out, the reverse of the guide) and 30 attacks exist; evaluation covers the input guardrail only; no judge, labels or kappa |
| Experiments E1-E4 | Fixed vs single vs team; defences off/on; playbook on/off; signature ablation; 3 repeats | **Not done** | None run |
| Human control | `interrupt()` approve/edit/reject; exact payload; edit invalidates; pre/post hooks | **Partial** | Verified: hash-bound approve/edit/reject, edit invalidation, no replay (tests + browser). Missing: LangGraph `interrupt()`, tool hooks, reviewer identity |
| Security | Threat model; input/output guardrails; least privilege; 30+ attacks; attack success off vs on; false-block rate | **Partial** | [THREAT_MODEL.md](THREAT_MODEL.md); regex guardrails; 30 attacks. Verified result: 13/30 blocked, 4/60 legitimate cases wrongly blocked. No off-vs-on run |
| Deployment | FastAPI streaming; Compose with app, MCP, vector store, Prometheus, Grafana; versioned prompts and model IDs; CI eval gate; one alert | **Partial** | Verified: FastAPI, NDJSON streaming, `/metrics`, CI gate script (currently fails). Written, unverified: Compose, Prometheus, Grafana dashboard, alert rule, GitHub Actions. Missing: vector store service, MCP services, prompts in versioned config |
| Prompt foundations | Six-slot prompts for every agent, critic, judge, reflection | **Not done** | One inline prompt in `planner.py` |
| Models | OpenRouter default, different-family judge | **Partial** | OpenRouter and Ollama clients exist; the local-model path has not been run (model not pulled) |
| Submission | One-command README, redrawn diagram, threat model, memory policy, 4-6 page report, experiment log, contribution log, slides, backup demo | **Partial** | README, diagram, threat model, memory policy, report, experiment log and contribution log drafts are in `docs`. Slides and demo recording are outside this folder |

## Requested stack versus this project

| Requested | In this folder |
|---|---|
| Ollama + Qwen3 | Client and status check; model not yet pulled or run |
| LiteLLM | Not used |
| LangGraph | Not used |
| PostgreSQL + pgvector or Qdrant | Not used (JSON and JSONL files) |
| Unsloth + PEFT, MLflow | Not present |
| Feedback dashboard | Web app and desktop apps |

A separate repository, `marketmind-ai`, contains work toward the heavier stack (Qdrant index, ported retrieval and approval modules, FastMCP servers); it is not merged here.

## Highest-value next steps

1. Pull the model and run one real Qwen3 generation end to end.
2. Replace the keyword guardrail evaluation with a run through the full workflow (input and output defences off vs on).
3. Rebuild orchestration as a LangGraph graph with a persistent checkpointer and `interrupt()` approval.
4. Turn the tools into FastMCP servers with schemas and per-tool tests.
5. Add labelled retrieval queries and measure Recall@5 before and after one change.
6. Rewrite prompts in six slots and move them, with model IDs, into one versioned config.
7. Re-split the golden set (about 20 development, 40+ held-out) with the held-out cases kept away from the agent tuner.
