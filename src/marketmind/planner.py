"""Campaign planner: baseline plan and optional local Qwen3 drafts."""

from __future__ import annotations

import json
from datetime import datetime

from marketmind.llm_client import chat
from marketmind.memory_store import relevant_approved_lessons
from marketmind.settings import PROMPTS_FILE, load_config

_LLM_CONFIG = load_config()["llm"]
OLLAMA_URL = _LLM_CONFIG.get("ollama_url", "http://localhost:11434/api/chat")
OLLAMA_MODEL = _LLM_CONFIG.get("ollama_model", "qwen3:4b")
OLLAMA_TIMEOUT = int(_LLM_CONFIG.get("timeout_seconds", 300))


def profile_value(profile: dict, key: str, fallback: str = "Not provided") -> str:
    value = profile.get(key, fallback)
    if value is None:
        return fallback
    return str(value).strip() or fallback


def build_campaign_plan(
    knowledge: dict,
    retrieval: dict | None,
    objective: str,
    audience: str,
    offer: str,
    channels: str,
    tone: str,
    budget: str,
) -> dict:
    profile = knowledge.get("company_profile", knowledge.get("profile", {}))
    if not isinstance(profile, dict):
        profile = {}
    company = profile_value(profile, "company_name", "Company")
    brand = profile_value(profile, "brand_name", company)
    products = profile_value(profile, "products")
    usp = profile_value(profile, "usp")
    location = profile_value(profile, "location")
    restrictions = profile_value(profile, "restrictions")

    channel_list = [item.strip() for item in channels.split(",") if item.strip()]
    if not channel_list:
        channel_list = ["Instagram", "Facebook", "WhatsApp", "Email"]

    evidence = []
    if retrieval and isinstance(retrieval.get("results"), list):
        for item in retrieval["results"][:5]:
            if isinstance(item, dict):
                evidence.append(
                    {
                        "chunk_id": item.get("chunk_id", "unknown"),
                        "source_ref": item.get("source_ref", "knowledge_base.json"),
                        "source_date": item.get("source_date", "not provided"),
                        "score": item.get("score", 0),
                        "evidence_text": item.get("text", ""),
                    }
                )
    if not evidence:
        evidence.append(
            {
                "chunk_id": "profile",
                "source_ref": "knowledge_base.json",
                "source_date": "not provided",
                "score": None,
                "evidence_text": f"Products: {products}; USP: {usp}; location: {location}",
            }
        )

    channel_plan = []
    for channel in channel_list:
        lower = channel.lower()
        if "whatsapp" in lower:
            role = "High-intent conversation and lead qualification"
            format_name = "Short offer message with one reply CTA"
            cta = "Reply CONSULTATION"
        elif "email" in lower:
            role = "Trust-building and follow-up"
            format_name = "Problem, evidence, offer, and reply CTA"
            cta = "Book a consultation"
        elif "facebook" in lower:
            role = "Reach and social proof"
            format_name = "Educational post or customer problem carousel"
            cta = "Send a message"
        else:
            role = "Awareness and visual education"
            format_name = "Short reel or carousel with one benefit"
            cta = "Learn more"
        channel_plan.append(
            {
                "channel": channel,
                "role": role,
                "recommended_format": format_name,
                "primary_cta": cta,
            }
        )

    return {
        "schema_version": "campaign-plan-1.0",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "human_approval_required": True,
        "publish_allowed": False,
        "inputs": {
            "objective": objective,
            "audience": audience,
            "offer": offer,
            "channels": channel_list,
            "tone": tone,
            "budget": budget,
        },
        "company_context": {
            "company_name": company,
            "brand_name": brand,
            "products": products,
            "target_customer": profile_value(profile, "target_customer"),
            "customer_problem": profile_value(profile, "customer_problem"),
            "unique_selling_point": usp,
            "location": location,
            "restrictions": restrictions,
        },
        "specialist_agents": {
            "strategy_agent": {
                "job": "Choose the campaign angle and audience message",
                "campaign_angle": f"Show how {brand} addresses {profile_value(profile, 'customer_problem', 'the customer problem')} with a clear, evidence-based benefit.",
                "message_promise": f"A practical next step for {audience} interested in {products}.",
            },
            "content_agent": {
                "job": "Convert the strategy into channel-ready content briefs",
                "opening_hook": f"Is {profile_value(profile, 'customer_problem', 'this problem')} increasing your cost or effort?",
                "proof_point": usp,
                "tone": tone,
                "content_rule": "One message, one proof point, one CTA per asset.",
            },
            "lead_agent": {
                "job": "Capture and qualify interested prospects",
                "lead_fields": ["name", "company", "phone_or_email", "location", "requirement", "timeline"],
                "qualification_questions": [
                    "What problem are you trying to solve?",
                    "What product or capacity do you need?",
                    "When do you want a discussion or quotation?",
                ],
                "handoff": "Human sales review before any quotation or commitment.",
            },
            "measurement_agent": {
                "job": "Measure campaign quality before scaling",
                "metrics": [
                    "reach",
                    "engagement rate",
                    "qualified leads",
                    "cost per qualified lead",
                    "response time",
                    "conversion rate",
                ],
                "review_rule": "Review results after a small test; do not scale automatically.",
            },
        },
        "channel_plan": channel_plan,
        "source_references": evidence,
        "safety_and_approval": {
            "no_auto_publish": True,
            "no_auto_messaging": True,
            "claims_must_be_verified": True,
            "human_review_before_release": True,
        },
    }


def ask_local_qwen(plan: dict) -> dict | str:
    evidence = plan.get("source_references", [])[:5]
    lesson_query = " ".join(
        [
            str(plan.get("inputs", {}).get("objective", "")),
            str(plan.get("inputs", {}).get("audience", "")),
            str(plan.get("inputs", {}).get("channels", "")),
            str(plan.get("company_context", {}).get("tone", "")),
        ]
    )
    approved_lessons = relevant_approved_lessons(lesson_query, limit=5)
    prompt_config = json.loads(PROMPTS_FILE.read_text(encoding="utf-8"))["campaign_drafter"]
    system = "\n".join(
        [
            f"Role: {prompt_config['role']}",
            f"Context: {prompt_config['context']}",
            f"Task: {prompt_config['task']}",
            "Constraints:",
            *[f"- {item}" for item in prompt_config["constraints"]],
            f"Format: {prompt_config['format']}",
            f"Examples: {json.dumps(prompt_config['examples'], ensure_ascii=False)}",
        ]
    )
    context = {
        "inputs": plan.get("inputs", {}),
        "company_context": plan.get("company_context", {}),
        "channel_plan": plan.get("channel_plan", []),
        "evidence": evidence,
        "approved_human_lessons": approved_lessons,
    }
    content = chat(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(context, ensure_ascii=False, indent=2)},
        ],
        json_mode=True,
    )
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError("LLM provider returned invalid JSON despite JSON mode.") from exc
