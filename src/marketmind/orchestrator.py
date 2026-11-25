"""MarketMind AI - orchestrator.

Plan -> execute -> review loop. The request first passes the input guardrail;
the run always stops at the human approval gate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from marketmind.agents import run_specialists
from marketmind.guardrails import check_input


@dataclass
class CampaignState:
    request: dict[str, Any]
    evidence: list[dict[str, Any]] = field(default_factory=list)
    plan: dict[str, Any] = field(default_factory=dict)
    specialist_results: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    retries: int = 0
    approval_required: bool = True


def run_campaign(state: CampaignState, llm_step: Callable[[CampaignState], dict] | None = None) -> CampaignState:
    text = str(state.request)
    guard = check_input(text)
    state.events.append({"node": "input_guardrail", "result": guard})
    if not guard["allowed"]:
        state.events.append({"node": "stopped", "reason": "prompt injection detected"})
        return state

    state.plan = {
        "objective": state.request.get("objective", ""),
        "audience": state.request.get("audience", ""),
        "channels": state.request.get("channels", []),
        "status": "planned",
    }
    state.events.append({"node": "supervisor", "action": "plan created"})
    context = {"inputs": state.request, "source_references": state.evidence}
    state.specialist_results = run_specialists(context)
    state.events.append({"node": "specialists", "agents": list(state.specialist_results)})

    if llm_step is not None:
        state.plan["draft"] = llm_step(state)
        state.events.append({"node": "llm_generation", "status": "completed"})
    state.events.append({"node": "approval_gate", "status": "waiting_for_human"})
    return state
