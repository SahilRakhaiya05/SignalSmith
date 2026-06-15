from __future__ import annotations

import asyncio
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.services.mcp_client import SplunkMCPClient
from app.services.saved_searches import saved_search_catalog
from app.services.splunk_client import SplunkClient
from app.services.storage import Storage

ROOT = Path(__file__).resolve().parents[2]


def _load_json_events(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _db_table(conn: sqlite3.Connection, table: str) -> list[dict]:
    rows = conn.execute(f"SELECT data FROM {table}").fetchall()
    return [json.loads(r[0]) for r in rows]


def _event_summary(events: list[dict]) -> dict:
    if not events:
        return {"count": 0, "total_bytes": 0, "services": {}, "event_types": {}}
    services: dict[str, int] = {}
    event_types: dict[str, int] = {}
    total_bytes = 0
    for e in events:
        svc = e.get("service", "unknown")
        et = e.get("event_type", "unknown")
        services[svc] = services.get(svc, 0) + 1
        event_types[et] = event_types.get(et, 0) + 1
        total_bytes += e.get("estimated_size_bytes", 0)
    return {
        "count": len(events),
        "total_bytes": total_bytes,
        "services": services,
        "event_types": event_types,
        "sample_events": events[:5],
    }


async def collect_poc_data() -> dict:
    settings = get_settings()
    storage = Storage()
    data_dir = storage.data_dir

    with storage._connect() as conn:
        meta = {r["key"]: r["value"] for r in conn.execute("SELECT key, value FROM meta").fetchall()}
        analyses = _db_table(conn, "analyses")
        proposals = _db_table(conn, "proposals")
        validations = _db_table(conn, "validations")
        audit = _db_table(conn, "audit")

    baseline = _load_json_events(data_dir / "baseline_events.json")
    candidate = _load_json_events(data_dir / "candidate_events.json")

    splunk = SplunkClient()
    splunk_report = await splunk.health_report()
    mcp = SplunkMCPClient()
    mcp_mode = await mcp.initialize()
    indexes, idx_src = await mcp.list_indexes()
    spl_sample, spl_src = await mcp.generate_spl("health check volume by service in baseline index")
    count, cnt_src = await mcp.run_search_count(
        f"index={settings.splunk_baseline_index} | stats count"
    )

    latest_analysis = analyses[-1] if analyses else None
    latest_proposal = proposals[-1] if proposals else None

    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "project": {
            "name": "SignalSmith AI",
            "version": "2.1.0",
            "tagline": "Cut telemetry cost without cutting incident coverage.",
            "repository": str(ROOT),
        },
        "environment": {
            "splunk_host": settings.splunk_host,
            "splunk_web_port": settings.splunk_web_port,
            "splunk_api_port": settings.splunk_api_port,
            "splunk_baseline_index": settings.splunk_baseline_index,
            "splunk_candidate_index": settings.splunk_candidate_index,
            "signalsmith_mode": settings.signalsmith_mode,
            "mcp_endpoint": mcp.endpoint,
        },
        "runtime_meta": meta,
        "splunk_health": splunk_report,
        "mcp": {
            "mode": mcp_mode,
            "status": mcp.status_dict(),
            "indexes_discovered": len(indexes),
            "index_source": idx_src,
            "generate_spl_sample": {"spl": spl_sample, "source": spl_src},
            "baseline_count_query": {"count": count, "source": cnt_src},
        },
        "saved_searches_catalog": saved_search_catalog(),
        "datasets": {
            "baseline": _event_summary(baseline),
            "candidate": _event_summary(candidate),
            "baseline_events_full": baseline,
            "candidate_events_full": candidate,
        },
        "analyses": analyses,
        "proposals": proposals,
        "validations": validations,
        "audit_trail": audit,
        "summary": {
            "analysis_count": len(analyses),
            "proposal_count": len(proposals),
            "validation_count": len(validations),
            "audit_entry_count": len(audit),
            "baseline_events": len(baseline),
            "candidate_events": len(candidate),
            "latest_analysis_id": latest_analysis.get("id") if latest_analysis else None,
            "latest_analysis_status": latest_analysis.get("status") if latest_analysis else None,
            "latest_proposal_id": latest_proposal.get("id") if latest_proposal else None,
            "latest_proposal_status": latest_proposal.get("status") if latest_proposal else None,
            "splunk_connected": splunk_report.get("rest_api", {}).get("reachable", False),
            "official_mcp_installed": mcp.is_mcp,
            "mcp_bridge_active": mcp.status_dict().get("bridge_active", False),
        },
    }


