"""
productivity.py
Personal productivity suite: persistent reminders, to-do list, notes, countdown timer, and stopwatch.
"""

import re
import threading
import time
from datetime import datetime, timedelta
from typing import Callable, Optional

from storage import storage


class ProductivityManager:
    """Manages reminders, tasks, notes, non-blocking timers, and a stopwatch."""

    def __init__(self, on_alert: Optional[Callable[[str], None]] = None) -> None:
        self.on_alert = on_alert
        self._shutdown_event = threading.Event()

        # Timer state
        self._timer_remaining: int = 0
        self._timer_running: bool = False
        self._timer_paused: bool = False
        self._timer_lock = threading.Lock()

        # Stopwatch state
        self._sw_start: Optional[float] = None
        self._sw_elapsed: float = 0.0

        self._scheduler_thread = threading.Thread(
            target=self._background_tick, name="ARROW-Scheduler", daemon=True
        )
        self._scheduler_thread.start()

    def shutdown(self) -> None:
        self._shutdown_event.set()

    def _trigger_alert(self, message: str) -> None:
        if self.on_alert:
            try:
                self.on_alert(message)
            except Exception:
                pass

    def _background_tick(self) -> None:
        """Checks due reminders and decrements active timer every second."""
        while not self._shutdown_event.is_set():
            now = datetime.now()

            # 1. Check due persistent reminders
            for rem in storage.get_reminders(include_triggered=False):
                try:
                    due_dt = datetime.fromisoformat(rem["due_iso"])
                    if now >= due_dt:
                        storage.mark_reminder_triggered(rem["id"])
                        self._trigger_alert(f"Reminder due: {rem['text']}")
                except Exception:
                    continue

            # 2. Decrement countdown timer
            fire_timer = False
            with self._timer_lock:
                if self._timer_running and not self._timer_paused:
                    if self._timer_remaining > 0:
                        self._timer_remaining -= 1
                    if self._timer_remaining <= 0:
                        self._timer_running = False
                        fire_timer = True

            if fire_timer:
                self._trigger_alert("Time is up! Your countdown timer has finished.")

            time.sleep(1.0)

    # ---------------- Reminders ----------------
    def parse_and_add_reminder(self, raw_command: str) -> str:
        """Parses relative ('in 30 minutes') or clock ('at 5 PM', 'tomorrow at 9 AM') reminders."""
        now = datetime.now()
        text = re.sub(r"^remind me\s+(?:to\s+)?", "", raw_command.strip(), flags=re.IGNORECASE)
        due_dt: Optional[datetime] = None

        # Pattern 1: "in/after X minutes/hours/seconds"
        rel_match = re.search(
            r"\b(?:in|after)\s+(\d+)\s+(second|seconds|sec|minute|minutes|min|hour|hours|hr)\b",
            text,
            flags=re.IGNORECASE,
        )
        if rel_match:
            amount = int(rel_match.group(1))
            unit = rel_match.group(2).lower()
            if unit.startswith("sec"):
                due_dt = now + timedelta(seconds=amount)
            elif unit.startswith("min"):
                due_dt = now + timedelta(minutes=amount)
            else:
                due_dt = now + timedelta(hours=amount)
            text = (text[: rel_match.start()] + text[rel_match.end() :]).strip(" ,.")

        # Pattern 2: "[tomorrow] at HH[:MM] [am/pm]"
        if due_dt is None:
            is_tomorrow = bool(re.search(r"\btomorrow\b", text, flags=re.IGNORECASE))
            time_match = re.search(
                r"\b(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b",
                text,
                flags=re.IGNORECASE,
            )
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2) or 0)
                meridiem = (time_match.group(3) or "").lower()
                if meridiem == "pm" and hour < 12:
                    hour += 12
                elif meridiem == "am" and hour == 12:
                    hour = 0

                target_date = (now + timedelta(days=1)).date() if is_tomorrow else now.date()
                due_dt = datetime(target_date.year, target_date.month, target_date.day, hour % 24, minute % 60)
                if due_dt <= now and not is_tomorrow:
                    due_dt += timedelta(days=1)

                text = re.sub(r"\btomorrow\b", "", text, flags=re.IGNORECASE)
                text = text.replace(time_match.group(0), "").strip(" ,.")
            elif is_tomorrow:
                due_dt = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
                text = re.sub(r"\btomorrow\b", "", text, flags=re.IGNORECASE).strip(" ,.")

        if due_dt is None:
            due_dt = now + timedelta(minutes=15)

        clean_task = text or "Scheduled reminder"
        item = storage.add_reminder(clean_task, due_dt.isoformat(timespec="seconds"))
        formatted_time = due_dt.strftime("%b %d at %I:%M %p")
        return f"Reminder saved (ID {item['id']}): '{clean_task}' set for {formatted_time}."

    def list_reminders(self) -> str:
        upcoming = storage.get_reminders(include_triggered=False)
        if not upcoming:
            return "You have no upcoming reminders."
        lines = []
        for r in upcoming:
            dt = datetime.fromisoformat(r["due_iso"]).strftime("%b %d, %I:%M %p")
            lines.append(f"• [{r['id']}] {r['text']} ({dt})")
        return "Upcoming reminders:\n" + "\n".join(lines)

    # ---------------- To-Do Manager ----------------
    def add_todo(self, task: str) -> str:
        if not task.strip():
            return "Please specify a task description."
        item = storage.add_todo(task)
        return f"Added task [{item['id']}]: {item['task']}"

    def list_todos(self, only_pending: bool = False, only_completed: bool = False) -> str:
        todos = storage.get_todos()
        if only_pending:
            todos = [t for t in todos if not t["completed"]]
        elif only_completed:
            todos = [t for t in todos if t["completed"]]

        if not todos:
            return "No matching tasks found."
        lines = [
            f"{idx}. [{'✓' if t['completed'] else ' '}] ({t['id']}) {t['task']}"
            for idx, t in enumerate(todos, start=1)
        ]
        return "Your To-Do List:\n" + "\n".join(lines)

    def complete_todo(self, identifier: str) -> str:
        item = storage.complete_todo(identifier)
        if item:
            return f"Marked task completed: '{item['task']}'."
        return f"Could not find a task matching '{identifier}'."

    def delete_todo(self, identifier: str) -> str:
        if storage.delete_todo(identifier):
            return f"Deleted task matching '{identifier}'."
        return f"Could not find a task matching '{identifier}'."

    # ---------------- Notes Manager ----------------
    def add_note(self, content: str, title: Optional[str] = None) -> str:
        if not content.strip():
            return "Cannot save an empty note."
        auto_title = title or (" ".join(content.split()[:4]).capitalize() + "...")
        note = storage.add_note(auto_title, content)
        return f"Saved note [{note['id']}] '{note['title']}'."

    def list_notes(self) -> str:
        notes = storage.get_notes()
        if not notes:
            return "You don't have any saved notes yet."
        lines = [f"• [{n['id']}] {n['title']}: {n['content'][:90]}" for n in notes[-10:]]
        return "Saved notes:\n" + "\n".join(lines)

    def search_notes(self, query: str) -> str:
        matches = storage.search_notes(query)
        if not matches:
            return f"No notes found containing '{query}'."
        lines = [f"• [{n['id']}] {n['title']}: {n['content']}" for n in matches]
        return f"Notes matching '{query}':\n" + "\n".join(lines)

    # ---------------- Timer & Stopwatch ----------------
    def start_timer(self, duration_str: str) -> str:
        match = re.search(
            r"(\d+)\s*(hour|hours|hr|minute|minutes|min|second|seconds|sec)",
            duration_str.lower(),
        )
        if not match:
            return "Specify a valid duration, for example: 'set timer 5 minutes'."

        val = int(match.group(1))
        unit = match.group(2)
        seconds = val * 3600 if unit.startswith("h") else (val * 60 if unit.startswith("m") else val)

        with self._timer_lock:
            self._timer_remaining = seconds
            self._timer_running = True
            self._timer_paused = False

        return f"Timer started for {val} {unit}."

    def pause_timer(self) -> str:
        with self._timer_lock:
            if not self._timer_running:
                return "No timer is currently active."
            self._timer_paused = True
            rem = self._timer_remaining
        return f"Timer paused with {rem} seconds remaining."

    def resume_timer(self) -> str:
        with self._timer_lock:
            if not self._timer_running or not self._timer_paused:
                return "There is no paused timer to resume."
            self._timer_paused = False
            rem = self._timer_remaining
        return f"Timer resumed ({rem} seconds remaining)."

    def cancel_timer(self) -> str:
        with self._timer_lock:
            if not self._timer_running:
                return "No active timer to cancel."
            self._timer_running = False
            self._timer_paused = False
            self._timer_remaining = 0
        return "Timer cancelled."

    def start_stopwatch(self) -> str:
        self._sw_start = time.time()
        self._sw_elapsed = 0.0
        return "Stopwatch started."

    def stop_stopwatch(self) -> str:
        if self._sw_start is None:
            return "Stopwatch is not running."
        total = self._sw_elapsed + (time.time() - self._sw_start)
        self._sw_start = None
        mins, secs = divmod(total, 60)
        return f"Stopwatch stopped at {int(mins)} minute(s) and {secs:.1f} seconds."