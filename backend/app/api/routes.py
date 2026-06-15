from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel

from app.api.deps import get_audit, get_orchestrator, get_storage
from app.models.analysis import AnalysisRecord, AnalysisStatus
from app.models.proposals import ProposalStatus
from app.services.job_runner import JobStatus, get_job_runner
from app.services.mcp_client import SplunkMCPClient
from app.services.otel_export import generate_otel_yaml, generate_rollback_yaml
from app.services.saved_searches import saved_search_catalog
from app.config import get_settings
from app.services.agent_catalog import agent_catalog
from app.services.gemini_service import GeminiService
from app.services.splunk_analytics import SplunkAnalyticsService
from app.services.splunk_dashboard import SplunkDashboardService
from app.services.splunk_auth_service import SplunkAuthService
from app.services.splunk_client import SplunkClient
from app.services.splunk_credentials import auth_source, get_splunk_username, reset_splunk_auth, set_splunk_auth
from app.services.splunk_data_service import SplunkDataService
router = APIRouter()


class AnalysisStartResponse(BaseModel):
    analysis_id: str
    status: str


@router.get("/health")
async def health():
    storage = get_storage()
    splunk = SplunkClient()
    connected, mode = await splunk.connect()
    mcp = SplunkMCPClient()
    mcp_mode = await mcp.initialize()
    connection = mcp_mode if mcp.is_mcp else (mode if connected else "offline")
    return {
        "status": "healthy",
        "service": "SignalSmith AI",
        "splunk_connection": connection,
        "splunk_connected": connected,
        "tagline": "Cut telemetry cost without cutting incident coverage.",
        "version": "3.0.0",
    }


@router.get("/integrations/status")
async def integrations_status():
    storage = get_storage()
    splunk = SplunkClient()
    mcp = SplunkMCPClient()
    mcp_mode = await mcp.initialize()
    splunk_report = await splunk.health_report()
    mcp_status = mcp.status_dict()
    connected, splunk_mode = await splunk.connect()
    connection = mcp_mode if mcp.is_mcp else (splunk_mode if connected else "offline")
    dash_svc = SplunkDashboardService()
    mcp_app = await dash_svc.check_mcp_app()
    dashboard = await dash_svc.dashboard_status()
    data_source = storage.get_meta("data_source") or "none"
    if mcp.is_mcp:
        connection_reason = "Official Splunk MCP Server — queries and tools run via JSON-RPC at /services/mcp."
        query_engine = "mcp"
    elif connected:
        connection_reason = (
            "Splunk REST API bridge — your Splunk instance is live. "
            "Install MCP Server (app 7931) for hosted AI SPL generation."
        )
        query_engine = "splunk_api"
    else:
        connection_reason = "Splunk unreachable — verify SPLUNK_HOST, credentials, and that Splunk is running."
        query_engine = "offline"
    baseline_local, _ = storage.event_file_stats("baseline_events.json")
    candidate_local, _ = storage.event_file_stats("candidate_events.json")
    return {
        "splunk_connection": connection,
        "splunk": splunk_report,
        "mcp": {**mcp_status, "app_7931": mcp_app},
        "ai": GeminiService().status_dict(),
        "splunk_dashboard": dashboard,
        "saved_searches": len(saved_search_catalog()),
        "data_source": data_source,
        "data_flow": {
            "source_label": (
                "Splunk indexes (live)"
                if data_source == "splunk"
                else "Local session files"
                if data_source == "local_json"
                else "No data loaded"
            ),
            "dataset_generated": storage.get_meta("dataset_generated") or "false",
            "baseline_index": splunk_report.get("baseline_index"),
            "candidate_index": splunk_report.get("candidate_index"),
            "local_baseline_events": baseline_local,
            "local_candidate_events": candidate_local,
            "splunk_baseline_events": splunk_report.get("indexes", {})
            .get(splunk_report.get("baseline_index", ""), {})
            .get("event_count", 0),
            "splunk_candidate_events": splunk_report.get("indexes", {})
            .get(splunk_report.get("candidate_index", ""), {})
            .get("event_count", 0),
        },
        "connection_detail": {
            "mode": connection,
            "query_engine": query_engine,
            "reason": connection_reason,
            "mcp_installed": bool(mcp_app.get("installed")),
            "mcp_reachable": bool(mcp_app.get("mcp_reachable")),
            "indexes_live": connected,
            "telemetry_origin": "splunk_index" if data_source == "splunk" else ("local_json" if data_source else "none"),
        },
        "splunk_auth": {
            "authenticated": connected,
            "username": get_splunk_username() if connected else None,
            "source": auth_source(),
            "web_url": get_settings().splunk_web_base,
            "api_url": get_settings().splunk_api_base,
        },
    }


