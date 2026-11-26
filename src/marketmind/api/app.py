"""FastAPI service: JSON API plus the browser UI served from /."""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel, Field

from marketmind import __version__
from marketmind.auth import (
    SESSION_COOKIE,
    AccountAlreadyExists,
    authenticate,
    cookie_secure,
    create_account,
    create_session,
    delete_session,
    user_for_session,
)
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
    SAMPLE_FILE,
    STATIC_DIR,
    load_config,
    workspace_file,
    workspace_scope,
)
from marketmind.tools.actions import decide_action, list_actions, prepare_action
from marketmind.workflow import invoke_workflow, workflow_status

app = FastAPI(title="MarketMind AI", version=__version__)

SOURCE_RISKS = {"prompt_injection", "secret_disclosure", "source_tampering", "auto_publish"}
REQUESTS = Counter("marketmind_requests_total", "HTTP requests", ["method", "path", "status"])
LATENCY = Histogram("marketmind_request_seconds", "HTTP request latency", ["path"])
PUBLIC_PATHS = {"/login", "/api/auth/register", "/api/auth/login", "/health", "/metrics"}


class Credentials(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=1, max_length=1024)


@app.middleware("http")
async def record_metrics(request: Request, call_next):
    start = time.perf_counter()
    path = request.url.path
    origin = request.headers.get("origin")
    if request.method not in {"GET", "HEAD", "OPTIONS"} and origin:
        expected = f"{request.url.scheme}://{request.url.netloc}"
        parsed_origin = urlsplit(origin)
        if f"{parsed_origin.scheme}://{parsed_origin.netloc}" != expected:
            return Response(
                content=json.dumps({"detail": "Cross-site request blocked."}),
                status_code=403,
                media_type="application/json",
            )
    if path not in PUBLIC_PATHS and not path.startswith("/static/"):
        user = user_for_session(request.cookies.get(SESSION_COOKIE))
        if user is None:
            response = (
                RedirectResponse("/login", status_code=303)
                if path == "/" or path.startswith("/docs") or path.startswith("/redoc")
                else Response(
                    content=json.dumps({"detail": "Sign in to continue."}),
                    status_code=401,
                    media_type="application/json",
                )
            )
            return response
        request.state.user = user
        with workspace_scope(user["id"]):
            response = await call_next(request)
    else:
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


@app.get("/login")
def login_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "login.html")


@app.post("/api/auth/register")
def register(body: Credentials, response: Response) -> dict:
    try:
        user = create_account(body.email, body.password)
    except AccountAlreadyExists as exc:
        raise HTTPException(status_code=409, detail="An account with this email already exists.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    token = create_session(user["id"])
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        secure=cookie_secure(),
        samesite="strict",
        path="/",
    )
    return {"email": user["email"]}


@app.post("/api/auth/login")
def login(body: Credentials, response: Response) -> dict:
    user = authenticate(body.email, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    token = create_session(user["id"])
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        secure=cookie_secure(),
        samesite="strict",
        path="/",
    )
    return {"email": user["email"]}


@app.post("/api/auth/logout")
def logout(request: Request, response: Response) -> dict:
    delete_session(request.cookies.get(SESSION_COOKIE))
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, secure=cookie_secure(), samesite="strict")
    return {"logged_out": True}


@app.get("/api/auth/me")
def current_user(request: Request) -> dict:
    return {"email": request.state.user["email"]}


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/status")
def status() -> dict:
    knowledge_file = workspace_file("knowledge_base.json")
    plan_file = workspace_file("campaign_plan.json")
    return {
        "llm": ollama_status(),
        "knowledge_saved": knowledge_file.exists(),
        "company": (read_json(knowledge_file) if knowledge_file.exists() else {}).get("company_profile", {}).get("company_name", ""),
        "plan_saved": plan_file.exists(),
        "leads": len(read_jsonl(workspace_file("leads.jsonl"))),
        "approved_lessons": len(load_approved_lessons(limit=1000)),
        "pending_actions": sum(a["status"] == "waiting_for_human_approval" for a in list_actions()),
    }


