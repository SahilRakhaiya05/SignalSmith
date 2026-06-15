from __future__ import annotations

from contextvars import ContextVar

from app.config import get_settings

_override: ContextVar[tuple[str, str] | None] = ContextVar("splunk_auth_override", default=None)


def set_splunk_auth(username: str | None, password: str | None) -> object | None:
    if username and password:
        return _override.set((username.strip(), password))
    return None


def reset_splunk_auth(token: object) -> None:
    _override.reset(token)


def get_splunk_auth() -> tuple[str, str]:
    override = _override.get()
    if override:
        return override
    settings = get_settings()
    return settings.splunk_username, settings.splunk_password


def get_splunk_username() -> str:
    return get_splunk_auth()[0]


def auth_source() -> str:
    return "session" if _override.get() else "env"