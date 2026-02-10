from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    stopped = "stopped"
    running = "running"


class FeedbackLabel(str, Enum):
    good = "GOOD"
    bad = "BAD"


class TrackMetadata(BaseModel):
    track_id: str
    title: str
    bpm: float = Field(..., ge=60, le=220)
    key: str = "Unknown"
    drop_times: list[float] = Field(default_factory=list)
    duration_s: float = Field(..., gt=0)


class DeckState(BaseModel):
    deck_id: Literal["A", "B"]
    track_id: str | None = None
    title: str | None = None
    bpm: float | None = None
    key: str | None = None
    progress_s: float = 0.0
    duration_s: float = 1.0
    is_drop_window: bool = False


class DecisionEvent(BaseModel):
    mode: Literal["single", "double", "early_cut", "fake_drop"]
    transition_type: Literal["hard_cut", "echo_out", "silence"]
    reason: str
    timestamp_s: float
    track_a: str | None = None
    track_b: str | None = None


class SessionState(BaseModel):
    session_id: str | None = None
    status: SessionStatus = SessionStatus.stopped
    bpm_target: float = 140.0
    deck_a: DeckState = Field(default_factory=lambda: DeckState(deck_id="A"))
    deck_b: DeckState = Field(default_factory=lambda: DeckState(deck_id="B"))
    current_decision: DecisionEvent | None = None


class FeedbackEvent(BaseModel):
    label: FeedbackLabel
    decision_mode: str
    track_a: str | None = None
    track_b: str | None = None
    transition_type: str
    context_bucket: str = "default"


class ScanResult(BaseModel):
    scanned_path: str
    tracks_found: int


class LibrarySnapshot(BaseModel):
    tracks: list[TrackMetadata]
