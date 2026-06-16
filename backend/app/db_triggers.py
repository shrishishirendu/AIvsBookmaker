"""DB-level enforcement of the prediction lock (BUILD_SPEC §5).

Once `locked_at` is set, the prediction PAYLOAD (winner, scores, probability,
reasoning, commit_hash, committed_at) can never change — enforced by the
database, not just app code. `revealed` and `locked_at` themselves are NOT
payload, so the REVEAL step is still allowed after lock.

Two dialect variants: Postgres (used by Alembic) and SQLite (used by the Phase 0
demo/tests). Both raise on a payload UPDATE of a locked row.
"""
from __future__ import annotations

PAYLOAD_COLUMNS = [
    "winner",
    "score_a",
    "score_b",
    "win_probability",
    "reasoning",
    "commit_hash",
    "committed_at",
]

# --- Postgres ---------------------------------------------------------------

POSTGRES_UP = """
CREATE OR REPLACE FUNCTION reject_locked_prediction_update()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.locked_at IS NOT NULL AND (
        NEW.winner          IS DISTINCT FROM OLD.winner          OR
        NEW.score_a         IS DISTINCT FROM OLD.score_a         OR
        NEW.score_b         IS DISTINCT FROM OLD.score_b         OR
        NEW.win_probability IS DISTINCT FROM OLD.win_probability OR
        NEW.reasoning       IS DISTINCT FROM OLD.reasoning       OR
        NEW.commit_hash     IS DISTINCT FROM OLD.commit_hash     OR
        NEW.committed_at    IS DISTINCT FROM OLD.committed_at
    ) THEN
        RAISE EXCEPTION 'prediction % is locked; payload is immutable', OLD.id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_reject_locked_prediction_update ON predictions;
CREATE TRIGGER trg_reject_locked_prediction_update
    BEFORE UPDATE ON predictions
    FOR EACH ROW
    EXECUTE FUNCTION reject_locked_prediction_update();
"""

POSTGRES_DOWN = """
DROP TRIGGER IF EXISTS trg_reject_locked_prediction_update ON predictions;
DROP FUNCTION IF EXISTS reject_locked_prediction_update();
"""

# --- SQLite -----------------------------------------------------------------
# SQLite supports "BEFORE UPDATE OF <cols>" with a WHEN clause and RAISE(ABORT).

SQLITE_UP = """
CREATE TRIGGER IF NOT EXISTS trg_reject_locked_prediction_update
BEFORE UPDATE OF {cols} ON predictions
FOR EACH ROW WHEN OLD.locked_at IS NOT NULL
BEGIN
    SELECT RAISE(ABORT, 'prediction is locked; payload is immutable');
END;
""".format(cols=", ".join(PAYLOAD_COLUMNS))


async def install_sqlite_trigger(conn) -> None:
    """Install the lock trigger on an async SQLite connection (demo/tests)."""
    from sqlalchemy import text

    await conn.execute(text(SQLITE_UP))
