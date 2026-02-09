from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .models import (
    DecisionEvent,
    FeedbackEvent,
    LibrarySnapshot,
    ScanResult,
    SessionState,
    SessionStatus,
    TrackMetadata,
)
from .store import ExperienceStore

ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "autodj" / "static"
DB_PATH = ROOT / "data" / "autodj.sqlite"
DEFAULT_MUSIC_DIR = Path(os.getenv("AUTODJ_MUSIC_DIR", str(ROOT / "music")))
SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".flac"}

logger = logging.getLogger("autodj")

app = FastAPI(title="Autonomous DJ MVP")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

store = ExperienceStore(DB_PATH)
state = SessionState()
library = LibrarySnapshot(tracks=[])


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


def _placeholder_metadata(track_path: Path) -> TrackMetadata:
    """Build minimal metadata until offline analyzer is connected."""
    return TrackMetadata(
        track_id=str(track_path.resolve()),
        title=track_path.stem,
        bpm=140,
        key="Unknown",
        drop_times=[32.0, 64.0],
        duration_s=180,
    )


def _scan_tracks(scan_path: Path) -> list[TrackMetadata]:
    logger.info("Scan started: %s", scan_path)
    files = [p for p in scan_path.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS]
    files.sort()

    total = len(files)
    if total == 0:
        logger.warning("Scan finished: no supported tracks found in %s", scan_path)
        return []

    tracks: list[TrackMetadata] = []
    for index, path in enumerate(files, start=1):
        tracks.append(_placeholder_metadata(path))
        if total <= 10 or index == total or index % max(1, total // 10) == 0:
            percent = int(index / total * 100)
            logger.info("Scan progress: %s/%s (%s%%)", index, total, percent)

    logger.info("Scan finished: found %s tracks in %s", total, scan_path)
    return tracks


@app.post("/library/scan", response_model=ScanResult)
def scan_library(path: str | None = Query(default=None)) -> ScanResult:
    target = Path(path) if path else DEFAULT_MUSIC_DIR
    if not target.exists() or not target.is_dir():
        raise HTTPException(status_code=404, detail=f"Music directory not found: {target}")

    tracks = _scan_tracks(target)
    library.tracks = tracks
    return ScanResult(scanned_path=str(target.resolve()), tracks_found=len(tracks))


@app.post("/session/start", response_model=SessionState)
def start_session() -> SessionState:
    if state.status == SessionStatus.running:
        return state

    if len(library.tracks) < 2:
        raise HTTPException(
            status_code=409,
            detail="Need at least 2 tracks. Run /library/scan with your music directory first.",
        )

    state.session_id = str(uuid.uuid4())
    state.status = SessionStatus.running
    state.deck_a.track_id = library.tracks[0].track_id
    state.deck_a.title = library.tracks[0].title
    state.deck_a.duration_s = library.tracks[0].duration_s
    state.deck_b.track_id = library.tracks[1].track_id
    state.deck_b.title = library.tracks[1].title
    state.deck_b.duration_s = library.tracks[1].duration_s
    state.current_decision = DecisionEvent(
        mode="single",
        transition_type="hard_cut",
        reason="bootstrap decision",
        timestamp_s=time.time(),
        track_a=state.deck_a.track_id,
        track_b=state.deck_b.track_id,
    )
    return state


@app.post("/session/stop", response_model=SessionState)
def stop_session() -> SessionState:
    state.status = SessionStatus.stopped
    return state


@app.get("/state", response_model=SessionState)
def get_state() -> SessionState:
    return state


@app.post("/feedback")
def submit_feedback(event: FeedbackEvent) -> dict[str, str]:
    if state.status != SessionStatus.running:
        raise HTTPException(status_code=409, detail="Session is not running")

    store.apply_feedback(event)
    return {"status": "ok"}


@app.get("/scores")
def get_scores() -> dict[str, list[dict[str, str | float | int | None]]]:
    return {"rows": store.top_rows()}


async def tick_state() -> None:
    while True:
        if state.status == SessionStatus.running:
            state.deck_a.progress_s = (state.deck_a.progress_s + 0.5) % state.deck_a.duration_s
            state.deck_b.progress_s = (state.deck_b.progress_s + 0.5) % state.deck_b.duration_s
            state.deck_a.is_drop_window = 26 <= state.deck_a.progress_s % 32 <= 30
            state.deck_b.is_drop_window = 30 <= state.deck_b.progress_s % 32 <= 34
        await asyncio.sleep(0.5)


@app.on_event("startup")
async def on_startup() -> None:
    DEFAULT_MUSIC_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(
        "Music directory ready: %s (set AUTODJ_MUSIC_DIR to override)",
        DEFAULT_MUSIC_DIR.resolve(),
    )
    if DEFAULT_MUSIC_DIR.exists() and DEFAULT_MUSIC_DIR.is_dir():
        library.tracks = _scan_tracks(DEFAULT_MUSIC_DIR)
    asyncio.create_task(tick_state())


@app.websocket("/ws/state")
async def ws_state(ws: WebSocket) -> None:
    await ws.accept()
    try:
        while True:
            await ws.send_json(state.model_dump(mode="json"))
            await asyncio.sleep(0.5)
    finally:
        await ws.close()
