from __future__ import annotations

import pytest

from app.services.gemini_service import GeminiService


def test_gemini_not_configured_when_key_empty(monkeypatch):
    svc = GeminiService()
    monkeypatch.setattr(svc.settings, "gemini_api_key", "")
    status = svc.status_dict()
    assert status["configured"] is False
    assert status["available"] is False


def test_invalid_key_format_detected(monkeypatch):
    svc = GeminiService()
    monkeypatch.setattr(svc.settings, "gemini_api_key", "sk-not-a-google-key")
    status = svc.status_dict()
    assert status["configured"] is True
    assert status["available"] is False
    assert status["auth_ok"] is False
    assert "AIza" in status["auth_hint"]


def test_auth_key_format_accepted(monkeypatch):
    svc = GeminiService()
    monkeypatch.setattr(svc.settings, "gemini_api_key", "AQ.FakeTestKeyForUnitTestsOnly_NotARealCredential")
    assert svc.auth_issue() is None
    status = svc.status_dict()
    assert status["available"] is True
    assert status["key_type"] == "auth"
    assert status["auth_ok"] is True


def test_valid_standard_key_format(monkeypatch):
    svc = GeminiService()
    monkeypatch.setattr(svc.settings, "gemini_api_key", "AIzaSyAbcdefghijklmnopqrstuvwxyz123456")
    assert svc.auth_issue() is None
    status = svc.status_dict()
    assert status["available"] is True
    assert status["key_type"] == "standard"


def test_friendly_error_on_401_for_auth_key():
    msg = GeminiService.friendly_error(401, '{"error":{"code":401}}', "AQ.testkey123456789012345678901234")
    assert "AQ." in msg
    assert "Google Cloud Console" in msg


def test_friendly_error_on_401_for_standard_key():
    msg = GeminiService.friendly_error(401, '{"error":{"code":401}}', "AIzaSyAbcdefghijklmnopqrstuvwxyz123456")
    assert "aistudio.google.com" in msg


def test_clean_spl_adds_search_prefix():
    assert GeminiService._clean_spl("index=main | head 10") == "search index=main | head 10"
    assert GeminiService._clean_spl("```\nsearch index=a | stats count\n```") == "search index=a | stats count"


@pytest.mark.asyncio
async def test_generate_spl_requires_api_key(monkeypatch):
    svc = GeminiService()
    monkeypatch.setattr(svc.settings, "gemini_api_key", "")
    with pytest.raises(RuntimeError, match="not configured"):
        await svc.generate_spl("show top services")