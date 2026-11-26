"""LangGraph campaign workflow with durable checkpoints and exact-payload approval."""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from typing import Any, Literal, TypedDict
from uuid import uuid4

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from marketmind.agents import AgentMessage, compliance_agent, content_agent, lead_agent, strategy_agent
from marketmind.content import build_drafts
from marketmind.guardrails import OUTPUT_FORBIDDEN, check_input, sanitize_data
from marketmind.mcp.actions_server import mcp as actions_server
from marketmind.mcp.checks_server import mcp as checks_server
from marketmind.mcp.knowledge_server import mcp as knowledge_server
from marketmind.mcp.records_server import mcp as records_server
from marketmind.memory_store import read_json
from marketmind.planner import build_campaign_plan
from marketmind.retrieval import build_index
from marketmind.settings import workspace_file
from marketmind.tools.actions import decide_action
from marketmind.tools.gateway import configured_server, invoke_tool


class WorkflowState(TypedDict, total=False):
    request: dict[str, Any]
    guard: dict[str, Any]
    evidence: list[dict[str, Any]]
    plan: dict[str, Any]
    strategy: dict[str, Any]
    content_brief: dict[str, Any]
    lead_brief: dict[str, Any]
    specialists: dict[str, Any]
    drafts: dict[str, Any]
    review: dict[str, Any]
    retries: int
    action: dict[str, Any]
    decision: dict[str, Any]
    status: str
    errors: list[str]
    events: list[dict[str, Any]]
    tool_calls: list[dict[str, Any]]


def _event(state: WorkflowState, node: str, **detail: Any) -> list[dict[str, Any]]:
    return [*state.get("events", []), {"node": node, **detail}]


def _guard(state: WorkflowState) -> dict[str, Any]:
    request = state["request"]
    result = check_input(json.dumps(request, ensure_ascii=False))
    status = "blocked" if not result["allowed"] else "running"
    return {"guard": result, "status": status, "events": _event(state, "input_guardrail", allowed=result["allowed"])}


def _after_guard(state: WorkflowState) -> Literal["research", "finish"]:
    return "finish" if state.get("status") == "blocked" else "research"


def _research(state: WorkflowState) -> dict[str, Any]:
    knowledge_file = workspace_file("knowledge_base.json")
    if not knowledge_file.exists():
        return {
            "status": "failed",
            "errors": ["Save company knowledge before starting a campaign."],
            "events": _event(state, "research", error="company knowledge is missing"),
        }
    knowledge = read_json(knowledge_file)
    request = state["request"]
    query = " ".join(str(request.get(key, "")) for key in ("objective", "audience", "offer"))
    index = build_index(knowledge)
    result, tool_event = invoke_tool(
        "research",
        configured_server("knowledge", knowledge_server),
        "search_company_knowledge",
        {"query": query, "limit": 5},
        prior_calls=len(state.get("tool_calls", [])),
    )
    if not result.get("ok"):
        return {
            "status": "failed",
            "errors": [result.get("error", "Knowledge search failed.")],
            "tool_calls": [*state.get("tool_calls", []), tool_event],
            "events": _event(state, "research", error="knowledge search failed"),
        }
    evidence = result.get("results", [])
    return {
        "evidence": evidence,
        "tool_calls": [*state.get("tool_calls", []), tool_event],
        "events": _event(state, "research", passages=len(evidence), chunks=len(index["chunks"]), tool=tool_event),
    }


def _after_research(state: WorkflowState) -> Literal["plan", "finish"]:
    return "finish" if state.get("status") == "failed" else "plan"


def _after_plan(state: WorkflowState) -> Literal["fixed", "single", "team"]:
    design = state.get("request", {}).get("design", "team")
    return design if design in ("fixed", "single", "team") else "team"


def _plan(state: WorkflowState) -> dict[str, Any]:
    request = state["request"]
    knowledge = read_json(workspace_file("knowledge_base.json"))
    plan = build_campaign_plan(
        knowledge,
        {"results": state.get("evidence", [])},
        request.get("objective", ""),
        request.get("audience", ""),
        request.get("offer", ""),
        ", ".join(request.get("channels", [])),
        request.get("tone", "Professional, clear, trustworthy"),
        request.get("budget", "Small test budget"),
    )
    return {"plan": plan, "events": _event(state, "planner", created=True)}


def _single_agent(state: WorkflowState) -> dict[str, Any]:
    request = state["request"]
    result = AgentMessage(
        sender="single_agent",
        purpose="campaign plan and specialist handoff",
        payload={
            "objective": request.get("objective", ""),
            "audience": request.get("audience", ""),
            "channels": request.get("channels", []),
            "evidence": state.get("evidence", []),
            "constraints": ["Use only cited facts", "Require human approval"],
        },
    )
    return {
        "specialists": {"single_agent": asdict(result)},
        "events": _event(state, "single_agent", handoff=result.sender),
    }


