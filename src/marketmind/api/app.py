"""FastAPI service: JSON API plus the browser UI served from /."""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from marketmind import __version__
from marketmind.content import build_drafts
from marketmind.evaluation import run_evaluation, save_report
from marketmind.feedback import build_feedback_record, save_feedback
from marketmind.guardrails import check_input, check_output, sanitize_data
from marketmind.ingestion import PROFILE_FIELDS, build_record, load_knowledge
from marketmind.leads import score_lead
from marketmind.llm_client import ollama_status
from marketmind.memory_store import load_approved_lessons, read_json, read_jsonl, write_json
from marketmind.planner import ask_local_qwen, build_campaign_plan
from marketmind.retrieval import build_index, search_index
from marketmind.retrieval_evaluation import run_retrieval_evaluation
from marketmind.schemas import (
    ActionDecision,
    ActionPrepare,
    CampaignRequest,
    DraftRequest,
    FeedbackInput,
    KnowledgeInput,
    LeadInput,
    SearchRequest,
    WorkflowResume,
    WorkflowStart,
)
from marketmind.settings import (
    DRAFTS_FILE,
    EVAL_DIR,
    KNOWLEDGE_FILE,
    LEADS_FILE,
    PLAN_FILE,
    REPORT_FILE,
    RETRIEVAL_FILE,
    SAMPLE_FILE,
    STATIC_DIR,
)
from marketmind.tools.actions import decide_action, list_actions, prepare_action
from marketmind.workflow import invoke_workflow, workflow_status

app = FastAPI(title="MarketMind AI", version=__version__)

SOURCE_RISKS = {"prompt_injection", "secret_disclosure", "source_tampering", "auto_publish"}
REQUESTS = Counter("marketmind_requests_total", "HTTP requests", ["method", "path", "status"])
LATENCY = Histogram("marketmind_request_seconds", "HTTP request latency", ["path"])


