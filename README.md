# 🎧 Autonomous Riddim DJ Agent

Autonomous real-time DJ agent for riddim / dubstep, operating on a local music collection, capable of live mixing, recording full DJ sets, and learning the user’s taste through explicit feedback.

This project focuses on **autonomous DJ decision-making**, not music generation.

---

## Core Idea

The agent:
- mixes music in real time (like a human DJ),
- works only with local audio files,
- records exactly what is played (live DJ set),
- receives direct user feedback (GOOD / BAD),
- adapts its mixing decisions over time.

The system does not generate music.  
It selects, combines, and transitions between existing tracks and drops.

---

## Goals

### Primary Goals
- Real-time autonomous DJing
- Continuous playback (no offline rendering)
- Full session recording
- Human-in-the-loop learning
- Genre-locked: riddim / dubstep (~140 BPM)

### Non-Goals
- Music generation
- Multi-genre DJing
- Perfect or commercial-grade mixing
- Black-box neural networks

---

## High-Level Architecture

```
User (UI)
   ↓ feedback
Decision Engine
   ↓ actions
Audio Engine
   ↓ master
Recorder
```

---

## Audio Model

### Audio Sources
- Local audio files (WAV / MP3 / FLAC)
- Pre-analysed once (offline)

### Mixing Model
- 2–3 virtual decks
- BPM-synced playback
- Single / Double drops (Triple later)
- Hard cuts, echo-outs, silence transitions
- Imperfect riddim-style transitions allowed

---

## Track Metadata (Offline Analysis)

Each track is analysed once and stored as metadata:

- BPM
- Musical key (Camelot / standard)
- Drop timestamps
- Bass energy profile
- Rhythmic density
- Track duration

Real-time playback never performs heavy analysis.

---

## Decision Engine

The agent chooses **actions**, not tracks.

### Example Actions
- Single drop
- Double drop
- Early cut
- Fake drop
- Transition type selection

### Decision Inputs
- Current playback context
- Upcoming transition windows
- Track compatibility
- Learned preference weights

---

## Learning Model (Human-in-the-Loop)

### User Feedback
- GOOD DROP
- BAD DROP

### What Is Learned
The agent learns which **decisions and combinations** work for the user.

Example stored experience:
```
mode: double
track_A: X
track_B: Y
bass_pattern_A: 1/4
bass_pattern_B: 1/2
reward: +1
```

Learning is reinforcement/scoring-based, not deep learning.

---

## User Interface (MVP)

### UI Purpose
- Monitoring
- Feedback
- Minimal control

### UI Elements
- Deck A / Deck B visualisation
- Track names and progress
- Drop indicator
- Buttons:
  - GOOD DROP
  - BAD DROP

The UI is not a DJ controller.

---

## Recording Model

- Always-on master recording
- Single continuous audio file per session
- No post-processing
- Output equals live playback

---

## Roadmap

### Phase 1 — MVP
- Local track loading
- BPM sync
- Single and basic double drops
- Real-time playback
- Full session recording
- Feedback buttons
- Simple scoring logic

### Phase 2
- Improved double logic
- Emergency transitions
- Better drop detection
- Preference persistence

### Phase 3
- Limited triple drops
- Contextual adaptation
- Session-based style memory

### Phase 4 (Optional)
- Voice feedback
- Advanced bass-pattern logic
- Session analytics

---

## Technology (MVP Bootstrap)

- Audio Engine: simulated transport loop (real mixer integration next)
- Backend Logic: Python + FastAPI
- UI Framework: Web UI (HTML/CSS/JS) served by backend
- Storage: SQLite (experience scoring)

This repository now includes a working MVP bootstrap for decision loop + UI feedback.

---

## Constraints

- Real-time audio latency limits
- Past audio cannot be modified
- Learning is gradual
- Quality depends on track preparation

---

## Philosophy

DJing is treated as **decision-making under time pressure**, not as a creativity problem.

Rules first.  
Feedback second.  
Learning last.

---

## Project Status

MVP bootstrap phase.

---

## Implemented MVP Skeleton

### Backend Endpoints

- `POST /library/scan`
- `POST /session/start`
- `POST /session/stop`
- `GET /state`
- `POST /feedback`
- `GET /scores`
- `WS /ws/state`

### Web UI Features

- Deck A / Deck B visual state with progress bars
- Session status indicator
- GOOD DROP / BAD DROP buttons
- Live score table (top learned combinations)

### Run Locally

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn autodj.main:app --reload --host 0.0.0.0 --port 8000
```

> If you created the virtualenv before this update, run `pip install -r requirements.txt` again so WebSocket support is installed.

Then open: `http://localhost:8000`

### Track directory configuration

By default, the app now creates and scans `backend/music` on startup.
Drop your `.wav` / `.mp3` / `.flac` files there for the quickest local test.
Startup and manual scans print progress logs in the server terminal.

You can point the app to your music folder in two ways:

1. Environment variable (default scan path):

```bash
export AUTODJ_MUSIC_DIR=/absolute/path/to/your/tracks
uvicorn autodj.main:app --reload --host 0.0.0.0 --port 8000
```

2. Per-request path via API scan endpoint:

```bash
curl -X POST "http://localhost:8000/library/scan?path=/absolute/path/to/your/tracks"
```

`/session/start` now requires at least 2 scanned tracks, so the normal flow is: scan library -> start session.
