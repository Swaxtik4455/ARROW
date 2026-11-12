"""
bridge/bridge_server.py
Standalone FastAPI + WebSocket communication adapter for ARROW.
Imports existing backend modules as READ-ONLY without modifying any backend source file.
"""

import asyncio
import sys
import threading
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import psutil
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure project root is on sys.path so existing backend modules import cleanly
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from automation import DesktopAutomation
from command_router import CommandRouter
from config import config
from entertainment import EntertainmentManager
from info_services import InfoServices
from productivity import ProductivityManager
from storage import storage
from voice_input import VoiceInputManager
from voice_output import VoiceOutputManager


class CommandRequest(BaseModel):
    text: str
    speak: bool = True


class SettingsUpdateRequest(BaseModel):
    updates: Dict[str, Any]


class MuteRequest(BaseModel):
    muted: bool


class WakeRequest(BaseModel):
    enabled: bool


class ArrowBridgeController:
    """Thread-safe headless orchestrator connecting existing ARROW backend to WebSockets/HTTP."""

    def __init__(self) -> None:
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.clients: Set[WebSocket] = set()

        self.state: str = "IDLE"
        self.is_muted: bool = False
        self._is_listening: bool = False
        self._is_thinking: bool = False
        self._is_speaking: bool = False

        # 1. Initialize untouched backend subsystems
        self.automation = DesktopAutomation()
        self.info_services = InfoServices()
        self.entertainment = EntertainmentManager()
        self.productivity = ProductivityManager(on_alert=self._on_scheduler_alert)
        self.voice_out = VoiceOutputManager(on_state_change=self._on_tts_state)

        self.router = CommandRouter(
            automation=self.automation,
            productivity=self.productivity,
            info_services=self.info_services,
            entertainment=self.entertainment,
            speaker=self.voice_out,
        )

        self.voice_in = VoiceInputManager(
            on_command=self._on_voice_command,
            on_wake=self._on_wake_detected,
            on_status=self._on_stt_status,
            on_error=self._on_stt_error,
        )

    # ------------------------------------------------------------------
    # WebSocket Broadcast Helpers (Thread-Safe -> Asyncio Loop)
    # ------------------------------------------------------------------
    def _broadcast_threadsafe(self, payload: Dict[str, Any]) -> None:
        if self.loop is None or self.loop.is_closed():
            return
        asyncio.run_coroutine_threadsafe(self._broadcast(payload), self.loop)

    async def _broadcast(self, payload: Dict[str, Any]) -> None:
        if not self.clients:
            return
        stale: List[WebSocket] = []
        for ws in list(self.clients):
            try:
                await ws.send_json(payload)
            except Exception:
                stale.append(ws)
        for ws in stale:
            self.clients.discard(ws)

    def _recompute_and_broadcast_state(self) -> None:
        if self._is_thinking:
            new_state = "THINKING"
        elif self._is_speaking:
            new_state = "SPEAKING"
        elif self._is_listening:
            new_state = "LISTENING"
        else:
            new_state = "IDLE"

        self.state = new_state
        self._broadcast_threadsafe(
            {
                "type": "state",
                "state": new_state,
                "isMuted": self.is_muted,
                "wakeWordActive": self.voice_in.is_continuous_active,
            }
        )

    # ------------------------------------------------------------------
    # Backend Callbacks
    # ------------------------------------------------------------------
    def _on_tts_state(self, speaking: bool) -> None:
        self._is_speaking = bool(speaking)
        self._recompute_and_broadcast_state()

    def _on_stt_status(self, status_text: str, is_listening: bool) -> None:
        self._is_listening = bool(is_listening)
        self._recompute_and_broadcast_state()
        self._broadcast_threadsafe(
            {
                "type": "stt_status",
                "text": status_text,
                "isListening": bool(is_listening),
            }
        )

    def _on_wake_detected(self) -> None:
        if not self.is_muted:
            self.voice_out.speak("Yes?")

    def _on_stt_error(self, error_msg: str) -> None:
        self._is_listening = False
        self.state = "ERROR"
        self._broadcast_threadsafe(
            {
                "type": "transcript",
                "sender": "SYS",
                "text": error_msg,
                "timestamp": datetime.now().strftime("%H:%M"),
            }
        )
        self._broadcast_threadsafe(
            {
                "type": "state",
                "state": "ERROR",
                "isMuted": self.is_muted,
                "wakeWordActive": self.voice_in.is_continuous_active,
            }
        )
        # Return gracefully to IDLE after brief error indicator
        threading.Timer(2.5, self._recompute_and_broadcast_state).start()

    def _on_voice_command(self, recognized_text: str) -> None:
        self._broadcast_threadsafe(
            {
                "type": "transcript",
                "sender": "USR",
                "text": recognized_text,
                "timestamp": datetime.now().strftime("%H:%M"),
            }
        )
        threading.Thread(
            target=self.execute_command,
            args=(recognized_text, True),
            daemon=True,
        ).start()

    def _on_scheduler_alert(self, alert_message: str) -> None:
        self._broadcast_threadsafe(
            {
                "type": "transcript",
                "sender": "SYS",
                "text": alert_message,
                "timestamp": datetime.now().strftime("%H:%M"),
            }
        )
        if not self.is_muted:
            self.voice_out.speak(alert_message)

    # ------------------------------------------------------------------
    # Command Execution Pipeline
    # ------------------------------------------------------------------
    def execute_command(self, text: str, speak_response: bool = True) -> Dict[str, Any]:
        clean = text.strip()
        if not clean:
            return {"reply": "", "speak": False, "category": "System"}

        self._is_thinking = True
        self._recompute_and_broadcast_state()

        try:
            result = self.router.route(clean)
            reply = result.get("reply", "")
            should_speak = speak_response and result.get("speak", True) and not self.is_muted
            category = result.get("category", "General")

            if reply:
                self._broadcast_threadsafe(
                    {
                        "type": "transcript",
                        "sender": "ARROW",
                        "text": reply,
                        "category": category,
                        "timestamp": datetime.now().strftime("%H:%M"),
                    }
                )

            if should_speak and reply:
                self.voice_out.speak(reply)

            return result
        except Exception as exc:
            err = f"Bridge execution error: {exc}"
            self._broadcast_threadsafe(
                {
                    "type": "transcript",
                    "sender": "SYS",
                    "text": err,
                    "timestamp": datetime.now().strftime("%H:%M"),
                }
            )
            return {"reply": err, "speak": False, "category": "Error"}
        finally:
            self._is_thinking = False
            self._recompute_and_broadcast_state()

    def shutdown(self) -> None:
        self.voice_in.shutdown()
        self.productivity.shutdown()
        self.voice_out.shutdown()