def _content(state: WorkflowState) -> dict[str, Any]:
    request = state["request"]
    knowledge = read_json(workspace_file("knowledge_base.json"))
    drafts = build_drafts(knowledge, request.get("objective", ""), request.get("offer", ""))
    return {"drafts": drafts["drafts"], "events": _event(state, "content", channels=list(drafts["drafts"]))}


def _strategy(state: WorkflowState) -> dict[str, Any]:
    result = strategy_agent(
        {
            "inputs": state["request"],
            "company_context": state.get("plan", {}).get("company_context", {}),
        }
    )
    return {
        "strategy": asdict(result),
        "events": _event(state, "strategy_specialist", handoff=result.sender),
    }


def _content_specialist(state: WorkflowState) -> dict[str, Any]:
    strategy = AgentMessage(**state["strategy"])
    result = content_agent({"inputs": state["request"]}, strategy)
    return {
        "content_brief": asdict(result),
        "events": _event(state, "content_specialist", handoff=result.sender),
    }


def _lead_specialist(state: WorkflowState) -> dict[str, Any]:
    result = lead_agent({"inputs": state["request"]})
    tool_result, tool_event = invoke_tool(
        "lead",
        configured_server("records", records_server),
        "get_leads",
        {"limit": 5},
        prior_calls=len(state.get("tool_calls", [])),
    )
    payload = {**result.payload, "saved_lead_count": len(tool_result.get("leads", []))}
    result = AgentMessage(result.sender, result.purpose, payload, result.warnings)
    return {
        "lead_brief": asdict(result),
        "tool_calls": [*state.get("tool_calls", []), tool_event],
        "events": _event(state, "lead_specialist", handoff=result.sender, tool=tool_event),
    }


def _review(state: WorkflowState) -> dict[str, Any]:
    checks = {}
    tool_calls = list(state.get("tool_calls", []))
    for channel, item in state.get("drafts", {}).items():
        result, event = invoke_tool(
            "review",
            configured_server("checks", checks_server),
            "check_marketing_copy",
            {"text": item.get("text", "")},
            prior_calls=len(tool_calls),
        )
        tool_calls.append(event)
        checks[channel] = result
    issues = [
        {"channel": channel, "hits": result.get("claim_or_safety_hits", [result.get("error", "check failed")])}
        for channel, result in checks.items()
        if not result.get("allowed", False)
    ]
    compliance = compliance_agent(
        {},
        AgentMessage(
            sender="content_specialist",
            purpose="channel drafts",
            payload={channel: item.get("text", "") for channel, item in state.get("drafts", {}).items()},
        ),
    )
    return {
        "review": {"passed": not issues, "issues": issues},
        "tool_calls": tool_calls,
        "specialists": {**state.get("specialists", {}), "compliance": asdict(compliance)},
        "events": _event(state, "review", passed=not issues, issues=len(issues)),
    }


def _after_review(state: WorkflowState) -> Literal["revise", "prepare", "finish"]:
    if state.get("review", {}).get("passed"):
        return "prepare"
    if state.get("retries", 0) < 1:
        return "revise"
    return "finish"


def _revise(state: WorkflowState) -> dict[str, Any]:
    drafts = {channel: dict(item) for channel, item in state.get("drafts", {}).items()}
    for channel, item in drafts.items():
        text = item.get("text", "")
        for phrase in OUTPUT_FORBIDDEN:
            text = re.sub(re.escape(phrase), "[claim removed for human review]", text, flags=re.IGNORECASE)
        item["text"] = text
    retries = state.get("retries", 0) + 1
    return {
        "drafts": drafts,
        "retries": retries,
        "events": _event(state, "self_correction", attempt=retries),
    }


def _prepare(state: WorkflowState) -> dict[str, Any]:
    action, tool_event = invoke_tool(
        "publisher",
        configured_server("actions", actions_server),
        "prepare_workflow_publish",
        {
            "payload": {
                "plan": state["plan"],
                "drafts": state["drafts"],
                "evidence": state.get("evidence", []),
            }
        },
        prior_calls=len(state.get("tool_calls", [])),
    )
    if not action["ok"]:
        return {
            "status": "failed",
            "errors": [action["error"]],
            "tool_calls": [*state.get("tool_calls", []), tool_event],
            "events": _event(state, "prepare_action", error=action["error"]),
        }
    return {
        "action": action,
        "status": "awaiting_approval",
        "tool_calls": [*state.get("tool_calls", []), tool_event],
        "events": _event(
            state,
            "prepare_action",
            action_id=action["action_id"],
            payload_hash=action["payload_hash"],
            tool=tool_event,
        ),
    }


