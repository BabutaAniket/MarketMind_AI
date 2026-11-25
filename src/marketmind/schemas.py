"""Typed request models for the API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

DEFAULT_CHANNELS = ["Instagram", "Facebook", "WhatsApp", "Email"]


class KnowledgeInput(BaseModel):
    company_profile: dict[str, str] = Field(default_factory=dict)
    source_text: str = ""


class SearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=20)
    save: bool = False


class CampaignRequest(BaseModel):
    objective: str
    audience: str
    offer: str
    channels: list[str] = Field(default_factory=lambda: list(DEFAULT_CHANNELS))
    tone: str = "Professional, clear, trustworthy"
    budget: str = "Small test budget"
    use_llm: bool = False
    design: Literal["fixed", "single", "team"] = "team"


class WorkflowStart(BaseModel):
    campaign: CampaignRequest
    thread_id: str | None = None


class WorkflowResume(BaseModel):
    decision: Literal["approve", "edit", "reject"]
    payload_hash: str = ""
    edited_payload: dict[str, Any] | None = None
    reviewer: str = "human"


class DraftRequest(BaseModel):
    campaign_goal: str = ""
    call_to_action: str = ""


class LeadInput(BaseModel):
    name: str = ""
    company: str = ""
    contact: str = ""
    location: str = ""
    requirement: str = ""
    timeline: str = ""


class ActionPrepare(BaseModel):
    action_type: Literal["publish_draft", "send_message", "write_lead", "save_note"]
    payload: dict[str, Any]


class ActionDecision(BaseModel):
    action_id: str
    decision: Literal["approve", "edit", "reject"]
    payload_hash: str = ""
    edited_payload: dict[str, Any] | None = None
    reviewer: str = "human"


class FeedbackInput(BaseModel):
    decision: Literal["approved", "rejected"]
    raw_input: str = ""
    corrected_meaning: str = ""
    lesson: str = ""
