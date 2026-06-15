from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ValidationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    REVISED = "revised"


class SearchCoverageResult(BaseModel):
    search_id: str
    search_name: str
    baseline_count: int
    candidate_count: int
    baseline_triggered: bool
    candidate_triggered: bool
    passed: bool
    importance: str = "high"
    detail: str = ""
    validation_method: str = "local"


class ValidationRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    proposal_id: str
    run_number: int = 1
    status: ValidationStatus = ValidationStatus.PENDING
    mode: str = "offline"
    baseline_event_count: int = 0
    candidate_event_count: int = 0
    event_reduction_percent: float = 0.0
    byte_reduction_percent: float = 0.0
    coverage_percent: float = 0.0
    protected_events_lost: int = 0
    tests_passed: int = 0
    tests_total: int = 0
    final_risk_level: str = "medium"
    coverage_results: list[SearchCoverageResult] = Field(default_factory=list)
    deliberate_failure: bool = False
    failure_reason: str | None = None
    revision_applied: bool = False
    revision_detail: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)