"""Tests for the HMAC-signed presigned-URL helpers (pepper-aware)."""
import time
import pytest
from app.services.presigned_url import build_token, decode_token_unverified, verify_token


def _setup_secret(monkeypatch):
    monkeypatch.setattr("app.services.presigned_url.settings.PRESIGNED_URL_SECRET", "test-secret")


def test_round_trip_decodes_image_id_and_exp(monkeypatch):
    _setup_secret(monkeypatch)
    exp = int(time.time()) + 3600
    token = build_token(image_id="abc-123", expires_at_epoch=exp, pepper="peppA")
    decoded = decode_token_unverified(token)
    assert decoded["image_id"] == "abc-123"
    assert decoded["exp"] == exp
    assert verify_token(payload=decoded["payload"], sig=decoded["sig"], pepper="peppA", exp=exp) is True


def test_verify_rejects_wrong_pepper(monkeypatch):
    _setup_secret(monkeypatch)
    exp = int(time.time()) + 3600
    token = build_token(image_id="abc-123", expires_at_epoch=exp, pepper="peppA")
    decoded = decode_token_unverified(token)
    assert verify_token(payload=decoded["payload"], sig=decoded["sig"], pepper="peppB", exp=exp) is False


def test_verify_rejects_tampered_signature(monkeypatch):
    _setup_secret(monkeypatch)
    exp = int(time.time()) + 3600
    token = build_token(image_id="abc-123", expires_at_epoch=exp, pepper="peppA")
    decoded = decode_token_unverified(token)
    bad_sig = decoded["sig"][:-2] + "00"
    assert verify_token(payload=decoded["payload"], sig=bad_sig, pepper="peppA", exp=exp) is False


def test_verify_rejects_expired(monkeypatch):
    _setup_secret(monkeypatch)
    exp = int(time.time()) - 1
    token = build_token(image_id="abc-123", expires_at_epoch=exp, pepper="peppA")
    decoded = decode_token_unverified(token)
    assert verify_token(payload=decoded["payload"], sig=decoded["sig"], pepper="peppA", exp=exp) is False


def test_verify_rejects_wrong_global_secret(monkeypatch):
    monkeypatch.setattr("app.services.presigned_url.settings.PRESIGNED_URL_SECRET", "secret-A")
    exp = int(time.time()) + 3600
    token = build_token(image_id="abc-123", expires_at_epoch=exp, pepper="peppA")
    decoded = decode_token_unverified(token)
    monkeypatch.setattr("app.services.presigned_url.settings.PRESIGNED_URL_SECRET", "secret-B")
    assert verify_token(payload=decoded["payload"], sig=decoded["sig"], pepper="peppA", exp=exp) is False


def test_decode_rejects_malformed():
    assert decode_token_unverified("not-a-token") is None
    assert decode_token_unverified("a.b.c") is None
    assert decode_token_unverified("") is None