@router.get("/splunk/auth/status")
async def splunk_auth_status():
    splunk = SplunkClient()
    connected, mode = await splunk.connect()
    settings = get_settings()
    return {
        "authenticated": connected,
        "username": get_splunk_username() if connected else None,
        "source": auth_source(),
        "connection": mode if connected else "offline",
        "web_url": settings.splunk_web_base,
        "api_url": settings.splunk_api_base,
        "host": settings.splunk_host,
    }


@router.post("/splunk/auth/login")
async def splunk_auth_login(body: SplunkLoginRequest):
    ok, message, meta = await SplunkAuthService().verify(body.username, body.password)
    if not ok:
        raise HTTPException(status_code=401, detail=message)
    token = set_splunk_auth(body.username, body.password)
    try:
        splunk = SplunkClient()
        connected, mode = await splunk.connect()
    finally:
        if token is not None:
            reset_splunk_auth(token)
    return {
        "authenticated": True,
        "username": body.username.strip(),
        "message": message,
        "connection": mode if connected else "offline",
        "splunk_connected": connected,
        **meta,
    }


class MCPToolCallRequest(BaseModel):
    name: str
    arguments: dict | None = None


class GenerateSPLRequest(BaseModel):
    query: str


class RunSPLRequest(BaseModel):
    query: str
    earliest: str = "-24h"
    latest: str = "now"


class AIChatRequest(BaseModel):
    message: str
    history: list[dict[str, str]] | None = None
    include_session: bool = True


class AIExplainRequest(BaseModel):
    topic: str
    include_session: bool = True


class SplunkLoginRequest(BaseModel):
    username: str
    password: str


async def _session_context() -> dict:
    storage = get_storage()
    analysis = storage.get_latest_analysis()
    proposal = storage.get_proposal_by_analysis(analysis.id) if analysis else None
    validations = storage.get_validations_for_proposal(proposal.id) if proposal else []
    baseline_count, baseline_bytes = storage.event_file_stats("baseline_events.json")
    candidate_count, candidate_bytes = storage.event_file_stats("candidate_events.json")
    settings = get_settings()
    return {
        "baseline_index": settings.splunk_baseline_index,
        "candidate_index": settings.splunk_candidate_index,
        "baseline_events": baseline_count,
        "baseline_bytes": baseline_bytes,
        "candidate_events": candidate_count,
        "candidate_bytes": candidate_bytes,
        "analysis_id": analysis.id if analysis else None,
        "analysis_status": analysis.status.value if analysis else None,
        "reducible_estimate": analysis.reducible_estimate if analysis else None,
        "proposal_status": proposal.status.value if proposal else None,
        "policy_count": len(proposal.recommendations) if proposal else 0,
        "validation_status": validations[-1].status.value if validations else None,
        "event_reduction_percent": validations[-1].event_reduction_percent if validations else None,
        "coverage_percent": validations[-1].coverage_percent if validations else None,
    }


@router.get("/splunk/mcp-app")
async def splunk_mcp_app_status():
    return await SplunkDashboardService().check_mcp_app()


@router.get("/splunk/dashboard")
async def splunk_dashboard_status():
    return await SplunkDashboardService().dashboard_status()


@router.get("/splunk/dashboard/xml")
async def splunk_dashboard_xml():
    from fastapi.responses import PlainTextResponse

    svc = SplunkDashboardService()
    return PlainTextResponse(svc.dashboard_xml(), media_type="application/xml")


