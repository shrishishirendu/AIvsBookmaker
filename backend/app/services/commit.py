"""Commit hashing (BUILD_SPEC §5).

    commit_hash = SHA256(model + match_id + canonical_json(prediction) + salt)

Committing and verifying MUST call this identical function. The salt comes from
COMMIT_SALT and is held server-side; publishing the hash before kickoff while
keeping the plaintext sealed is what makes "the AI called it" unfalsifiable.
"""
from __future__ import annotations

import hashlib

from ..ai.base import MatchPrediction
from ..canonical import canonical_json
from ..config import settings


def compute_commit_hash(
    competitor: str,
    match_id: int,
    prediction: MatchPrediction,
    *,
    salt: str | None = None,
) -> str:
    salt = salt if salt is not None else settings.commit_salt
    payload = f"{competitor}{match_id}{canonical_json(prediction)}{salt}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def verify_commit_hash(
    competitor: str,
    match_id: int,
    prediction: MatchPrediction,
    expected_hash: str,
    *,
    salt: str | None = None,
) -> bool:
    return compute_commit_hash(competitor, match_id, prediction, salt=salt) == expected_hash
