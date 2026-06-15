from __future__ import annotations

from app.models.audit import AuditEntry
from app.services.storage import Storage


class AuditLogService:
    def __init__(self, storage: Storage) -> None:
        self.storage = storage

    def record(
        self,
        actor: str,
        action: str,
        source: str,
        input_summary: str = "",
        output_summary: str = "",
        analysis_id: str | None = None,
        proposal_id: str | None = None,
        metadata: dict | None = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            actor=actor,
            action=action,
            source=source,
            input_summary=input_summary,
            output_summary=output_summary,
            analysis_id=analysis_id,
            proposal_id=proposal_id,
            metadata=metadata or {},
        )
        self.storage.add_audit(entry)
        return entry

    def list_entries(self, limit: int = 500) -> list[AuditEntry]:
        return self.storage.list_audit(limit=limit)