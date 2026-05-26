import time

import pytest

from app.services import session_service


def test_session_sign_verify_roundtrip():
    token = session_service.sign_session({"u": "a@b.c", "d": "A B", "exp": int(time.time()) + 60})
    payload = session_service.verify_session(token, max_age=120)
    assert payload["u"] == "a@b.c"
    assert payload["d"] == "A B"


def test_session_expired_returns_none():
    token = session_service.sign_session({"u": "a@b.c", "d": "A", "exp": 0})
    # Force expiry by passing max_age=0
    assert session_service.verify_session(token, max_age=0) is None


def test_session_tampered_returns_none():
    token = session_service.sign_session({"u": "a@b.c", "d": "A", "exp": int(time.time()) + 60})
    tampered = token[:-2] + ("AA" if not token.endswith("AA") else "BB")
    assert session_service.verify_session(tampered, max_age=120) is None


def test_state_sign_verify_roundtrip():
    token = session_service.sign_state({"s": "abc123", "r": "/foo"})
    payload = session_service.verify_state(token, max_age=300)
    assert payload == {"s": "abc123", "r": "/foo"}


def test_state_and_session_have_distinct_signatures():
    """A session-signed token must not validate as a state token (different salt)."""
    sess = session_service.sign_session({"u": "a@b.c", "d": "A", "exp": int(time.time()) + 60})
    assert session_service.verify_state(sess, max_age=300) is None
