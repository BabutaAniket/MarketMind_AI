# MarketMind AI

Grounded campaign planning and lead qualification for a company's own marketing. Every draft is traceable to saved company information, and nothing is sent or published without a human approving the exact payload. All external actions are mocked.

## Quick start

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt -e .
.\.venv\Scripts\python.exe -m marketmind
```

The browser opens at <http://127.0.0.1:8000>. Create an account or sign in, then click **Load sample company** and **Save knowledge**. Each account has a separate workspace. Full instructions, including the local model and Docker, are in [docs/SETUP.md](docs/SETUP.md).

For a repeatable Docker demo walkthrough, preflight script, and presentation talking points, see [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md).

## What is included

| Area | Where |
|---|---|
| Web app (FastAPI + browser UI) | `src/marketmind/api`, `src/marketmind/web/static` |
| Desktop apps (Tkinter) | `apps/desktop` |
| Core logic: ingestion, hybrid retrieval, planning, drafts, leads, feedback, evaluation | `src/marketmind` |
| LangGraph workflow, SQLite checkpoint and approval interrupt | `src/marketmind/workflow.py` |
| FastMCP knowledge, records, checks and actions servers | `src/marketmind/mcp` |
| Tool allowlists, call budget and scrubbed audit summaries | `src/marketmind/tools/gateway.py` |
| Guardrails and specialist agents | `src/marketmind/guardrails.py`, `agents.py`, `orchestrator.py` |
| Evaluation sets and set generator | `eval` |
| Tests and CI gate | `tests`, `scripts/eval_gate.py`, `.github/workflows/ci.yml` |
| Docker, Prometheus, Grafana | `Dockerfile`, `docker-compose.yml`, `config` |
| Submission documents | `docs` |

## Layout

```
MarketMind_AI/
├── src/marketmind/        application package
│   ├── api/               FastAPI app
│   ├── mcp/               four FastMCP server entry points
│   ├── tools/             logic, gateway and approval records
│   ├── workflow.py        LangGraph graph and SQLite checkpoint
│   └── web/static/        browser UI
├── apps/desktop/          Tkinter apps (same logic as the web app)
├── config/                config.json, Prometheus, alerts, Grafana
├── data/
│   ├── input/             source documents
│   ├── sample/            synthetic sample company
│   └── output/            generated files (git-ignored)
├── eval/                  golden set, red-team set, retrieval labels/report
├── docs/                  setup, architecture, policies, reports
├── scripts/               Ollama check, CI evaluation gate
└── tests/
```

## Status

This is a working prototype, not a finished capstone. Local workflow, FastMCP tools and retrieval benchmarks are now implemented and tested. The campaign evaluation gate still fails; held-out experiments, judge calibration, real model use, authentication and Docker verification remain pending. See [docs/GUIDELINE_STATUS.md](docs/GUIDELINE_STATUS.md).

## Safety boundary

No social post, message, email or CRM write reaches an external system. Approved "publish" and "send" actions are recorded as mock executions; approved leads are written only to a local file.
