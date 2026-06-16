"""canonical_json must be deterministic and stable, or the moat breaks."""
from __future__ import annotations

from app.ai.base import MatchPrediction
from app.canonical import canonical_json
from app.services.commit import compute_commit_hash, verify_commit_hash


def test_key_order_is_irrelevant():
    a = {"b": 1, "a": 2, "c": 3}
    b = {"c": 3, "a": 2, "b": 1}
    assert canonical_json(a) == canonical_json(b)


def test_no_insignificant_whitespace():
    assert canonical_json({"a": 1, "b": [1, 2]}) == '{"a":1,"b":[1,2]}'


def test_float_precision_is_fixed():
    # values that differ only beyond FLOAT_PRECISION must canonicalize identically
    assert canonical_json({"p": 0.5}) == canonical_json({"p": 0.5000001})
    assert canonical_json({"p": 0.123456}) == canonical_json({"p": 0.1234564})


def test_floats_below_precision_still_distinct():
    assert canonical_json({"p": 0.5}) != canonical_json({"p": 0.6})


def test_non_ascii_preserved():
    # reasoning text in any language must round-trip deterministically
    out = canonical_json({"reasoning": "Mbappé's diagonale tue la défense"})
    assert "Mbappé" in out
    assert canonical_json({"reasoning": "Mbappé"}) == canonical_json({"reasoning": "Mbappé"})


def test_pydantic_model_supported():
    pred = MatchPrediction(
        winner="TEAM_A", score_a=2, score_b=1, win_probability=0.71, reasoning="x"
    )
    assert canonical_json(pred) == canonical_json(pred.model_dump())


def test_bool_is_not_int():
    assert canonical_json({"x": True}) == '{"x":true}'
    assert canonical_json({"x": True}) != canonical_json({"x": 1})


def test_commit_hash_roundtrips():
    pred = MatchPrediction(
        winner="TEAM_A", score_a=2, score_b=0, win_probability=0.66,
        reasoning="Argentina's press suffocates Algeria's buildout.",
    )
    h = compute_commit_hash("Claude", 1001, pred, salt="season-salt")
    assert verify_commit_hash("Claude", 1001, pred, h, salt="season-salt")
    # any field change must break verification
    tampered = pred.model_copy(update={"score_a": 3})
    assert not verify_commit_hash("Claude", 1001, tampered, h, salt="season-salt")
    # a different salt must break verification (proves the salt is bound in)
    assert not verify_commit_hash("Claude", 1001, pred, h, salt="other-salt")
