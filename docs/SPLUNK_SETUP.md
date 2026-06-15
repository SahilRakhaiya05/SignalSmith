# Splunk Setup Guide

Complete guide to connect SignalSmith AI to Splunk Enterprise for the hackathon demo and judging.

---

## Overview

SignalSmith uses a **shadow index pattern**:

| Index | Role | Modified? |
|-------|------|-----------|
| `signalsmith_baseline` | Original telemetry for analysis and validation baseline | **Never** — read and bootstrap only |
| `signalsmith_candidate` | Post-policy filtered shadow telemetry | Yes — receives candidate ingest |

SignalSmith never modifies your production source indexes.

---

## Step 1 — Splunk Enterprise

1. [Download Splunk Enterprise](https://www.splunk.com/en_us/download/splunk-enterprise.html) (60-day trial)
2. Optional: apply a [Developer License](https://dev.splunk.com/) (6 months, dev use cases)
3. Note your ports from **Settings → Server settings → General settings**:
   - Web UI — often `8000` or `8005`
   - Management port — often `8089` or `8090`

---

## Step 2 — Configure environment

```powershell
copy .env.example .env
```

| Variable | What to set |
|----------|-------------|
| `SPLUNK_USERNAME` / `SPLUNK_PASSWORD` | Splunk admin credentials |
| `SPLUNK_WEB_PORT` | Web UI port (e.g. `8005`) |
| `SPLUNK_API_PORT` | REST/MCP port (e.g. `8090`) |
| `SPLUNK_API_SCHEME` | `https` for local Splunk (self-signed OK in demo) |
| `SPLUNK_MCP_URL` | From MCP Server → Endpoints (e.g. `https://localhost:8090/services/mcp`) |
| `SPLUNK_MCP_TOKEN` | Encrypted token from MCP Server → Create MCP Encrypted Token |
| `SPLUNK_HEC_TOKEN` | Optional — enables HEC ingest (faster bootstrap) |
| `SPLUNK_BASELINE_INDEX` | Default: `signalsmith_baseline` |
| `SPLUNK_CANDIDATE_INDEX` | Default: `signalsmith_candidate` |

---

## Step 3 — Install Splunk MCP Server

**Recommended** for hackathon judging (Best Use of Splunk MCP Server prize).

```powershell
.\scripts\install_mcp.ps1
```

Or install manually from [Splunkbase app 7931](https://splunkbase.splunk.com/app/7931).

After install:

1. Open Splunk Web → **MCP Server**
2. Copy the **endpoint URL** → `SPLUNK_MCP_URL` in `.env`
3. Create an **encrypted token** → `SPLUNK_MCP_TOKEN` in `.env`
4. Verify:

```powershell
cd backend
python scripts/check_mcp.py
```

---

## Step 4 — Create indexes

SignalSmith auto-creates indexes via REST when Splunk is reachable. Manual fallback:

```spl
splunk add index signalsmith_baseline
splunk add index signalsmith_candidate
```

---

## Step 5 — HEC token (optional, faster ingest)

1. Splunk Web → **Settings → Data inputs → HTTP Event Collector**
2. Create a token with access to both indexes
3. Set `SPLUNK_HEC_TOKEN` in `.env`

Without HEC, SignalSmith uses the REST stream receiver (also works; returns HTTP 204 on success).

---

## Step 6 — Start SignalSmith

```powershell
.\scripts\setup.ps1      # first time only
.\scripts\start.ps1
```

Open **http://localhost:8080** → log in with Splunk credentials.

Check integrations: **http://localhost:8080/api/integrations/status**

Expected connection mode: `splunk_mcp` when MCP is configured.

---

## Use your own data (not limited to the demo)

SignalSmith is a **platform**, not a payment-only tool.

### Point at your indexes

```env
SPLUNK_BASELINE_INDEX=your_production_index
SPLUNK_CANDIDATE_INDEX=your_shadow_index
```

### Add your detections

```powershell
copy config\detections.example.json config\detections.json
```

Edit SPL templates (use `$INDEX$`). Set `SIGNALSMITH_INCLUDE_DEMO_DETECTIONS=false` to disable the built-in e-commerce demo detections.

See [config/README.md](../config/README.md) for FinTech, SOC, SRE, and NetOps examples.

Discovery also loads saved searches from **Splunk MCP/REST** automatically when available.

---

## Built-in demo detections (shadow validation)

SignalSmith replays these five detections during validation. SPL uses `$INDEX$` for baseline vs candidate targeting.

### Payment Outage Detection

```spl
index=$INDEX$ service="payment-service" (level="ERROR" OR http_status>=500) scenario="payment_outage"
```

### High HTTP Error Rate

```spl
index=$INDEX$ http_status>=500
```

### Slow Payment Requests

```spl
index=$INDEX$ service="payment-service" duration_ms>=1500
```

### Credential Stuffing Detection

```spl
index=$INDEX$ scenario="credential_stuffing" OR (service="auth-service" event_type="failed_login" http_status=401)
```

### Privileged User Login Anomaly

```spl
index=$INDEX$ is_privileged=true service="auth-service" event_type="login"
```

Templates also ship in `samples/detections.json`.

---

## Connection modes

| Mode | When | Query path |
|------|------|------------|
| `splunk_mcp` | MCP `initialize` succeeds | SplunkMCPClient → JSON-RPC |
| `splunk_api` | MCP unavailable | MCPRestBridge → REST oneshot |
| `offline` | Splunk unreachable | Local JSON replay only |

The UI labels the active mode so judges always know what's live vs fallback.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| MCP connection failed | Verify `SPLUNK_MCP_URL` and token; run `python backend/scripts/check_mcp.py` |
| Validation shows 0/0 hits | Re-run pipeline; ensure `stats count` wrapper is active (fixed in current build) |
| Double candidate counts | Fixed — HTTP 204 now treated as ingest success |
| SSL errors | Demo disables TLS verify for local Splunk; set `SPLUNK_API_SCHEME=https` |
| Slow bootstrap | Set `SPLUNK_HEC_TOKEN` or reduce `PROFILE_EXPORT_LIMIT` in `.env` |
| Mentor offline | Set `GEMINI_API_KEY` in `.env`; SPL templates still work without it |

---

## CLI helpers

```powershell
cd backend
python -m app.cli health
python -m app.cli integrations
python -m app.cli bootstrap
python -m app.cli run
```

---

## Next

- Run the demo: [DEMO_SCRIPT.md](DEMO_SCRIPT.md)
- Record video: [DEMO_VIDEO_SCRIPT.md](DEMO_VIDEO_SCRIPT.md)
- Submit: [SUBMISSION.md](SUBMISSION.md)