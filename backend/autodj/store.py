from __future__ import annotations

import sqlite3
from pathlib import Path

from .models import FeedbackEvent


class ExperienceStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS experience_scores (
                    mode TEXT NOT NULL,
                    track_a TEXT,
                    track_b TEXT,
                    transition_type TEXT NOT NULL,
                    context_bucket TEXT NOT NULL,
                    score REAL NOT NULL DEFAULT 0,
                    n_positive INTEGER NOT NULL DEFAULT 0,
                    n_negative INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (mode, track_a, track_b, transition_type, context_bucket)
                )
                """
            )

    def apply_feedback(self, event: FeedbackEvent) -> None:
        delta = 1 if event.label.value == "GOOD" else -1
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO experience_scores (
                    mode, track_a, track_b, transition_type, context_bucket,
                    score, n_positive, n_negative
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(mode, track_a, track_b, transition_type, context_bucket)
                DO UPDATE SET
                    score = experience_scores.score * 0.98 + excluded.score,
                    n_positive = experience_scores.n_positive + excluded.n_positive,
                    n_negative = experience_scores.n_negative + excluded.n_negative
                """,
                (
                    event.decision_mode,
                    event.track_a,
                    event.track_b,
                    event.transition_type,
                    event.context_bucket,
                    delta,
                    1 if delta > 0 else 0,
                    1 if delta < 0 else 0,
                ),
            )

    def top_rows(self, limit: int = 20) -> list[dict[str, str | float | int | None]]:
        with self._connect() as conn:
            cur = conn.execute(
                """
                SELECT mode, track_a, track_b, transition_type, context_bucket,
                       score, n_positive, n_negative
                FROM experience_scores
                ORDER BY score DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cur.fetchall()
        return [
            {
                "mode": row[0],
                "track_a": row[1],
                "track_b": row[2],
                "transition_type": row[3],
                "context_bucket": row[4],
                "score": round(row[5], 3),
                "n_positive": row[6],
                "n_negative": row[7],
            }
            for row in rows
        ]
