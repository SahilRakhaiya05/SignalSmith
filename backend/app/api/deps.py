from __future__ import annotations

from functools import lru_cache

from app.services.analysis_orchestrator import AnalysisOrchestrator
from app.services.audit_log import AuditLogService
from app.services.storage import Storage


_storage: Storage | None = None


def get_storage() -> Storage:
    global _storage
    if _storage is None:
        _storage = Storage()
    return _storage


def set_storage(storage: Storage) -> None:
    global _storage
    _storage = storage


def get_audit() -> AuditLogService:
    return AuditLogService(get_storage())


def get_orchestrator() -> AnalysisOrchestrator:
    return AnalysisOrchestrator(get_storage())