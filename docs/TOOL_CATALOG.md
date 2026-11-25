# MCP tool catalog

FastMCP infers JSON input schemas from the typed function signatures below. Outputs are structured dictionaries with an `ok` flag or explicit result fields. Tests call each tool through an in-process MCP client.

## Knowledge server — `marketmind.mcp.knowledge_server`

| Tool | Input schema | Access | Allowed caller |
|---|---|---|---|
| `search_company_knowledge` | `query: str`, `limit: int = 5` | Read-only | Research |
| `get_company_passage` | `chunk_id: str` | Read-only | Research |

## Records server — `marketmind.mcp.records_server`

| Tool | Input schema | Access | Allowed caller |
|---|---|---|---|
| `get_leads` | `limit: int = 50` | Read-only | Lead |
| `qualify_lead` | `name: str`, `company: str`, `contact: str`, `requirement: str`, `timeline: str`, `location: str = ""` | Read-only | Lead |
| `prepare_lead_write` | Same lead fields | Write: creates pending action only | Lead; must be human-approved to save |

## Checks server — `marketmind.mcp.checks_server`

| Tool | Input schema | Access | Allowed caller |
|---|---|---|---|
| `check_campaign_request` | `text: str` | Read-only | Review |
| `check_marketing_copy` | `text: str` | Read-only | Content, Review |

## Actions server — `marketmind.mcp.actions_server`

| Tool | Input schema | Access | Allowed caller |
|---|---|---|---|
| `list_pending_actions` | none | Read-only | Human reviewer |
| `prepare_mock_publish` | `channel: str`, `text: str`, `subject: str = ""` | Write: creates pending mock action | Publisher |
| `prepare_workflow_publish` | `payload: dict` | Write: creates pending mock action | Publisher |
| `record_human_decision` | `action_id: str`, `decision: str`, `payload_hash: str`, `reviewer: str` | Write: approve/reject only | Human integration; edits go through the web UI |

## Enforcement

`src/marketmind/tools/gateway.py` enforces agent allowlists and a per-workflow call budget. Write tools only create local pending records. The workflow interrupt approves the exact payload hash; edits invalidate the earlier hash. No tool connects to a social network, messaging service or external CRM.

In the local demo, clients connect to in-process FastMCP servers. Compose defines four HTTP services, but that transport setup is not yet verified.
