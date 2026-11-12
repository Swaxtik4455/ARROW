# ARROW — Futuristic JARVIS-Style Desktop AI Assistant

**ARROW** is a local-first, voice-enabled desktop AI assistant featuring a custom obsidian-and-cyan HUD interface built with **Electron, React, and TypeScript**, seamlessly coupled to a modular **Python AI & automation backend** via a high-speed **FastAPI + WebSocket bridge**.

---

## Key Features

- **5-Region HUD Desktop Interface:** Frameless dark Windows desktop application (`#03060a` technical grid) with custom window controls, corner-bracketed branding, live `CPU`/`MEM` circular telemetry gauges, a real-time transcript stream, and bottom voice equalizer controls.
- **Programmatic Multi-Layer AI Core:** Custom SVG + HTML5 Canvas animated orb with 7 concentric rotating telemetry rings, 72-tick radial degree scales, orbiting particles, energy pulse waves, and reactive visual states (`IDLE`, `LISTENING`, `THINKING`, `SPEAKING`, `ERROR`, `DISCONNECTED`).
- **Decoupled Bridge Architecture:** `bridge/bridge_server.py` exposes local HTTP REST endpoints and a low-latency WebSocket stream (`127.0.0.1:8765`) while keeping all core Python backend modules strictly read-only.
- **Voice & Persona Engine:** Supports wake-word activation (`"ARROW"`), push-to-talk speech recognition, real-time speech interruption, mute controls, and configurable AI response personas (`normal`, `detailed`, `coding`, `study`, `professional`).
- **Desktop Automation & Productivity:** Handles Windows application launching, system utilities, weather/news lookups, reminders, timers, and persistent SQLite conversation history.
- **Standalone Windows Executable:** Compiles via `electron-builder` into `ARROW.exe`, automatically spawning and terminating the Python backend silently in the background.

---

## System Architecture

```text
+-------------------------------------------------------------------+
|                   Electron Desktop Window (ARROW.exe)              |
|  +-------------------------------------------------------------+  |
|  |  React + TypeScript HUD (arrow-ui)                          |  |
|  |  - AICore (SVG + Canvas)   - Telemetry Gauges               |  |
|  |  - Live Transcript         - Settings & Voice Controls      |  |
|  +-----------------------------+-------------------------------+  |
+--------------------------------|----------------------------------+
                                 | HTTP REST + WebSocket (127.0.0.1:8765)
+--------------------------------v----------------------------------+
|               FastAPI Bridge (bridge/bridge_server.py)            |
|  - Thread-safe state & telemetry broadcaster                      |
|  - Auto-managed lifecycle via Electron main process               |
+--------------------------------|----------------------------------+
                                 | Direct Python Module Imports
+--------------------------------v----------------------------------+
|                 Modular Python Core Backend                       |
|  - command_router.py   - ai_engine.py       - config.py           |
|  - voice_input.py      - voice_output.py    - storage.py          |
|  - automation.py       - productivity.py    - info_services.py    |
+-------------------------------------------------------------------+