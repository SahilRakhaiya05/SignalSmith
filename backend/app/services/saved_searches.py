from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from app.config import get_settings
from app.models.events import TelemetryEvent

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class SavedSearchDefinition:
    id: str
    name: str
    description: str
    spl_template: str
    importance: str
    trigger_threshold: int = 1
    matcher: Callable[[TelemetryEvent], bool] | None = None
    source: str = "builtin"

    def spl_for_index(self, index: str) -> str:
        return self.spl_template.replace("$INDEX$", index)


def _match_payment_outage(event: TelemetryEvent) -> bool:
    return (
        event.service == "payment-service"
        and event.scenario == "payment_outage"
        and (event.level == "ERROR" or (event.http_status or 0) >= 500)
    )


def _match_high_http_errors(event: TelemetryEvent) -> bool:
    return (event.http_status or 0) >= 500


def _match_slow_payment(event: TelemetryEvent) -> bool:
    return event.service == "payment-service" and (event.duration_ms or 0) >= 1500


def _match_credential_stuffing(event: TelemetryEvent) -> bool:
    return event.scenario == "credential_stuffing" or (
        event.service == "auth-service"
        and event.event_type == "failed_login"
        and event.http_status == 401
    )


def _match_privileged_anomaly(event: TelemetryEvent) -> bool:
    return event.is_privileged and event.service == "auth-service" and event.event_type == "login"


DEMO_SAVED_SEARCHES: list[SavedSearchDefinition] = [
    SavedSearchDefinition(
        id="payment_outage",
        name="Payment Outage Detection",
        description="Detects payment-service errors during outage scenarios",
        spl_template='index=$INDEX$ service="payment-service" (level="ERROR" OR http_status>=500) scenario="payment_outage"',
        importance="critical",
        trigger_threshold=1,
        matcher=_match_payment_outage,
        source="demo",
    ),
    SavedSearchDefinition(
        id="high_http_error_rate",
        name="High HTTP Error Rate",
        description="Detects elevated HTTP 5xx responses across all services",
        spl_template="index=$INDEX$ http_status>=500",
        importance="high",
        trigger_threshold=5,
        matcher=_match_high_http_errors,
        source="demo",
    ),
    SavedSearchDefinition(
        id="slow_payment_requests",
        name="Slow Payment Requests",
        description="Detects payment requests with duration >= 1500ms",
        spl_template='index=$INDEX$ service="payment-service" duration_ms>=1500',
        importance="high",
        trigger_threshold=1,
        matcher=_match_slow_payment,
        source="demo",
    ),
    SavedSearchDefinition(
        id="credential_stuffing",
        name="Credential Stuffing Detection",
        description="Detects credential stuffing attack patterns",
        spl_template='index=$INDEX$ scenario="credential_stuffing" OR (service="auth-service" event_type="failed_login" http_status=401)',
        importance="critical",
        trigger_threshold=3,
        matcher=_match_credential_stuffing,
        source="demo",
    ),
    SavedSearchDefinition(
        id="privileged_user_anomaly",
        name="Privileged User Login Anomaly",
        description="Detects privileged user authentication events",
        spl_template='index=$INDEX$ is_privileged=true service="auth-service" event_type="login"',
        importance="critical",
        trigger_threshold=1,
        matcher=_match_privileged_anomaly,
        source="demo",
    ),
]

# Back-compat alias
SAVED_SEARCHES = DEMO_SAVED_SEARCHES

_custom_cache: list[SavedSearchDefinition] | None = None


def _detections_file_path() -> Path | None:
    settings = get_settings()
    if settings.signalsmith_detections_file:
        return Path(settings.signalsmith_detections_file)
    default = _REPO_ROOT / "config" / "detections.json"
    return default if default.exists() else None


def load_custom_detections() -> list[SavedSearchDefinition]:
    path = _detections_file_path()
    if not path or not path.exists():
        return []

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        items = raw if isinstance(raw, list) else raw.get("detections", [])
        results: list[SavedSearchDefinition] = []
        for item in items:
            if not item.get("id") or not item.get("spl_template"):
                continue
            results.append(
                SavedSearchDefinition(
                    id=str(item["id"]),
                    name=str(item.get("name", item["id"])),
                    description=str(item.get("description", "")),
                    spl_template=str(item["spl_template"]),
                    importance=str(item.get("importance", "high")),
                    trigger_threshold=int(item.get("trigger_threshold", 1)),
                    matcher=None,
                    source="custom",
                )
            )
        return results
    except Exception as exc:
        logger.warning("Failed to load custom detections from %s: %s", path, exc)
        return []


def get_active_saved_searches(*, reload: bool = False) -> list[SavedSearchDefinition]:
    global _custom_cache
    settings = get_settings()

    if reload or _custom_cache is None:
        _custom_cache = load_custom_detections()

    merged: dict[str, SavedSearchDefinition] = {}
    for search in _custom_cache:
        merged[search.id] = search
    if settings.signalsmith_include_demo_detections:
        for search in DEMO_SAVED_SEARCHES:
            merged.setdefault(search.id, search)

    if not merged:
        return list(DEMO_SAVED_SEARCHES)
    return list(merged.values())


def event_matches_search(event: TelemetryEvent, search: SavedSearchDefinition) -> bool:
    if search.matcher:
        return search.matcher(event)
    return False


def run_saved_search(events: list[TelemetryEvent], search: SavedSearchDefinition) -> int:
    if not search.matcher:
        return 0
    return sum(1 for e in events if event_matches_search(e, search))


def saved_search_catalog() -> list[dict[str, Any]]:
    return [
        {
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "spl_template": s.spl_template,
            "importance": s.importance,
            "trigger_threshold": s.trigger_threshold,
            "source": s.source,
        }
        for s in get_active_saved_searches()
    ]