def render_markdown(data: dict) -> str:
    s = data["summary"]
    splunk = data["splunk_health"]
    mcp = data["mcp"]
    baseline = data["datasets"]["baseline"]
    candidate = data["datasets"]["candidate"]
    lines = [
        "# SignalSmith AI — POC Results",
        "",
        f"**Exported:** {data['exported_at']}",
        f"**Project:** {data['project']['name']} v{data['project']['version']}",
        "",
        "## Executive Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Splunk REST connected | {s['splunk_connected']} |",
        f"| Official MCP installed | {s['official_mcp_installed']} |",
        f"| MCP REST bridge active | {s['mcp_bridge_active']} |",
        f"| Baseline events (local) | {s['baseline_events']:,} |",
        f"| Candidate events (local) | {s['candidate_events']:,} |",
        f"| Analyses run | {s['analysis_count']} |",
        f"| Validations run | {s['validation_count']} |",
        f"| Latest analysis | {s['latest_analysis_status'] or '—'} |",
        f"| Latest proposal | {s['latest_proposal_status'] or '—'} |",
        "",
        "## Splunk Integration",
        "",
        f"- **Host:** {data['environment']['splunk_host']}:{data['environment']['splunk_api_port']}",
        f"- **Web UI:** https://localhost:{data['environment']['splunk_web_port']}",
        f"- **Baseline index:** `{data['environment']['splunk_baseline_index']}`",
        f"- **Candidate index:** `{data['environment']['splunk_candidate_index']}`",
        f"- **Ingest mode:** {splunk.get('ingest_mode', '—')}",
        "",
        "### Index event counts (Splunk)",
        "",
    ]

    for idx, info in splunk.get("indexes", {}).items():
        lines.append(f"- `{idx}`: exists={info.get('exists')}, events={info.get('event_count', '—')}")

    lines.extend([
        "",
        "## MCP Server",
        "",
        f"- **Mode:** {mcp['mode']}",
        f"- **Endpoint:** {mcp['status'].get('endpoint')}",
        f"- **Official MCP:** {mcp['status'].get('available')}",
        f"- **Bridge active:** {mcp['status'].get('bridge_active')}",
        f"- **Indexes via MCP/bridge:** {mcp['indexes_discovered']}",
        "",
        "### generate_spl sample",
        "",
        f"```spl",
        mcp["generate_spl_sample"]["spl"],
        "```",
        f"Source: `{mcp['generate_spl_sample']['source']}`",
        "",
        f"### Baseline count via run_splunk_query",
        "",
        f"- Count: **{mcp['baseline_count_query']['count']:,}**",
        f"- Source: `{mcp['baseline_count_query']['source']}`",
        "",
        "## Dataset Summary",
        "",
        "### Baseline",
        "",
        f"- Events: {baseline['count']:,}",
        f"- Bytes: {baseline['total_bytes']:,}",
        f"- Services: {json.dumps(baseline['services'])}",
        "",
        "### Candidate",
        "",
        f"- Events: {candidate['count']:,}",
        f"- Bytes: {candidate['total_bytes']:,}",
        f"- Services: {json.dumps(candidate['services'])}",
        "",
    ])

    if data["validations"]:
        lines.append("## Validation Results")
        lines.append("")
        for v in data["validations"]:
            lines.extend([
                f"### Run {v.get('run_number')} — {v.get('status')}",
                "",
                f"- Event reduction: {v.get('event_reduction_percent')}%",
                f"- Byte reduction: {v.get('byte_reduction_percent')}%",
                f"- Coverage: {v.get('coverage_percent')}%",
                f"- Tests passed: {v.get('tests_passed')}/{v.get('tests_total')}",
                f"- Protected events lost: {v.get('protected_events_lost')}",
                f"- Deliberate failure: {v.get('deliberate_failure')}",
                "",
            ])
            if v.get("coverage_results"):
                lines.append("| Search | Baseline | Candidate | Passed | Method |")
                lines.append("|--------|----------|-----------|--------|--------|")
                for r in v["coverage_results"]:
                    lines.append(
                        f"| {r.get('search_name')} | {r.get('baseline_count')} | "
                        f"{r.get('candidate_count')} | {r.get('passed')} | {r.get('validation_method', '—')} |"
                    )
                lines.append("")

    if data["proposals"]:
        p = data["proposals"][-1]
        lines.extend([
            "## Latest Proposal",
            "",
            f"- ID: `{p.get('id')}`",
            f"- Status: {p.get('status')}",
            f"- Reduction estimate: {p.get('total_reduction_percent')}%",
            f"- Recommendations: {len(p.get('recommendations', []))}",
            "",
        ])
        for rec in p.get("recommendations", [])[:10]:
            lines.append(f"- **{rec.get('action')}** — {rec.get('condition')} (risk: {rec.get('risk_level')})")
        lines.append("")

    lines.extend([
        "## Audit Trail (last 15)",
        "",
        "| Time | Actor | Action | Source |",
        "|------|-------|--------|--------|",
    ])
    for entry in data["audit_trail"][-15:]:
        lines.append(
            f"| {entry.get('timestamp', '')[:19]} | {entry.get('actor')} | "
            f"{entry.get('action')} | {entry.get('source')} |"
        )

    lines.extend([
        "",
        "## Files",
        "",
        "- Full JSON export: `poc_results.json`",
        "- Compact summary JSON: `poc_results_summary.json`",
        "",
        "## Next Steps",
        "",
        "1. Install Splunk MCP Server (app 7931): `.\\scripts\\install_mcp.ps1`",
        "2. Run the full pipeline from the Command Center or `POST /api/session/run-pipeline`",
        "3. Review validation results and export approved OpenTelemetry configuration",
        "",
    ])
    return "\n".join(lines)


async def main() -> None:
    data = await collect_poc_data()

    json_path = ROOT / "poc_results.json"
    summary_path = ROOT / "poc_results_summary.json"
    md_path = ROOT / "poc_result.md"

    summary = {k: v for k, v in data.items() if k != "datasets"}
    summary["datasets"] = {
        "baseline": data["datasets"]["baseline"],
        "candidate": data["datasets"]["candidate"],
    }

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)

    md_path.write_text(render_markdown(data), encoding="utf-8")

    print(f"Wrote {json_path} ({json_path.stat().st_size:,} bytes)")
    print(f"Wrote {summary_path} ({summary_path.stat().st_size:,} bytes)")
    print(f"Wrote {md_path}")


if __name__ == "__main__":
    asyncio.run(main())