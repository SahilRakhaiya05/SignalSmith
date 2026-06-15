# SignalSmith Architecture

SignalSmith is an agentic telemetry optimization platform. It reads Splunk baseline telemetry, runs a multi-agent analysis pipeline, applies reduction policies to a **shadow candidate** index, validates detection coverage, and exports OpenTelemetry collector YAML after human approval.

**Devpost diagram:** [architecture.svg](../architecture.svg) at repo root (1800×1350, six layers, full legend)

**Related docs:** [README.md](README.md) · [TECHNICAL_DESIGN.md](TECHNICAL_DESIGN.md) · [SPLUNK_SETUP.md](SPLUNK_SETUP.md)

---

## 1. System context

How the operator, frontend, backend, Splunk, and AI layer fit together.

```mermaid
flowchart TB
  subgraph User["Operator"]
    Browser["Browser · localhost:8080"]
  end

  subgraph Frontend["Frontend · React / Vite / TypeScript"]
    UI["Views: Command Center, Data Flow, Mentor, Pipeline, Validation, Approval"]
    Ctx["SessionContext · api.ts"]
    Browser --> UI
    UI --> Ctx
  end

  subgraph Backend["Backend · FastAPI · Python"]
    API["/api routes · routes.py"]
    Orch["AnalysisOrchestrator"]
    Store["Storage · SQLite + JSON files"]
    API --> Orch
    Orch --> Store
    Ctx -->|"REST + X-Splunk-User/Pass"| API
  end

  subgraph Splunk["Splunk Enterprise"]
    MCP["MCP Server · :8090 /services/mcp"]
    REST["REST API · :8089"]
    HEC["HEC · :8088"]
    BL["signalsmith_baseline"]
    CD["signalsmith_candidate"]
    MCP --> BL
    MCP --> CD
    REST --> BL
    REST --> CD
    HEC --> BL
    HEC --> CD
  end

  subgraph AI["AI & guidance"]
    Mentor["SignalSmith Mentor · GeminiService"]
    SPL["SPL templates · mcp_rest_bridge"]
    Mentor --> SPL
  end

  API --> MCP
  API --> REST
  API --> HEC
  API --> Mentor
```

| Layer | Location | Role |
|-------|----------|------|
| Frontend | `frontend/src/` | SPA UI, session state, Splunk auth headers |
| API | `backend/app/api/routes.py` | REST surface for pipeline, Splunk, Mentor, jobs |
| Orchestrator | `backend/app/services/analysis_orchestrator.py` | Coordinates agents and validation |
| Storage | `backend/app/services/storage.py`, `backend/data/` | SQLite + `baseline_events.json` / `candidate_events.json` |
| Splunk clients | `splunk_client.py`, `mcp_client.py`, `mcp_rest_bridge.py` | Query, ingest, MCP JSON-RPC |

---

## 2. Splunk integration

SignalSmith never mutates production source indexes in place. It reads **baseline**, writes a **candidate** shadow index, and replays saved searches on both.

```mermaid
flowchart LR
  subgraph Ingest["Ingest paths"]
    GEN["TelemetryGenerator / bootstrap export"]
    HEC_P["HEC batch POST"]
    RX["REST receiver / stream"]
    GEN --> HEC_P
    GEN --> RX
  end

  subgraph Clients["Backend clients"]
    SC["SplunkClient"]
    MC["SplunkMCPClient"]
    BR["MCPRestBridge · Splunk API fallback"]
    MC -->|"splunk_run_query"| MCP_SRV["Splunk MCP Server"]
    MC -->|"tool missing / error"| BR
    BR --> SC
    SC --> REST_API["Splunk REST :8089"]
    SC --> HEC_P
    SC --> RX
  end

  subgraph Indexes["Indexes"]
    BL2["signalsmith_baseline"]
    CD2["signalsmith_candidate"]
  end

  HEC_P --> BL2
  HEC_P --> CD2
  RX --> BL2
  RX --> CD2
  MCP_SRV --> BL2
  MCP_SRV --> CD2
  REST_API --> BL2
  REST_API --> CD2

  subgraph Queries["Query use cases"]
    Q1["Bootstrap · export up to 25k events"]
    Q2["Live analytics · charts & counts"]
    Q3["Shadow validation · detection SPL + stats count"]
    Q4["Mentor / generate-spl · natural language → SPL"]
  end

  MCP_SRV --> Q1
  MCP_SRV --> Q2
  MCP_SRV --> Q3
  REST_API --> Q4
```

### Connection modes

