"""
ai_engine.py
Google Gemini AI integration using the official `google-genai` SDK (free-tier compatible).
Handles multi-turn conversation memory, personality modes, and safe structured intent routing.
"""

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types
from google.genai.errors import APIError

from config import RESPONSE_MODES, config
from storage import storage


class GeminiEngine:
    """Wrapper around Google's `google-genai` SDK with conversation context and error handling."""

    def __init__(self) -> None:
        self._client: Optional[genai.Client] = None
        self._cached_key: str = ""

    def _get_client(self) -> genai.Client:
        api_key = config.gemini_api_key
        if not api_key or api_key == "your_gemini_api_key_here":
            raise ValueError(
                "Gemini API key is missing. Add GEMINI_API_KEY to your .env file "
                "(get a free key at https://aistudio.google.com/apikey)."
            )
        if self._client is None or api_key != self._cached_key:
            self._client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(timeout=25_000),  # 25-second timeout in ms
            )
            self._cached_key = api_key
        return self._client

    def _build_system_prompt(self, mode_override: Optional[str] = None) -> str:
        assistant_name = config.get("assistant_name", "ARROW")
        mode_key = (mode_override or config.get("response_mode", "normal")).lower()
        mode_cfg = RESPONSE_MODES.get(mode_key, RESPONSE_MODES["normal"])
        now_str = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")

        return (
            f"You are {assistant_name} (Adaptive Responsive Real-time Operations & Workflow Assistant), "
            f"a JARVIS-inspired personal desktop AI assistant running locally on Windows.\n"
            f"Current local date and time: {now_str}.\n"
            f"Active response mode: {mode_cfg['label']} — {mode_cfg['instruction']}\n"
            "Important rules:\n"
            "1. Never claim you have live real-time internet access unless tool output was provided.\n"
            "2. Never suggest destructive system commands.\n"
            "3. Remember previous turns in the conversation and resolve pronouns like 'it', 'that', or 'earlier'."
        )

    def _format_history_contents(self, current_user_message: str) -> List[types.Content]:
        """Builds bounded multi-turn conversation history for Gemini."""
        limit = int(config.get("history_limit", 12))
        recent = storage.get_recent_messages(limit=limit)

        contents: List[types.Content] = []
        for msg in recent:
            role = "user" if msg.get("role") == "user" else "model"
            text = str(msg.get("content", "")).strip()
            if text:
                contents.append(
                    types.Content(role=role, parts=[types.Part.from_text(text=text)])
                )

        # Ensure the latest user turn is at the end
        if not contents or contents[-1].role != "user" or contents[-1].parts[0].text != current_user_message:
            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=current_user_message)],
                )
            )
        return contents

    def generate_reply(
        self,
        user_message: str,
        mode_override: Optional[str] = None,
        use_history: bool = True,
    ) -> str:
        """Generates a conversational response using the configured free-tier Gemini model."""
        try:
            client = self._get_client()
            model_name = config.get("gemini_model", "gemini-2.5-flash")
            system_instruction = self._build_system_prompt(mode_override)

            if use_history:
                contents = self._format_history_contents(user_message)
            else:
                contents = user_message

            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.65,
                    max_output_tokens=1024,
                ),
            )

            reply_text = (response.text or "").strip()
            if not reply_text:
                return "I received an empty response from Gemini. Please try rephrasing your request."
            return reply_text

        except ValueError as e:
            return str(e)
        except APIError as e:
            return self._friendly_api_error(e)
        except Exception as e:
            err = str(e).lower()
            if "timeout" in err or "timed out" in err:
                return "The Gemini request timed out. Please check your internet connection and try again."
            if "getaddrinfo" in err or "connection" in err or "network" in err:
                return (
                    "I appear to be offline and cannot reach Gemini right now. "
                    "Local desktop commands, timers, notes, and offline voice still work."
                )
            return f"AI service error: {e}"

    def classify_intent(self, user_command: str) -> Dict[str, Any]:
        """
        Uses Gemini to map ambiguous natural language into a strictly allowlisted JSON action,
        or returns {'action': 'chat'} when no desktop tool is needed.
        """
        try:
            client = self._get_client()
            model_name = config.get("gemini_model", "gemini-2.5-flash")
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M (%A)")

            classifier_prompt = (
                "You are an intent classifier for a desktop assistant. Classify the user request into "
                "EXACTLY ONE JSON object with keys 'action' and 'params'. No markdown, no extra text.\n"
                f"Current local datetime: {now_str}\n\n"
                "Allowed actions and params:\n"
                '1. {"action": "open_website", "params": {"target": "<site name or url>"}}\n'
                '2. {"action": "web_search", "params": {"query": "<search query>"}}\n'
                '3. {"action": "youtube_search", "params": {"query": "<video query>"}}\n'
                '4. {"action": "open_app", "params": {"app_name": "<vscode|notepad|calculator|cmd|settings|explorer|taskmgr>"}}\n'
                '5. {"action": "play_music", "params": {"song": "<song name>"}}\n'
                '6. {"action": "add_reminder", "params": {"text": "<reminder task>", "when": "<natural time expression e.g. in 30 minutes | tomorrow 09:00 | 17:00>"}}\n'
                '7. {"action": "add_todo", "params": {"task": "<task description>"}}\n'
                '8. {"action": "add_note", "params": {"title": "<short title>", "content": "<note body>"}}\n'
                '9. {"action": "set_timer", "params": {"duration": "<e.g. 5 minutes | 90 seconds>"}}\n'
                '10. {"action": "get_weather", "params": {"city": "<city name or empty>"}}\n'
                '11. {"action": "get_news", "params": {"category": "<general|technology|business|sports|science|health>"}}\n'
                '12. {"action": "wikipedia", "params": {"topic": "<topic name>"}}\n'
                '13. {"action": "system_info", "params": {"type": "<battery|specs|screenshot|volume_up|volume_down|mute>"}}\n'
                '14. {"action": "chat", "params": {}}\n\n'
                "Rules:\n"
                "- Choose 'chat' for general knowledge, coding help, explanations, follow-ups, advice, or creative questions.\n"
                "- Never invent actions outside the 14 listed above.\n\n"
                f"User input: {user_command}"
            )

            response = client.models.generate_content(
                model=model_name,
                contents=classifier_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    max_output_tokens=180,
                ),
            )

            raw = (response.text or "").strip()
            # Strip accidental markdown code fences if present
            raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.IGNORECASE).strip()
            parsed = json.loads(raw)
            if isinstance(parsed, dict) and "action" in parsed:
                if not isinstance(parsed.get("params"), dict):
                    parsed["params"] = {}
                return parsed
        except Exception:
            # If classification fails (offline, rate-limited, malformed JSON), degrade gracefully to chat
            pass

        return {"action": "chat", "params": {}}

    @staticmethod
    def _friendly_api_error(error: APIError) -> str:
        code = getattr(error, "code", None)
        msg = str(error)
        if code == 429 or "RESOURCE_EXHAUSTED" in msg or "quota" in msg.lower():
            return (
                "Gemini free-tier rate limit or daily quota reached (HTTP 429). "
                "Wait ~30 seconds before sending another AI question, or switch to another free model "
                "like 'gemini-2.5-flash-lite' in Settings."
            )
        if code in (400, 401, 403) or "API_KEY_INVALID" in msg or "permission" in msg.lower():
            return (
                "Invalid or unauthorized Gemini API key. Verify GEMINI_API_KEY in your .env file "
                "and ensure the model name is valid."
            )
        if code == 404 or "not found" in msg.lower():
            return (
                f"Model '{config.get('gemini_model')}' was not found or is unavailable on your tier. "
                "Change GEMINI_MODEL in Settings or .env to 'gemini-2.5-flash'."
            )
        return f"Gemini API returned an error ({code}): {msg}"


# Shared singleton AI engine
ai_engine = GeminiEngine()