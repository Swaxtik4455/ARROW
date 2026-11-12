"""
entertainment.py
Music library manager (upgraded from music.py), media playback controls,
and offline entertainment (jokes, facts, quotes, trivia quiz, number guessing game).
"""

import ctypes
import random
import urllib.parse
import webbrowser
from typing import Any, Dict, List, Optional

from storage import storage


class EntertainmentManager:
    """Handles music playback/search and interactive mini-games without wasting AI tokens."""

    JOKES = [
        "Why do programmers prefer dark mode? Because light attracts bugs.",
        "There are only 10 kinds of people in the world: those who understand binary and those who don't.",
        "A SQL query walks into a bar, walks up to two tables, and asks: 'Can I join you?'",
        "Debugging is like being the detective in a crime movie where you are also the murderer.",
        "Why did the developer go broke? Because he used up all his cache.",
    ]

    FACTS = [
        "Honey never spoils. Archaeologists have found 3,000-year-old pots of honey in Egyptian tombs that are still edible.",
        "A day on Venus is longer than a year on Venus because it rotates very slowly on its axis.",
        "Python was named after the British comedy troupe Monty Python, not the snake.",
        "Octopuses have three hearts, nine brains, and blue copper-based blood.",
        "The first computer bug was an actual moth found trapped inside a Harvard Mark II relay in 1947.",
    ]

    QUOTES = [
        "\"The best way to predict the future is to invent it.\" — Alan Kay",
        "\"Simplicity is the soul of efficiency.\" — Austin Freeman",
        "\"First, solve the problem. Then, write the code.\" — John Johnson",
        "\"It does not matter how slowly you go as long as you do not stop.\" — Confucius",
        "\"Action is the foundational key to all success.\" — Pablo Picasso",
    ]

    QUIZ_QUESTIONS: List[Dict[str, str]] = [
        {"q": "What does CPU stand for?", "a": "central processing unit"},
        {"q": "Which planet in our solar system is known as the Red Planet?", "a": "mars"},
        {"q": "In Python, which keyword is used to define a function?", "a": "def"},
        {"q": "What is the chemical symbol for gold?", "a": "au"},
        {"q": "Who developed the theory of general relativity?", "a": "einstein"},
    ]

    def __init__(self) -> None:
        self._game_mode: Optional[str] = None  # "guess" or "quiz"
        self._secret_number: int = 0
        self._guess_attempts: int = 0
        self._quiz_index: int = 0
        self._quiz_score: int = 0

    # ---------------- Music Library (Upgraded from music.py) ----------------
    def play_song(self, query: str) -> str:
        clean = query.strip().lower()
        if not clean:
            return "Tell me the name of the song you want to play."

        library = storage.get_music_library()

        # 1. Exact match
        if clean in library:
            webbrowser.open(library[clean])
            return f"Playing '{clean.title()}' from your music library."

        # 2. Partial match (fixes 'play the wolf' or 'play sky' failing in original main.py)
        for title, url in library.items():
            if clean in title or title in clean:
                webbrowser.open(url)
                return f"Playing '{title.title()}' from your music library."

        # 3. Graceful fallback to YouTube search
        encoded = urllib.parse.quote_plus(query.strip())
        webbrowser.open(f"https://www.youtube.com/results?search_query={encoded}")
        return f"'{query}' wasn't in your saved library, so I opened YouTube search results for it."

    def add_custom_song(self, name: str, url: str) -> str:
        if not url.startswith(("http://", "https://")):
            return "Please provide a valid YouTube or streaming URL starting with https://."
        storage.add_song(name, url)
        return f"Saved '{name.strip()}' to your custom music library."

    @staticmethod
    def media_play_pause() -> str:
        VK_MEDIA_PLAY_PAUSE = 0xB3
        KEYEVENTF_KEYUP = 0x0002
        ctypes.windll.user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, KEYEVENTF_KEYUP, 0)
        return "Toggled media play/pause."

    @staticmethod
    def media_stop() -> str:
        VK_MEDIA_STOP = 0xB2
        KEYEVENTF_KEYUP = 0x0002
        ctypes.windll.user32.keybd_event(VK_MEDIA_STOP, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_MEDIA_STOP, 0, KEYEVENTF_KEYUP, 0)
        return "Stopped active media playback."

    # ---------------- Jokes, Facts & Quotes ----------------
    def tell_joke(self) -> str:
        return random.choice(self.JOKES)

    def tell_fact(self) -> str:
        return f"Did you know? {random.choice(self.FACTS)}"

    def tell_quote(self) -> str:
        return random.choice(self.QUOTES)

    # ---------------- Interactive Mini-Games ----------------
    def has_active_game(self) -> bool:
        return self._game_mode is not None

    def stop_game(self) -> str:
        self._game_mode = None
        return "Exited the current game."

    def start_number_game(self) -> str:
        self._game_mode = "guess"
        self._secret_number = random.randint(1, 50)
        self._guess_attempts = 0
        return "I've picked a secret number between 1 and 50. Type or say your guess! (Say 'quit game' anytime.)"

    def start_quiz(self) -> str:
        self._game_mode = "quiz"
        self._quiz_index = 0
        self._quiz_score = 0
        first_q = self.QUIZ_QUESTIONS[0]["q"]
        return f"Starting a 5-question quick quiz! Question 1: {first_q}"

    def handle_game_input(self, user_text: str) -> Optional[str]:
        if self._game_mode == "guess":
            digits = "".join(ch for ch in user_text if ch.isdigit())
            if not digits:
                return "Please guess a number between 1 and 50, or say 'quit game'."
            guess = int(digits)
            self._guess_attempts += 1
            if guess < self._secret_number:
                return f"Higher than {guess}! Try again."
            if guess > self._secret_number:
                return f"Lower than {guess}! Try again."
            attempts = self._guess_attempts
            self._game_mode = None
            return f"Spot on! The number was {guess}, and you got it in {attempts} attempt(s)."

        if self._game_mode == "quiz":
            current = self.QUIZ_QUESTIONS[self._quiz_index]
            correct = current["a"] in user_text.strip().lower()
            if correct:
                self._quiz_score += 1
                feedback = "Correct!"
            else:
                feedback = f"Not quite — the answer was '{current['a'].title()}'."

            self._quiz_index += 1
            if self._quiz_index >= len(self.QUIZ_QUESTIONS):
                score = self._quiz_score
                total = len(self.QUIZ_QUESTIONS)
                self._game_mode = None
                return f"{feedback} Quiz finished! Your final score is {score} out of {total}."

            next_q = self.QUIZ_QUESTIONS[self._quiz_index]["q"]
            return f"{feedback} Question {self._quiz_index + 1}: {next_q}"

        return None