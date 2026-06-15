from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"
_BACKEND_ENV = Path(__file__).resolve().parents[1] / ".env"
_ENV_FILE = _ROOT_ENV if _ROOT_ENV.exists() else _BACKEND_ENV


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    splunk_host: str = "localhost"
    splunk_web_port: int = 8000
    splunk_web_scheme: str = "http"
    splunk_api_port: int = 8089
    splunk_api_scheme: str = "https"
    splunk_hec_port: int = 8088
    splunk_username: str = "admin"
    splunk_password: str = "changeme123"
    splunk_hec_token: str = ""
    splunk_baseline_index: str = "signalsmith_baseline"
    splunk_candidate_index: str = "signalsmith_candidate"
    splunk_mcp_url: str = ""
    splunk_mcp_token: str = ""
    profile_export_limit: int = 25000
    require_splunk: bool = True

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    gemini_enabled: bool = True

    data_dir: Path = Path(__file__).resolve().parents[1] / "data"
    event_count_default: int = 20000
    random_seed: int = 42
    debug_policy_audit: bool = False

    # Custom detections: config/detections.json or any JSON file (see config/detections.example.json)
    signalsmith_detections_file: str = ""
    signalsmith_include_demo_detections: bool = True

    @property
    def splunk_api_base(self) -> str:
        return f"{self.splunk_api_scheme}://{self.splunk_host}:{self.splunk_api_port}"

    @property
    def splunk_web_base(self) -> str:
        return f"{self.splunk_web_scheme}://{self.splunk_host}:{self.splunk_web_port}"

    @property
    def splunk_mcp_endpoint(self) -> str:
        if self.splunk_mcp_url:
            return self.splunk_mcp_url.rstrip("/")
        return f"{self.splunk_api_base}/services/mcp"

    @property
    def splunk_hec_url(self) -> str:
        return f"{self.splunk_api_scheme}://{self.splunk_host}:{self.splunk_hec_port}/services/collector/event"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reload_settings() -> Settings:
    """Clear cached settings so .env changes are picked up on restart/reload."""
    get_settings.cache_clear()
    return get_settings()