| Mode | Detection | Query path |
|------|-----------|------------|
| `splunk_mcp` | MCP `initialize` succeeds | `SplunkMCPClient` → JSON-RPC `tools/call` |
| `splunk_api` | MCP unavailable | `MCPRestBridge` → Splunk REST oneshot jobs |
| `offline` | Splunk unreachable | Local JSON replay only |

### Key files

| File | Responsibility |
|------|----------------|
| `backend/app/services/splunk_client.py` | REST connect, index ensure, HEC/REST ingest, oneshot SPL |
| `backend/app/services/mcp_client.py` | Official Splunk MCP JSON-RPC, tool aliases, call history |
| `backend/app/services/mcp_rest_bridge.py` | Implements MCP tool names via Splunk REST when MCP app absent |
| `backend/app/services/splunk_data_service.py` | Bootstrap export, count parsing, row → `TelemetryEvent` |
| `backend/app/services/splunk_analytics.py` | Live chart queries for Command Center / Analytics |
| `backend/app/services/splunk_dashboard.py` | Deploy Splunk dashboard XML |
| `backend/app/config.py` | `splunk_baseline_index`, `splunk_candidate_index`, host/ports |

### Auth

- Operator logs in via `LoginView` → `POST /api/splunk/auth/login`
- Frontend stores credentials in `sessionStorage`; sends `X-Splunk-User` / `X-Splunk-Pass` on every API call
- Backend resolves auth in `splunk_credentials.py` for REST, MCP, and HEC

---

## 3. AI models and agents

Two categories: **pipeline agents** (deterministic analysis) and **SignalSmith Mentor** (natural-language guidance + SPL).

```mermaid
flowchart TB
  subgraph PipelineAgents["Pipeline agents · backend/app/agents/"]
    D["DiscoveryAgent · indexes, saved searches, bootstrap"]
    P["TelemetryProfiler · service/event/scenario stats"]
    PM["ProtectionMapBuilder · detection-critical events"]
    PG["PolicyGenerator · drop/sample/preserve rules"]
    PE["PolicyEngine · apply policies → candidate_events.json"]
    RV["ReplayValidator · SPL replay baseline vs candidate"]
    RA["RevisionAgent · fix coverage regressions"]
    D --> P --> PM --> PG --> PE --> RV
    RV -->|"fail"| RA --> PE
  end

  subgraph MentorLayer["SignalSmith Mentor"]
    AV["AssistantView · frontend"]
    CHAT["POST /api/ai/chat"]
    EXPL["POST /api/ai/explain"]
    GS["GeminiService · gemini_service.py"]
    CTX["Session context · analysis, proposal, validation"]
    AV --> CHAT --> GS
    AV --> EXPL --> GS
    GS --> CTX
  end

  subgraph SPLGen["SPL generation fallback chain"]
    MCP_SPL["MCP generate_spl"]
    GEM_SPL["GeminiService.generate_spl"]
    TPL["Template SPL · mcp_rest_bridge"]
    MCP_SPL --> GEM_SPL --> TPL
  end

  Orch2["AnalysisOrchestrator"] --> PipelineAgents
  API2["routes.py"] --> Orch2
  API2 --> MentorLayer
  API2 --> SPLGen
```

### Agent catalog

Defined in `backend/app/services/agent_catalog.py`:

| Agent | Phase | Human in loop |
|-------|-------|---------------|
| Discovery Agent | analyze | No |
| Telemetry Profiler | analyze | No |
| Protection Map Builder | analyze | No |
| Policy Generator | analyze | Yes |
| Policy Engine | apply | No |
| Replay Validator | validate | No |
| Revision Agent | revise | Yes |
| SignalSmith Mentor | assist | Yes |

### Mentor behavior

- **Online:** `GeminiService.chat()` with session context (baseline counts, policies, validation results)
- **Offline:** Template SPL via `POST /api/mcp/generate-spl` and local saved-search matchers
- User-facing label is always **SignalSmith Mentor** — no provider names in UI copy

---

## 4. End-to-end data flow

Shadow pipeline: read → analyze → apply → validate → (revise) → approve → export.

```mermaid
sequenceDiagram
  participant U as Operator
  participant FE as Frontend
  participant API as FastAPI /api
  participant O as AnalysisOrchestrator
  participant S as Storage
  participant SP as Splunk

  U->>FE: Run pipeline
  FE->>API: POST /session/run
  API->>SP: Bootstrap · SPL on signalsmith_baseline
  SP-->>API: Event rows
  API->>S: baseline_events.json

  API->>O: run_analysis
  O->>O: Discovery → Profiler → Protection → PolicyGenerator
  O->>S: proposal + analysis (SQLite)

  API->>O: apply_proposal
  O->>S: candidate_events.json
  API->>SP: Ingest candidate → signalsmith_candidate

  API->>O: run_validation
  O->>SP: Ingest tagged replay source
  O->>SP: Detection SPL + stats count (MCP)
  O->>S: validation record + coverage_results

  alt validation failed
    API->>O: revise_and_revalidate
    O->>S: revised proposal + run 2 validation
  end

  U->>FE: Approve
  FE->>API: POST /proposals/{id}/approve
  API-->>FE: GET /proposals/{id}/export/otel · YAML
```

