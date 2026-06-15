from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AnalysisStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentAction(BaseModel):
    timestamp: str
    agent: str
    action: str
    source: str
    detail: str
    status: str = "success"


class AnalysisRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    status: AnalysisStatus = AnalysisStatus.PENDING
    mode: str = "offline"
    progress: float = 0.0
    message: str = ""
    baseline_event_count: int = 0
    baseline_bytes: int = 0
    services: list[str] = Field(default_factory=list)
    event_types: list[str] = Field(default_factory=list)
    saved_searches: list[dict[str, Any]] = Field(default_factory=list)
    reducible_estimate: int = 0
    profile_summary: dict[str, Any] = Field(default_factory=dict)
    protection_map: list[dict[str, Any]] = Field(default_factory=list)
    agent_timeline: list[AgentAction] = Field(default_factory=list)
    error: str | None = None