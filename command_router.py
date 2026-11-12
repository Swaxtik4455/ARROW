"""
command_router.py
Modular, security-allowlisted command router for ARROW.
Stage 1: Fast deterministic local routing (0 API calls, works offline).
Stage 2: Gemini structured intent classification + allowlist validation.
Stage 3: Multi-turn conversational AI response.
"""

import re
from typing import Any, Callable, Dict, Optional

from ai_engine import ai_engine
from config import RESPONSE_MODES, config
from storage import storage


class CommandRouter:
    """Routes user text/voice commands safely across local modules and Gemini AI."""

    def __init__(
        self,
        automation: Any,
        productivity: Any,
        info_services: Any,
        entertainment: Any,
        speaker: Any = None,
    ) -> None:
        self.automation = automation
        self.productivity = productivity
        self.info = info_services
        self.entertainment = entertainment
        self.speaker = speaker

        # Stores pending destructive action awaiting explicit "confirm" / "cancel"
        self._pending_confirmation: Optional[Dict[str, Any]] = None

        # Explicit allowlist of actions that AI-classified intents are permitted to trigger
        self.ALLOWED_ACTIONS: Dict[str, Callable[[Dict[str, Any]], str]] = {
            "open_website": self._act_open_website,
            "web_search": self._act_web_search,
            "youtube_search": self._act_youtube_search,
            "open_app": self._act_open_app,
            "play_music": self._act_play_music,
            "add_reminder": self._act_add_reminder,
            "add_todo": self._act_add_todo,
            "add_note": self._act_add_note,
            "set_timer": self._act_set_timer,
            "get_weather": self._act_get_weather,
            "get_news": self._act_get_news,
            "wikipedia": self._act_wikipedia,
            "system_info": self._act_system_info,
        }

    def route(self, raw_input: str) -> Dict[str, Any]:
        """
        Main entry point for both voice transcripts and GUI text input.
        Returns: {"reply": str, "speak": bool, "category": str}
        """
        text = raw_input.strip()
        if not text:
            return {"reply": "", "speak": False, "category": "System"}

        lower = text.lower().strip()

        # 0. Check if user is responding to a pending confirmation prompt
        if self._pending_confirmation is not None:
            return self._handle_confirmation_reply(lower)

        # Active interactive game intercept (number guessing or trivia quiz)
        if self.entertainment.has_active_game():
            if lower in ("quit game", "stop game", "exit game", "cancel game"):
                msg = self.entertainment.stop_game()
                return {"reply": msg, "speak": True, "category": "Entertainment"}
            game_reply = self.entertainment.handle_game_input(text)
            if game_reply is not None:
                return {"reply": game_reply, "speak": True, "category": "Entertainment"}

        # Log user turn to conversation history
        active_mode = config.get("response_mode", "normal")
        storage.append_message("user", text, mode=active_mode)

        # Stage 1: Fast local deterministic commands (Zero Gemini API calls)
        local_result = self._try_local_fast_path(text, lower)
        if local_result is not None:
            storage.append_message("assistant", local_result["reply"], mode=active_mode)
            return local_result

        # Stage 2: Natural language intent classification via Gemini + Allowlist Execution
        intent = ai_engine.classify_intent(text)
        action_name = intent.get("action", "chat")
        params = intent.get("params", {})

        if action_name in self.ALLOWED_ACTIONS:
            try:
                reply = self.ALLOWED_ACTIONS[action_name](params)
                storage.append_message("assistant", reply, mode=active_mode)
                return {"reply": reply, "speak": True, "category": f"Action:{action_name}"}
            except Exception as e:
                err_msg = f"I understood the request ({action_name}), but encountered an error: {e}"
                storage.append_message("assistant", err_msg, mode=active_mode)
                return {"reply": err_msg, "speak": True, "category": "Error"}

        # Stage 3: Full conversational AI response with multi-turn memory
        ai_reply = ai_engine.generate_reply(text, mode_override=active_mode, use_history=True)
        storage.append_message("assistant", ai_reply, mode=active_mode)
        return {"reply": ai_reply, "speak": True, "category": f"AI ({active_mode})"}

    # ------------------------------------------------------------------
    # Confirmation Gate for Sensitive / Destructive Operations
    # ------------------------------------------------------------------
    def request_confirmation(self, action_type: str, target: str, callback: Callable[[], str]) -> Dict[str, Any]:
        self._pending_confirmation = {
            "action_type": action_type,
            "target": target,
            "callback": callback,
        }
        prompt = (
            f"Confirmation required: Are you sure you want to {action_type} ({target})? "
            "Reply 'confirm' or 'yes' to proceed, or 'cancel' to abort."
        )
        return {"reply": prompt, "speak": True, "category": "Security"}

    def _handle_confirmation_reply(self, lower: str) -> Dict[str, Any]:
        pending = self._pending_confirmation
        self._pending_confirmation = None

        if lower in ("confirm", "yes", "yes please", "do it", "proceed", "ok", "okay"):
            result = pending["callback"]()
            return {"reply": result, "speak": True, "category": "Security"}

        return {
            "reply": f"Cancelled {pending['action_type']}. No changes were made.",
            "speak": True,
            "category": "Security",
        }

    # ------------------------------------------------------------------
    # Stage 1: Deterministic Local Fast-Path Matchers
    # ------------------------------------------------------------------
    def _try_local_fast_path(self, text: str, lower: str) -> Optional[Dict[str, Any]]:
        # 1. Help / Quick Commands
        if lower in ("help", "commands", "what can you do", "show commands", "quick commands"):
            return {"reply": self.get_help_text(), "speak": False, "category": "Help"}

        # 2. Voice control (stop speaking / switch voice engine)
        if lower in ("stop speaking", "be quiet", "shut up", "silence", "mute voice"):
            if self.speaker:
                self.speaker.stop()
            return {"reply": "Speech output stopped.", "speak": False, "category": "Voice"}

        if "switch voice to offline" in lower or "use pyttsx3" in lower:
            config.set("tts_engine", "pyttsx3")
            return {"reply": "Switched voice engine to offline pyttsx3.", "speak": True, "category": "Voice"}

        if "switch voice to online" in lower or "use gtts" in lower:
            config.set("tts_engine", "gtts")
            return {"reply": "Switched voice engine to online gTTS.", "speak": True, "category": "Voice"}

        # 3. Response Mode Switching
        mode_match = re.match(
            r"^(?:switch|set|change)\s+(?:to\s+)?(normal|detailed|coding|study|professional)(?:\s+mode)?$",
            lower,
        )
        if not mode_match:
            mode_match = re.match(r"^(normal|detailed|coding|study|professional)\s+mode$", lower)
        if mode_match:
            chosen = mode_match.group(1)
            config.set("response_mode", chosen)
            desc = RESPONSE_MODES[chosen]["description"]
            return {
                "reply": f"Switched to {chosen.capitalize()} mode. {desc}",
                "speak": True,
                "category": "Mode",
            }

        # 4. Conversation History Controls
        if lower in ("clear history", "clear chat", "clear conversation", "reset memory"):
            return self.request_confirmation(
                "clear all saved conversation history",
                "data/conversations.json",
                lambda: (storage.clear_messages(), "Conversation memory cleared.")[1],
            )

        if lower in ("what did we discuss earlier", "show history", "recent history"):
            recent = storage.get_recent_messages(limit=6)
            if len(recent) <= 1:
                return {"reply": "We haven't had any prior conversation yet in this log.", "speak": True, "category": "Memory"}
            lines = [f"- {m['role'].capitalize()}: {m['content'][:120]}" for m in recent[:-1]]
            return {"reply": "Here is what we discussed recently:\n" + "\n".join(lines), "speak": True, "category": "Memory"}

        # 5. Date & Time (Local, offline)
        if any(p in lower for p in ("what time is it", "current time", "tell me the time", "time now")):
            return {"reply": self.info.get_current_time(), "speak": True, "category": "DateTime"}

        if any(p in lower for p in ("what is the date", "today's date", "current date", "what day is it", "day of the week")):
            return {"reply": self.info.get_current_date(), "speak": True, "category": "DateTime"}

        # 6. Browser & Search Shortcuts
        if lower.startswith("search google for ") or lower.startswith("google "):
            query = re.sub(r"^(?:search google for|google)\s+", "", text, flags=re.IGNORECASE)
            return {"reply": self.automation.search_google(query), "speak": True, "category": "Browser"}

        if lower.startswith("search youtube for ") or lower.startswith("youtube "):
            query = re.sub(r"^(?:search youtube for|youtube)\s+", "", text, flags=re.IGNORECASE)
            return {"reply": self.automation.search_youtube(query), "speak": True, "category": "Browser"}

        if lower.startswith("add shortcut "):
            # Format: add shortcut reddit https://reddit.com
            parts = text.split()
            if len(parts) >= 4:
                name, url = parts[2], parts[3]
                config.add_shortcut(name, url)
                return {"reply": f"Added website shortcut '{name}' -> {url}.", "speak": True, "category": "Browser"}

        if lower.startswith("open "):
            target = text[5:].strip()
            # Check Windows apps first, then websites/URLs
            app_res = self.automation.try_open_app(target)
            if app_res is not None:
                return {"reply": app_res, "speak": True, "category": "App"}
            web_res = self.automation.try_open_website(target)
            if web_res is not None:
                return {"reply": web_res, "speak": True, "category": "Browser"}

        # 7. File & System Controls
        if lower.startswith("find file ") or lower.startswith("search file "):
            filename = re.sub(r"^(?:find|search)\s+file\s+", "", text, flags=re.IGNORECASE)
            return {"reply": self.automation.search_files(filename), "speak": True, "category": "Files"}

        if lower.startswith("list files"):
            folder = text[10:].strip()
            return {"reply": self.automation.list_files(folder or None), "speak": False, "category": "Files"}

        if lower.startswith("create folder "):
            folder_name = text[14:].strip()
            return {"reply": self.automation.create_folder(folder_name), "speak": True, "category": "Files"}

        if lower.startswith("read file "):
            file_path = text[10:].strip()
            return {"reply": self.automation.read_text_file(file_path), "speak": False, "category": "Files"}

        if lower.startswith("file info "):
            file_path = text[10:].strip()
            return {"reply": self.automation.file_info(file_path), "speak": True, "category": "Files"}

        if lower.startswith("delete file "):
            file_path = text[12:].strip()
            return self.request_confirmation(
                "permanently delete file",
                file_path,
                lambda: self.automation.delete_file_confirmed(file_path),
            )

        if any(p in lower for p in ("take a screenshot", "take screenshot", "capture screen")):
            return {"reply": self.automation.take_screenshot(), "speak": True, "category": "System"}

        if "battery" in lower:
            return {"reply": self.automation.get_battery_status(), "speak": True, "category": "System"}

        if any(p in lower for p in ("system info", "system information", "pc specs", "cpu usage")):
            return {"reply": self.automation.get_system_info(), "speak": True, "category": "System"}

        if "volume up" in lower or "increase volume" in lower:
            return {"reply": self.automation.adjust_volume("up"), "speak": True, "category": "System"}

        if "volume down" in lower or "decrease volume" in lower:
            return {"reply": self.automation.adjust_volume("down"), "speak": True, "category": "System"}

        if "mute system" in lower or "mute audio" in lower:
            return {"reply": self.automation.adjust_volume("mute"), "speak": True, "category": "System"}

        if lower in ("shutdown computer", "shut down computer", "shutdown pc"):
            return self.request_confirmation(
                "shut down Windows",
                "Local PC",
                self.automation.shutdown_pc_confirmed,
            )

        if lower in ("restart computer", "restart pc", "reboot computer"):
            return self.request_confirmation(
                "restart Windows",
                "Local PC",
                self.automation.restart_pc_confirmed,
            )

        # 8. Productivity: Reminders, To-Dos, Notes, Timer, Stopwatch
        if lower.startswith("remind me "):
            return {"reply": self.productivity.parse_and_add_reminder(text), "speak": True, "category": "Reminders"}

        if lower in ("show reminders", "list reminders", "upcoming reminders", "my reminders"):
            return {"reply": self.productivity.list_reminders(), "speak": True, "category": "Reminders"}

        if lower.startswith("add task ") or lower.startswith("add todo ") or lower.startswith("add to-do "):
            task = re.sub(r"^add\s+(?:task|todo|to-do)\s+", "", text, flags=re.IGNORECASE)
            return {"reply": self.productivity.add_todo(task), "speak": True, "category": "Todo"}

        if lower in ("show tasks", "my tasks", "todo list", "to-do list", "pending tasks"):
            return {"reply": self.productivity.list_todos(only_pending=True), "speak": True, "category": "Todo"}

        if lower in ("completed tasks", "show completed tasks"):
            return {"reply": self.productivity.list_todos(only_completed=True), "speak": True, "category": "Todo"}

        if lower.startswith("complete task ") or lower.startswith("mark task "):
            target = re.sub(r"^(?:complete|mark)\s+task\s+", "", text, flags=re.IGNORECASE)
            target = re.sub(r"\s+(?:as\s+)?(?:done|completed)$", "", target, flags=re.IGNORECASE)
            return {"reply": self.productivity.complete_todo(target), "speak": True, "category": "Todo"}

        if lower.startswith("delete task ") or lower.startswith("remove task "):
            target = re.sub(r"^(?:delete|remove)\s+task\s+", "", text, flags=re.IGNORECASE)
            return {"reply": self.productivity.delete_todo(target), "speak": True, "category": "Todo"}

        if lower.startswith("take a note ") or lower.startswith("create note ") or lower.startswith("note "):
            body = re.sub(r"^(?:take a note|create note|note)\s*:?\s*", "", text, flags=re.IGNORECASE)
            return {"reply": self.productivity.add_note(body), "speak": True, "category": "Notes"}

        if lower in ("show notes", "read notes", "my notes", "list notes"):
            return {"reply": self.productivity.list_notes(), "speak": True, "category": "Notes"}

        if lower.startswith("search notes "):
            q = text[13:].strip()
            return {"reply": self.productivity.search_notes(q), "speak": True, "category": "Notes"}

        if lower.startswith("set timer ") or lower.startswith("set a timer "):
            dur = re.sub(r"^set\s+(?:a\s+)?timer\s+(?:for\s+)?", "", text, flags=re.IGNORECASE)
            return {"reply": self.productivity.start_timer(dur), "speak": True, "category": "Timer"}

        if lower in ("cancel timer", "stop timer"):
            return {"reply": self.productivity.cancel_timer(), "speak": True, "category": "Timer"}

        if lower in ("pause timer",):
            return {"reply": self.productivity.pause_timer(), "speak": True, "category": "Timer"}

        if lower in ("resume timer",):
            return {"reply": self.productivity.resume_timer(), "speak": True, "category": "Timer"}

        if lower in ("start stopwatch",):
            return {"reply": self.productivity.start_stopwatch(), "speak": True, "category": "Stopwatch"}

        if lower in ("stop stopwatch", "check stopwatch", "stopwatch status"):
            return {"reply": self.productivity.stop_stopwatch(), "speak": True, "category": "Stopwatch"}

        # 9. Music & Entertainment (Zero API cost)
        if lower.startswith("play "):
            song_query = text[5:].strip()
            return {"reply": self.entertainment.play_song(song_query), "speak": True, "category": "Music"}

        if lower.startswith("add song "):
            # Format: add song believer https://www.youtube.com/watch?v=...
            parts = text.split()
            if len(parts) >= 4:
                url = parts[-1]
                song_name = " ".join(parts[2:-1])
                return {"reply": self.entertainment.add_custom_song(song_name, url), "speak": True, "category": "Music"}

        if lower in ("pause music", "resume music", "play pause"):
            return {"reply": self.entertainment.media_play_pause(), "speak": True, "category": "Music"}

        if lower in ("stop music",):
            return {"reply": self.entertainment.media_stop(), "speak": True, "category": "Music"}

        if "joke" in lower:
            return {"reply": self.entertainment.tell_joke(), "speak": True, "category": "Entertainment"}

        if "interesting fact" in lower or "random fact" in lower or lower == "tell me a fact":
            return {"reply": self.entertainment.tell_fact(), "speak": True, "category": "Entertainment"}

        if "motivational quote" in lower or "inspire me" in lower or lower == "give me a quote":
            return {"reply": self.entertainment.tell_quote(), "speak": True, "category": "Entertainment"}

        if "start a quiz" in lower or "play quiz" in lower or "trivia" in lower:
            return {"reply": self.entertainment.start_quiz(), "speak": True, "category": "Entertainment"}

        if "guessing game" in lower or "guess the number" in lower:
            return {"reply": self.entertainment.start_number_game(), "speak": True, "category": "Entertainment"}

        # 10. News, Weather, Wikipedia & Clipboard Assistant
        if lower in ("news", "top news", "headlines", "indian news", "latest news"):
            return {"reply": self.info.get_news(), "speak": True, "category": "News"}

        if lower.startswith("news about ") or lower.startswith("news on "):
            topic = re.sub(r"^news\s+(?:about|on)\s+", "", text, flags=re.IGNORECASE)
            return {"reply": self.info.get_news(category=topic), "speak": True, "category": "News"}

        if lower.startswith("weather"):
            city = text[7:].replace("in ", "").replace("for ", "").strip()
            return {"reply": self.info.get_weather(city or None), "speak": True, "category": "Weather"}

        if lower.startswith("wikipedia "):
            topic = text[10:].strip()
            return {"reply": self.info.search_wikipedia(topic), "speak": True, "category": "Wikipedia"}

        if lower in ("read clipboard", "what is on my clipboard"):
            clip = self.automation.read_clipboard()
            return {"reply": f"Clipboard content:\n{clip}", "speak": False, "category": "Clipboard"}

        if lower in ("summarize clipboard", "summarize my clipboard"):
            clip = self.automation.read_clipboard()
            if clip.startswith("Clipboard is empty"):
                return {"reply": clip, "speak": True, "category": "Clipboard"}
            summary = ai_engine.generate_reply(
                f"Summarize the following clipboard text concisely in bullet points:\n\n{clip}",
                mode_override="normal",
                use_history=False,
            )
            return {"reply": summary, "speak": True, "category": "Clipboard"}

        if lower in ("explain copied code", "explain clipboard code"):
            clip = self.automation.read_clipboard()
            if clip.startswith("Clipboard is empty"):
                return {"reply": clip, "speak": True, "category": "Clipboard"}
            explanation = ai_engine.generate_reply(
                f"Explain what this copied code does, highlight any bugs, and suggest improvements:\n\n{clip}",
                mode_override="coding",
                use_history=False,
            )
            return {"reply": explanation, "speak": False, "category": "Clipboard"}

        return None

    # ------------------------------------------------------------------
    # Stage 2: Allowlisted Action Handlers (Invoked by Gemini Classifier)
    # ------------------------------------------------------------------
    def _act_open_website(self, params: Dict[str, Any]) -> str:
        target = str(params.get("target", "")).strip()
        return self.automation.try_open_website(target) or self.automation.search_google(target)

    def _act_web_search(self, params: Dict[str, Any]) -> str:
        return self.automation.search_google(str(params.get("query", "")))

    def _act_youtube_search(self, params: Dict[str, Any]) -> str:
        return self.automation.search_youtube(str(params.get("query", "")))

    def _act_open_app(self, params: Dict[str, Any]) -> str:
        app = str(params.get("app_name", "")).strip()
        return self.automation.try_open_app(app) or f"Application '{app}' is not in the safe launch allowlist."

    def _act_play_music(self, params: Dict[str, Any]) -> str:
        return self.entertainment.play_song(str(params.get("song", "")))

    def _act_add_reminder(self, params: Dict[str, Any]) -> str:
        text = str(params.get("text", "Reminder")).strip()
        when = str(params.get("when", "in 10 minutes")).strip()
        return self.productivity.parse_and_add_reminder(f"remind me to {text} {when}")

    def _act_add_todo(self, params: Dict[str, Any]) -> str:
        return self.productivity.add_todo(str(params.get("task", "")))

    def _act_add_note(self, params: Dict[str, Any]) -> str:
        title = str(params.get("title", "Quick Note"))
        content = str(params.get("content", ""))
        return self.productivity.add_note(content, title=title)

    def _act_set_timer(self, params: Dict[str, Any]) -> str:
        return self.productivity.start_timer(str(params.get("duration", "1 minute")))

    def _act_get_weather(self, params: Dict[str, Any]) -> str:
        city = str(params.get("city", "")).strip()
        return self.info.get_weather(city or None)

    def _act_get_news(self, params: Dict[str, Any]) -> str:
        cat = str(params.get("category", "")).strip()
        return self.info.get_news(category=cat or None)

    def _act_wikipedia(self, params: Dict[str, Any]) -> str:
        return self.info.search_wikipedia(str(params.get("topic", "")))

    def _act_system_info(self, params: Dict[str, Any]) -> str:
        kind = str(params.get("type", "specs")).lower()
        if kind == "battery":
            return self.automation.get_battery_status()
        if kind == "screenshot":
            return self.automation.take_screenshot()
        if kind in ("volume_up", "volume_down", "mute"):
            return self.automation.adjust_volume(kind.replace("volume_", ""))
        return self.automation.get_system_info()

    @staticmethod
    def get_help_text() -> str:
        return (
            "ARROW Quick Command Reference:\n"
            "• AI & Modes: Ask any question naturally | 'coding mode', 'study mode', 'detailed mode', 'normal mode', 'professional mode'\n"
            "• Memory & Clipboard: 'what did we discuss earlier' | 'clear history' | 'summarize clipboard' | 'explain copied code'\n"
            "• Browser & Apps: 'open youtube/github/gmail' | 'search google for <query>' | 'open vscode/notepad/calculator/settings'\n"
            "• Productivity: 'remind me to study in 30 minutes' | 'add task finish report' | 'show tasks' | 'take a note <text>' | 'set timer 5 minutes'\n"
            "• Info & Weather: 'weather in Lucknow' | 'news' | 'news about technology' | 'wikipedia <topic>' | 'what time is it'\n"
            "• Music & Fun: 'play skyfall' | 'pause music' | 'tell me a joke' | 'interesting fact' | 'start a quiz' | 'guessing game'\n"
            "• System: 'take a screenshot' | 'battery status' | 'system info' | 'volume up/down' | 'stop speaking'"
        )