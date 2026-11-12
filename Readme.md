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
         [http://127.0.0.1:8765/api/](http://127.0.0.1:8765/api/)    |  (State, Transcripts, Telemetry)
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
```

### Command Execution Lifecycle
1. **Input Capture:** User either submits text in the HUD transcript bar (`POST /api/command`) or speaks after triggering the microphone (`POST /api/voice/listen` or wake-word trigger).
2. **State Broadcast (`THINKING`):** `ArrowBridgeController` transitions state to `THINKING` and pushes `{ "type": "state", "state": "THINKING" }` over `/ws`, accelerating the AICore rings and shifting aura harmonics.
3. **Intent Classification & Execution:** `CommandRouter.route()` evaluates deterministic system/productivity/info intents first, falling back to `AIEngine` (Gemini) for open-ended reasoning.
4. **Transcript & Speech Synthesis (`SPEAKING`):** The response is persisted in SQLite, broadcast as `{ "type": "transcript", "sender": "ARROW", ... }`, and passed to `VoiceOutputManager.speak()` (unless muted), transitioning the HUD to `SPEAKING` with active waveform animation until completion or user interruption.

---

## HUD Interface & Visual State Machine

The central **AI Core (`AICore.tsx`)** combines multi-layered SVG geometry (7 concentric counter-rotating telemetry rings, 72-tick radial degree scales, orbital reticle markers) with a 60fps HTML5 `<canvas>` particle and energy-wave renderer.

| System State | Trigger Condition | Orb & HUD Visual Behavior |
| :--- | :--- | :--- |
| **`IDLE`** | Bridge connected, awaiting user input | Steady cyan breathing pulse (`#00e5ff`), slow counter-rotating outer rings, calm particle drift. |
| **`LISTENING`** | Microphone active (`trigger_single_listen` or wake word) | High-contrast cyan expansion, inward-drawing audio energy rings, status indicator `LISTENING...`. |
| **`THINKING`** | `CommandRouter` / Gemini LLM processing request | Accelerated ring rotation speed, high-frequency core shimmer, status indicator `PROCESSING...`. |
| **`SPEAKING`** | `VoiceOutputManager` actively speaking response | Synchronized radial pulse waves, animated bottom equalizer waveform bars, `INTERRUPT` button active. |
| **`ERROR`** | Microphone capture failure or backend exception | Brief amber/crimson warning pulse (`2.5s` auto-recovery back to `IDLE`), error logged to transcript. |
| **`DISCONNECTED`** | Bridge unreachable (`127.0.0.1:8765` offline) | Dimmed low-power standby ring, automatic WebSocket reconnect loop every `2.0s`. |

---

## Repository Structure

```text
python-ai-assistant/
├── arrow-ui/                          # Electron + React + TypeScript Desktop HUD
│   ├── electron/
│   │   ├── main.ts                    # Electron main process, Python process lifecycle, IPC
│   │   └── preload.ts                 # Context-isolated window control bridge (window.arrowDesktop)
│   ├── src/
│   │   ├── components/
│   │   │   ├── AICore.tsx             # Multi-layer SVG + Canvas animated HUD orb
│   │   │   ├── BrandHeader.tsx        # Top-left corner-bracketed ARROW HUD header
│   │   │   ├── Controls.tsx           # Bottom status pill, audio waveform, Mute & Interrupt
│   │   │   ├── SettingsModal.tsx      # System Parameters modal (AI, TTS, Wake-Word, History)
│   │   │   ├── Telemetry.tsx          # Left-side circular CPU & MEM gauges
│   │   │   ├── TitleBar.tsx           # Frameless custom window titlebar & connection dot
│   │   │   └── Transcript.tsx         # Live scrollable conversation log & command input
│   │   ├── hooks/
│   │   │   └── useArrowSystem.ts      # Centralized state store & auto-reconnecting WS hook
│   │   ├── services/
│   │   │   └── arrowClient.ts         # Typed HTTP REST & WebSocket client
│   │   ├── types/
│   │   │   └── arrow.ts               # Shared TypeScript interfaces & state unions
│   │   ├── App.tsx                    # Root 5-region HUD layout & global hotkeys
│   │   ├── index.css                  # HUD grid styling, custom scrollbars, CSS variables
│   │   └── main.tsx                   # React DOM entry point
│   ├── index.html                     # HUD HTML shell
│   ├── package.json                   # Frontend dependencies & electron-builder config
│   ├── tsconfig.json                  # React TypeScript configuration
│   ├── tsconfig.electron.json         # Electron main/preload TypeScript configuration
│   └── vite.config.ts                 # Vite bundler config (base: "./" for packaged .exe)
├── bridge/
│   └── bridge_server.py               # FastAPI + WebSocket bridge & psutil telemetry server
├── main.py                            # Legacy standalone Python entry point
├── command_router.py                  # Deterministic + LLM intent router
├── ai_engine.py                       # Google Gemini API client & persona system prompts
├── voice_input.py                     # SpeechRecognition & continuous wake-word listener
├── voice_output.py                    # pyttsx3 (SAPI5) & gTTS audio output manager
├── automation.py                      # Windows application launcher & OS automation
├── productivity.py                    # Timers, reminders, and scheduler alert callbacks
├── info_services.py                   # Weather, news, and Wikipedia lookup handlers
├── entertainment.py                   # Media & entertainment command handlers
├── storage.py                         # SQLite database layer for messages & persistence
├── config.py                          # Persistent JSON/env settings manager
├── Dockerfile                         # Container definition for the Python FastAPI bridge
├── docker-compose.yml                 # Local Docker Compose service stack
├── .dockerignore                      # Excludes frontend builds, .venv, and .env from Docker
├── .env.example                       # Environment variable template
├── .gitignore                         # Excludes secrets, virtualenvs, and build artifacts
├── requirements.txt                   # Cross-platform Python dependencies
└── Readme.md                          # Project documentation
```

---

## Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Desktop Shell** | Electron 35, Node.js `child_process`, Context-Isolated Preload IPC |
| **Frontend HUD** | React 19, TypeScript 5.7, Vite 6, Framer Motion, Lucide Icons, HTML5 Canvas & SVG |
| **Bridge & Transport** | FastAPI, Uvicorn (ASGI), WebSockets, Pydantic v2, `psutil` |
| **AI & NLP** | Google GenAI SDK (`google-genai`), Gemini 2.5 Flash / Pro |
| **Speech & Audio** | `SpeechRecognition`, `PyAudio`, `sounddevice`, `pyttsx3` (Windows SAPI5), `gTTS`, `pygame` |
| **Persistence & Packaging** | SQLite3, `electron-builder`, Docker & Docker Compose |

---

## Prerequisites

* **Operating System:** Windows 10 or Windows 11 (required for full native desktop windowing, Windows SAPI5 offline TTS, and OS automation).
* **Python:** Python `3.10` – `3.12` with `pip` and `venv`.
* **Node.js:** Node.js `20.x` LTS or newer with `npm`.
* **Hardware:** Working microphone (for voice commands) and speakers/headphones (for voice synthesis).
* **API Key:** A valid **Google Gemini API Key** from [Google AI Studio](https://aistudio.google.com/).

---

## Local Development Setup

### 1. Clone the Repository
```powershell
git clone [https://github.com/Swaxtik4455/ARROW.git](https://github.com/Swaxtik4455/ARROW.git)
cd ARROW
```

### 2. Configure Environment Variables
Create a `.env` file in the root directory from the provided template:
```powershell
Copy-Item .env.example .env
```
Open `.env` and add your Gemini API key:
```env
GEMINI_API_KEY=your_actual_google_gemini_api_key_here
```

### 3. Set Up the Python Virtual Environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Install Frontend Dependencies & Launch ARROW
```powershell
cd arrow-ui
npm install
npm run dev
```

**What happens on `npm run dev`:**
1. Vite starts the HUD renderer on `http://localhost:5173`.
2. Electron compiles `electron/main.ts` and `electron/preload.ts` into `dist-electron/`.
3. Electron automatically spawns `.venv\Scripts\python.exe bridge\bridge_server.py` silently in the background.
4. Once `http://127.0.0.1:8765/api/health` responds `200 OK`, the frameless **ARROW — Voice Interface** window opens and connects via WebSocket.

---

## Building the Standalone Windows Executable (`.exe`)

To package ARROW into a standalone Windows desktop application that bundles the compiled React HUD, Electron runtime, Python virtual environment, and backend scripts into a single folder:

1. Ensure no running instances of ARROW or `bridge_server.py` are locking files.
2. From inside `arrow-ui/`, run:
   ```powershell
   cd arrow-ui
   npm run dist:win
   ```
3. `electron-builder` outputs the standalone Windows application to:
   ```text
   arrow-ui/release/win-unpacked/ARROW.exe
   ```
4. **Launch:** Double-click `ARROW.exe` (or right-click -> **Send to -> Desktop (create shortcut)**). Electron automatically resolves `resources/backend/.venv/Scripts/python.exe` and starts the bridge with zero terminal windows.

> **Windows Build Tip:** If `electron-builder` reports a symbolic link privilege error during extraction on Windows, enable **Developer Mode** (`Settings -> System -> For developers -> Developer Mode = On`) or run your terminal as Administrator.

---

## Containerized Deployment with Docker

The Python FastAPI/WebSocket bridge (`bridge/bridge_server.py`) can be built and run as an isolated Linux container using the included `Dockerfile` and `docker-compose.yml`.

### Build and Start with Docker Compose
```bash
docker compose up --build -d
```

### Verify Container Health & Logs
```bash
# Check container status and healthcheck
docker ps

# Test the REST health endpoint
curl [http://127.0.0.1:8765/api/health](http://127.0.0.1:8765/api/health)

# View real-time bridge logs
docker logs -f arrow-ai-bridge
```

### Stop the Container
```bash
docker compose down
```

> **Platform Scope Note:** Docker containerizes the headless FastAPI bridge, Gemini AI engine, scheduler, and REST/WebSocket API. Native Windows GUI automation (`automation.py`), Windows SAPI5 voices (`pyttsx3`), and host microphone capture require running natively on Windows rather than inside a headless Linux container.

---

## Bridge API & WebSocket Protocol Reference

The Python bridge binds strictly to `127.0.0.1:8765` and exposes the following endpoints:

### HTTP REST Endpoints

| Method | Endpoint | Request Body | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | — | Returns bridge status, active assistant name, state, mute status, and wake-word status. |
| `POST` | `/api/command` | `{"text": "string", "speak": true}` | Routes a text command through `CommandRouter`, broadcasts reply, and optionally speaks it. |
| `POST` | `/api/voice/listen` | — | Unmutes if muted and triggers single-utterance microphone speech recognition. |
| `POST` | `/api/voice/wake` | `{"enabled": true}` | Enables or disables continuous background wake-word listening. |
| `POST` | `/api/voice/mute` | `{"muted": true}` | Mutes or unmutes TTS output and immediately stops any active speech when muted. |
| `POST` | `/api/voice/interrupt` | — | Immediately halts ongoing TTS speech playback without muting future responses. |
| `GET` | `/api/settings` | — | Retrieves current `config.py` settings along with enumerated Windows SAPI5 voices. |
| `POST` | `/api/settings` | `{"updates": {...}}` | Validates and persists updated configuration keys (`gemini_model`, `response_mode`, `speech_rate`, etc.). |
| `GET` | `/api/history?limit=30` | — | Fetches recent persisted conversation turns from SQLite. |
| `DELETE` | `/api/history` | — | Clears all stored conversation history from SQLite. |

### WebSocket Stream (`ws://127.0.0.1:8765/ws`)

Upon connection, the bridge immediately emits a state snapshot and continues streaming JSON frames:

* **State Frame:**
  ```json
  {
    "type": "state",
    "state": "IDLE | LISTENING | THINKING | SPEAKING | ERROR",
    "isMuted": false,
    "wakeWordActive": false
  }
  ```
* **Telemetry Frame (every 1.5s):**
  ```json
  {
    "type": "telemetry",
    "cpuPercent": 14.2,
    "memPercent": 48.6,
    "activeMode": "normal",
    "wakeWordActive": false
  }
  ```
* **Transcript Frame:**
  ```json
  {
    "type": "transcript",
    "sender": "USR | ARROW | SYS",
    "text": "Current local time is 10:45 AM.",
    "category": "Information",
    "timestamp": "10:45"
  }
  ```

---

## Configuration & Environment Variables

### Environment Variables (`.env`)
| Variable | Required | Description |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | **Yes** | Google Gemini API key used by `ai_engine.py` for LLM responses. |

### Runtime Settings (Configurable via HUD Settings Modal)
* **`assistant_name`:** Display and wake-word assistant identifier (default: `"ARROW"`).
* **`wake_word`:** Hotword phrase monitored during continuous listening (default: `"arrow"`).
* **`gemini_model`:** Gemini model identifier (e.g., `gemini-2.5-flash`, `gemini-2.5-pro`).
* **`response_mode`:** AI persona mode (`normal`, `detailed`, `coding`, `study`, `professional`).
* **`tts_engine`:** Speech synthesis backend (`pyttsx3` for offline Windows SAPI5 or `gtts` for neural voice).
* **`speech_rate` & `speech_volume`:** Words-per-minute speed and output gain (`0.0` – `1.0`).
* **`voice_index`:** Index of the installed Windows SAPI5 voice profile.
* **`default_city`:** Default location used for localized weather queries.

---

## Voice Commands & Keyboard Shortcuts

### Example Commands
* **Conversational AI:** *"Explain how WebSockets differ from HTTP polling"*, *"Write a Python decorator for retry logic"*
* **System & App Automation:** *"Open Calculator"*, *"Open Notepad"*, *"Open Chrome"*, *"Search YouTube for lo-fi coding beats"*
* **Productivity & Timers:** *"Set a timer for 10 minutes"*, *"Remind me to review pull requests at 5 PM"*
* **Live Information:** *"What is the weather right now?"*, *"Tell me the latest technology news"*, *"Who is Alan Turing?"*

### Global HUD Keyboard Shortcuts
| Shortcut | Action |
| :--- | :--- |
| `Ctrl + M` | Toggle voice output mute / unmute |
| `Escape` | Interrupt active speech playback or close the Settings modal |
| `Enter` | Submit command text in the Transcript input box |

---

## Security & Privacy Model

* **Loopback-Only Binding:** `bridge_server.py` binds strictly to `127.0.0.1:8765`, ensuring the control API and WebSocket stream are unreachable from external LAN or WAN interfaces.
* **Strict CORS Allowlist:** Only local HUD origins (`http://localhost:5173`, `http://127.0.0.1:5173`, and packaged local file origins) are permitted.
* **Electron Process Sandboxing:** Renderer runs with `contextIsolation: true` and `nodeIntegration: false`, exposing only explicit window control methods (`minimize`, `maximize`, `close`) via `electron/preload.ts`.
* **Secret Hygiene:** `.env`, local SQLite databases (`*.db`, `*.sqlite`), virtual environments (`.venv/`), and compiled binaries (`release/`) are excluded from version control via `.gitignore`.

---

## Troubleshooting

| Symptom | Likely Cause | Resolution |
| :--- | :--- | :--- |
| **HUD shows `DISCONNECTED` or `Failed to fetch`** | Port `8765` is blocked by an older orphaned Python process or `.venv` is missing dependencies. | Stop any running `python.exe` processes using port `8765` and verify `pip install -r requirements.txt` succeeded inside `.venv`. |
| **`ARROW.exe` opens to a blank dark window** | `vite.config.ts` is missing `base: "./"` or `dist/` was not built prior to `electron-builder`. | Ensure `base: "./"` is set in `arrow-ui/vite.config.ts`, then re-run `npm run dist:win`. |
| **Microphone does not capture voice** | Default Windows recording device is muted or `PyAudio` is missing. | Check Windows Sound Settings -> Input microphone permissions, and verify `pyaudio` is installed in `.venv`. |
| **`electron-builder` fails with symlink error** | Windows Developer Mode is disabled when extracting winCodeSign archives. | Enable **Developer Mode** in Windows Settings (`System -> For developers`) and re-run `npm run dist:win`. |