def _approval(state: WorkflowState) -> dict[str, Any]:
    action = state["action"]
    response = interrupt(
        {
            "action_id": action["action_id"],
            "action_type": action["action_type"],
            "payload": action["exact_payload"],
            "payload_hash": action["payload_hash"],
            "options": ["approve", "edit", "reject"],
        }
    )
    decision = response if isinstance(response, dict) else {}
    kind = decision.get("decision")
    if kind == "edit":
        edited_payload = decision.get("edited_payload")
        if not isinstance(edited_payload, dict):
            return {
                "status": "awaiting_approval",
                "errors": ["An edited payload must be an object."],
                "events": _event(state, "approval", result="edit_rejected", reason="invalid edited payload"),
            }
        updated = decide_action(
            action["action_id"],
            "edit",
            edited_payload=edited_payload,
            reviewer=str(decision.get("reviewer", "human")),
        )
        if not updated["ok"]:
            return {"status": "failed", "errors": [updated["error"]]}
        return {
            "action": updated,
            "status": "awaiting_approval",
            "events": _event(state, "approval", result="edited", payload_hash=updated["payload_hash"]),
        }
    if kind == "reject":
        result = decide_action(action["action_id"], "reject", reviewer=str(decision.get("reviewer", "human")))
        if not result["ok"]:
            return {"status": "failed", "errors": [result["error"]]}
        return {"action": result, "status": "rejected", "events": _event(state, "approval", result="rejected")}
    if kind == "approve":
        seen_hash = str(decision.get("payload_hash", ""))
        if seen_hash != action["payload_hash"]:
            return {
                "status": "awaiting_approval",
                "errors": ["The payload changed; review and approve the current version."],
                "events": _event(state, "approval", result="stale_hash_rejected"),
            }
        result = decide_action(
            action["action_id"],
            "approve",
            payload_hash_seen=seen_hash,
            reviewer=str(decision.get("reviewer", "human")),
        )
        if not result["ok"]:
            return {"status": "failed", "errors": [result["error"]]}
        return {"action": result, "status": "approved_mock", "events": _event(state, "approval", result="approved")}
    return {
        "status": "awaiting_approval",
        "errors": ["Choose approve, edit or reject."],
        "events": _event(state, "approval", result="invalid_decision"),
    }


def _after_approval(state: WorkflowState) -> Literal["approval", "finish"]:
    return "approval" if state.get("status") == "awaiting_approval" else "finish"


def _after_prepare(state: WorkflowState) -> Literal["approval", "finish"]:
    return "approval" if state.get("status") == "awaiting_approval" else "finish"


def _finish(state: WorkflowState) -> dict[str, Any]:
    return {"events": _event(state, "finish", status=state.get("status", "complete"))}


def build_workflow(checkpointer: Any) -> Any:
    graph = StateGraph(WorkflowState)
    graph.add_node("guard", _guard)
    graph.add_node("research", _research)
    graph.add_node("plan", _plan)
    graph.add_node("single_agent", _single_agent)
    graph.add_node("strategy", _strategy)
    graph.add_node("content_specialist", _content_specialist)
    graph.add_node("lead_specialist", _lead_specialist)
    graph.add_node("content", _content)
    graph.add_node("review", _review)
    graph.add_node("revise", _revise)
    graph.add_node("prepare", _prepare)
    graph.add_node("approval", _approval)
    graph.add_node("finish", _finish)
    graph.add_edge(START, "guard")
    graph.add_conditional_edges("guard", _after_guard)
    graph.add_conditional_edges("research", _after_research)
    graph.add_conditional_edges(
        "plan",
        _after_plan,
        {"fixed": "content", "single": "single_agent", "team": "strategy"},
    )
    graph.add_edge("single_agent", "content")
    graph.add_edge("strategy", "content_specialist")
    graph.add_edge("content_specialist", "lead_specialist")
    graph.add_edge("lead_specialist", "content")
    graph.add_edge("content", "review")
    graph.add_conditional_edges("review", _after_review)
    graph.add_edge("revise", "review")
    graph.add_conditional_edges("prepare", _after_prepare)
    graph.add_conditional_edges("approval", _after_approval)
    graph.add_edge("finish", END)
    return graph.compile(checkpointer=checkpointer)


def invoke_workflow(
    request: dict[str, Any] | None = None,
    *,
    thread_id: str | None = None,
    resume: dict[str, Any] | None = None,
) -> dict[str, Any]:
    checkpoint_file = workspace_file("workflow-checkpoints.sqlite")
    checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
    config = {"configurable": {"thread_id": thread_id or str(uuid4())}}
    with SqliteSaver.from_conn_string(str(checkpoint_file)) as checkpointer:
        graph = build_workflow(checkpointer)
        if resume is None:
            if request is None:
                raise ValueError("request is required to start a workflow")
            result = graph.invoke(
                {"request": sanitize_data(request), "retries": 0, "events": [], "status": "running"},
                config=config,
            )
        else:
            result = graph.invoke(Command(resume=resume), config=config)
    return {"thread_id": config["configurable"]["thread_id"], **result}


def workflow_status(thread_id: str) -> dict[str, Any] | None:
    checkpoint_file = workspace_file("workflow-checkpoints.sqlite")
    if not checkpoint_file.exists():
        return None
    config = {"configurable": {"thread_id": thread_id}}
    with SqliteSaver.from_conn_string(str(checkpoint_file)) as checkpointer:
        state = build_workflow(checkpointer).get_state(config)
    if not state.values:
        return None
    interrupts = [item.value for task in state.tasks for item in task.interrupts]
    return {"thread_id": thread_id, **state.values, "next": list(state.next), "interrupts": interrupts}