@app.middleware("http")
async def record_metrics(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    path = request.url.path if request.url.path.startswith("/api") or request.url.path == "/health" else "other"
    REQUESTS.labels(request.method, path, response.status_code).inc()
    LATENCY.labels(path).observe(time.perf_counter() - start)
    return response


def require_knowledge() -> dict:
    try:
        return load_knowledge()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": "marketmind-ai", "version": __version__, "publish_allowed": False}


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/status")
def status() -> dict:
    knowledge = read_json(KNOWLEDGE_FILE) if KNOWLEDGE_FILE.exists() else None
    return {
        "llm": ollama_status(),
        "knowledge_saved": knowledge is not None,
        "company": (knowledge or {}).get("company_profile", {}).get("company_name", ""),
        "plan_saved": PLAN_FILE.exists(),
        "leads": len(read_jsonl(LEADS_FILE)),
        "approved_lessons": len(load_approved_lessons(limit=1000)),
        "pending_actions": sum(a["status"] == "waiting_for_human_approval" for a in list_actions()),
    }


@app.get("/api/knowledge")
def get_knowledge() -> dict:
    saved = read_json(KNOWLEDGE_FILE) if KNOWLEDGE_FILE.exists() else {}
    return {"profile_fields": PROFILE_FIELDS, "saved": bool(saved), **saved}


@app.get("/api/sample")
def sample() -> dict:
    return read_json(SAMPLE_FILE)


@app.post("/api/knowledge")
def save_knowledge(body: KnowledgeInput) -> dict:
    if not body.source_text.strip() and not any(body.company_profile.values()):
        raise HTTPException(status_code=422, detail="Provide company details or source text.")
    safe_profile = sanitize_data(body.company_profile)
    safe_source = sanitize_data(body.source_text)
    record = build_record(safe_profile, safe_source)
    write_json(KNOWLEDGE_FILE, record)
    screen = check_input(safe_source)
    flagged = sorted(
        set(screen["risk_categories"]) & SOURCE_RISKS
        | ({"prompt_injection"} if screen["injection_patterns"] else set())
    )
    return {
        "saved": True,
        "word_count": record["extraction"]["word_count"],
        "warnings": sorted(
            set(flagged)
            | ({"pii_redacted"} if safe_source != body.source_text or safe_profile != body.company_profile else set())
        ),
    }


@app.post("/api/search")
def search(body: SearchRequest) -> dict:
    index = build_index(require_knowledge())
    results = search_index(index, body.query, top_k=body.top_k)
    if body.save:
        write_json(RETRIEVAL_FILE, {"query": body.query, "results": results, "human_review_required": True})
    return {"query": body.query, "chunks_indexed": len(index["chunks"]), "results": results}


def plan_events(body: CampaignRequest) -> Iterator[dict]:
    safe_request = sanitize_data(body.model_dump(exclude={"use_llm"}))
    guard = check_input(json.dumps(safe_request, ensure_ascii=False))
    yield {"step": "input_guardrail", "allowed": guard["allowed"], "risk_categories": guard["risk_categories"]}
    if not guard["allowed"]:
        yield {"step": "blocked", "error": "The request was blocked by the input guardrail."}
        return
    knowledge = require_knowledge()
    results = search_index(
        build_index(knowledge),
        f"{safe_request['objective']} {safe_request['offer']} benefits",
        top_k=5,
    )
    yield {"step": "retrieval", "passages": len(results)}
    plan = build_campaign_plan(
        knowledge,
        {"results": results},
        safe_request["objective"],
        safe_request["audience"],
        safe_request["offer"],
        ", ".join(safe_request["channels"]),
        safe_request["tone"],
        safe_request["budget"],
    )
    yield {"step": "plan", "created": True}
    if body.use_llm:
        yield {"step": "llm", "status": "generating"}
        try:
            plan["qwen3_output"] = ask_local_qwen(plan)
        except RuntimeError as exc:
            yield {"step": "llm", "status": "failed", "error": str(exc)}
        else:
            yield {"step": "llm", "status": "done"}
    write_json(PLAN_FILE, plan)
    yield {"step": "done", "plan": plan}


def _workflow_view(result: dict) -> dict:
    interruptions = result.get("__interrupt__", ())
    pending = []
    for item in interruptions:
        value = getattr(item, "value", None)
        if value is not None:
            pending.append(value)
    return {
        "thread_id": result["thread_id"],
        "status": result.get("status", "running"),
        "events": result.get("events", []),
        "plan": result.get("plan"),
        "strategy": result.get("strategy"),
        "content_brief": result.get("content_brief"),
        "lead_brief": result.get("lead_brief"),
        "specialists": result.get("specialists", {}),
        "drafts": result.get("drafts"),
        "review": result.get("review"),
        "action": result.get("action"),
        "tool_calls": result.get("tool_calls", []),
        "retries": result.get("retries", 0),
        "interrupts": pending,
        "errors": result.get("errors", []),
    }


@app.post("/api/workflow/start")
def start_workflow(body: WorkflowStart) -> dict:
    thread_id = body.thread_id or str(uuid4())
    result = invoke_workflow(
        body.campaign.model_dump(exclude={"use_llm"}),
        thread_id=thread_id,
    )
    return _workflow_view(result)


@app.get("/api/workflow/{thread_id}")
def get_workflow(thread_id: str) -> dict:
    state = workflow_status(thread_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    return state


@app.post("/api/workflow/{thread_id}/resume")
def resume_workflow(thread_id: str, body: WorkflowResume) -> dict:
    state = workflow_status(thread_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    if state.get("status") != "awaiting_approval":
        raise HTTPException(status_code=409, detail="Workflow is not waiting for approval.")
    result = invoke_workflow(thread_id=thread_id, resume=body.model_dump())
    return _workflow_view(result)


@app.post("/api/plan")
def create_plan(body: CampaignRequest) -> dict:
    events = list(plan_events(body))
    last = events[-1]
    if last["step"] == "blocked":
        raise HTTPException(status_code=400, detail=last["error"])
    return {"events": events[:-1], "plan": last["plan"]}


@app.post("/api/plan/stream")
def stream_plan(body: CampaignRequest) -> StreamingResponse:
    def lines() -> Iterator[str]:
        try:
            for event in plan_events(body):
                yield json.dumps(event, ensure_ascii=False) + "\n"
        except HTTPException as exc:
            yield json.dumps({"step": "blocked", "error": exc.detail}) + "\n"

    return StreamingResponse(lines(), media_type="application/x-ndjson")


@app.post("/api/drafts")
def create_drafts(body: DraftRequest) -> dict:
    record = build_drafts(require_knowledge(), body.campaign_goal, body.call_to_action)
    for draft in record["drafts"].values():
        draft["compliance"] = check_output(draft["text"])
    write_json(DRAFTS_FILE, record)
    return record


@app.post("/api/leads/score")
def lead_score(body: LeadInput) -> dict:
    return score_lead(body.model_dump())


@app.get("/api/leads")
def leads() -> dict:
    return {"leads": read_jsonl(LEADS_FILE)}


@app.post("/api/actions/prepare")
def action_prepare(body: ActionPrepare) -> dict:
    result = prepare_action(body.action_type, body.payload)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get("/api/actions")
def actions() -> dict:
    return {"actions": list_actions()}


@app.post("/api/actions/decide")
def action_decide(body: ActionDecision) -> dict:
    result = decide_action(body.action_id, body.decision, body.payload_hash, body.edited_payload, body.reviewer)
    if not result["ok"]:
        raise HTTPException(status_code=409, detail=result["error"])
    return result


@app.get("/api/lessons")
def lessons() -> dict:
    return {"lessons": load_approved_lessons(limit=50)}


@app.post("/api/feedback")
def feedback(body: FeedbackInput) -> dict:
    if not PLAN_FILE.exists():
        raise HTTPException(status_code=409, detail="Create a campaign plan first.")
    record = build_feedback_record(
        read_json(PLAN_FILE), body.decision, body.raw_input, body.corrected_meaning, body.lesson
    )
    save_feedback(record)
    return {"saved": True, "used_for_future_prompts": record["human_approved"]}


@app.post("/api/evaluation/run")
def evaluation_run() -> dict:
    try:
        report = run_evaluation()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    save_report(report)
    return report


@app.post("/api/evaluation/retrieval")
def retrieval_evaluation() -> dict:
    report = run_retrieval_evaluation()
    write_json(EVAL_DIR / "retrieval_report.json", report)
    return report


@app.get("/api/evaluation/report")
def evaluation_report() -> dict:
    if not REPORT_FILE.exists():
        raise HTTPException(status_code=404, detail="No report yet.")
    return read_json(REPORT_FILE)


@app.get("/")
def index_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
