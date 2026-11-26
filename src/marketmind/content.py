"""Template-based channel drafts grounded in the saved company profile."""

from __future__ import annotations

from datetime import datetime

from marketmind.settings import workspace_file


def value(profile: dict, key: str, fallback: str) -> str:
    text = str(profile.get(key, "")).strip()
    return text or fallback


def build_drafts(knowledge: dict, campaign_goal: str, call_to_action: str) -> dict:
    profile = knowledge.get("company_profile", {})
    company = value(profile, "company_name", "Our company")
    brand = value(profile, "brand_name", value(profile, "products", "Our product"))
    products = value(profile, "products", brand)
    audience = value(profile, "target_customer", "customers looking for a reliable solution")
    problem = value(profile, "customer_problem", "a common customer problem")
    usp = value(profile, "usp", "quality, reliability and professional support")
    tone = value(profile, "tone", "professional and trustworthy")
    location = value(profile, "location", "your area")
    restrictions = value(profile, "restrictions", "Verify all claims before publishing.")
    goal = campaign_goal.strip() or "Create awareness and invite a product consultation."
    cta = call_to_action.strip() or value(
        profile,
        "offer_price",
        "Contact us for a suitable recommendation.",
    )

    common = {
        "company": company,
        "brand": brand,
        "product": products,
        "audience": audience,
        "problem": problem,
        "usp": usp,
        "tone": tone,
        "location": location,
        "campaign_goal": goal,
        "call_to_action": cta,
        "safety_note": restrictions,
    }

    drafts = {
        "instagram": {
            "format": "caption",
            "text": (
                f"Looking for a dependable solution for {problem.lower()}?\n\n"
                f"Meet {brand} by {company}. {products}.\n"
                f"Why consider it: {usp}.\n\n"
                f"Designed for {audience.lower()} in {location}.\n"
                f"{cta}\n\n"
                f"# {brand.replace(' ', '')} #Innovation #ReliableSolutions"
            ).replace("# ", "#"),
            "visual_brief": (
                f"Create a clean product-focused advertising image for {brand}; "
                f"show the product in a realistic {location} setting, with no unsupported claims."
            ),
        },
        "facebook": {
            "format": "post",
            "text": (
                f"{brand} — a practical choice for {audience}.\n\n"
                f"Customer need: {problem}.\n"
                f"Our approach: {usp}.\n\n"
                f"Campaign objective: {goal}\n"
                f"{cta}\n\n"
                f"Please contact {company} for verified product details and suitability."
            ),
            "visual_brief": (
                f"Create a professional Facebook product graphic for {brand}, using brand-safe "
                f"colours and a clear consultation call-to-action."
            ),
        },
        "whatsapp": {
            "format": "short_message",
            "text": (
                f"Hello, this is {company}.\n\n"
                f"Product: {brand}\n"
                f"Suitable for: {audience}\n"
                f"Main benefit: {usp}\n\n"
                f"{cta}\n"
                f"Reply CONSULTATION to know more."
            ),
            "visual_brief": "Use a simple product image with one verified benefit and one CTA.",
        },
        "email": {
            "format": "subject_and_body",
            "subject": f"A practical solution from {company}: {brand}",
            "text": (
                f"Dear Customer,\n\n"
                f"If you are evaluating options for {problem.lower()}, {brand} may be worth reviewing.\n\n"
                f"Product information: {products}\n"
                f"Key differentiator: {usp}\n"
                f"Intended audience: {audience}\n\n"
                f"{cta}\n\n"
                f"Regards,\n{company}"
            ),
            "visual_brief": "Optional email banner using only approved product information.",
        },
    }

    source_refs = [
        "company_profile.company_name",
        "company_profile.brand_name",
        "company_profile.products",
        "company_profile.target_customer",
        "company_profile.customer_problem",
        "company_profile.usp",
        "company_profile.restrictions",
    ]

    return {
        "schema_version": "drafts-1.0",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "mode": "dry_run",
        "published": False,
        "source_knowledge_file": str(workspace_file("knowledge_base.json")),
        "campaign": common,
        "grounding": {
            "source_references": source_refs,
            "retrieval_method": "direct structured profile lookup",
            "human_review_required": True,
        },
        "drafts": drafts,
    }
