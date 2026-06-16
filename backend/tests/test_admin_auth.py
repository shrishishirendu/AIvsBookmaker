"""The admin gate: enforced when ADMIN_API_KEY is set, no-op when unset."""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.api import routes
from app.config import settings


def test_gate_enforced_when_key_set(monkeypatch):
    monkeypatch.setattr(settings, "admin_api_key", "secret123")
    with pytest.raises(HTTPException):
        routes.require_admin(None)          # missing key
    with pytest.raises(HTTPException):
        routes.require_admin("wrong")       # wrong key
    assert routes.require_admin("secret123") is None  # correct key passes


def test_gate_open_when_key_unset(monkeypatch):
    monkeypatch.setattr(settings, "admin_api_key", None)
    assert routes.require_admin(None) is None
    assert routes.require_admin("anything") is None