@router.post("/splunk/dashboard/deploy")
async def splunk_dashboard_deploy():
    svc = SplunkDashboardService()
    splunk = SplunkClient()
    connected, _ = await splunk.connect()
    if not connected:
        raise HTTPException(status_code=503, detail="Splunk is not reachable. Connect Splunk before deploying the dashboard.")
    try:
        result = await svc.deploy_dashboard()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    get_audit().record("SplunkDashboard", "deploy", "splunk_api", output_summary=result.get("url", ""))
    return result


@router.get("/splunk/analytics/live")
async def splunk_live_analytics():
    splunk = SplunkClient()
    connected, _ = await splunk.connect()
    if not connected:
        raise HTTPException(status_code=503, detail="Splunk is not reachable.")
    try:
        return await SplunkAnalyticsService().live_dashboard_data()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/agents")
async def list_agents():
    storage = get_storage()
    analysis = storage.get_latest_analysis()
    timeline = analysis.agent_timeline if analysis else []
    active = {t.agent for t in timeline}
    agents = []
    for agent in agent_catalog():
        entry = dict(agent)
        entry["ran_in_session"] = any(
            agent["name"].split()[0].lower() in t.agent.lower() or agent["id"] in t.agent.lower()
            for t in timeline
        ) or agent["id"] in {"signalsmith_mentor", "gemini_copilot"}
        entry["action_count"] = sum(
            1 for t in timeline if agent["name"].split()[0].lower() in t.agent.lower()
        )
        agents.append(entry)
    return {
        "agents": agents,
        "timeline_actions": len(timeline),
        "active_agents": len(active),
    }


@router.get("/ai/status")
async def ai_status():
    return GeminiService().status_dict()


@router.post("/ai/chat")
async def ai_chat(body: AIChatRequest):
    gemini = GeminiService()
    if not gemini.is_configured():
        raise HTTPException(status_code=503, detail="SignalSmith Mentor is offline. SPL templates still work.")
    if not gemini.settings.gemini_enabled:
        raise HTTPException(status_code=503, detail="SignalSmith Mentor is disabled. SPL templates still work.")
    if auth_issue := gemini.auth_issue():
        raise HTTPException(status_code=503, detail=auth_issue)

    context = await _session_context() if body.include_session else None
    try:
        reply = await gemini.chat(body.message, body.history, context)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    get_audit().record(
        "SignalSmithMentor",
        "chat",
        "mentor",
        input_summary=body.message[:200],
        output_summary=reply[:300],
    )
    return {"reply": reply, "model": gemini.model, "source": "mentor"}


@router.post("/ai/explain")
async def ai_explain(body: AIExplainRequest):
    gemini = GeminiService()
    if not gemini.is_configured():
        raise HTTPException(status_code=503, detail="SignalSmith Mentor is offline. SPL templates still work.")
    if auth_issue := gemini.auth_issue():
        raise HTTPException(status_code=503, detail=auth_issue)

    context = await _session_context() if body.include_session else None
    try:
        reply = await gemini.explain(body.topic, context)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    get_audit().record(
        "SignalSmithMentor",
        "explain",
        "mentor",
        input_summary=body.topic[:200],
        output_summary=reply[:300],
    )
    return {"reply": reply, "model": gemini.model, "source": "mentor"}


@router.get("/mcp/status")
async def mcp_status():
    mcp = SplunkMCPClient()
    await mcp.initialize()
    return mcp.status_dict()


@router.get("/mcp/tools")
async def mcp_tools():
    mcp = SplunkMCPClient()
    await mcp.initialize()
    tools = mcp.tools or [{"name": t, "description": f"Splunk MCP tool: {t}"} for t in mcp.status_dict()["official_tools"]]
    return {"tools": tools, "mode": mcp.mode, "official_mcp": mcp.is_mcp}


@router.post("/mcp/tools/call")
async def mcp_call_tool(body: MCPToolCallRequest):
    mcp = SplunkMCPClient()
    await mcp.initialize()
    try:
        result, source = await mcp.call_tool(body.name, body.arguments or {})
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    get_audit().record(
        "MCPClient",
        f"tool_{body.name}",
        source,
        input_summary=str(body.arguments or {}),
        output_summary=str(result)[:300],
    )
    return {"tool": body.name, "source": source, "result": result}


