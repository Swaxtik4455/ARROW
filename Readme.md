# ARROW — Autonomous Reactive Runtime & Orchestration Workstation

> **A local-first, voice-enabled Windows desktop AI assistant featuring a custom obsidian-and-cyan JARVIS-style HUD built with Electron, React, and TypeScript, paired with a modular Python AI, speech, and OS-automation engine over a real-time FastAPI + WebSocket bridge.**

---

## Table of Contents

1. [Overview & Design Philosophy](#overview--design-philosophy)
2. [Core Capabilities](#core-capabilities)
3. [System Architecture & Data Flow](#system-architecture--data-flow)
4. [HUD Interface & Visual State Machine](#hud-interface--visual-state-machine)
5. [Repository Structure](#repository-structure)
6. [Technology Stack](#technology-stack)
7. [Prerequisites](#prerequisites)
8. [Local Development Setup](#local-development-setup)
9. [Building the Standalone Windows Executable (`.exe`)](#building-the-standalone-windows-executable-exe)
10. [Containerized Deployment with Docker](#containerized-deployment-with-docker)
11. [Bridge API & WebSocket Protocol Reference](#bridge-api--websocket-protocol-reference)
12. [Configuration & Environment Variables](#configuration--environment-variables)
13. [Voice Commands & Keyboard Shortcuts](#voice-commands--keyboard-shortcuts)
14. [Security & Privacy Model](#security--privacy-model)
15. [Troubleshooting](#troubleshooting)

---

## Overview & Design Philosophy

**ARROW** is engineered around strict separation of concerns between presentation, transport, and execution:

* **Non-Destructive Backend Isolation:** All core Python modules (`command_router.py`, `ai_engine.py`, `voice_input.py`, `voice_output.py`, `automation.py`, `productivity.py`, `info_services.py`, `entertainment.py`, `storage.py`, `config.py`) operate cleanly without UI dependencies.
* **Local Loopback Bridge (`127.0.0.1:8765`):** A standalone FastAPI + WebSocket server (`bridge/bridge_server.py`) wraps the Python subsystems in a thread-safe orchestrator, broadcasting state transitions, transcripts, scheduler alerts, and live `psutil` hardware metrics to the HUD.
* **Unified Desktop Lifecycle:** When launched as a desktop application (`ARROW.exe` or `npm run dev`), Electron's main process automatically spawns the Python bridge silently (`windowsHide: true`), waits for the `/api/health` readiness check, renders the frameless HUD, and terminates the child Python process cleanly upon window exit.

---

## Core Capabilities

### 1. Conversational Intelligence (`ai_engine.py`)
* Powered by **Google Gemini (`google-genai`)** with configurable model selection (default: `gemini-2.5-flash`).
* **Multi-Persona Response Modes:** Switch dynamically from the HUD **System Parameters** modal between `normal`, `detailed`, `coding`, `study`, and `professional` modes.
* **Persistent Context:** Maintains local SQLite conversation history (`storage.py`) with configurable context window limits and one-click history clearing.

### 2. Dual-Mode Voice Pipeline (`voice_input.py` & `voice_output.py`)
* **Push-to-Talk & Continuous Wake-Word Listening:** Trigger single-utterance capture by clicking the central AI Core orb or toggle continuous background wake-word detection (`"ARROW"`).
* **Dual Speech Synthesis Engines:** Supports offline Windows SAPI5 voices (`pyttsx3`) with selectable system voice index, speech rate (`WPM`), and volume, alongside neural cloud fallback (`gTTS` + `pygame`).
* **Instant Barge-In / Interrupt:** Halts active speech mid-utterance via the HUD `INTERRUPT` control, `Escape` key, or REST endpoint (`/api/voice/interrupt`).

### 3. Windows Desktop Automation & Productivity (`automation.py`, `productivity.py`)
* **OS & Application Control:** Launches native Windows applications, opens web targets, manages system utilities, and executes desktop macros safely.
* **Background Scheduler & Alerts:** Runs non-blocking timers, alarms, and reminders that push proactive notifications into the HUD transcript and speak alerts aloud when unmuted.
* **Real-Time Information & Media (`info_services.py`, `entertainment.py`):** Retrieves localized weather forecasts, news headlines, Wikipedia summaries, and media playback actions.

### 4. Real-Time Telemetry & HUD (`arrow-ui`)
* **5-Region Technical HUD:** Frameless dark window (`#03060a`) with custom window controls (`minimize`, `maximize`, `close`), corner-bracketed telemetry framing, live `CPU` and `MEM` circular SVG gauges updated every 1.5 seconds, live message transcript, and animated audio equalizer bars.

---

## System Architecture & Data Flow

```text
+-----------------------------------------------------------------------------+
|                    ELECTRON DESKTOP SHELL (ARROW.exe)                       |
|  - Frameless Native Window (1380x840)  - IPC Window Controls                |
|  - Auto-spawns & terminates Python child process via Node child_process     |
|                                                                             |
|  +-----------------------------------------------------------------------+  |
|  |                 REACT + TYPESCRIPT HUD (arrow-ui/src)                 |  |
|  |                                                                       |  |
|  |  [BrandHeader]   [Telemetry: CPU/MEM]   [AICore: SVG + HTML5 Canvas]  |  |
|  |  [Transcript + Command Input]           [Controls: Mic/Mute/Interrupt]|  |
|  |  [SettingsModal: Personas, Voices, Wake-Word, History Management]     |  |
|  +-----------------------------------+-----------------------------------+  |
+--------------------------------------|--------------------------------------+
                                       |
         HTTP REST (Commands/Settings) |  WebSocket ws://127.0.0.1:8765/ws
         [http://127.0.0.1:8765/api/](http://127.0.0.1:8765/api/)*   |  (State, Transcripts, Telemetry)
                                       v
+-----------------------------------------------------------------------------+
|                FASTAPI + WEBSOCKET BRIDGE (bridge/bridge_server.py)         |
|  - ArrowBridgeController (Thread-safe bridge -> asyncio loop broadcaster)   |
|  - Background psutil Telemetry Broadcaster (1.5s interval)                  |
|  - Lifespan Manager (Graceful startup & subsystem shutdown)                 |
+--------------------------------------+--------------------------------------+
                                       | Direct In-Process Python Imports
                                       v
+-----------------------------------------------------------------------------+
|                     MODULAR PYTHON CORE BACKEND (Root)                      |
|                                                                             |
|  +-------------------+   +-------------------+   +-----------------------+  |
|  |  command_router   |-->|    ai_engine      |   |     voice_input       |  |
|  | (Intent Dispatch) |   |  (Gemini LLM)     |   | (STT + Wake-Word)     |  |
|  +---------+---------+   +-------------------+   +-----------------------+  |
|            |                                                                |
|            +---> automation.py      (Windows App & OS Automation)           |
|            +---> productivity.py    (Timers, Reminders, Scheduler Alerts)   |
|            +---> info_services.py   (Weather, News, Wikipedia)              |
|            +---> entertainment.py   (Media & Playback)                      |
|            +---> storage.py         (SQLite Persistence)                    |
|            +---> config.py          (Settings & Runtime Configuration)      |
|            +---> voice_output.py    (pyttsx3 SAPI5 / gTTS Speech Engine)    |
+-----------------------------------------------------------------------------+