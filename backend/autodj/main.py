from __future__ import annotations

import asyncio
import logging
import os
import re
import time
import uuid
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
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
TARGET_BPM = 140.0

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


def _extract_bpm_key(track_path: Path) -> tuple[float, str]:
    name = track_path.stem

    bpm_match = re.search(r"(?<!\d)(\d{2,3}(?:\.\d+)?)\s?bpm(?!\d)", name, flags=re.IGNORECASE)
    bpm = TARGET_BPM
    if bpm_match:
        candidate = float(bpm_match.group(1))
        if 60 <= candidate <= 220:
            bpm = candidate

    camelot_match = re.search(r"(?<![A-Za-z0-9])(\d{1,2}[AB])(?![A-Za-z0-9])", name, flags=re.IGNORECASE)
    if camelot_match:
        return bpm, camelot_match.group(1).upper()

    key_match = re.search(r"(?<![A-Za-z0-9])([A-G](?:#|b)?m?)(?![A-Za-z0-9])", name)
    if key_match:
        return bpm, key_match.group(1)

    return bpm, "Unknown"


def _placeholder_metadata(track_path: Path) -> TrackMetadata:
    bpm, key = _extract_bpm_key(track_path)
    return TrackMetadata(
        track_id=str(track_path.resolve()),
        title=track_path.stem,
        bpm=bpm,
        key=key,
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


def _find_track(track_id: str) -> TrackMetadata | None:
    return next((track for track in library.tracks if track.track_id == track_id), None)


def _to_library_payload(track: TrackMetadata) -> dict[str, str | float | list[float]]:
    return {
        "track_id": track.track_id,
        "title": track.title,
        "bpm": track.bpm,
        "key": track.key,
        "drop_times": track.drop_times,
        "duration_s": track.duration_s,
        "media_url": f"/media?track_id={quote(track.track_id, safe='')}",
    }


@app.get("/library")
def get_library() -> dict[str, list[dict[str, str | float | list[float]]]]:
    return {"tracks": [_to_library_payload(track) for track in library.tracks]}


@app.get("/media")
def get_media(track_id: str = Query(...)) -> FileResponse:
    track = _find_track(track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found in scanned library")

    track_path = Path(track.track_id)
    if not track_path.exists() or not track_path.is_file():
        raise HTTPException(status_code=404, detail=f"Track file missing: {track_path}")

    return FileResponse(track_path)


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

    track_a = library.tracks[0]
    track_b = library.tracks[1]
    state.session_id = str(uuid.uuid4())
    state.status = SessionStatus.running
    state.bpm_target = TARGET_BPM

    state.deck_a.track_id = track_a.track_id
    state.deck_a.title = track_a.title
    state.deck_a.duration_s = track_a.duration_s
    state.deck_a.bpm = track_a.bpm
    state.deck_a.key = track_a.key

    state.deck_b.track_id = track_b.track_id
    state.deck_b.title = track_b.title
    state.deck_b.duration_s = track_b.duration_s
    state.deck_b.bpm = track_b.bpm
    state.deck_b.key = track_b.key

    state.current_decision = DecisionEvent(
        mode="double",
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
            state.deck_a.progress_s = (state.deck_a.progress_s + 0.5) % max(state.deck_a.duration_s, 1.0)
            state.deck_b.progress_s = (state.deck_b.progress_s + 0.5) % max(state.deck_b.duration_s, 1.0)
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
    except WebSocketDisconnect:
        return
