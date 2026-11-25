from marketmind.tools.actions import decide_action, payload_hash, prepare_action
from marketmind.tools.knowledge import get_passage, search_knowledge
from marketmind.tools.records import add_lead, list_leads


def test_add_lead_requires_approval():
    assert add_lead({"name": "A"})["ok"] is False
    assert list_leads()["leads"] == []


def test_unknown_action_is_rejected():
    assert decide_action("act_missing", "approve", "x")["ok"] is False


def test_approval_needs_matching_payload_hash():
    action = prepare_action("write_lead", {"name": "A", "contact": "a@b.co"})
    assert decide_action(action["action_id"], "approve", "wrong-hash")["ok"] is False
    assert list_leads()["leads"] == []


def test_exact_approval_executes_once():
    action = prepare_action("write_lead", {"name": "A", "contact": "a@b.co"})
    first = decide_action(action["action_id"], "approve", action["payload_hash"])
    assert first["ok"] and first["status"] == "executed"
    assert len(list_leads()["leads"]) == 1
    assert decide_action(action["action_id"], "approve", action["payload_hash"])["ok"] is False
    assert len(list_leads()["leads"]) == 1


def test_edit_invalidates_earlier_hash():
    action = prepare_action("write_lead", {"name": "A", "contact": "a@b.co"})
    edited = decide_action(action["action_id"], "edit", edited_payload={"name": "B", "contact": "b@b.co"})
    assert edited["payload_hash"] == payload_hash({"name": "B", "contact": "b@b.co"})
    assert decide_action(action["action_id"], "approve", action["payload_hash"])["ok"] is False
    assert decide_action(action["action_id"], "approve", edited["payload_hash"])["ok"] is True


def test_rejected_action_cannot_execute():
    action = prepare_action("write_lead", {"name": "A", "contact": "a@b.co"})
    decide_action(action["action_id"], "reject")
    assert decide_action(action["action_id"], "approve", action["payload_hash"])["ok"] is False
    assert list_leads()["leads"] == []


def test_unsupported_action_type_is_refused():
    assert prepare_action("delete_everything", {})["ok"] is False


def test_knowledge_tools_follow_the_query():
    from marketmind.memory_store import write_json
    from marketmind.settings import KNOWLEDGE_FILE

    write_json(
        KNOWLEDGE_FILE,
        {
            "saved_at": "2026-01-01",
            "company_profile": {"company_name": "Acme", "usp": "Quiet cooling"},
            "source_text": "Acme builds air conditioners. Delivery is available across the city.",
        },
    )
    hit = search_knowledge("quiet cooling")
    assert hit["ok"] and hit["results"][0]["chunk_id"] == "profile:usp"
    assert search_knowledge("zzzxxyy")["results"] == []
    assert get_passage("profile:usp")["ok"] is True
    assert get_passage("missing")["ok"] is False