@router.post("/mcp/generate-spl")
async def mcp_generate_spl(body: GenerateSPLRequest):
    mcp = SplunkMCPClient()
    await mcp.initialize()
    try:
        spl, source = await mcp.generate_spl(body.query)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    get_audit().record(
        "MCPClient",
        "generate_spl",
        source,
        input_summary=body.query,
        output_summary=spl[:300],
    )
    return {"spl": spl, "source": source, "query": body.query, "official_mcp": mcp.is_mcp}


@router.post("/mcp/run-query")
async def mcp_run_query(body: RunSPLRequest):
    mcp = SplunkMCPClient()
    await mcp.initialize()
    result, source = await mcp.run_splunk_query(body.query, body.earliest, body.latest)
    get_audit().record(
        "MCPClient",
        "run_splunk_query",
        source,
        input_summary=body.query[:200],
        output_summary=str(result)[:300],
    )
    return {"source": source, "result": result, "query": body.query}


@router.get("/analyses")
async def list_analyses(limit: int = 20):
    storage = get_storage()
    analyses = storage.list_analyses(limit=limit)
    return {
        "analyses": [
            {
                "id": a.id,
                "status": a.status.value,
                "mode": a.mode,
                "baseline_event_count": a.baseline_event_count,
                "reducible_estimate": a.reducible_estimate,
                "created": a.agent_timeline[0].timestamp if a.agent_timeline else None,
            }
            for a in analyses
        ]
    }


@router.get("/saved-searches")
async def list_saved_searches():
    return {"saved_searches": saved_search_catalog()}


@router.get("/comparison/{analysis_id}")
async def get_comparison(analysis_id: str):
    storage = get_storage()
    analysis = storage.get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    proposal = storage.get_proposal_by_analysis(analysis_id)
    baseline_count, baseline_bytes = storage.event_file_stats("baseline_events.json")
    candidate_count, candidate_bytes = storage.event_file_stats("candidate_events.json")
    validations = storage.get_validations_for_proposal(proposal.id) if proposal else []
    final = validations[-1] if validations else None
    profile = analysis.profile_summary or {}
    return {
        "analysis_id": analysis_id,
        "baseline": {"events": baseline_count, "bytes": baseline_bytes},
        "candidate": {"events": candidate_count, "bytes": candidate_bytes},
        "event_reduction_percent": final.event_reduction_percent if final else None,
        "byte_reduction_percent": final.byte_reduction_percent if final else None,
        "coverage_percent": final.coverage_percent if final else None,
        "tests_passed": final.tests_passed if final else None,
        "tests_total": final.tests_total if final else None,
        "by_service": profile.get("by_service", {}),
        "by_scenario": profile.get("by_scenario", {}),
    }


@router.get("/jobs")
async def list_jobs(limit: int = 20):
    return {"jobs": [j.model_dump() for j in get_job_runner().list_jobs(limit)]}


@router.get("/jobs/{job_id}")
async def get_job(job_id: str):
    job = get_job_runner().get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/jobs/{job_id}/stream")
