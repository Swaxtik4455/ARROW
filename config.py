"""
config.py
Central configuration and persistent user settings manager for ARROW.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict
from dotenv import load_dotenv

# Base project paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
ENV_PATH = BASE_DIR / ".env"

# Ensure required runtime directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

# Load environment variables from .env
load_dotenv(dotenv_path=ENV_PATH)

SETTINGS_FILE = DATA_DIR / "settings.json"
CONVERSATIONS_FILE = DATA_DIR / "conversations.json"
REMINDERS_FILE = DATA_DIR / "reminders.json"
TODOS_FILE = DATA_DIR / "todos.json"
NOTES_FILE = DATA_DIR / "notes.json"
MUSIC_FILE = DATA_DIR / "music_library.json"

# 5 Distinct AI Personality & Response Modes
RESPONSE_MODES: Dict[str, Dict[str, str]] = {
    "normal": {
        "label": "Normal",
        "description": "Concise, natural, friendly JARVIS-style responses.",
        "instruction": (
            "Respond clearly, naturally, and concisely in 2 to 4 sentences unless "
            "more detail is explicitly asked. Sound intelligent, warm, and slightly futuristic, "
            "suitable for both reading and spoken voice output. Avoid raw markdown clutter."
        ),
    },
    "detailed": {
        "label": "Detailed",
        "description": "Comprehensive, structured explanations with examples.",
        "instruction": (
            "Provide a thorough, well-structured, comprehensive explanation covering key concepts, "
            "nuances, and practical examples while maintaining a polished assistant tone."
        ),
    },
    "coding": {
        "label": "Coding",
        "description": "Senior software engineer technical & debugging assistance.",
        "instruction": (
            "Act as a senior software engineer. Provide clean, well-commented code examples, "
            "clear debugging diagnostics, edge-case warnings, and best practices. Never claim "
            "to have executed code yourself."
        ),
    },
    "study": {
        "label": "Study",
        "description": "Beginner-friendly, step-by-step educational tutor.",
        "instruction": (
            "Explain concepts like a patient, encouraging tutor speaking to a beginner. "
            "Use simple analogies, step-by-step breakdowns, and check understanding without jargon."
        ),
    },
    "professional": {
        "label": "Professional",
        "description": "Formal, executive, business-ready communication.",
        "instruction": (
            "Maintain a formal, executive, crisp, and objective tone suitable for workplace "
            "reports, emails, and professional decision-making."
        ),
    },
}

DEFAULT_SHORTCUTS: Dict[str, str] = {
    "google": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "gmail": "https://mail.google.com",
    "github": "https://github.com",
    "linkedin": "https://www.linkedin.com",
    "wikipedia": "https://en.wikipedia.org",
    "stackoverflow": "https://stackoverflow.com",
    "chatgpt": "https://chat.openai.com",
    "gemini": "https://gemini.google.com",
}

DEFAULT_SETTINGS: Dict[str, Any] = {
    "assistant_name": "ARROW",
    "wake_word": "arrow",
    "gemini_model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash",
    "response_mode": "normal",
    "history_limit": 12,  # Number of recent messages sent to Gemini to control token usage
    "tts_engine": "pyttsx3",  # "pyttsx3" (offline/fast) or "gtts" (online/natural)
    "speech_rate": 180,  # Words per minute for pyttsx3 (100 - 260)
    "speech_volume": 0.95,  # 0.0 to 1.0
    "voice_index": 0,  # Windows SAPI5 voice index
    "listen_timeout": 5,  # Seconds to wait for speech start
    "phrase_time_limit": 12,  # Max seconds per spoken command
    "default_city": os.getenv("DEFAULT_CITY", "Lucknow").strip() or "Lucknow",
    "file_search_root": str(Path.home() / "Documents"),
    "custom_shortcuts": DEFAULT_SHORTCUTS.copy(),
    "start_on_boot": False,
}


class ConfigManager:
    """Manages environment secrets and persistent JSON application settings."""

    def __init__(self) -> None:
        self._settings: Dict[str, Any] = self._load_settings()

    def _load_settings(self) -> Dict[str, Any]:
        merged = DEFAULT_SETTINGS.copy()
        merged["custom_shortcuts"] = DEFAULT_SHORTCUTS.copy()

        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                if isinstance(saved, dict):
                    shortcuts = saved.pop("custom_shortcuts", {})
                    merged.update(saved)
                    if isinstance(shortcuts, dict):
                        merged["custom_shortcuts"].update(shortcuts)
            except (json.JSONDecodeError, OSError):
                # Preserve defaults if settings file is corrupted
                pass
        else:
            self._save_to_disk(merged)

        return merged

    def _save_to_disk(self, data: Dict[str, Any]) -> None:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get(self, key: str, default: Any = None) -> Any:
        return self._settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._settings[key] = value
        self._save_to_disk(self._settings)

    def update_many(self, updates: Dict[str, Any]) -> None:
        self._settings.update(updates)
        self._save_to_disk(self._settings)

    def all_settings(self) -> Dict[str, Any]:
        return self._settings.copy()

    def add_shortcut(self, name: str, url: str) -> None:
        clean_name = name.strip().lower()
        clean_url = url.strip()
        if not clean_url.startswith(("http://", "https://")):
            clean_url = "https://" + clean_url
        self._settings["custom_shortcuts"][clean_name] = clean_url
        self._save_to_disk(self._settings)

    @property
    def gemini_api_key(self) -> str:
        # Reload .env dynamically in case user edited it while app was open
        load_dotenv(dotenv_path=ENV_PATH, override=True)
        return os.getenv("GEMINI_API_KEY", "").strip()

    @property
    def news_api_key(self) -> str:
        load_dotenv(dotenv_path=ENV_PATH, override=True)
        return os.getenv("NEWS_API_KEY", "").strip()


# Shared singleton configuration instance
config = ConfigManager()