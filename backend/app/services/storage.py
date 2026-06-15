from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.models.analysis import AnalysisRecord
from app.models.audit import AuditEntry
from app.models.events import TelemetryEvent
from app.models.proposals import ProposalRecord
from app.models.validation import ValidationRecord


class Storage:
    def __init__(self, data_dir: Path | None = None) -> None:
        settings = get_settings()
        self.data_dir = data_dir or settings.data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "signalsmith.db"
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS audit (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS analyses (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS proposals (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS validations (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )

    def reset_all(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                "DELETE FROM audit; DELETE FROM analyses; DELETE FROM proposals; DELETE FROM validations; DELETE FROM meta;"
            )
        for name in ("baseline_events.json", "candidate_events.json"):
            path = self.data_dir / name
            if path.exists():
                path.unlink()

    def set_meta(self, key: str, value: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
                (key, value),
            )

    def get_meta(self, key: str, default: str = "") -> str:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def add_audit(self, entry: AuditEntry) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO audit(id, data) VALUES (?, ?)",
                (entry.id, entry.model_dump_json()),
            )

    def list_audit(self, limit: int = 500) -> list[AuditEntry]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT data FROM audit ORDER BY rowid DESC LIMIT ?", (limit,)
            ).fetchall()
        return [AuditEntry.model_validate_json(r["data"]) for r in rows]

    def save_analysis(self, record: AnalysisRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO analyses(id, data) VALUES (?, ?)",
                (record.id, record.model_dump_json()),
            )

    def get_analysis(self, analysis_id: str) -> AnalysisRecord | None:
        with self._connect() as conn:
            row = conn.execute("SELECT data FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
        return AnalysisRecord.model_validate_json(row["data"]) if row else None

    def list_analyses(self, limit: int = 20) -> list[AnalysisRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT data FROM analyses ORDER BY rowid DESC LIMIT ?", (limit,)
            ).fetchall()
        return [AnalysisRecord.model_validate_json(r["data"]) for r in rows]

    def get_latest_analysis(self) -> AnalysisRecord | None:
        with self._connect() as conn:
            rows = conn.execute("SELECT data FROM analyses ORDER BY rowid DESC").fetchall()
        for row in rows:
            record = AnalysisRecord.model_validate_json(row["data"])
            if record.status.value == "completed":
                return record
        return AnalysisRecord.model_validate_json(rows[0]["data"]) if rows else None

    def save_proposal(self, record: ProposalRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO proposals(id, data) VALUES (?, ?)",
                (record.id, record.model_dump_json()),
            )

    def get_proposal(self, proposal_id: str) -> ProposalRecord | None:
        with self._connect() as conn:
            row = conn.execute("SELECT data FROM proposals WHERE id = ?", (proposal_id,)).fetchone()
        return ProposalRecord.model_validate_json(row["data"]) if row else None

    def get_proposal_by_analysis(self, analysis_id: str) -> ProposalRecord | None:
        with self._connect() as conn:
            rows = conn.execute("SELECT data FROM proposals").fetchall()
        for row in rows:
            proposal = ProposalRecord.model_validate_json(row["data"])
            if proposal.analysis_id == analysis_id:
                return proposal
        return None

    def save_validation(self, record: ValidationRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO validations(id, data) VALUES (?, ?)",
                (record.id, record.model_dump_json()),
            )

    def get_validation(self, validation_id: str) -> ValidationRecord | None:
        with self._connect() as conn:
            row = conn.execute("SELECT data FROM validations WHERE id = ?", (validation_id,)).fetchone()
        return ValidationRecord.model_validate_json(row["data"]) if row else None

    def get_validations_for_proposal(self, proposal_id: str) -> list[ValidationRecord]:
        with self._connect() as conn:
            rows = conn.execute("SELECT data FROM validations").fetchall()
        results = []
        for row in rows:
            record = ValidationRecord.model_validate_json(row["data"])
            if record.proposal_id == proposal_id:
                results.append(record)
        return sorted(results, key=lambda r: r.run_number)

    def save_events(self, filename: str, events: list[TelemetryEvent]) -> None:
        path = self.data_dir / filename
        with path.open("w", encoding="utf-8") as f:
            json.dump([e.model_dump() for e in events], f, indent=2)

    def load_events(self, filename: str) -> list[TelemetryEvent]:
        path = self.data_dir / filename
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as f:
            raw: list[dict[str, Any]] = json.load(f)
        return [TelemetryEvent.model_validate(item) for item in raw]

    def event_file_stats(self, filename: str) -> tuple[int, int]:
        events = self.load_events(filename)
        total_bytes = sum(e.estimated_size_bytes for e in events)
        return len(events), total_bytes