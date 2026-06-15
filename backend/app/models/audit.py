from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AuditEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    actor: str
    action: str
    source: str
    input_summary: str = ""
    output_summary: str = ""
    analysis_id: str | None = None
    proposal_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)