async def stream_job(job_id: str):
    import asyncio
    import json

    async def event_generator():
        while True:
            job = get_job_runner().get(job_id)
            if not job:
                yield f"data: {json.dumps({'error': 'not found'})}\n\n"
                break
            payload = job.model_dump()
            yield f"data: {json.dumps(payload)}\n\n"
            if job.status in {JobStatus.COMPLETED, JobStatus.FAILED}:
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/session/status")
async def session_status():
    storage = get_storage()
    analysis = storage.get_latest_analysis()
    proposal = storage.get_proposal_by_analysis(analysis.id) if analysis else None
    validations = storage.get_validations_for_proposal(proposal.id) if proposal else []
    baseline_count, baseline_bytes = storage.event_file_stats("baseline_events.json")
    candidate_count, candidate_bytes = storage.event_file_stats("candidate_events.json")
    settings = get_settings()
    splunk_counts = {}
    try:
        data_svc = SplunkDataService()
        if await data_svc.connect():
            for idx in (settings.splunk_baseline_index, settings.splunk_candidate_index):
                cnt, _ = await data_svc.index_event_count(idx)
                splunk_counts[idx] = cnt
    except Exception:
        pass

    splunk = SplunkClient()
    connected, splunk_mode = await splunk.connect()
    mcp = SplunkMCPClient()
    mcp_mode = await mcp.initialize()
    connection = mcp_mode if mcp.is_mcp else (splunk_mode if connected else "offline")

    data_source = storage.get_meta("data_source") or "none"
    source_labels = {
        "splunk": "Splunk indexes (live)",
        "local_json": "Local session files",
        "none": "No data loaded",
    }
    return {
        "has_data": baseline_count > 0 or bool(splunk_counts),
        "splunk_connected": connected,
        "splunk_connection": connection,
        "data_source": data_source,
        "data_flow": {
            "source_label": source_labels.get(data_source, data_source),
            "dataset_generated": storage.get_meta("dataset_generated") or "false",
            "splunk_connection_meta": storage.get_meta("splunk_connection") or connection,
            "baseline_index": settings.splunk_baseline_index,
            "candidate_index": settings.splunk_candidate_index,
            "local_baseline_events": baseline_count,
            "local_candidate_events": candidate_count,
            "local_baseline_bytes": baseline_bytes,
            "local_candidate_bytes": candidate_bytes,
            "splunk_baseline_events": splunk_counts.get(settings.splunk_baseline_index, 0),
            "splunk_candidate_events": splunk_counts.get(settings.splunk_candidate_index, 0),
        },
        "baseline_event_count": baseline_count,
        "baseline_bytes": baseline_bytes,
        "candidate_event_count": candidate_count,
        "candidate_bytes": candidate_bytes,
        "splunk_index_counts": splunk_counts,
        "analysis": analysis,
        "proposal": proposal,
        "validations": validations,
    }


@router.post("/session/bootstrap")
@router.get("/session/bootstrap")
async def session_bootstrap():
    """Load real telemetry from Splunk baseline index for analysis."""
    storage = get_storage()
    audit = get_audit()
    settings = get_settings()

    if settings.require_splunk:
        splunk = SplunkClient()
        connected, _ = await splunk.connect()
        if not connected:
            raise HTTPException(
                status_code=503,
                detail="Splunk is required. Connect Splunk and ensure baseline index has data.",
            )

    try:
        data_svc = SplunkDataService()
        result = await data_svc.bootstrap_baseline()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Bootstrap failed: {exc}") from exc

    events = result["events"]
    if not events:
        raise HTTPException(status_code=400, detail="No events exported from Splunk baseline index.")

    storage.save_events("baseline_events.json", events)
    storage.set_meta("dataset_generated", "true")
    storage.set_meta("data_source", "splunk")
    storage.set_meta("splunk_connection", result["splunk_mode"])

    audit.record(
        "SplunkDataService",
        "bootstrap_baseline",
        result["export_source"],
        input_summary=f"index={result['index']}, splunk_count={result['event_count']}",
        output_summary=f"exported={len(events)}, profile_source={result['profile_source']}",
    )

    return {
        "status": "bootstrapped",
        "index": result["index"],
        "splunk_event_count": result["event_count"],
        "exported_events": len(events),
        "export_source": result["export_source"],
        "profile_source": result["profile_source"],
        "mode": result["splunk_mode"],
    }


@router.post("/session/reset")
async def session_reset():
    storage = get_storage()
    audit = get_audit()
    storage.reset_all()
    audit.record("user", "session_reset", "api", output_summary="Session state cleared")
    return {"status": "reset", "message": "Session state cleared"}