bridge = ArrowBridgeController()


async def _telemetry_broadcaster() -> None:
    """Streams real CPU and RAM utilization over WebSockets every 1.5 seconds."""
    psutil.cpu_percent(interval=None)
    while True:
        await asyncio.sleep(1.5)
        if bridge.clients:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory().percent
            await bridge._broadcast(
                {
                    "type": "telemetry",
                    "cpuPercent": cpu,
                    "memPercent": mem,
                    "activeMode": config.get("response_mode", "normal"),
                    "wakeWordActive": bridge.voice_in.is_continuous_active,
                }
            )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    bridge.loop = asyncio.get_running_loop()
    telemetry_task = asyncio.create_task(_telemetry_broadcaster())
    try:
        yield
    finally:
        telemetry_task.cancel()
        bridge.shutdown()


app = FastAPI(title="ARROW Local Bridge", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check() -> Dict[str, Any]:
    return {
        "status": "online",
        "assistant": config.get("assistant_name", "ARROW"),
        "state": bridge.state,
        "isMuted": bridge.is_muted,
        "wakeWordActive": bridge.voice_in.is_continuous_active,
    }


@app.post("/api/command")
async def post_command(req: CommandRequest) -> Dict[str, Any]:
    result = await asyncio.to_thread(bridge.execute_command, req.text, req.speak)
    return result


@app.post("/api/voice/listen")
def trigger_listen() -> Dict[str, Any]:
    if bridge.is_muted:
        bridge.is_muted = False
    bridge.voice_in.trigger_single_listen()
    return {"ok": True, "state": "LISTENING"}


@app.post("/api/voice/wake")
def set_wake_word(req: WakeRequest) -> Dict[str, Any]:
    if req.enabled:
        bridge.voice_in.start_continuous()
    else:
        bridge.voice_in.stop_continuous()
    bridge._recompute_and_broadcast_state()
    return {"ok": True, "wakeWordActive": bridge.voice_in.is_continuous_active}


@app.post("/api/voice/mute")
def set_mute(req: MuteRequest) -> Dict[str, Any]:
    bridge.is_muted = req.muted
    if bridge.is_muted:
        bridge.voice_out.stop()
    bridge._recompute_and_broadcast_state()
    return {"ok": True, "isMuted": bridge.is_muted}


@app.post("/api/voice/interrupt")
def interrupt_speech() -> Dict[str, Any]:
    bridge.voice_out.stop()
    bridge._recompute_and_broadcast_state()
    return {"ok": True, "state": bridge.state}


@app.get("/api/settings")
def get_settings() -> Dict[str, Any]:
    data = config.all_settings()
    data["available_voices"] = bridge.voice_out.get_available_voices()
    return data


@app.post("/api/settings")
def update_settings(req: SettingsUpdateRequest) -> Dict[str, Any]:
    allowed_keys = {
        "assistant_name",
        "wake_word",
        "gemini_model",
        "response_mode",
        "tts_engine",
        "speech_rate",
        "speech_volume",
        "voice_index",
        "default_city",
        "history_limit",
    }
    filtered = {k: v for k, v in req.updates.items() if k in allowed_keys}
    if filtered:
        config.update_many(filtered)
    updated = config.all_settings()
    updated["available_voices"] = bridge.voice_out.get_available_voices()
    return updated


@app.get("/api/history")
def get_history(limit: int = 30) -> Dict[str, Any]:
    return {"messages": storage.get_recent_messages(limit=limit)}


@app.delete("/api/history")
def clear_history() -> Dict[str, Any]:
    storage.clear_messages()
    return {"ok": True}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    bridge.clients.add(websocket)
    try:
        # Send immediate initial snapshot on connect
        await websocket.send_json(
            {
                "type": "state",
                "state": bridge.state,
                "isMuted": bridge.is_muted,
                "wakeWordActive": bridge.voice_in.is_continuous_active,
            }
        )
        while True:
            # Keep connection alive; client actions use REST endpoints
            await websocket.receive_text()
    except WebSocketDisconnect:
        bridge.clients.discard(websocket)
    except Exception:
        bridge.clients.discard(websocket)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")