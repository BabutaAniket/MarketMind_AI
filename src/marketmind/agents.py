"""MarketMind AI - specialist agents.

Strategy, content, lead and compliance agents. The compliance agent runs the
output guardrail and always requires human review.

Used by: orchestrator.py through run_specialists().
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from marketmind.guardrails import check_output


@dataclass
class AgentMessage:
    sender: str
    purpose: str
    payload: dict[str, Any]
    warnings: list[str] = field(default_factory=list)


def strategy_agent(context: dict) -> AgentMessage:
    profile = context.get("company_context", {})
    return AgentMessage(
        "strategy_agent",
        "campaign angle",
        {
            "angle": f"Connect {profile.get('products', 'the product')} to the verified customer problem.",
            "audience": context.get("inputs", {}).get("audience", "not provided"),
            "must_verify": ["price", "performance claims", "certifications", "customer numbers"],
        },
    )


def content_agent(context: dict, strategy: AgentMessage) -> AgentMessage:
    return AgentMessage(
        "content_agent",
        "channel drafts",
        {
            "channels": context.get("inputs", {}).get("channels", []),
            "rule": "one message, one evidence-backed benefit, one CTA",
            "strategy_used": strategy.payload,
        },
    )


def lead_agent(context: dict) -> AgentMessage:
    return AgentMessage(
        "lead_agent",
        "lead qualification",
        {
            "fields": ["name", "company", "contact", "location", "requirement", "timeline"],
            "human_handoff_required": True,
        },
    )


def compliance_agent(context: dict, draft: AgentMessage) -> AgentMessage:
    text = str(draft.payload)
    result = check_output(text)
    return AgentMessage(
        "compliance_agent",
        "claims and safety review",
        {
            "allowed": result["allowed"],
            "hits": result["claim_or_safety_hits"],
            "human_review_required": True,
        },
    )


def run_specialists(context: dict) -> dict:
    strategy = strategy_agent(context)
    content = content_agent(context, strategy)
    lead = lead_agent(context)
    compliance = compliance_agent(context, content)
    return {
        "strategy": strategy.__dict__,
        "content": content.__dict__,
        "lead": lead.__dict__,
        "compliance": compliance.__dict__,
    }
