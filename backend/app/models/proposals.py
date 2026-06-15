from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ProposalStatus(str, Enum):
    DRAFT = "draft"
    APPLIED = "applied"
    APPROVED = "approved"
    REJECTED = "rejected"


class PolicyRecommendation(BaseModel):
    id: str
    action: str
    condition: str
    affected_event_count: int
    estimated_reduction: int
    risk_level: str
    reasoning: str
    spl_query: str
    affected_saved_searches: list[str] = Field(default_factory=list)
    approval_status: str = "pending"
    parameters: dict[str, Any] = Field(default_factory=dict)


class ProposalRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    analysis_id: str
    status: ProposalStatus = ProposalStatus.DRAFT
    version: int = 1
    recommendations: list[PolicyRecommendation] = Field(default_factory=list)
    total_reduction_estimate: int = 0
    total_reduction_percent: float = 0.0
    intentional_demo_failure: bool = False
    notes: str = ""