async def _do_ingest(index_key: str, filename: str, progress_cb) -> dict:
    storage = get_storage()
    audit = get_audit()
    events = storage.load_events(filename)
    if not events:
        raise ValueError("No events to ingest")

    progress_cb(0.05, f"Connecting to Splunk ({len(events)} events)...")
    splunk = SplunkClient()
    connected, mode = await splunk.connect()
    if not connected:
        raise ValueError("Splunk is not reachable. Connect Splunk before ingesting.")
    storage.set_meta("splunk_connection", mode)
    index = (
        splunk.settings.splunk_baseline_index
        if index_key == "baseline"
        else splunk.settings.splunk_candidate_index
    )
    progress_cb(0.1, "Ensuring indexes exist...")
    await splunk.ensure_indexes()
    progress_cb(0.15, f"Ingesting to {index}...")
    ingested, ingest_mode = await splunk.ingest_events(index, events)
    progress_cb(0.95, f"Ingested {ingested} events")

    audit.record(
        "SplunkClient",
        f"ingest_{index_key}",
        ingest_mode,
        input_summary=f"events={len(events)}",
        output_summary=f"ingested={ingested}, mode={ingest_mode}",
    )
    return {
        "status": "ingested",
        "event_count": len(events),
        "ingested": ingested,
        "mode": ingest_mode,
        "index": index,
    }


@router.post("/session/ingest-candidate")
async def ingest_candidate(async_job: bool = False):
    storage = get_storage()
    if not storage.load_events("candidate_events.json"):
        raise HTTPException(status_code=400, detail="Apply proposal first")

    if async_job:
        job = get_job_runner().start(
            "ingest-candidate",
            lambda cb: _do_ingest("candidate", "candidate_events.json", cb),
        )
        return {"job_id": job.id, "status": "started"}

    try:
        return await _do_ingest("candidate", "candidate_events.json", lambda _p, _m: None)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


async def _execute_full_pipeline(progress_cb) -> dict:
    """Production pipeline: bootstrap → analyze → apply → validate → approve."""
    storage = get_storage()
    progress_cb(0.02, "Loading telemetry from Splunk...")
    try:
        await session_bootstrap()
    except HTTPException as exc:
        raise RuntimeError(str(exc.detail)) from exc
    progress_cb(0.15, "Running multi-agent analysis...")
    orchestrator = get_orchestrator()
    record = AnalysisRecord(status=AnalysisStatus.PENDING)
    storage.save_analysis(record)
    completed = await orchestrator.run_analysis(record.id)
    proposal = storage.get_proposal_by_analysis(completed.id)
    if not proposal:
        raise RuntimeError("Analysis completed without proposal")
    progress_cb(0.55, "Applying optimization policies...")
    await orchestrator.apply_proposal(proposal.id)
    progress_cb(0.75, "Running shadow validation...")
    validation = await orchestrator.run_validation(proposal.id)
    if validation.status.value != "passed":
        progress_cb(0.85, "Revising policies after validation...")
        revised, validation = await orchestrator.revise_and_revalidate(validation.id)
        proposal = revised
    if validation.status.value == "passed":
        proposal.status = ProposalStatus.APPROVED
        for rec in proposal.recommendations:
            rec.approval_status = "approved"
        storage.save_proposal(proposal)
    progress_cb(
        1.0,
        f"Complete — {validation.event_reduction_percent}% reduction, "
        f"{validation.coverage_percent}% detection coverage",
    )
    return {
        "analysis_id": completed.id,
        "proposal_id": proposal.id,
        "validation_status": validation.status.value,
        "event_reduction_percent": validation.event_reduction_percent,
        "coverage_percent": validation.coverage_percent,
    }


@router.post("/session/run")
async def run_full_session(async_job: bool = False):
    if async_job:
        job = get_job_runner().start("full-pipeline", _execute_full_pipeline)
        return {"job_id": job.id, "status": "started"}

    try:
        return await _execute_full_pipeline(lambda _p, _m: None)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {exc}") from exc


@router.post("/analysis/start", response_model=AnalysisStartResponse)
async def start_analysis():
    storage = get_storage()
    events = storage.load_events("baseline_events.json")
    if not events:
        raise HTTPException(
            status_code=400,
            detail="Bootstrap from Splunk first (POST /api/session/bootstrap).",
        )

    record = AnalysisRecord(status=AnalysisStatus.PENDING)
    storage.save_analysis(record)
    orchestrator = get_orchestrator()
    completed = await orchestrator.run_analysis(record.id)
    return AnalysisStartResponse(analysis_id=completed.id, status=completed.status.value)


