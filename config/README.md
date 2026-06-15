# Custom Detections

SignalSmith is **not limited to payment or e-commerce**. Point it at any Splunk indexes and any saved-search SPL.

---

## Use your own detections

1. Copy the example file:

```powershell
copy config\detections.example.json config\detections.json
```

2. Edit `config/detections.json` — add your SPL templates. Use `$INDEX$` for baseline/candidate substitution.

3. Optional in `.env`:

```env
# Path to custom detections (default: config/detections.json if it exists)
SIGNALSMITH_DETECTIONS_FILE=config/detections.json

# Set false to use ONLY your detections (no built-in demo set)
SIGNALSMITH_INCLUDE_DEMO_DETECTIONS=false
```

4. Restart SignalSmith and run the pipeline.

Custom detections replay via **live MCP SPL** on your Splunk indexes. Discovery also loads saved searches from Splunk MCP/REST when available.

---

## Use your own Splunk data

In `.env`:

```env
SPLUNK_BASELINE_INDEX=your_production_index
SPLUNK_CANDIDATE_INDEX=your_shadow_index
```

Bootstrap exports from your index (up to `PROFILE_EXPORT_LIMIT` events). Policies apply to the shadow candidate — your source index is never modified.

---

## Example use cases

| Industry | Baseline data | Example detections |
|----------|---------------|-------------------|
| FinTech / SaaS | App logs, APM | Error rate, slow APIs, auth failures |
| Security / SOC | Windows, firewall, IDS | Brute force, deny spikes, ES alerts |
| Platform / SRE | Kubernetes, CI/CD | Pod crashes, deploy failures |
| NetOps | Network devices | Link down, BGP flap, deny storms |
| Observability | Metrics + traces | SLO breach, anomaly thresholds |

The hackathon **demo** uses synthetic e-commerce telemetry. The **platform** works with any of the above.