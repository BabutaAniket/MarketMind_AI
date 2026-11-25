# Guideline status

Checked against `capstone_fullstack_projects.pdf` (the minimum bar on page 3 and the evaluation protocol on pages 5-6). Status is based on what runs in this folder.

**Verified** means exercised on the build machine (tests, live server, browser). **Written, unverified** means the files exist but could not be run there (no Docker).

| Area | Minimum bar | Status | Evidence / gap |
|---|---|---|---|
| Retrieval | Source and date metadata; hybrid BM25 + vectors with RRF; reranker; one query-side technique; passage IDs; Recall@5 on 30+ queries before and after a change | **Partial** | Verified: FastEmbed MiniLM vectors in in-memory Qdrant, BM25+RRF, query expansion, overlap reranker; 30 labeled synthetic queries: Recall@5 0.7241 → 0.8621. Labels cover only the included fictional profile; no cross-encoder or persistent Qdrant collection |
| Tools and MCP | 3+ FastMCP servers, typed I/O, structured errors, read/write marks, one test per tool | **Done locally** | Four FastMCP servers, typed signatures, structured results, read/write annotations and in-process client tests. Agent allowlists and a 12-call budget are enforced in the gateway. Knowledge-server HTTP transport also passed a localhost smoke test; the four-service Compose stack is unverified |
| Orchestration | LangGraph, typed state, conditional edges, self-correction loop, persistent checkpointer, stop and resume | **Mostly done** | Typed LangGraph state, conditional design routes, one deterministic correction pass, SQLite checkpoint, `interrupt()` approve/edit/reject and resume. Verified resume from a separate Python process after the start process exited. Record the demo for submission |
| Memory | Short-term trimming; long-term store; written policy; memory on/off comparison | **Partial** | Approved lessons are filtered for relevance before the prompt; written policy ([MEMORY_POLICY.md](MEMORY_POLICY.md)); no short-term chat trimming or memory on/off comparison |
| Planning | Plan object; replan on contradiction; ReAct in specialists | **Partial** | Plan object and evidence search are in the graph; contradiction-triggered replan and ReAct loops are not implemented |
| Multi-agent | Supervisor + 3 specialists with own tools, typed hand-offs, single-agent baseline | **Partial** | Strategy, content, lead and compliance handoffs run in the team route; fixed, single-node and team-node dry-run routes exist. Research/review/publisher use allowlisted tools. Routes use deterministic code, not comparable LLM agents, so E1 is still pending |
| Improvement | Reflexion loop, human-reviewed lessons, frozen playbook, held-out before/after | **Partial** | Human-approved lesson storage and context filtering exist; no automated reflection generation, frozen playbook version or held-out before/after result |
| Evaluation | 60+ cases (about 20 dev / 40+ held-out), outcomes, trajectories, tool use, different-family judge, 20+ human labels, kappa | **Partial** | 60 cases (40 dev / 20 held-out, wrong split), 30 attacks. Input guardrail only: 13/30 attacks blocked and 4/60 clean requests false-blocked. No independent judge, human labels or kappa |
| Experiments E1-E4 | Fixed vs single vs team; defences off/on; playbook on/off; signature ablation; 3 repeats | **Not done** | None run |
| Human control | `interrupt()` approve/edit/reject; exact payload; edit invalidates; pre/post hooks | **Partial** | LangGraph `interrupt()` pauses for approve/edit/reject; exact payload hashes, changed-hash reapproval and replay rejection are tested. Gateway enforces allowlists/budget and logs scrubbed tool summaries. No authenticated reviewer identity; no separate process-level stop/resume demonstration |
| Security | Threat model; input/output guardrails; least privilege; 30+ attacks; attack success off vs on; false-block rate | **Partial** | [THREAT_MODEL.md](THREAT_MODEL.md); regex guardrails; 30 attacks. Input-only off/on: attack success 100% → 56.7%, false blocks 0% → 6.7%. Full workflow/output-attack comparison remains pending |
| Deployment | FastAPI streaming; Compose with app, MCP servers, vector store, Prometheus, Grafana; versioned prompts/model IDs; CI eval gate; alert | **Partial** | Verified: FastAPI, NDJSON stream, `/metrics`. Compose defines app + four MCP services + Prometheus/Grafana and one alert; Docker services are unverified. Qdrant collection is in-memory, not a persistent service. CI gate runs guardrail evaluation and currently fails |
| Prompt foundations | Six-slot prompts for every agent, critic, judge, reflection | **Partial** | Six-slot versioned campaign-drafter prompt is in `config/prompts.json`. Specialist, judge and reflection prompts are not complete |
| Models | OpenRouter default, different-family judge | **Partial** | LiteLLM routes Ollama/Qwen3 and optional OpenRouter; provider call is mock-tested. No real model generation or calibrated different-family judge has been run |
| Submission | One-command README, redrawn diagram, threat model, memory policy, 4-6 page report, experiment log, contribution log, slides, backup demo | **Partial** | README, diagram, threat model, memory policy, report, experiment log and contribution log drafts are in `docs`. Slides and demo recording are outside this folder |

## Requested stack versus this project

| Requested | In this folder |
|---|---|
| Ollama + Qwen3 | Configured route; model generation not run on this laptop |
| LiteLLM | Integrated in the model gateway; mock-tested, real provider unverified |
| LangGraph | Integrated with SQLite checkpoints and human interrupt/resume |
| PostgreSQL + pgvector or Qdrant | Local-memory Qdrant is used for each retrieval query; no persistent Qdrant service or PostgreSQL records store |
| Unsloth + PEFT, MLflow | Not present |
| Feedback dashboard | Web app and desktop apps |

A separate repository, `marketmind-ai`, contains work toward the heavier stack (Qdrant index, ported retrieval and approval modules, FastMCP servers); it is not merged here.

## Highest-value next steps

1. Run a process-stop / restart / resume demo, then verify the HTTP MCP services with Docker Compose on another machine.
2. Install Qwen3 on a machine that supports it; run and record a real LiteLLM generation.
3. Keep the 30-query Recall@5 report as development evidence only; independently label 30+ retrieval queries and rerun before/after.
4. Build full-workflow E1-E4 comparisons, judge calibration and three final held-out repeats.
5. Rebuild the golden split using independently written cases (about 20 dev / 40+ held-out), and keep held-out cases inaccessible to tuning.
6. Add authenticated reviewer identity and persistent Qdrant/PostgreSQL memory if required by the final stack.
7. Finish the evaluation report, contribution log, slides, backup demo, and source/data license review.
