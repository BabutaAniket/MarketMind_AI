# Architecture

## Diagram

```mermaid
flowchart TD
    U[Browser or desktop user] --> API[FastAPI]
    API --> G[LangGraph: typed state + SQLite checkpointer]
    G --> IG[Input guardrail]
    IG -->|blocked| STOP[Stop]
    IG --> R[Research specialist]
    R --> KM[Knowledge FastMCP]
    KM --> Q[FastEmbed vectors + Qdrant in-memory]
    KM --> BM[BM25]
    Q --> RF[Reciprocal Rank Fusion + overlap reranker]
    BM --> RF
    RF --> P[Planner]
    P --> S[Strategy specialist]
    S --> C[Content specialist]
    C --> L[Lead specialist]
    L --> D[Template drafts]
    D --> V[Review + Checks FastMCP]
    V -->|failed check, one retry| D
    V -->|passed| A[Prepare action via Actions FastMCP]
    A --> I[LangGraph interrupt: exact payload + SHA-256]
    H[Human reviewer] -->|approve / edit / reject| I
    I -->|approved exact hash| M[Mock action only]
    M --> LE[Local leads/actions JSON]
    U --> FB[Human feedback]
    FB --> MEM[Approved lesson JSONL]
    API --> MET[/metrics]
    MET --> PR[Prometheus]
    PR --> GR[Grafana + alert rule]
    API -. optional .-> LT[LiteLLM]
    LT -. local route .-> OL[Ollama + Qwen3]
    LT -. optional route .-> OR[OpenRouter]
```

## Walkthrough of the LangGraph workflow

1. The user saves one company profile and its source text. The demo sample is fictional. Text is screened for selected injection risks.
2. `POST /api/workflow/start` starts a graph run with a unique `thread_id`.
3. The graph checks the request, then calls the read-only knowledge FastMCP tool through the tool gateway.
4. Retrieval preserves passage IDs, source references and dates. It combines BM25 and FastEmbed vectors in a local-memory Qdrant collection using RRF and a content-word overlap reranker.
5. Planner, strategy, content and lead specialist nodes pass typed `AgentMessage` data. They are deterministic functions; they are not independent model agents.
6. Channel drafts use Ashutosh's template approach. The review node calls the Checks FastMCP server. A forbidden phrase can trigger one deterministic correction attempt.
7. The publisher role prepares a mock action through the Actions FastMCP server. The graph pauses at `interrupt()` and checkpoints the state in SQLite.
8. The reviewer sees the exact payload and hash. An edit changes the hash and returns the workflow to the interrupt. A stale hash, replay, or rejected action cannot execute.
9. Resume uses `Command(resume=...)` and the same `thread_id`. Approved publication is recorded as mock-only; no external system is contacted.

The app also retains the simpler baseline routes: `/api/plan` and `/api/plan/stream`.

The workflow form can route to fixed-template, single-node, or team-node designs. These are deterministic dry-run routes for exercising graph control flow; they are not the required fair E1 result because no real model or cost/quality comparison has been run.

## Tool gateway

| Agent | Allowed tools |
|---|---|
| Research | Search knowledge, get passage |
| Content | Check marketing copy |
| Review | Check request and marketing copy |
| Lead | Read leads, qualify a lead |
| Publisher | Prepare a mock publish action |

The gateway rejects calls outside an agent's allowlist and enforces the configured call budget. Tool results are structured. Four FastMCP servers have in-process tests. Compose configures HTTP transport, but that deployment path is not yet verified.

## Who decides

| Decision | Made by |
|---|---|
| Whether a request matches known unsafe patterns | Guardrail code |
| Which passages are retrieved | BM25, vector search, RRF and reranker code |
| Draft wording | Templates; optional model route through LiteLLM |
| Lead score | Deterministic code |
| Whether a prepared action runs | Human decision checked by code |
| Whether a lesson is stored for reuse | Human reviewer |

## Known limits

- The Qdrant collection is in-memory and rebuilt for each query; it is not a persistent service.
- The overlap reranker is a deterministic baseline, not a cross-encoder.
- The 30-query Recall@5 set is hand-labeled for the included synthetic company only.
- No real Ollama or OpenRouter generation has been run here.
- No authentication or reviewer identity is implemented.
- Compose, Grafana and external HTTP MCP transports still need a clean-machine test.
- Reflexion, E1-E4, the calibrated judge and full held-out evaluation remain pending.

Redraw this diagram by hand for the final review, as the guidelines require.
