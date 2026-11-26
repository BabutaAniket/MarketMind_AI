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
    if products.startswith(("A ", "An ", "The ")):
        products = products[0].lower() + products[1:]
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
        "location": location,
        "campaign_goal": goal,
        "call_to_action": cta,
        "tone": tone,
        "safety_note": restrictions,
    }

    location_line = f" Location: {location}." if location.lower() not in {"online", "not provided"} else ""
    drafts = {
        "instagram": {
            "format": "caption",
            "text": (
                f"Need a shared view of team work?\n\n"
                f"{brand} is {products} for {audience}.\n"
                f"{usp}.{location_line}\n\n"
                f"{cta}\n\n"
                f"#{''.join(brand.split())}"
            ),
            "visual_brief": (
                f"Create a clean product-focused advertising image for {brand}; "
                f"show the product in a realistic {location} setting, with no unsupported claims."
            ),
        },
        "facebook": {
            "format": "post",
            "text": (
                f"{brand} is {products} for {audience}.\n\n"
                f"{usp}.{location_line}\n\n"
                f"{cta}\n\n"
                f"Learn more from {company}."
            ),
            "visual_brief": (
                f"Create a professional Facebook product graphic for {brand}, using brand-safe "
                f"colours and a clear consultation call-to-action."
            ),
        },
        "whatsapp": {
            "format": "short_message",
            "text": (
                f"Hello, we’d like to introduce {brand}.\n"
                f"{products} for {audience}.\n"
                f"{usp}.\n\n"
                f"{cta}\n"
                f"Reply if you’d like to know more."
            ),
            "visual_brief": "Use a simple product image with one verified benefit and one CTA.",
        },
        "email": {
            "format": "subject_and_body",
            "subject": f"A practical solution from {company}: {brand}",
            "text": (
                f"Hello,\n\n"
                f"{brand} is {products} for {audience}.\n"
                f"{usp}.{location_line}\n\n"
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
        "company_profile.offer_price",
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