@router.get("/analysis/{analysis_id}")
async def get_analysis(analysis_id: str):
    storage = get_storage()
    record = storage.get_analysis(analysis_id)
    if not record:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return record


@router.get("/analysis/{analysis_id}/events")
async def get_analysis_events(analysis_id: str):
    storage = get_storage()
    record = storage.get_analysis(analysis_id)
    if not record:
        raise HTTPException(status_code=404, detail="Analysis not found")
    profile = record.profile_summary or {}
    return {
        "analysis_id": analysis_id,
        "service_distribution": profile.get("service_distribution", []),
        "category_distribution": profile.get("category_distribution", []),
        "patterns": profile.get("patterns", [])[:20],
    }


@router.get("/proposals/{analysis_id}")
async def get_proposal_by_analysis(analysis_id: str):
    storage = get_storage()
    proposal = storage.get_proposal_by_analysis(analysis_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return proposal


@router.post("/proposals/{proposal_id}/apply")
async def apply_proposal(proposal_id: str):
    orchestrator = get_orchestrator()
    try:
        proposal = await orchestrator.apply_proposal(proposal_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    candidate_count, candidate_bytes = get_storage().event_file_stats("candidate_events.json")
    return {
        "proposal_id": proposal.id,
        "status": proposal.status.value,
        "candidate_event_count": candidate_count,
        "candidate_bytes": candidate_bytes,
    }


@router.post("/validation/{proposal_id}/run")
async def run_validation(proposal_id: str):
    orchestrator = get_orchestrator()
    try:
        validation = await orchestrator.run_validation(proposal_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return validation


@router.get("/validation/{validation_id}")
async def get_validation(validation_id: str):
    storage = get_storage()
    record = storage.get_validation(validation_id)
    if not record:
        raise HTTPException(status_code=404, detail="Validation not found")
    return record


@router.post("/validation/{validation_id}/revise")
async def revise_validation(validation_id: str):
    orchestrator = get_orchestrator()
    try:
        proposal, validation = await orchestrator.revise_and_revalidate(validation_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "proposal": proposal,
        "validation": validation,
        "message": "Policy revised and second validation completed",
    }


@router.post("/proposals/{proposal_id}/approve")
async def approve_proposal(proposal_id: str):
    storage = get_storage()
    audit = get_audit()
    proposal = storage.get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    proposal.status = ProposalStatus.APPROVED
    for rec in proposal.recommendations:
        rec.approval_status = "approved"
    storage.save_proposal(proposal)
    audit.record("user", "approve_proposal", "user", proposal_id=proposal_id, analysis_id=proposal.analysis_id)
    return {"status": "approved", "proposal_id": proposal_id}


@router.post("/proposals/{proposal_id}/reject")
async def reject_proposal(proposal_id: str):
    storage = get_storage()
    audit = get_audit()
    proposal = storage.get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    proposal.status = ProposalStatus.REJECTED
    for rec in proposal.recommendations:
        rec.approval_status = "rejected"
    storage.save_proposal(proposal)
    audit.record("user", "reject_proposal", "user", proposal_id=proposal_id, analysis_id=proposal.analysis_id)
    return {"status": "rejected", "proposal_id": proposal_id}


@router.get("/proposals/{proposal_id}/export/otel")
async def export_otel(proposal_id: str):
    storage = get_storage()
    proposal = storage.get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    content = generate_otel_yaml(proposal)
    return PlainTextResponse(content, media_type="application/x-yaml")


@router.get("/proposals/{proposal_id}/export/rollback")
async def export_rollback(proposal_id: str):
    storage = get_storage()
    proposal = storage.get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    content = generate_rollback_yaml(proposal)
    return PlainTextResponse(content, media_type="application/x-yaml")


@router.get("/audit")
async def list_audit():
    audit = get_audit()
    return {"entries": audit.list_entries()}