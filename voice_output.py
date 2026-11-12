"""
voice_output.py
Thread-safe, interruptible Text-to-Speech manager for ARROW.
Supports offline pyttsx3 (primary) and online gTTS + pygame (optional) with guaranteed temp cleanup.
"""

import os
import queue
import re
import tempfile
import threading
from typing import Callable, List, Optional

import pyttsx3

from config import config

try:
    import pygame
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False


class VoiceOutputManager:
    """Background worker that speaks queued messages without freezing the GUI."""

    def __init__(self, on_state_change: Optional[Callable[[bool], None]] = None) -> None:
        self._queue: queue.Queue[str] = queue.Queue()
        self._stop_event = threading.Event()
        self._shutdown_event = threading.Event()
        self._is_speaking = False
        self._on_state_change = on_state_change
        self._active_engine: Optional[pyttsx3.Engine] = None

        self._worker = threading.Thread(target=self._run_loop, name="ARROW-TTS", daemon=True)
        self._worker.start()

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking

    def _notify_state(self, speaking: bool) -> None:
        self._is_speaking = speaking
        if self._on_state_change:
            try:
                self._on_state_change(speaking)
            except Exception:
                pass

    @staticmethod
    def _clean_text_for_speech(text: str) -> str:
        """Strips markdown symbols and long URLs so spoken output sounds natural."""
        cleaned = re.sub(r"https?://\S+", "link", text)
        cleaned = re.sub(r"[`*_#>~]", "", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        # Keep spoken output reasonably concise if user pasted a giant wall of text
        if len(cleaned) > 900:
            cleaned = cleaned[:900] + "... Full details are displayed on your screen."
        return cleaned

    def speak(self, text: str) -> None:
        """Queues text to be spoken asynchronously."""
        cleaned = self._clean_text_for_speech(text)
        if not cleaned:
            return
        self._stop_event.clear()
        self._queue.put(cleaned)

    def stop(self) -> None:
        """Immediately stops current speech and flushes queued utterances."""
        self._stop_event.set()
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except queue.Empty:
                break

        if self._active_engine is not None:
            try:
                self._active_engine.stop()
            except Exception:
                pass

        if GTTS_AVAILABLE:
            try:
                if pygame.mixer.get_init():
                    pygame.mixer.music.stop()
            except Exception:
                pass

        self._notify_state(False)

    def shutdown(self) -> None:
        """Cleanly terminates the TTS worker thread on application exit."""
        self._shutdown_event.set()
        self.stop()

    def get_available_voices(self) -> List[str]:
        """Returns installed Windows SAPI5 voice names for Settings UI."""
        try:
            temp_engine = pyttsx3.init()
            voices = temp_engine.getProperty("voices") or []
            names = [v.name for v in voices]
            temp_engine.stop()
            return names or ["Default System Voice"]
        except Exception:
            return ["Default System Voice"]

    def _run_loop(self) -> None:
        while not self._shutdown_event.is_set():
            try:
                text = self._queue.get(timeout=0.25)
            except queue.Empty:
                continue

            if self._stop_event.is_set():
                self._queue.task_done()
                continue

            self._notify_state(True)
            try:
                engine_choice = str(config.get("tts_engine", "pyttsx3")).lower()
                if engine_choice == "gtts" and GTTS_AVAILABLE:
                    self._speak_gtts(text)
                else:
                    self._speak_pyttsx3(text)
            except Exception:
                # Fallback to offline pyttsx3 if online gTTS fails (e.g., no internet)
                try:
                    self._speak_pyttsx3(text)
                except Exception:
                    pass
            finally:
                self._notify_state(False)
                self._queue.task_done()

    def _speak_pyttsx3(self, text: str) -> None:
        engine = pyttsx3.init()
        self._active_engine = engine
        try:
            rate = int(config.get("speech_rate", 180))
            volume = float(config.get("speech_volume", 0.95))
            voice_idx = int(config.get("voice_index", 0))

            engine.setProperty("rate", max(100, min(300, rate)))
            engine.setProperty("volume", max(0.0, min(1.0, volume)))

            voices = engine.getProperty("voices") or []
            if 0 <= voice_idx < len(voices):
                engine.setProperty("voice", voices[voice_idx].id)

            engine.say(text)
            engine.runAndWait()
        finally:
            self._active_engine = None
            try:
                engine.stop()
            except Exception:
                pass

    def _speak_gtts(self, text: str) -> None:
        temp_path = ""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                temp_path = tmp.name

            tts = gTTS(text=text, lang="en")
            tts.save(temp_path)

            if not pygame.mixer.get_init():
                pygame.mixer.init()

            pygame.mixer.music.set_volume(float(config.get("speech_volume", 0.95)))
            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.play()

            clock = pygame.time.Clock()
            while pygame.mixer.music.get_busy():
                if self._stop_event.is_set() or self._shutdown_event.is_set():
                    pygame.mixer.music.stop()
                    break
                clock.tick(15)

            pygame.mixer.music.unload()
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass