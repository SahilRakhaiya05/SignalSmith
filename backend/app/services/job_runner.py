from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine
from uuid import uuid4

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    message: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    result: dict[str, Any] | None = None
    error: str | None = None


class JobRunner:
    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._tasks: dict[str, asyncio.Task] = {}

    def get(self, job_id: str) -> JobRecord | None:
        return self._jobs.get(job_id)

    def list_jobs(self, limit: int = 20) -> list[JobRecord]:
        jobs = list(self._jobs.values())
        return sorted(jobs, key=lambda j: j.updated_at, reverse=True)[:limit]

    def _update(self, job_id: str, **kwargs: Any) -> JobRecord:
        job = self._jobs[job_id]
        for key, value in kwargs.items():
            setattr(job, key, value)
        job.updated_at = datetime.now(timezone.utc).isoformat()
        return job

    def start(
        self,
        name: str,
        coro_factory: Callable[[Callable[[float, str], None]], Coroutine[Any, Any, dict[str, Any]]],
    ) -> JobRecord:
        job = JobRecord(name=name, status=JobStatus.RUNNING, message="Starting...")
        self._jobs[job.id] = job

        def progress_cb(value: float, message: str) -> None:
            self._update(job.id, progress=max(0.0, min(1.0, value)), message=message)

        async def _run() -> None:
            try:
                result = await coro_factory(progress_cb)
                self._update(
                    job.id,
                    status=JobStatus.COMPLETED,
                    progress=1.0,
                    message="Complete",
                    result=result,
                )
            except Exception as exc:
                self._update(
                    job.id,
                    status=JobStatus.FAILED,
                    message="Failed",
                    error=str(exc),
                )

        self._tasks[job.id] = asyncio.create_task(_run())
        return job


_job_runner: JobRunner | None = None


def get_job_runner() -> JobRunner:
    global _job_runner
    if _job_runner is None:
        _job_runner = JobRunner()
    return _job_runner