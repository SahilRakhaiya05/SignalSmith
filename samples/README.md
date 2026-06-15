# Sample Data

Synthetic **demo** data for judges — SignalSmith itself is **not limited** to this format. For real workloads, point at your Splunk indexes and add `config/detections.json`. See [../config/README.md](../config/README.md).

---

## Files

| File | Contents |
|------|----------|
| `demo_baseline_events.json` | 250 deterministic e-commerce telemetry events (seed=42) |
| `detections.json` | Five saved-search SPL templates used in shadow validation |

---

## Event schema

Each event includes fields used by agents and detections:

- `service` — auth, checkout, payment, inventory
- `level` — INFO, WARN, ERROR
- `http_status`, `duration_ms`, `route`
- `scenario` — payment_outage, credential_stuffing, normal_traffic, etc.
- `event_type`, `is_privileged`, `country`

---

## Detections

1. Payment Outage Detection
2. High HTTP Error Rate
3. Slow Payment Requests
4. Credential Stuffing Detection
5. Privileged User Login Anomaly

SPL uses `$INDEX$` placeholder — replaced with `signalsmith_baseline` or `signalsmith_candidate` during replay.

---

## Regenerate

```powershell
cd backend
python scripts/export_samples.py
```

---

## Full demo dataset

For the full dataset, start the app (`.\scripts\start.ps1`) and click **Run pipeline**, or call `POST /api/session/run` on the API.