@app.get("/api/knowledge")
def get_knowledge() -> dict:
    knowledge_file = workspace_file("knowledge_base.json")
    saved = read_json(knowledge_file) if knowledge_file.exists() else {}
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
    write_json(workspace_file("knowledge_base.json"), record)
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
        write_json(workspace_file("retrieval_test_results.json"), {"query": body.query, "results": results, "human_review_required": True})
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
    plan["generation"] = {
        "status": "template_generated",
        "model": None,
        "message": "Prepared from the saved company profile; no language model was used.",
    }
    yield {"step": "plan", "created": True}
    if body.use_llm:
        yield {"step": "llm", "status": "generating"}
        try:
            plan["qwen3_output"] = ask_local_qwen(plan)
        except RuntimeError as exc:
            plan["generation"] = {
                "status": "template_fallback",
                "model": None,
                "message": "Model generation failed; this result is a template-based fallback.",
                "error": str(exc),
            }
            yield {"step": "llm", "status": "failed", "error": str(exc)}
        else:
            llm_config = load_config()["llm"]
            provider = llm_config["provider"]
            model = llm_config["ollama_model"] if provider == "ollama" else llm_config["openrouter_model"]
            plan["generation"] = {
                "status": "ai_generated",
                "model": f"{provider}/{model}",
                "message": "The configured model generated campaign suggestions.",
            }
            yield {"step": "llm", "status": "done"}
    write_json(workspace_file("campaign_plan.json"), plan)
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
def resume_workflow(thread_id: str, body: WorkflowResume, request: Request) -> dict:
    state = workflow_status(thread_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Workflow not found.")
    if state.get("status") != "awaiting_approval":
        raise HTTPException(status_code=409, detail="Workflow is not waiting for approval.")
    decision = body.model_dump()
    decision["reviewer"] = request.state.user["email"]
    result = invoke_workflow(thread_id=thread_id, resume=decision)
    return _workflow_view(result)


@app.post("/api/plan")
def create_plan(body: CampaignRequest) -> dict:
    events = list(plan_events(body))
    last = events[-1]
    if last["step"] == "blocked":
        raise HTTPException(status_code=400, detail=last["error"])
    return {"events": events[:-1], "plan": last["plan"]}


@app.post("/api/plan/stream")
def stream_plan(body: CampaignRequest, request: Request) -> StreamingResponse:
    workspace_id = request.state.user["id"]
    events = plan_events(body)

    def lines() -> Iterator[str]:
        while True:
            try:
                with workspace_scope(workspace_id):
                    event = next(events)
            except StopIteration:
                break
            except HTTPException as exc:
                yield json.dumps({"step": "blocked", "error": exc.detail}) + "\n"
                break
            yield json.dumps(event, ensure_ascii=False) + "\n"

    return StreamingResponse(lines(), media_type="application/x-ndjson")


@app.post("/api/drafts")
def create_drafts(body: DraftRequest) -> dict:
    record = build_drafts(require_knowledge(), body.campaign_goal, body.call_to_action)
    for draft in record["drafts"].values():
        draft["compliance"] = check_output(draft["text"])
    write_json(workspace_file("content_drafts.json"), record)
    return record


@app.post("/api/leads/score")
def lead_score(body: LeadInput) -> dict:
    return score_lead(body.model_dump())


@app.get("/api/leads")
def leads() -> dict:
    return {"leads": read_jsonl(workspace_file("leads.jsonl"))}


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
def action_decide(body: ActionDecision, request: Request) -> dict:
    result = decide_action(
        body.action_id,
        body.decision,
        body.payload_hash,
        body.edited_payload,
        request.state.user["email"],
    )
    if not result["ok"]:
        raise HTTPException(status_code=409, detail=result["error"])
    return result


@app.get("/api/lessons")
def lessons() -> dict:
    return {"lessons": load_approved_lessons(limit=50)}


@app.post("/api/feedback")
def feedback(body: FeedbackInput) -> dict:
    plan_file = workspace_file("campaign_plan.json")
    if not plan_file.exists():
        raise HTTPException(status_code=409, detail="Create a campaign plan first.")
    record = build_feedback_record(
        read_json(plan_file), body.decision, body.raw_input, body.corrected_meaning, body.lesson
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
    write_json(workspace_file("retrieval_report.json"), report)
    return report


@app.get("/api/evaluation/report")
def evaluation_report() -> dict:
    report_file = workspace_file("evaluation_report.json")
    if not report_file.exists():
        raise HTTPException(status_code=404, detail="No report yet.")
    return read_json(report_file)


@app.get("/")
def index_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
