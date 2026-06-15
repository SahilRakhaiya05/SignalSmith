from __future__ import annotations

import pytest
from pathlib import Path

from app.config import get_settings
from app.services.storage import Storage
from app.services.telemetry_generator import TelemetryGenerator


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep tests isolated from the developer's live Splunk instance."""
    monkeypatch.setenv("REQUIRE_SPLUNK", "false")
    get_settings.cache_clear()


@pytest.fixture
def temp_storage(tmp_path: Path) -> Storage:
    return Storage(data_dir=tmp_path / "data")


def seed_baseline_events(storage: Storage, event_count: int = 5000, seed: int = 42) -> int:
    events = TelemetryGenerator(seed=seed, event_count=event_count).generate()
    storage.save_events("baseline_events.json", events)
    storage.set_meta("data_source", "splunk")
    return len(events)