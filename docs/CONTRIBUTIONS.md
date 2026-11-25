# Contribution log

Update from the first day. The viva asks each member to explain their part in depth and the whole architecture.

## Roles

| Member | Role (guide) | Owns |
|---|---|---|
| Dr. Ashutosh Verma | Product and evaluation lead | Problem framing, golden set, held-out cases, red-team suite, judge calibration, experiments, demo script |
| Damini Shrawan | Knowledge, memory and tools engineer | Ingestion, retrieval, memory store and policy, tool servers |
| Kisalaya Pathak | Agents and orchestration engineer | Graph, planner, specialists, improvement loop |
| Aniket Babuta | Control, security and deployment engineer | Hooks, approval gate, guardrails, threat model, API and UI, Compose, CI, dashboards |

## Log

| Date | Member | Change or decision | Evidence (file, commit, result) |
|---|---|---|---|
| 2026-11-25 | Dr. Ashutosh Verma | Supplied the original prototype scaffold and X1-X7 desktop modules used as the starting point | Source archive hashes and reuse/license confirmation still need to be recorded |
| 2026-11-25 | Aniket Babuta with AI coding assistance | Reorganized the scaffold; added the browser app, approval-hash flow, tests, setup and submission drafts | 46 automated tests pass; confirm the personal contribution description before submission |
| 2026-11-25 | Aniket Babuta with AI coding assistance | Added LangGraph workflow, four FastMCP servers, LiteLLM adapter, Qdrant/embedding retrieval and local benchmark | `docs/GUIDELINE_STATUS.md`, `eval/retrieval_report.json`; team to review |

## Reused and AI-assisted work

State what was reused or generated and how it was checked. AI coding tools may write parts of the implementation; framing, design, evaluation and interpretation must be the team's own.

| Item | Source | Checked by |
|---|---|---|
| Prototype modules (ingestion, retrieval, planner, drafts, leads, feedback, guardrails) | Scaffold provided by the product lead | |
| Restructure, web app, approval hash binding, tests, deployment files | Assisted | |
