"""
main.py
Main entry point for ARROW (Adaptive Responsive Real-time Operations & Workflow Assistant).
Connects voice I/O, command routing, productivity scheduler, and the CustomTkinter desktop GUI.
"""

import threading
import tkinter as tk
from typing import Optional

from automation import DesktopAutomation
from command_router import CommandRouter
from config import config
from entertainment import EntertainmentManager
from gui import ArrowDesktopGUI
from info_services import InfoServices
from productivity import ProductivityManager
from voice_input import VoiceInputManager
from voice_output import VoiceOutputManager


class ArrowApplication:
    """Coordinates lifecycle and cross-module events for ARROW."""

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.gui: Optional[ArrowDesktopGUI] = None

        # 1. Initialize domain subsystems
        self.automation = DesktopAutomation()
        self.info_services = InfoServices()
        self.entertainment = EntertainmentManager()
        self.productivity = ProductivityManager(on_alert=self._handle_scheduler_alert)

        # 2. Initialize Voice Output (TTS)
        self.voice_out = VoiceOutputManager(on_state_change=self._handle_tts_state)

        # 3. Initialize Command Router
        self.router = CommandRouter(
            automation=self.automation,
            productivity=self.productivity,
            info_services=self.info_services,
            entertainment=self.entertainment,
            speaker=self.voice_out,
        )

        # 4. Initialize Voice Input (STT + Wake Word)
        self.voice_in = VoiceInputManager(
            on_command=self._handle_voice_command,
            on_wake=self._handle_wake_detected,
            on_status=self._handle_stt_status,
            on_error=self._handle_stt_error,
        )

        # 5. Initialize Modern CustomTkinter Desktop GUI
        self.gui = ArrowDesktopGUI(
            root=self.root,
            on_submit_command=self.process_user_command,
            voice_in=self.voice_in,
            voice_out=self.voice_out,
            automation=self.automation,
            productivity=self.productivity,
            on_shutdown=self.shutdown,
        )

    def start(self) -> None:
        name = config.get("assistant_name", "ARROW")
        welcome = (
            f"{name} online and ready. Click 'Speak' or enable 'Wake Word' for voice control, "
            "or type 'help' below to view all commands."
        )
        if self.gui:
            self.gui.append_chat(name, welcome, "assistant")
            self.gui.log_activity(f"{name} initialized (Model: {config.get('gemini_model')})")
        self.voice_out.speak(f"Initializing {name}. All systems operational.")
        self.root.mainloop()

    # ------------------------------------------------------------------
    # Command Execution Pipeline (Runs in Worker Threads)
    # ------------------------------------------------------------------
    def process_user_command(self, text: str, speak_response: bool = True) -> None:
        if self.gui:
            self.gui.enqueue_event("thinking", True)

        try:
            result = self.router.route(text)
            reply = result.get("reply", "")
            should_speak = speak_response and result.get("speak", True)
            category = result.get("category", "General")

            if self.gui and reply:
                self.gui.enqueue_event(
                    "chat",
                    {
                        "sender": config.get("assistant_name", "ARROW"),
                        "text": reply,
                        "tag": "assistant",
                    },
                )
                self.gui.enqueue_event("log", f"Executed [{category}]")

            if should_speak and reply:
                self.voice_out.speak(reply)
        finally:
            if self.gui:
                self.gui.enqueue_event("thinking", False)

    # ------------------------------------------------------------------
    # Background Worker Callbacks -> GUI Queue
    # ------------------------------------------------------------------
    def _handle_voice_command(self, recognized_text: str) -> None:
        if self.gui:
            self.gui.enqueue_event(
                "chat", {"sender": "You (Voice)", "text": recognized_text, "tag": "user"}
            )
            self.gui.enqueue_event("log", f"Voice recognized: {recognized_text}")
        threading.Thread(
            target=self.process_user_command, args=(recognized_text, True), daemon=True
        ).start()

    def _handle_wake_detected(self) -> None:
        if self.gui:
            self.gui.enqueue_event("log", "Wake word detected!")
        self.voice_out.speak("Yes?")

    def _handle_stt_status(self, status_text: str, is_listening: bool) -> None:
        if self.gui:
            self.gui.enqueue_event("listening", (status_text, is_listening))

    def _handle_stt_error(self, error_msg: str) -> None:
        if self.gui:
            self.gui.enqueue_event("log", f"Voice notice: {error_msg}")
            self.gui.enqueue_event(
                "chat", {"sender": "Voice System", "text": error_msg, "tag": "system"}
            )

    def _handle_tts_state(self, is_speaking: bool) -> None:
        if self.gui:
            self.gui.enqueue_event("speaking", is_speaking)

    def _handle_scheduler_alert(self, alert_message: str) -> None:
        if self.gui:
            self.gui.enqueue_event("alert", alert_message)
        self.voice_out.speak(alert_message)

    def shutdown(self) -> None:
        self.voice_in.shutdown()
        self.productivity.shutdown()
        self.voice_out.shutdown()


if __name__ == "__main__":
    app = ArrowApplication()
    app.start()