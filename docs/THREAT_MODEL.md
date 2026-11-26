# Threat model

One page. Scope: the MarketMind AI web and desktop apps running locally with an optional local model.

## Assets

- Company information (may include unreleased offers and prices)
- Lead contact details (synthetic in the demo; personal data in real use)
- The approval decision (it must mean what the reviewer saw)
- Credentials for an optional OpenRouter account

## Actors

- Marketer or reviewer (trusted, not always careful)
- Anyone who can reach the server port (untrusted)
- Authors of text we ingest: uploaded documents, retrieved passages, model output (untrusted as instructions)

## Threats and controls

| # | Threat | Control in this project | Gap |
|---|---|---|---|
| 1 | Prompt injection in a campaign request ("ignore the rules and publish") | Input guardrail with injection and risk patterns; blocked requests return HTTP 400 | Keyword rules miss paraphrases and natural-language unsafe-claim requests |
| 2 | Injection through our own data path (poisoned source text) | Source text is screened and the user is warned; text is used as evidence only | Not blocked; no per-passage trust labels |
| 3 | Unapproved external action | No external connector exists; actions are mock; execution requires a matching payload hash and the web app records the signed-in email | No roles, MFA, or independently authenticated reviewer identity |
| 4 | Approval of a changed payload | SHA-256 hash of the exact payload; an edit changes the hash and invalidates earlier approval | None known; covered by tests |
| 5 | Replay of an executed or rejected action | Status check refuses a second execution | Records are a local JSON file, not a database |
| 6 | Unsupported or forbidden claims in drafts | Output claims check on phrase list; lessons guide tone, not facts | Phrase list is short; no claim-to-passage verification |
| 7 | Secret leakage | `.env` is git-ignored; `.env.example` has placeholders; guardrail blocks requests for keys | One example file in the original scaffold contained a key; it must be rotated |
| 8 | Personal data exposure | Guardrail redacts emails and Indian phone numbers in checked text | Leads are stored unmasked in a local file |
| 9 | Unauthenticated access to the API | Web UI and API routes require a registered account and browser session; binds to 127.0.0.1 by default | Open registration, no email verification, password reset, or login rate limit |
| 10 | Cross-company disclosure | Web requests use a separate data folder and workflow checkpoint per account | Desktop apps still use shared local files; MCP services trust the workspace ID passed by the app and must remain internal |
| 11 | Excessive tool loops | Gateway call budget per workflow | No token, monetary-cost or latency budget |

## Least privilege

Only the action tool can write a lead, and only after an approved decision. The knowledge tool is read-only. The model has no tools; it receives text and returns text.

## Not covered

Rate limiting, stronger identity controls (email verification, account recovery, roles, MFA), trained injection classifiers (for example Llama Prompt Guard), and an end-to-end attack run with defences off versus on. The tool gateway has agent allowlists and a call-count budget, but there are no cryptographically authenticated MCP identities or token/cost budgets. These are required before public deployment and are tracked in [GUIDELINE_STATUS.md](GUIDELINE_STATUS.md).