### Persistent artifacts

| Artifact | Path / table | Written by |
|----------|--------------|------------|
| Baseline events | `backend/data/baseline_events.json` | Bootstrap / generator |
| Candidate events | `backend/data/candidate_events.json` | PolicyEngine |
| Analysis | SQLite `analyses` | Discovery + profiler pipeline |
| Proposal | SQLite `proposals` | PolicyGenerator |
| Validation | SQLite `validations` | ReplayValidator |
| Audit trail | SQLite `audit` | All agents + Mentor |

---

## 5. Frontend ↔ API map

```mermaid
flowchart LR
  subgraph Views["frontend/src/views/"]
    OV["OverviewView"]
    DF["DataFlowView"]
    WV["WorkflowView"]
    AV["AssistantView · Mentor"]
    VV["ValidationView"]
    AP["ApprovalView"]
  end

  subgraph Session["SessionContext"]
    RF["refreshSession · GET /session/status"]
    RFP["runFullPipeline · POST /session/run"]
    RWS["runWorkflowStep · bootstrap/analyze/apply/validate/..."]
  end

  subgraph Endpoints["Key API endpoints"]
    E1["/session/status"]
    E2["/session/bootstrap"]
    E3["/session/run"]
    E4["/analysis/start"]
    E5["/proposals/{id}/apply"]
    E6["/validation/{id}/run"]
    E7["/ai/chat"]
    E8["/splunk/analytics/live"]
    E9["/integrations/status"]
  end

  OV --> RF
  DF --> RF
  WV --> RWS
  AV --> E7
  VV --> E1
  RF --> E1
  RFP --> E3
  RWS --> E2
  RWS --> E4
  RWS --> E5
  RWS --> E6
  OV --> E8
  DF --> E9
```

| View | Primary API calls |
|------|-------------------|
| Command Center (`OverviewView`) | `/session/status`, `/splunk/analytics/live` |
| Data Flow (`DataFlowView`) | `/integrations/status`, `/session/status`, `/audit` |
| Pipeline (`WorkflowView`) | `/session/bootstrap`, `/analysis/start`, `/proposals/.../apply`, `/validation/.../run` |
| Mentor (`AssistantView`) | `/ai/chat`, `/ai/explain`, `/mcp/generate-spl`, `/mcp/run-query` |
| Validation (`ValidationView`) | `/session/status` (coverage_results) |
| Approval (`ApprovalView`) | `/proposals/.../approve`, `/export/otel` |

---

## 6. Repository layout (architecture-relevant)

```
splunk/
├── frontend/src/
│   ├── api.ts                 # HTTP client → /api/*
│   ├── context/SessionContext.tsx
│   ├── views/                 # Page components
│   ├── components/            # ChatMessage, WorkflowStepper, Sidebar, …
│   └── lib/workflow.ts        # Pipeline step gating
├── backend/app/
│   ├── main.py                # FastAPI app, serves frontend/dist
│   ├── api/routes.py          # All REST endpoints
│   ├── agents/                # Pipeline agents
│   ├── services/              # Splunk, MCP, Mentor, storage, jobs
│   └── models/                # Pydantic records
├── backend/data/
│   ├── signalsmith.db
│   ├── baseline_events.json
│   └── candidate_events.json
├── docs/
│   ├── ARCHITECTURE.md        # This file
│   └── architecture.svg       # Static diagram
└── scripts/                   # setup, start, install_mcp only
```

---

## 7. Static diagram

The repo-root [architecture.svg](../architecture.svg) is the **Devpost submission diagram** (1800×1350). It includes:

- **Four tiers:** Presentation (React UI) · Application (FastAPI + agents) · Splunk Enterprise (MCP/REST/HEC) · Governance
- **All 8 agents** with phases, human gates, and the revision feedback loop
- **Shadow validation** detail: baseline vs candidate replay, `stats count`, and all 5 detections
- **End-to-end pipeline:** Bootstrap → Analyze → Apply → Ingest → Validate → Revise → Approve → OTel YAML
- **Connection modes:** `splunk_mcp` · `splunk_api` · `offline`
- **Legend** for data flows, MCP integration, AI layer, and impact

For slides or print, open [architecture.svg](architecture.svg) in this folder (same file as repo root).