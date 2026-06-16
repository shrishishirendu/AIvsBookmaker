"""Canonical JSON — the single most safety-critical util in the system.

Commit and verify MUST serialize identically or the whole trust model breaks
(BUILD_SPEC §5). Rules:

  * keys sorted
  * no insignificant whitespace
  * floats rounded to a FIXED precision so 0.5 and 0.50000000001 can never
    produce two different hashes for the "same" prediction
  * non-ASCII preserved verbatim (ensure_ascii=False) so reasoning text in any
    language hashes deterministically

There is exactly ONE implementation. Everything that hashes or verifies a
prediction calls `canonical_json()`. Do not inline json.dumps anywhere else.
"""
from __future__ import annotations

import json
from typing import Any

# Decimal places every float is rounded to before serialization.
FLOAT_PRECISION = 6


def _normalize(obj: Any) -> Any:
    """Recursively coerce values into a canonical, hash-stable form."""
    if isinstance(obj, bool):
        # bool is a subclass of int — keep it as a JSON boolean, not 1/0.
        return obj
    if isinstance(obj, float):
        # Round to fixed precision. round() yields a float whose repr is stable
        # for a given value, so json.dumps below is deterministic.
        return round(obj, FLOAT_PRECISION)
    if isinstance(obj, dict):
        return {str(k): _normalize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_normalize(v) for v in obj]
    return obj


def canonical_json(obj: Any) -> str:
    """Return the canonical JSON string for `obj`.

    `obj` may be a dict, a list, or anything exposing `.model_dump()`
    (e.g. a pydantic model).
    """
    if hasattr(obj, "model_dump"):
        obj = obj.model_dump()
    return json.dumps(
        _normalize(obj),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
