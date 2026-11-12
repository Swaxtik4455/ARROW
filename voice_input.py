"""
voice_input.py
Non-blocking SpeechRecognition pipeline with wake-word detection ("ARROW"),
single-calibrated mic stream, background noise adjustment, and optional offline Vosk support.
"""

import json
import os
import threading
import time
from typing import Callable, Optional

import speech_recognition as sr

from config import BASE_DIR, config

# Optional offline Vosk model detection (place 'vosk-model' folder in project root if desired)
VOSK_MODEL_DIR = BASE_DIR / "vosk-model"
try:
    from vosk import KaldiRecognizer, Model as VoskModel
    VOSK_AVAILABLE = VOSK_MODEL_DIR.exists()
except ImportError:
    VOSK_AVAILABLE = False


class VoiceInputManager:
    """Manages continuous wake-word listening and manual push-to-talk capture."""

    def __init__(
        self,
        on_command: Callable[[str], None],
        on_wake: Callable[[], None],
        on_status: Callable[[str, bool], None],
        on_error: Callable[[str], None],
    ) -> None:
        self.on_command = on_command
        self.on_wake = on_wake
        self.on_status = on_status  # (status_text, is_listening)
        self.on_error = on_error

        self._recognizer = sr.Recognizer()
        self._recognizer.dynamic_energy_threshold = True
        self._recognizer.pause_threshold = 0.8

        self._continuous_enabled = False
        self._single_listen_requested = False
        self._shutdown_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        self._vosk_model = None
        if VOSK_AVAILABLE:
            try:
                self._vosk_model = VoskModel(str(VOSK_MODEL_DIR))
            except Exception:
                self._vosk_model = None

    @property
    def is_continuous_active(self) -> bool:
        return self._continuous_enabled

    def start_continuous(self) -> None:
        """Enables always-on wake-word listening in a single background thread."""
        with self._lock:
            self._continuous_enabled = True
            self._ensure_worker_running()

    def stop_continuous(self) -> None:
        """Stops continuous wake-word listening."""
        with self._lock:
            self._continuous_enabled = False
        self.on_status("Standby", False)

    def trigger_single_listen(self) -> None:
        """Captures one spoken command immediately (for GUI Microphone button)."""
        with self._lock:
            self._single_listen_requested = True
            self._ensure_worker_running()

    def shutdown(self) -> None:
        """Terminates voice listener cleanly on exit."""
        self._shutdown_event.set()
        self._continuous_enabled = False
        self._single_listen_requested = False

    def _ensure_worker_running(self) -> None:
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(
                target=self._listen_worker, name="ARROW-STT", daemon=True
            )
            self._thread.start()

    def _transcribe_audio(self, audio: sr.AudioData) -> str:
        """Transcribes audio via Google STT first, falling back to offline Vosk if offline."""
        try:
            return self._recognizer.recognize_google(audio, language="en-IN").strip()
        except sr.UnknownValueError:
            return ""
        except sr.RequestError:
            # Internet unavailable — attempt offline Vosk if configured
            if self._vosk_model is not None:
                try:
                    raw_wav = audio.get_raw_data(convert_rate=16000, convert_width=2)
                    rec = KaldiRecognizer(self._vosk_model, 16000)
                    rec.AcceptWaveform(raw_wav)
                    res = json.loads(rec.FinalResult())
                    return str(res.get("text", "")).strip()
                except Exception:
                    pass
            raise

    def _listen_worker(self) -> None:
        try:
            mic = sr.Microphone()
        except OSError:
            self._continuous_enabled = False
            self._single_listen_requested = False
            self.on_status("No Microphone", False)
            self.on_error(
                "No microphone detected. Check Windows Privacy > Microphone permissions "
                "or use the text input box below."
            )
            return
        except Exception as e:
            self._continuous_enabled = False
            self._single_listen_requested = False
            self.on_status("Mic Error", False)
            self.on_error(f"Microphone initialization failed: {e}")
            return

        try:
            # Open microphone ONCE and calibrate ambient noise cleanly
            with mic as source:
                self.on_status("Calibrating mic...", True)
                self._recognizer.adjust_for_ambient_noise(source, duration=0.8)

                while not self._shutdown_event.is_set():
                    if not self._continuous_enabled and not self._single_listen_requested:
                        self.on_status("Standby", False)
                        time.sleep(0.2)
                        continue

                    # Mode A: Direct push-to-talk command capture
                    if self._single_listen_requested:
                        self._single_listen_requested = False
                        self._capture_and_dispatch_command(source)
                        continue

                    # Mode B: Continuous wake-word listening
                    wake_word = str(config.get("wake_word", "arrow")).lower().strip() or "arrow"
                    self.on_status(f"Listening for '{wake_word.upper()}'...", True)
                    try:
                        audio = self._recognizer.listen(
                            source, timeout=3, phrase_time_limit=4
                        )
                        heard = self._transcribe_audio(audio).lower()
                        if wake_word in heard:
                            # Check if user spoke command in the same breath: "Arrow what time is it"
                            after_wake = heard.split(wake_word, 1)[1].strip(" ,.!?")
                            self.on_wake()
                            if len(after_wake) >= 3:
                                self.on_command(after_wake)
                            else:
                                time.sleep(0.35)
                                self._capture_and_dispatch_command(source)
                    except sr.WaitTimeoutError:
                        continue
                    except sr.RequestError:
                        self.on_error(
                            "Speech recognition service unreachable (offline). "
                            "Type commands or install an offline Vosk model."
                        )
                        time.sleep(2.0)
                    except Exception:
                        time.sleep(0.3)

        except Exception as e:
            self.on_status("Mic Disconnected", False)
            self.on_error(f"Microphone stream interrupted: {e}")
            self._continuous_enabled = False

    def _capture_and_dispatch_command(self, source: sr.AudioSource) -> None:
        timeout = int(config.get("listen_timeout", 5))
        phrase_limit = int(config.get("phrase_time_limit", 12))
        self.on_status("Listening for command...", True)

        try:
            audio = self._recognizer.listen(
                source, timeout=timeout, phrase_time_limit=phrase_limit
            )
            self.on_status("Processing speech...", False)
            command = self._transcribe_audio(audio)
            if command:
                self.on_command(command)
            else:
                self.on_error("I didn't catch that clearly. Please try again.")
        except sr.WaitTimeoutError:
            self.on_error("Listening timed out before any speech was detected.")
        except sr.RequestError:
            self.on_error("Internet unavailable for speech-to-text. Use text input or offline Vosk.")
        except Exception as e:
            self.on_error(f"Voice capture error: {e}")
        finally:
            if not self._continuous_enabled:
                self.on_status("Standby", False)