# Technical Design

SignalSmith AI — agentic telemetry optimization with shadow validation, Splunk MCP integration, and human-governed OTel export.

**See also:** [ARCHITECTURE.md](ARCHITECTURE.md) · [architecture.svg](architecture.svg) · [SPLUNK_SETUP.md](SPLUNK_SETUP.md)

---

## Design principles

1. **Proof over promises** — every policy is validated by replaying real SPL on baseline vs candidate
2. **Shadow-first** — never mutate production indexes; experiment on `signalsmith_candidate`
3. **Deterministic agents** — auditable pipeline; Mentor assists but does not auto-deploy
4. **Human gates** — policy review, revision review, and final approval before OTel export
5. **Graceful degradation** — MCP → REST → offline local JSON with clear UI labeling

---

## System layers

| Layer | Stack | Port |
|-------|-------|------|
| Presentation | React · TypeScript · Vite | Served by backend |
| Application | Python · FastAPI · Pydantic | `8080` (UI + API) |
| Persistence | SQLite + JSON event files | `backend/data/` (gitignored) |
| Splunk | MCP Server · REST · HEC | Configurable via `.env` |
| AI assist | GeminiService (SignalSmith Mentor) | Optional `GEMINI_API_KEY` |

---

## Backend agents

| Agent | Phase | Responsibility |
|-------|-------|----------------|
| `DiscoveryAgent` | analyze | MCP/API connectivity, index inventory, saved-search discovery, bootstrap export |
| `TelemetryProfiler` | analyze | Service/event/scenario distribution, reducible noise estimate |
| `ProtectionMapBuilder` | analyze | Maps events tied to critical detections — security + ops coverage |
| `PolicyGenerator` | analyze | Drop/sample/preserve rules with SPL evidence and byte reduction estimates |
| `PolicyEngine` | apply | Applies policies → `candidate_events.json` (baseline untouched) |
| `ReplayValidator` | validate | SPL shadow replay via MCP with `| stats count as count` |
| `RevisionAgent` | revise | Removes failing rules, re-applies, triggers re-validation |
| `SignalSmith Mentor` | assist | Natural-language SPL, pipeline coaching, session context |

Orchestrated by `AnalysisOrchestrator`. Full pipeline: `POST /api/session/run`.

---

## Frontend views

| View | Purpose |
|------|---------|
| Command Center | Live Splunk analytics, reduction metrics, connection status |
| Data Flow | End-to-end pipeline visualization + integration health |
| Pipeline | Step-by-step workflow with gating |
| Validation | Baseline vs candidate hit counts per detection |
| Mentor | Single-scroll chat, SPL blocks, session-aware coaching |
| Approval | Human approve + OTel YAML + rollback YAML export |
| Settings / MCP Tools | Integration config and MCP explorer |

State managed by `SessionContext` — pipeline progress, Splunk auth headers, live refresh.

---

## Data flow

```
Bootstrap (SPL → baseline_events.json)
  → Analyze (4 agents → proposal in SQLite)
  → Apply (PolicyEngine → candidate_events.json)
  → Ingest (candidate → signalsmith_candidate index)
  → Validate (ReplayValidator → MCP SPL counts)
  → [Revise if FAIL → re-apply → re-validate]
  → Approve (human gate)
  → Export (OTel collector YAML + rollback YAML)
```

Synthetic demo: `TelemetryGenerator` produces ~20,000 deterministic events (seed=42) across four e-commerce services.

---

## Splunk integration

### Clients

| Client | Role |
|--------|------|
| `SplunkMCPClient` | Official MCP JSON-RPC — primary query path |
| `MCPRestBridge` | Implements MCP tool names via REST when MCP app absent |
| `SplunkClient` | REST connect, index ensure, HEC/REST ingest, oneshot SPL |
| `SplunkDataService` | Bootstrap export, count parsing, row → TelemetryEvent |
| `SplunkAnalytics` | Live chart SPL for Command Center |

### Validation count fix

MCP returns event rows, not aggregates. `run_search_count` appends `| stats count as count` so shadow replay shows real hit comparison (e.g. 136/136), not vacuous 0/0.

### Ingest fix

Splunk stream receiver returns HTTP 204 on success. Treating only 200/201 as success caused double-ingest; now 204 is accepted.

---

## Intentional demo failure loop

First-pass proposal includes `rec_sample_successful_logins_demo`:

1. Processes before protection map (`bypass_protection`)
2. Aggressively samples privileged login events
3. Causes `privileged_user_anomaly` detection to fail validation

`RevisionAgent` removes the rule → re-applies → second validation passes with protected events preserved. Demonstrates true agentic ops.

---

## API surface

REST under `/api/`. Key endpoints:

| Endpoint | Action |
|----------|--------|
| `POST /session/run` | Full pipeline (bootstrap → approve-ready) |
| `POST /session/bootstrap` | Export baseline from Splunk |
| `POST /analysis/start` | Run analyze-phase agents |
| `POST /proposals/{id}/apply` | Apply policies to candidate |
| `POST /validation/{id}/run` | Shadow validation replay |
| `POST /validation/{id}/revise` | Auto-revise on failure |
| `POST /proposals/{id}/approve` | Human approval gate |
| `GET /proposals/{id}/export/otel` | OTel collector YAML |
| `POST /ai/chat` | SignalSmith Mentor |
| `GET /splunk/analytics/live` | Live chart data |
| `GET /integrations/status` | MCP/REST/offline mode |

Async jobs supported via SSE (`job_id` from `POST /session/run?async_job=true`).

---

## Storage

| Artifact | Location | Contents |
|----------|----------|----------|
| SQLite DB | `signalsmith.db` | analyses, proposals, validations, audit |
| Baseline events | `baseline_events.json` | Up to 25k exported events |
| Candidate events | `candidate_events.json` | Post-policy shadow dataset |
| Samples | `samples/` | 250 demo events + detection SPL (committed) |

---

## Testing

**43 pytest cases** covering:

- Per-agent unit tests (profiler, protection map, policy engine, validation)
- MCP client and Splunk count extraction
- API integration (full workflow)
- End-to-end: deliberate failure → revision → pass, >40% reduction, zero protected-event loss

```powershell
cd backend
python -m pytest tests -v
```

CI: `.github/workflows/ci.yml` runs tests + frontend typecheck on push.

---

## Security notes

See [SECURITY.md](SECURITY.md). Demo scope: local Splunk, synthetic data, human approval before export.