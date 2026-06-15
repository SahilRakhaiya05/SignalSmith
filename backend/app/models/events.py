from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TelemetryEvent(BaseModel):
    timestamp: str
    service: str
    environment: str = "production"
    level: str
    event_type: str
    message: str
    trace_id: str
    user_id: str | None = None
    http_method: str | None = None
    http_route: str | None = None
    http_status: int | None = None
    duration_ms: int | None = None
    source_ip: str | None = None
    country: str | None = None
    is_privileged: bool = False
    scenario: str
    estimated_size_bytes: int

    def to_splunk_payload(self) -> dict[str, Any]:
        return self.model_dump()