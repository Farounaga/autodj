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

## Technology (TBD)

- Audio Engine: TBD
- Backend Logic: TBD
- UI Framework: TBD
- Storage: SQLite / JSON

Technology choice intentionally postponed.

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

Early design / repository bootstrap phase.
