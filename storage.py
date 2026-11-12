"""
storage.py
Thread-safe JSON persistence for ARROW's memory, reminders, tasks, notes, and music.
"""

import json
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import (
    CONVERSATIONS_FILE,
    MUSIC_FILE,
    NOTES_FILE,
    REMINDERS_FILE,
    TODOS_FILE,
)

# Seeded from the user's original music.py file
INITIAL_MUSIC_SEED: Dict[str, str] = {
    "stealth": "https://www.youtube.com/watch?v=U47Tr9BB_wE",
    "march": "https://www.youtube.com/watch?v=Xqeq4b5u_Xw",
    "skyfall": "https://www.youtube.com/watch?v=DeumyOzKqgI&pp=ygUHc2t5ZmFsbA%3D%3D",
    "wolf": "https://www.youtube.com/watch?v=ThCH0U6aJpU&list=PLnrGi_-oOR6wm0Vi-1OsiLiV5ePSPs9oF&index=21",
}


class JSONStore:
    """Thread-safe reader/writer for a single JSON file."""

    def __init__(self, file_path: Path, default_data: Any) -> None:
        self.file_path = file_path
        self.default_data = default_data
        self._lock = threading.RLock()
        if not self.file_path.exists():
            self.write(default_data)

    def read(self) -> Any:
        with self._lock:
            if not self.file_path.exists():
                return self._clone_default()
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return self._clone_default()

    def write(self, data: Any) -> None:
        with self._lock:
            temp_path = self.file_path.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            temp_path.replace(self.file_path)

    def _clone_default(self) -> Any:
        return json.loads(json.dumps(self.default_data))


