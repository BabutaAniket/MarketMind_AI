import json

import pytest
from fastapi.testclient import TestClient

from marketmind.api.app import app
from marketmind.settings import SAMPLE_FILE

client = TestClient(app)


@pytest.fixture(autouse=True)
def signed_in_user():
    response = client.post(
        "/api/auth/register",
        json={"email": "workflow@example.com", "password": "a-very-long-workflow-password"},
    )
    assert response.status_code == 200


def _save_sample() -> None:
    sample = json.loads(SAMPLE_FILE.read_text(encoding="utf-8"))
    assert client.post("/api/knowledge", json=sample).status_code == 200


def _start(design: str = "team") -> dict:
    _save_sample()
    response = client.post(
        "/api/workflow/start",
        json={
            "campaign": {
                "objective": "Introduce the shared task board",
                "audience": "Small project teams",
                "offer": "Request a guided walkthrough",
                "channels": ["Instagram"],
                "design": design,
            }
        },
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "awaiting_approval"
    assert result["interrupts"]
    if design == "team":
        assert result["strategy"]["sender"] == "strategy_agent"
        assert result["content_brief"]["sender"] == "content_agent"
        assert result["lead_brief"]["sender"] == "lead_agent"
    if design == "single":
        assert result["specialists"]["single_agent"]["sender"] == "single_agent"
    assert result["specialists"]["compliance"]["payload"]["human_review_required"] is True
    expected_tools = {
        "search_company_knowledge",
        "check_marketing_copy",
        "prepare_workflow_publish",
    }
    if design == "team":
        expected_tools.add("get_leads")
    assert {item["tool"] for item in result["tool_calls"]} >= expected_tools
    assert all(item["ok"] for item in result["tool_calls"])
    assert all(item["call_number"] <= item["budget"] for item in result["tool_calls"])
    return result


def test_langgraph_pauses_then_resumes_after_exact_approval():
    pending = _start()
    approval = pending["interrupts"][0]
    assert approval["payload"]["campaign_summary"]["audience"] == "Small project teams"
    assert approval["payload"]["drafts"]["instagram"]["text"]
    assert approval["payload"]["sources"][0]["evidence_text"]
    assert "plan" not in approval["payload"]
    status = client.get(f"/api/workflow/{pending['thread_id']}")
    assert status.status_code == 200
    assert status.json()["status"] == "awaiting_approval"
    assert status.json()["interrupts"][0]["payload_hash"] == approval["payload_hash"]

    approved = client.post(
        f"/api/workflow/{pending['thread_id']}/resume",
        json={"decision": "approve", "payload_hash": approval["payload_hash"]},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved_mock"
    assert approved.json()["action"]["external_side_effect"] is False


def test_edit_invalidates_old_hash_and_requires_second_interrupt():
    pending = _start()
    thread_id = pending["thread_id"]
    old = pending["interrupts"][0]
    edited_payload = dict(old["payload"])
    edited_payload["reviewer_note"] = "Edited in demo"

    edited = client.post(
        f"/api/workflow/{thread_id}/resume",
        json={"decision": "edit", "edited_payload": edited_payload},
    )
    assert edited.status_code == 200, edited.text
    new = edited.json()["interrupts"][0]
    assert new["payload_hash"] != old["payload_hash"]

    stale = client.post(
        f"/api/workflow/{thread_id}/resume",
        json={"decision": "approve", "payload_hash": old["payload_hash"]},
    )
    assert stale.status_code == 200
    assert stale.json()["status"] == "awaiting_approval"
    assert stale.json()["interrupts"][0]["payload_hash"] == new["payload_hash"]

    final = client.post(
        f"/api/workflow/{thread_id}/resume",
        json={"decision": "approve", "payload_hash": new["payload_hash"]},
    )
    assert final.status_code == 200, final.text
    assert final.json()["status"] == "approved_mock"


def test_workflow_can_be_rejected():
    pending = _start()
    response = client.post(
        f"/api/workflow/{pending['thread_id']}/resume",
        json={"decision": "reject"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


def test_workflow_checkpoint_stores_redacted_request():
    pending = client.post(
        "/api/workflow/start",
        json={
            "campaign": {
                "objective": "Ask jane@example.com about a shared task board",
                "audience": "Small teams",
                "offer": "Request a walkthrough",
                "channels": ["Instagram"],
            }
        },
    )
    assert pending.status_code == 200
    thread_id = pending.json()["thread_id"]
    stored = client.get(f"/api/workflow/{thread_id}").json()
    assert "jane@example.com" not in stored["request"]["objective"]
    assert "[EMAIL_REDACTED]" in stored["request"]["objective"]


def test_workflow_runs_one_deterministic_correction_pass():
    sample = json.loads(SAMPLE_FILE.read_text(encoding="utf-8"))
    sample["company_profile"]["usp"] = "100% saving guaranteed"
    sample["source_text"] += "\n100% saving guaranteed."
    assert client.post("/api/knowledge", json=sample).status_code == 200
    result = client.post(
        "/api/workflow/start",
        json={
            "campaign": {
                "objective": "Introduce the product",
                "audience": "Small teams",
                "offer": "Request a walkthrough",
                "channels": ["Instagram"],
            }
        },
    ).json()
    assert any(event["node"] == "self_correction" for event in result["events"])
    assert result["retries"] == 1
    assert result["review"]["passed"] is True


def test_workflow_design_routes_are_distinct():
    fixed = _start("fixed")
    single = _start("single")
    team = _start("team")
    fixed_nodes = {item["node"] for item in fixed["events"]}
    single_nodes = {item["node"] for item in single["events"]}
    team_nodes = {item["node"] for item in team["events"]}
    assert "strategy_specialist" not in fixed_nodes
    assert "single_agent" in single_nodes and "strategy_specialist" not in single_nodes
    assert {"strategy_specialist", "content_specialist", "lead_specialist"} <= team_nodes
