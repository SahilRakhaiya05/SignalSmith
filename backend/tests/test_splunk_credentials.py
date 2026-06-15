from __future__ import annotations

from app.services.splunk_credentials import auth_source, get_splunk_auth, reset_splunk_auth, set_splunk_auth


def test_get_splunk_auth_uses_env_by_default():
    user, pwd = get_splunk_auth()
    assert user
    assert pwd
    assert auth_source() == "env"


def test_session_override():
    token = set_splunk_auth("dev", "secret")
    try:
        assert get_splunk_auth() == ("dev", "secret")
        assert auth_source() == "session"
    finally:
        if token is not None:
            reset_splunk_auth(token)
    assert auth_source() == "env"