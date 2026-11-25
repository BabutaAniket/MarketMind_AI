# Setup guide

## Requirements

- Python 3.11 or newer (3.12 tested)
- Windows, macOS or Linux
- Optional: [Ollama](https://ollama.com/download) for local model generation
- Optional: Docker Desktop for the container stack (not verified on the build machine)

## 1. Install

Windows PowerShell, from the project folder:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt -e .
```

macOS or Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt -e .
```

## 2. Run the web app

```powershell
.\.venv\Scripts\python.exe -m marketmind
```

Options: `--port 8080`, `--host 0.0.0.0`, `--no-browser`. API documentation is at `/docs`, metrics at `/metrics`.

The app has no login. Run it only on your own machine or a trusted network.

## 3. First use

1. **Company**: click *Load sample company*, then *Save knowledge*. Or paste your own approved company information.
2. **Search**: ask a question; each result shows its passage ID, source and date. The first search downloads the FastEmbed model (internet required once).
3. **Campaign**: use **Run approval workflow** for the LangGraph/SQLite/approval demo. **Create plan** is the simpler baseline route.
4. **Drafts**: generate channel drafts; each is checked for forbidden phrases.
5. **Approvals**: edit and approve the exact payload. The workflow resumes from its checkpoint.
6. **Feedback**: approve a lesson to guide later model prompts.
7. **Evaluation**: run the guardrail evaluation.

## 4. Local model (optional)

```powershell
ollama pull qwen3:4b
.\.venv\Scripts\python.exe scripts\check_ollama.py
```

The status bar in the web app shows whether Ollama is reachable and the model is installed. Change the model or URL with `config/config.json` or the environment variables in `.env.example`. Without Ollama the web app, Qdrant/BM25 retrieval, LangGraph approval workflow, template drafts, lead scoring and guardrail evaluation still work. Model-generated drafts remain unavailable.

OpenRouter is supported through `LLM_PROVIDER=openrouter`, `OPENROUTER_API_KEY` and `OPENROUTER_MODEL`. Never commit a key.

## 5. Desktop apps (optional)

Install the project first using section 1, then run a desktop app from the project folder in PowerShell:

```powershell
.\.venv\Scripts\python.exe apps\desktop\knowledge_app.py
```

This opens the Company Knowledge window. The desktop tools are separate windows rather than one combined launcher. To open another tool, close the current window and run its script instead:

```powershell
.\.venv\Scripts\python.exe apps\desktop\retrieval_app.py
.\.venv\Scripts\python.exe apps\desktop\content_app.py
.\.venv\Scripts\python.exe apps\desktop\planner_app.py
.\.venv\Scripts\python.exe apps\desktop\feedback_app.py
.\.venv\Scripts\python.exe apps\desktop\leads_app.py
.\.venv\Scripts\python.exe apps\desktop\evaluation_app.py
```

Each app reads and writes the same files in `data/output` as the web app. No web server is needed for the desktop tools.

## 6. Test

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check src apps tests scripts eval
$env:PYTHONPATH = "src"; .\.venv\Scripts\python.exe scripts\eval_gate.py
.\.venv\Scripts\python.exe scripts\retrieval_eval.py
.\.venv\Scripts\python.exe scripts\report_guardrails.py
```

The evaluation gate exits non-zero when the guardrail evaluation is below `evaluation.minimum_pass_rate` in `config/config.json`. It currently **fails**, because the keyword guardrail catches only 13 of 30 attacks. See [EVALUATION_REPORT.md](EVALUATION_REPORT.md).

## 7. Docker (unverified)

```powershell
docker compose up --build
```

Defines the app on :8000, four FastMCP services, Prometheus on :9090 and Grafana on :3000. Docker Compose has not been verified on this machine. Ollama runs on the host and is reached through `host.docker.internal`.

## Generated files

Everything the apps write goes to `data/output` (git-ignored): knowledge, retrieval results, FastEmbed cache, plans, drafts, leads, feedback, lessons, approval records and SQLite workflow checkpoints. Delete the folder contents to reset.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: marketmind` | Install with `-e .` or set `PYTHONPATH=src` |
| Status shows *Local model offline* | Start Ollama |
| Status shows *Model not installed* | `ollama pull qwen3:4b` |
| Plan or drafts return 409 | Save company knowledge first |
| Plan returns 400 | The input guardrail blocked the request text |
| Port already in use | `python -m marketmind --port 8080` |