class StorageManager:
    """Unified local storage API across all ARROW subsystems."""

    def __init__(self) -> None:
        self.conversations = JSONStore(CONVERSATIONS_FILE, [])
        self.reminders = JSONStore(REMINDERS_FILE, [])
        self.todos = JSONStore(TODOS_FILE, [])
        self.notes = JSONStore(NOTES_FILE, [])
        self.music = JSONStore(MUSIC_FILE, INITIAL_MUSIC_SEED)

    # ---------------- Conversation History ----------------
    def append_message(self, role: str, content: str, mode: str = "normal") -> Dict[str, Any]:
        history: List[Dict[str, Any]] = self.conversations.read()
        entry = {
            "id": str(uuid.uuid4())[:8],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "role": role,  # "user" or "assistant"
            "mode": mode,
            "content": content,
        }
        history.append(entry)
        # Cap total stored archive at 500 entries to prevent unbounded disk bloat
        if len(history) > 500:
            history = history[-500:]
        self.conversations.write(history)
        return entry

    def get_recent_messages(self, limit: int = 12) -> List[Dict[str, Any]]:
        history: List[Dict[str, Any]] = self.conversations.read()
        if limit <= 0:
            return []
        return history[-limit:]

    def get_all_messages(self) -> List[Dict[str, Any]]:
        return self.conversations.read()

    def clear_messages(self) -> None:
        self.conversations.write([])

    # ---------------- Reminders ----------------
    def add_reminder(self, text: str, due_iso: str) -> Dict[str, Any]:
        items: List[Dict[str, Any]] = self.reminders.read()
        item = {
            "id": str(uuid.uuid4())[:6],
            "text": text.strip(),
            "due_iso": due_iso,
            "triggered": False,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        items.append(item)
        self.reminders.write(items)
        return item

    def get_reminders(self, include_triggered: bool = True) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = self.reminders.read()
        if include_triggered:
            return items
        return [r for r in items if not r.get("triggered", False)]

    def mark_reminder_triggered(self, reminder_id: str) -> None:
        items: List[Dict[str, Any]] = self.reminders.read()
        for item in items:
            if item["id"] == reminder_id:
                item["triggered"] = True
        self.reminders.write(items)

    def update_reminder(self, reminder_id: str, new_text: Optional[str] = None, new_due_iso: Optional[str] = None) -> bool:
        items: List[Dict[str, Any]] = self.reminders.read()
        updated = False
        for item in items:
            if item["id"] == reminder_id:
                if new_text:
                    item["text"] = new_text.strip()
                if new_due_iso:
                    item["due_iso"] = new_due_iso
                    item["triggered"] = False
                updated = True
        if updated:
            self.reminders.write(items)
        return updated

    def delete_reminder(self, reminder_id: str) -> bool:
        items: List[Dict[str, Any]] = self.reminders.read()
        filtered = [r for r in items if r["id"] != reminder_id]
        if len(filtered) != len(items):
            self.reminders.write(filtered)
            return True
        return False

    # ---------------- To-Do List ----------------
    def add_todo(self, task: str) -> Dict[str, Any]:
        items: List[Dict[str, Any]] = self.todos.read()
        item = {
            "id": str(uuid.uuid4())[:6],
            "task": task.strip(),
            "completed": False,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        items.append(item)
        self.todos.write(items)
        return item

    def get_todos(self) -> List[Dict[str, Any]]:
        return self.todos.read()

    def complete_todo(self, identifier: str) -> Optional[Dict[str, Any]]:
        items: List[Dict[str, Any]] = self.todos.read()
        needle = identifier.strip().lower()
        target = None
        for idx, item in enumerate(items, start=1):
            if (
                item["id"].lower() == needle
                or str(idx) == needle
                or needle in item["task"].lower()
            ):
                item["completed"] = True
                target = item
                break
        if target:
            self.todos.write(items)
        return target

    def delete_todo(self, identifier: str) -> bool:
        items: List[Dict[str, Any]] = self.todos.read()
        needle = identifier.strip().lower()
        new_items = []
        removed = False
        for idx, item in enumerate(items, start=1):
            if not removed and (
                item["id"].lower() == needle
                or str(idx) == needle
                or needle in item["task"].lower()
            ):
                removed = True
                continue
            new_items.append(item)
        if removed:
            self.todos.write(new_items)
        return removed

    # ---------------- Notes ----------------
    def add_note(self, title: str, content: str) -> Dict[str, Any]:
        items: List[Dict[str, Any]] = self.notes.read()
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        item = {
            "id": str(uuid.uuid4())[:6],
            "title": title.strip() or f"Note {len(items) + 1}",
            "content": content.strip(),
            "updated_at": now,
        }
        items.append(item)
        self.notes.write(items)
        return item

    def get_notes(self) -> List[Dict[str, Any]]:
        return self.notes.read()

    def search_notes(self, query: str) -> List[Dict[str, Any]]:
        q = query.strip().lower()
        return [
            n for n in self.notes.read()
            if q in n.get("title", "").lower() or q in n.get("content", "").lower()
        ]

    def update_note(self, note_id: str, title: str, content: str) -> bool:
        items: List[Dict[str, Any]] = self.notes.read()
        for item in items:
            if item["id"] == note_id:
                item["title"] = title.strip()
                item["content"] = content.strip()
                item["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                self.notes.write(items)
                return True
        return False

    def delete_note(self, identifier: str) -> bool:
        items: List[Dict[str, Any]] = self.notes.read()
        needle = identifier.strip().lower()
        filtered = [
            n for n in items
            if n["id"].lower() != needle and needle not in n["title"].lower()
        ]
        if len(filtered) != len(items):
            self.notes.write(filtered)
            return True
        return False

    # ---------------- Music Library ----------------
    def get_music_library(self) -> Dict[str, str]:
        return self.music.read()

    def add_song(self, name: str, url: str) -> None:
        lib = self.music.read()
        lib[name.strip().lower()] = url.strip()
        self.music.write(lib)

    def remove_song(self, name: str) -> bool:
        lib = self.music.read()
        key = name.strip().lower()
        if key in lib:
            del lib[key]
            self.music.write(lib)
            return True
        return False


# Shared singleton storage instance
storage = StorageManager()