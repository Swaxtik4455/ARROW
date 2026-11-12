"""
gui.py
Modern, futuristic JARVIS-inspired UI/UX for ARROW built with CustomTkinter.
Features rounded cards, chat bubbles, quick-action chips, live system telemetry,
and an animated Neural Core visualizer — strictly thread-safe via `ui_queue`.
"""

import math
import queue
import threading
import tkinter as tk
from datetime import datetime
from tkinter import messagebox
from typing import Any, Callable, Dict, List

import customtkinter as ctk

from config import RESPONSE_MODES, config
from storage import storage

# Configure CustomTkinter dark appearance globally
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class NeuralCoreCanvas(tk.Canvas):
    """Animated JARVIS-style concentric HUD core that reacts to ARROW's live state."""

    STATE_COLORS = {
        "standby": ("#00E5FF", "#0E3A4D"),
        "listening": ("#10B981", "#064E3B"),
        "thinking": ("#F59E0B", "#78350F"),
        "speaking": ("#38BDF8", "#0369A1"),
    }

    def __init__(self, master: Any, size: int = 190, **kwargs: Any) -> None:
        super().__init__(
            master,
            width=size,
            height=size,
            bg="#111827",
            highlightthickness=0,
            bd=0,
            **kwargs,
        )
        self.size = size
        self.center = size // 2
        self.angle = 0.0
        self.pulse_phase = 0.0
        self.state = "standby"
        self._running = True
        self._animate()

    def set_state(self, state: str) -> None:
        if state in self.STATE_COLORS:
            self.state = state

    def stop(self) -> None:
        self._running = False

    def _animate(self) -> None:
        if not self._running:
            return
        self.delete("all")
        primary, secondary = self.STATE_COLORS.get(self.state, self.STATE_COLORS["standby"])
        c = self.center

        # Speed scales with active state
        speed = {"standby": 1.2, "listening": 3.5, "thinking": 6.0, "speaking": 4.2}[self.state]
        self.angle = (self.angle + speed) % 360
        self.pulse_phase = (self.pulse_phase + 0.12) % (2 * math.pi)
        pulse = math.sin(self.pulse_phase) * (5 if self.state != "standby" else 2)

        # Outer subtle halo ring
        r1 = 76 + pulse * 0.4
        self.create_oval(c - r1, c - r1, c + r1, c + r1, outline=secondary, width=2)

        # Rotating segmented HUD arcs
        r2 = 64
        for offset in (0, 120, 240):
            self.create_arc(
                c - r2,
                c - r2,
                c + r2,
                c + r2,
                start=self.angle + offset,
                extent=75,
                style=tk.ARC,
                outline=primary,
                width=3,
            )

        # Counter-rotating inner ring
        r3 = 48
        for offset in (45, 225):
            self.create_arc(
                c - r3,
                c - r3,
                c + r3,
                c + r3,
                start=-self.angle * 1.5 + offset,
                extent=110,
                style=tk.ARC,
                outline=secondary,
                width=2,
            )

        # Core energy orb
        r_core = 26 + pulse
        self.create_oval(
            c - r_core,
            c - r_core,
            c + r_core,
            c + r_core,
            fill=secondary,
            outline=primary,
            width=2,
        )

        # Center status label
        self.create_text(
            c,
            c,
            text=self.state.upper(),
            fill="#F8FAFC",
            font=("Consolas", 8, "bold"),
        )

        self.after(33, self._animate)  # ~30 FPS smooth animation


class ArrowDesktopGUI:
    """Modern glass-dark CustomTkinter desktop dashboard for ARROW."""

    # Color Tokens
    BG_ROOT = "#090D16"
    BG_SIDEBAR = "#0F1624"
    BG_CARD = "#131C2E"
    BG_ELEVATED = "#1A253B"
    ACCENT_CYAN = "#00E5FF"
    ACCENT_BLUE = "#2563EB"
    ACCENT_GREEN = "#10B981"
    ACCENT_AMBER = "#F59E0B"
    ACCENT_RED = "#EF4444"
    TEXT_PRIMARY = "#F1F5F9"
    TEXT_MUTED = "#94A3B8"
    BORDER_SUBTLE = "#1E293B"

    def __init__(
        self,
        root: tk.Tk,
        on_submit_command: Callable[[str, bool], None],
        voice_in: Any,
        voice_out: Any,
        automation: Any,
        productivity: Any,
        on_shutdown: Callable[[], None],
    ) -> None:
        self.root = root
        self.on_submit_command = on_submit_command
        self.voice_in = voice_in
        self.voice_out = voice_out
        self.automation = automation
        self.productivity = productivity
        self.on_shutdown = on_shutdown

        self.ui_queue: queue.Queue[Dict[str, Any]] = queue.Queue()
        self._active_page = "Home"
        self._nav_buttons: Dict[str, ctk.CTkButton] = {}
        self._pages: Dict[str, ctk.CTkFrame] = {}

        # Track state flags for Neural Core visualizer
        self._is_listening = False
        self._is_thinking = False
        self._is_speaking = False

        self._setup_window()
        self._build_layout()
        self._start_clock_loop()
        self._poll_ui_queue()

    def _setup_window(self) -> None:
        name = config.get("assistant_name", "ARROW")
        self.root.title(f"{name} — Adaptive Responsive Real-time Operations & Workflow Assistant")
        self.root.geometry("1240x780")
        self.root.minsize(1020, 660)
        self.root.configure(bg=self.BG_ROOT)
        self.root.protocol("WM_DELETE_WINDOW", self._handle_close)

    def _build_layout(self) -> None:
        # Root container
        self.main_shell = ctk.CTkFrame(self.root, fg_color=self.BG_ROOT, corner_radius=0)
        self.main_shell.pack(fill="both", expand=True)

        # ---------------- Top Glass Header ----------------
        header = ctk.CTkFrame(
            self.main_shell,
            fg_color=self.BG_SIDEBAR,
            height=62,
            corner_radius=0,
            border_width=1,
            border_color=self.BORDER_SUBTLE,
        )
        header.pack(side="top", fill="x")
        header.pack_propagate(False)

        brand_box = ctk.CTkFrame(header, fg_color="transparent")
        brand_box.pack(side="left", padx=20)

        self.lbl_brand = ctk.CTkLabel(
            brand_box,
            text=f"◈  {config.get('assistant_name', 'ARROW')}",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=self.ACCENT_CYAN,
        )
        self.lbl_brand.pack(side="left")

        ctk.CTkLabel(
            brand_box,
            text="   NEURAL DESKTOP CORE",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=self.TEXT_MUTED,
        ).pack(side="left", pady=(3, 0))

        # Status Pill Badges
        pills = ctk.CTkFrame(header, fg_color="transparent")
        pills.pack(side="left", padx=28)

        self.pill_listen = self._create_status_pill(pills, "● LISTENING")
        self.pill_think = self._create_status_pill(pills, "● THINKING")
        self.pill_speak = self._create_status_pill(pills, "● SPEAKING")

        # Right Status + Digital Clock
        right_hdr = ctk.CTkFrame(header, fg_color="transparent")
        right_hdr.pack(side="right", padx=20)

        self.lbl_clock = ctk.CTkLabel(
            right_hdr,
            text="",
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color=self.TEXT_PRIMARY,
        )
        self.lbl_clock.pack(side="right")

        self.lbl_status_badge = ctk.CTkLabel(
            right_hdr,
            text="  ONLINE  ",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color="#05101A",
            fg_color=self.ACCENT_CYAN,
            corner_radius=6,
        )
        self.lbl_status_badge.pack(side="right", padx=(0, 16))

        # ---------------- Workspace Body ----------------
        body = ctk.CTkFrame(self.main_shell, fg_color=self.BG_ROOT, corner_radius=0)
        body.pack(side="top", fill="both", expand=True)

        # Left Navigation Rail
        sidebar = ctk.CTkFrame(
            body,
            fg_color=self.BG_SIDEBAR,
            width=220,
            corner_radius=0,
            border_width=1,
            border_color=self.BORDER_SUBTLE,
        )
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        ctk.CTkLabel(
            sidebar,
            text="COMMAND MODULES",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=self.TEXT_MUTED,
        ).pack(anchor="w", padx=20, pady=(18, 8))

        nav_items = [
            ("Home", "⌂   Dashboard"),
            ("Chat History", "☷   Chat Archive"),
            ("Reminders", "⏰   Reminders"),
            ("To-Do List", "☑   Task Board"),
            ("Notes", "✎   Smart Notes"),
            ("Settings", "⚙   Preferences"),
            ("About", "ℹ   System Info"),
        ]

        for key, label in nav_items:
            btn = ctk.CTkButton(
                sidebar,
                text=label,
                anchor="w",
                height=38,
                corner_radius=10,
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                fg_color="transparent",
                text_color=self.TEXT_PRIMARY,
                hover_color=self.BG_ELEVATED,
                command=lambda k=key: self.show_page(k),
            )
            btn.pack(fill="x", padx=12, pady=3)
            self._nav_buttons[key] = btn

        # AI Personality Mode Card inside Sidebar
        mode_card = ctk.CTkFrame(sidebar, fg_color=self.BG_CARD, corner_radius=12)
        mode_card.pack(fill="x", padx=12, pady=(22, 10))

        ctk.CTkLabel(
            mode_card,
            text="AI PERSONA MODE",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=self.ACCENT_CYAN,
        ).pack(anchor="w", padx=12, pady=(10, 4))

        self.mode_var = ctk.StringVar(value=config.get("response_mode", "normal"))
        self.mode_menu = ctk.CTkOptionMenu(
            mode_card,
            variable=self.mode_var,
            values=list(RESPONSE_MODES.keys()),
            fg_color=self.BG_ELEVATED,
            button_color=self.ACCENT_BLUE,
            button_hover_color="#1D4ED8",
            dropdown_fg_color=self.BG_CARD,
            corner_radius=8,
            command=self._on_mode_changed,
        )
        self.mode_menu.pack(fill="x", padx=12, pady=(0, 12))

        # Bottom Always-On Wake Word Toggle
        self.btn_wake = ctk.CTkButton(
            sidebar,
            text="🎙  Wake Word: OFF",
            height=42,
            corner_radius=12,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color=self.BG_ELEVATED,
            hover_color="#263554",
            text_color=self.TEXT_PRIMARY,
            command=self._toggle_wake_word,
        )
        self.btn_wake.pack(side="bottom", fill="x", padx=12, pady=16)

        # Main Content Stack
        self.content_area = ctk.CTkFrame(body, fg_color=self.BG_ROOT, corner_radius=0)
        self.content_area.pack(side="left", fill="both", expand=True, padx=16, pady=16)

        self._build_home_page()
        self._build_history_page()
        self._build_reminders_page()
        self._build_todos_page()
        self._build_notes_page()
        self._build_settings_page()
        self._build_about_page()

        self.show_page("Home")

    def _create_status_pill(self, parent: ctk.CTkFrame, text: str) -> ctk.CTkLabel:
        lbl = ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color=self.TEXT_MUTED,
            fg_color=self.BG_CARD,
            corner_radius=8,
            padx=10,
            pady=4,
        )
        lbl.pack(side="left", padx=5)
        return lbl

    # ------------------------------------------------------------------
    # Page 1: Modern Home Dashboard
    # ------------------------------------------------------------------
    def _build_home_page(self) -> None:
        page = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self._pages["Home"] = page

        # Top split: Conversation Bubbles (Left) + Neural HUD & Telemetry (Right)
        top_split = ctk.CTkFrame(page, fg_color="transparent")
        top_split.pack(fill="both", expand=True)

        # Left Conversation Feed Card
        chat_card = ctk.CTkFrame(
            top_split,
            fg_color=self.BG_CARD,
            corner_radius=16,
            border_width=1,
            border_color=self.BORDER_SUBTLE,
        )
        chat_card.pack(side="left", fill="both", expand=True, padx=(0, 12))

        chat_header = ctk.CTkFrame(chat_card, fg_color="transparent")
        chat_header.pack(fill="x", padx=16, pady=(12, 6))

        ctk.CTkLabel(
            chat_header,
            text="CONVERSATION STREAM",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=self.ACCENT_CYAN,
        ).pack(side="left")

        ctk.CTkButton(
            chat_header,
            text="? Commands",
            width=95,
            height=26,
            corner_radius=8,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color=self.BG_ELEVATED,
            hover_color="#263554",
            command=lambda: self._dispatch_text("help", speak_back=False),
        ).pack(side="right")

        # Scrollable Chat Bubble Container
        self.chat_scroll = ctk.CTkScrollableFrame(
            chat_card,
            fg_color="transparent",
            scrollbar_button_color=self.BG_ELEVATED,
        )
        self.chat_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Right Telemetry & Neural Core Dock
        right_dock = ctk.CTkFrame(
            top_split,
            fg_color="#111827",
            width=285,
            corner_radius=16,
            border_width=1,
            border_color=self.BORDER_SUBTLE,
        )
        right_dock.pack(side="right", fill="y")
        right_dock.pack_propagate(False)

        ctk.CTkLabel(
            right_dock,
            text="NEURAL CORE",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=self.ACCENT_CYAN,
        ).pack(pady=(14, 2))

        self.neural_core = NeuralCoreCanvas(right_dock, size=185)
        self.neural_core.pack(pady=4)

        ctk.CTkLabel(
            right_dock,
            text="LIVE TELEMETRY LOG",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=self.TEXT_MUTED,
        ).pack(anchor="w", padx=14, pady=(10, 4))

        self.activity_box = ctk.CTkTextbox(
            right_dock,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color="#0B101B",
            text_color=self.TEXT_MUTED,
            corner_radius=10,
            border_width=1,
            border_color=self.BORDER_SUBTLE,
            state="disabled",
        )
        self.activity_box.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # Quick-Action Chips Bar
        chips_bar = ctk.CTkFrame(page, fg_color="transparent")
        chips_bar.pack(fill="x", pady=(10, 6))

        quick_chips = [
            ("🌤 Weather", "weather"),
            ("📰 Top News", "news"),
            ("💻 System Specs", "system info"),
            ("😄 Tell a Joke", "tell me a joke"),
            ("📋 Summarize Clipboard", "summarize clipboard"),
        ]
        for label, cmd in quick_chips:
            ctk.CTkButton(
                chips_bar,
                text=label,
                height=28,
                corner_radius=14,
                font=ctk.CTkFont(family="Segoe UI", size=11),
                fg_color=self.BG_CARD,
                hover_color=self.BG_ELEVATED,
                border_width=1,
                border_color=self.BORDER_SUBTLE,
                text_color=self.TEXT_PRIMARY,
                command=lambda c=cmd: self._dispatch_text(c, speak_back=False),
            ).pack(side="left", padx=(0, 8))

        # Bottom Command Composer Bar
        composer = ctk.CTkFrame(
            page,
            fg_color=self.BG_CARD,
            height=62,
            corner_radius=16,
            border_width=1,
            border_color=self.BORDER_SUBTLE,
        )
        composer.pack(fill="x")
        composer.pack_propagate(False)

        self.btn_mic = ctk.CTkButton(
            composer,
            text="🎤 Speak",
            width=105,
            height=40,
            corner_radius=12,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=self.ACCENT_CYAN,
            hover_color="#38BDF8",
            text_color="#05101A",
            command=self._on_mic_click,
        )
        self.btn_mic.pack(side="left", padx=(12, 6), pady=11)

        self.btn_mute = ctk.CTkButton(
            composer,
            text="⏹",
            width=40,
            height=40,
            corner_radius=12,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            fg_color=self.BG_ELEVATED,
            hover_color=self.ACCENT_RED,
            text_color=self.TEXT_PRIMARY,
            command=self._on_stop_speaking,
        )
        self.btn_mute.pack(side="left", padx=(0, 10), pady=11)

        self.entry_cmd = ctk.CTkEntry(
            composer,
            placeholder_text="Ask ARROW anything, or type a desktop command...",
            height=40,
            corner_radius=12,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            fg_color=self.BG_ELEVATED,
            border_width=0,
            text_color=self.TEXT_PRIMARY,
        )
        self.entry_cmd.pack(side="left", fill="x", expand=True, padx=4, pady=11)
        self.entry_cmd.bind("<Return>", lambda _e: self._on_send_click())

        self.btn_send = ctk.CTkButton(
            composer,
            text="Send  ➤",
            width=105,
            height=40,
            corner_radius=12,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color=self.ACCENT_BLUE,
            hover_color="#1D4ED8",
            command=self._on_send_click,
        )
        self.btn_send.pack(side="right", padx=12, pady=11)

    # ------------------------------------------------------------------
    # Page 2: Chat History
    # ------------------------------------------------------------------
    def _build_history_page(self) -> None:
        page = ctk.CTkFrame(self.content_area, fg_color=self.BG_CARD, corner_radius=16)
        self._pages["Chat History"] = page

        hdr = ctk.CTkFrame(page, fg_color="transparent")
        hdr.pack(fill="x", padx=20, pady=16)
        ctk.CTkLabel(
            hdr,
            text="SAVED CONVERSATION ARCHIVE",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=self.ACCENT_CYAN,
        ).pack(side="left")

        ctk.CTkButton(
            hdr,
            text="Clear Archive",
            fg_color=self.ACCENT_RED,
            hover_color="#DC2626",
            corner_radius=10,
            command=self._clear_history_from_ui,
        ).pack(side="right")

        self.history_box = ctk.CTkTextbox(
            page,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            fg_color="#0D1320",
            corner_radius=12,
        )
        self.history_box.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    # ------------------------------------------------------------------
    # Page 3: Reminders
    # ------------------------------------------------------------------
    def _build_reminders_page(self) -> None:
        page = ctk.CTkFrame(self.content_area, fg_color=self.BG_CARD, corner_radius=16)
        self._pages["Reminders"] = page

        ctk.CTkLabel(
            page,
            text="PERSISTENT REMINDERS",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=self.ACCENT_CYAN,
        ).pack(anchor="w", padx=20, pady=(18, 10))

        form = ctk.CTkFrame(page, fg_color="transparent")
        form.pack(fill="x", padx=20, pady=6)

        self.rem_entry = ctk.CTkEntry(
            form,
            placeholder_text="e.g., Remind me to submit lab report in 30 minutes",
            height=38,
            corner_radius=10,
            fg_color=self.BG_ELEVATED,
        )
        self.rem_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ctk.CTkButton(
            form,
            text="+ Schedule",
            height=38,
            corner_radius=10,
            fg_color=self.ACCENT_CYAN,
            text_color="#05101A",
            font=ctk.CTkFont(weight="bold"),
            command=self._ui_add_reminder,
        ).pack(side="left")

        self.rem_listbox = tk.Listbox(
            page,
            font=("Consolas", 11),
            bg="#0D1320",
            fg=self.TEXT_PRIMARY,
            bd=0,
            highlightthickness=0,
            selectbackground=self.ACCENT_BLUE,
        )
        self.rem_listbox.pack(fill="both", expand=True, padx=20, pady=14)

        ctk.CTkButton(
            page,
            text="Delete Selected",
            fg_color=self.ACCENT_RED,
            hover_color="#DC2626",
            corner_radius=10,
            command=self._ui_delete_reminder,
        ).pack(anchor="e", padx=20, pady=(0, 18))

    # ------------------------------------------------------------------
    # Page 4: To-Do List
    # ------------------------------------------------------------------
    def _build_todos_page(self) -> None:
        page = ctk.CTkFrame(self.content_area, fg_color=self.BG_CARD, corner_radius=16)
        self._pages["To-Do List"] = page

        ctk.CTkLabel(
            page,
            text="TASK & WORKFLOW BOARD",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=self.ACCENT_CYAN,
        ).pack(anchor="w", padx=20, pady=(18, 10))

        form = ctk.CTkFrame(page, fg_color="transparent")
        form.pack(fill="x", padx=20, pady=6)

        self.todo_entry = ctk.CTkEntry(
            form,
            placeholder_text="Enter a new task...",
            height=38,
            corner_radius=10,
            fg_color=self.BG_ELEVATED,
        )
        self.todo_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ctk.CTkButton(
            form,
            text="+ Add Task",
            height=38,
            corner_radius=10,
            fg_color=self.ACCENT_CYAN,
            text_color="#05101A",
            font=ctk.CTkFont(weight="bold"),
            command=self._ui_add_todo,
        ).pack(side="left")

        self.todo_listbox = tk.Listbox(
            page,
            font=("Consolas", 11),
            bg="#0D1320",
            fg=self.TEXT_PRIMARY,
            bd=0,
            highlightthickness=0,
            selectbackground=self.ACCENT_BLUE,
        )
        self.todo_listbox.pack(fill="both", expand=True, padx=20, pady=14)

        btns = ctk.CTkFrame(page, fg_color="transparent")
        btns.pack(fill="x", padx=20, pady=(0, 18))

        ctk.CTkButton(
            btns,
            text="✓ Complete Task",
            fg_color=self.ACCENT_GREEN,
            hover_color="#059669",
            text_color="#05101A",
            font=ctk.CTkFont(weight="bold"),
            corner_radius=10,
            command=self._ui_complete_todo,
        ).pack(side="left")

        ctk.CTkButton(
            btns,
            text="Delete Task",
            fg_color=self.ACCENT_RED,
            hover_color="#DC2626",
            corner_radius=10,
            command=self._ui_delete_todo,
        ).pack(side="right")

    # ------------------------------------------------------------------
    # Page 5: Smart Notes
    # ------------------------------------------------------------------
    def _build_notes_page(self) -> None:
        page = ctk.CTkFrame(self.content_area, fg_color=self.BG_CARD, corner_radius=16)
        self._pages["Notes"] = page

        ctk.CTkLabel(
            page,
            text="PERSONAL KNOWLEDGE NOTES",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=self.ACCENT_CYAN,
        ).pack(anchor="w", padx=20, pady=(18, 10))

        form = ctk.CTkFrame(page, fg_color="transparent")
        form.pack(fill="x", padx=20)

        self.note_title_entry = ctk.CTkEntry(
            form,
            placeholder_text="Note Title",
            height=36,
            corner_radius=10,
            fg_color=self.BG_ELEVATED,
        )
        self.note_title_entry.pack(fill="x", pady=(0, 8))

        self.note_body_text = ctk.CTkTextbox(
            form,
            height=90,
            corner_radius=10,
            fg_color=self.BG_ELEVATED,
            font=ctk.CTkFont(family="Segoe UI", size=12),
        )
        self.note_body_text.pack(fill="x", pady=(0, 8))

        ctk.CTkButton(
            form,
            text="Save Note",
            corner_radius=10,
            fg_color=self.ACCENT_CYAN,
            text_color="#05101A",
            font=ctk.CTkFont(weight="bold"),
            command=self._ui_add_note,
        ).pack(anchor="e")

        self.notes_listbox = tk.Listbox(
            page,
            font=("Consolas", 11),
            bg="#0D1320",
            fg=self.TEXT_PRIMARY,
            bd=0,
            highlightthickness=0,
            selectbackground=self.ACCENT_BLUE,
        )
        self.notes_listbox.pack(fill="both", expand=True, padx=20, pady=12)

        ctk.CTkButton(
            page,
            text="Delete Selected Note",
            fg_color=self.ACCENT_RED,
            hover_color="#DC2626",
            corner_radius=10,
            command=self._ui_delete_note,
        ).pack(anchor="e", padx=20, pady=(0, 18))

    # ------------------------------------------------------------------
    # Page 6: Preferences & Personalization
    # ------------------------------------------------------------------
    def _build_settings_page(self) -> None:
        page = ctk.CTkScrollableFrame(self.content_area, fg_color=self.BG_CARD, corner_radius=16)
        self._pages["Settings"] = page

        ctk.CTkLabel(
            page,
            text="ARROW SYSTEM PREFERENCES",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=self.ACCENT_CYAN,
        ).pack(anchor="w", padx=20, pady=(16, 14))

        self.set_name_var = ctk.StringVar(value=config.get("assistant_name", "ARROW"))
        self.set_wake_var = ctk.StringVar(value=config.get("wake_word", "arrow"))
        self.set_model_var = ctk.StringVar(value=config.get("gemini_model", "gemini-2.5-flash"))
        self.set_tts_var = ctk.StringVar(value=config.get("tts_engine", "pyttsx3"))
        self.set_rate_var = ctk.IntVar(value=int(config.get("speech_rate", 180)))
        self.set_vol_var = ctk.DoubleVar(value=float(config.get("speech_volume", 0.95)))
        self.set_city_var = ctk.StringVar(value=config.get("default_city", "Faizabad"))
        self.set_hist_var = ctk.StringVar(value=str(config.get("history_limit", 12)))
        self.set_boot_var = ctk.BooleanVar(value=bool(config.get("start_on_boot", False)))

        rows = [
            ("Assistant Identity Name", ctk.CTkEntry(page, textvariable=self.set_name_var, width=280, fg_color=self.BG_ELEVATED)),
            ("Wake Word Trigger", ctk.CTkEntry(page, textvariable=self.set_wake_var, width=280, fg_color=self.BG_ELEVATED)),
            ("Gemini Free-Tier Model", ctk.CTkEntry(page, textvariable=self.set_model_var, width=280, fg_color=self.BG_ELEVATED)),
            ("Voice Engine", ctk.CTkOptionMenu(page, variable=self.set_tts_var, values=["pyttsx3", "gtts"], width=280, fg_color=self.BG_ELEVATED)),
            ("Speech Speed (WPM)", ctk.CTkSlider(page, from_=110, to=260, variable=self.set_rate_var, width=280)),
            ("Speech Volume", ctk.CTkSlider(page, from_=0.1, to=1.0, variable=self.set_vol_var, width=280)),
            ("Default Weather City", ctk.CTkEntry(page, textvariable=self.set_city_var, width=280, fg_color=self.BG_ELEVATED)),
            ("Memory Context Turns", ctk.CTkEntry(page, textvariable=self.set_hist_var, width=280, fg_color=self.BG_ELEVATED)),
        ]

        for label_txt, widget in rows:
            row = ctk.CTkFrame(page, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=7)
            ctk.CTkLabel(row, text=label_txt, width=220, anchor="w", font=ctk.CTkFont(size=13)).pack(side="left")
            widget.pack(side="left", padx=12)

        ctk.CTkCheckBox(
            page,
            text="Launch ARROW automatically on Windows startup (disabled by default)",
            variable=self.set_boot_var,
            fg_color=self.ACCENT_CYAN,
            text_color=self.TEXT_MUTED,
        ).pack(anchor="w", padx=20, pady=(14, 18))

        ctk.CTkButton(
            page,
            text="Save Configuration",
            height=40,
            corner_radius=12,
            fg_color=self.ACCENT_CYAN,
            hover_color="#38BDF8",
            text_color="#05101A",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._save_settings_ui,
        ).pack(anchor="w", padx=20, pady=(0, 20))

    # ------------------------------------------------------------------
    # Page 7: About
    # ------------------------------------------------------------------
    def _build_about_page(self) -> None:
        page = ctk.CTkFrame(self.content_area, fg_color=self.BG_CARD, corner_radius=16)
        self._pages["About"] = page

        about_text = (
            "ARROW — Adaptive Responsive Real-time Operations & Workflow Assistant\n"
            "Modern Neural Desktop Edition\n\n"
            "• AI Intelligence: Google Gemini API via official `google-genai` SDK (Free-Tier Compatible)\n"
            "• Voice Pipeline: Non-blocking SpeechRecognition + Wake-Word Core + Offline pyttsx3 / gTTS\n"
            "• Security Architecture: Allowlisted Action Router & Confirmation Gate for destructive commands\n"
            "• Local-First Storage: Persistent JSON memory, tasks, reminders, notes, and custom music library\n\n"
            "Click '? Commands' on the Dashboard or type 'help' anytime to explore all supported commands."
        )
        ctk.CTkLabel(
            page,
            text=about_text,
            justify="left",
            anchor="nw",
            font=ctk.CTkFont(family="Segoe UI", size=14),
            text_color=self.TEXT_PRIMARY,
        ).pack(fill="both", expand=True, padx=26, pady=26)

    # ------------------------------------------------------------------
    # Navigation & Refresh Helpers
    # ------------------------------------------------------------------
    def show_page(self, page_name: str) -> None:
        self._active_page = page_name
        for frame in self._pages.values():
            frame.pack_forget()
        self._pages[page_name].pack(fill="both", expand=True)

        for name, btn in self._nav_buttons.items():
            if name == page_name:
                btn.configure(fg_color=self.BG_ELEVATED, text_color=self.ACCENT_CYAN)
            else:
                btn.configure(fg_color="transparent", text_color=self.TEXT_PRIMARY)

        if page_name == "Chat History":
            self._refresh_history_view()
        elif page_name == "Reminders":
            self._refresh_reminders_view()
        elif page_name == "To-Do List":
            self._refresh_todos_view()
        elif page_name == "Notes":
            self._refresh_notes_view()

    def _refresh_history_view(self) -> None:
        self.history_box.configure(state="normal")
        self.history_box.delete("1.0", "end")
        for msg in storage.get_all_messages():
            self.history_box.insert(
                "end",
                f"[{msg['timestamp']}] ({msg.get('mode', 'normal')}) {msg['role'].upper()}:\n{msg['content']}\n\n",
            )
        self.history_box.configure(state="disabled")

    def _refresh_reminders_view(self) -> None:
        self.rem_listbox.delete(0, tk.END)
        self._cached_rems: List[Dict[str, Any]] = storage.get_reminders(include_triggered=True)
        for r in self._cached_rems:
            status = "DONE" if r.get("triggered") else "UPCOMING"
            self.rem_listbox.insert(tk.END, f" [{status}] ({r['id']}) {r['due_iso']} — {r['text']}")

    def _refresh_todos_view(self) -> None:
        self.todo_listbox.delete(0, tk.END)
        self._cached_todos: List[Dict[str, Any]] = storage.get_todos()
        for t in self._cached_todos:
            mark = "✓" if t["completed"] else " "
            self.todo_listbox.insert(tk.END, f" [{mark}] ({t['id']}) {t['task']}")

    def _refresh_notes_view(self) -> None:
        self.notes_listbox.delete(0, tk.END)
        self._cached_notes: List[Dict[str, Any]] = storage.get_notes()
        for n in self._cached_notes:
            self.notes_listbox.insert(tk.END, f" ({n['id']}) {n['title']} — {n['content'][:80]}")

    # ------------------------------------------------------------------
    # Modern Chat Bubble Renderer
    # ------------------------------------------------------------------
    def append_chat(self, sender: str, message: str, tag: str = "assistant") -> None:
        is_user = tag == "user"
        is_system = tag == "system"

        row = ctk.CTkFrame(self.chat_scroll, fg_color="transparent")
        row.pack(fill="x", pady=5, padx=6)

        bubble_bg = "#1D4ED8" if is_user else ("#292524" if is_system else self.BG_ELEVATED)
        header_color = "#BAE6FD" if is_user else (self.ACCENT_AMBER if is_system else self.ACCENT_CYAN)

        bubble = ctk.CTkFrame(
            row,
            fg_color=bubble_bg,
            corner_radius=14,
            border_width=1,
            border_color="#2E3B55" if not is_user else "#3B82F6",
        )
        bubble.pack(side="right" if is_user else "left", anchor="e" if is_user else "w")

        ts = datetime.now().strftime("%I:%M %p")
        ctk.CTkLabel(
            bubble,
            text=f"{sender}  •  {ts}",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=header_color,
        ).pack(anchor="w", padx=14, pady=(8, 2))

        ctk.CTkLabel(
            bubble,
            text=message,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=self.TEXT_PRIMARY,
            justify="left",
            wraplength=560,
        ).pack(anchor="w", padx=14, pady=(0, 10))

        # Auto-scroll smoothly to newest message
        self.root.after(40, lambda: self.chat_scroll._parent_canvas.yview_moveto(1.0))

    # ------------------------------------------------------------------
    # Interactive Control Callbacks
    # ------------------------------------------------------------------
    def _on_send_click(self) -> None:
        text = self.entry_cmd.get().strip()
        if not text:
            return
        self.entry_cmd.delete(0, "end")
        self._dispatch_text(text, speak_back=False)

    def _dispatch_text(self, text: str, speak_back: bool) -> None:
        self.append_chat("You", text, "user")
        self.log_activity(f"Submitted: {text[:42]}")
        threading.Thread(
            target=self.on_submit_command, args=(text, speak_back), daemon=True
        ).start()

    def _on_mic_click(self) -> None:
        self.log_activity("Push-to-talk triggered")
        self.voice_in.trigger_single_listen()

    def _on_stop_speaking(self) -> None:
        self.voice_out.stop()
        self.log_activity("Voice output muted")

    def _toggle_wake_word(self) -> None:
        if self.voice_in.is_continuous_active:
            self.voice_in.stop_continuous()
            self.btn_wake.configure(
                text="🎙  Wake Word: OFF",
                fg_color=self.BG_ELEVATED,
                text_color=self.TEXT_PRIMARY,
            )
            self.log_activity("Wake-word listener stopped")
        else:
            self.voice_in.start_continuous()
            wake = config.get("wake_word", "arrow").upper()
            self.btn_wake.configure(
                text=f"🎙  Wake '{wake}': ON",
                fg_color=self.ACCENT_GREEN,
                text_color="#05101A",
            )
            self.log_activity(f"Wake-word active ('{wake}')")

    def _on_mode_changed(self, new_mode: str) -> None:
        config.set("response_mode", new_mode)
        self.log_activity(f"Mode -> {new_mode}")
        self.append_chat("System", f"Switched AI persona mode to {new_mode.capitalize()}.", "system")

    def _clear_history_from_ui(self) -> None:
        if messagebox.askyesno("Confirm Clear", "Clear all saved conversation history?"):
            storage.clear_messages()
            self._refresh_history_view()
            self.log_activity("History cleared")

    def _ui_add_reminder(self) -> None:
        raw = self.rem_entry.get().strip()
        if raw:
            res = self.productivity.parse_and_add_reminder(raw)
            self.rem_entry.delete(0, "end")
            self._refresh_reminders_view()
            self.log_activity(res)

    def _ui_delete_reminder(self) -> None:
        sel = self.rem_listbox.curselection()
        if sel:
            storage.delete_reminder(self._cached_rems[sel[0]]["id"])
            self._refresh_reminders_view()

    def _ui_add_todo(self) -> None:
        task = self.todo_entry.get().strip()
        if task:
            self.productivity.add_todo(task)
            self.todo_entry.delete(0, "end")
            self._refresh_todos_view()

    def _ui_complete_todo(self) -> None:
        sel = self.todo_listbox.curselection()
        if sel:
            storage.complete_todo(self._cached_todos[sel[0]]["id"])
            self._refresh_todos_view()

    def _ui_delete_todo(self) -> None:
        sel = self.todo_listbox.curselection()
        if sel:
            storage.delete_todo(self._cached_todos[sel[0]]["id"])
            self._refresh_todos_view()

    def _ui_add_note(self) -> None:
        title = self.note_title_entry.get().strip()
        body = self.note_body_text.get("1.0", "end").strip()
        if body:
            self.productivity.add_note(body, title=title)
            self.note_title_entry.delete(0, "end")
            self.note_body_text.delete("1.0", "end")
            self._refresh_notes_view()

    def _ui_delete_note(self) -> None:
        sel = self.notes_listbox.curselection()
        if sel:
            storage.delete_note(self._cached_notes[sel[0]]["id"])
            self._refresh_notes_view()

    def _save_settings_ui(self) -> None:
        new_name = self.set_name_var.get().strip() or "ARROW"
        try:
            hist_turns = max(2, min(40, int(self.set_hist_var.get())))
        except ValueError:
            hist_turns = 12

        config.update_many(
            {
                "assistant_name": new_name,
                "wake_word": self.set_wake_var.get().strip().lower() or "arrow",
                "gemini_model": self.set_model_var.get().strip() or "gemini-2.5-flash",
                "tts_engine": self.set_tts_var.get(),
                "speech_rate": int(self.set_rate_var.get()),
                "speech_volume": round(float(self.set_vol_var.get()), 2),
                "default_city": self.set_city_var.get().strip() or "Faizabad",
                "history_limit": hist_turns,
            }
        )
        self.lbl_brand.configure(text=f"◈  {new_name}")
        startup_msg = self.automation.set_windows_startup(self.set_boot_var.get())
        self.log_activity("Preferences updated")
        messagebox.showinfo("Saved", f"Preferences updated successfully.\n{startup_msg}")

    # ------------------------------------------------------------------
    # Thread-Safe UI Event Poller & Core State Sync
    # ------------------------------------------------------------------
    def enqueue_event(self, event_type: str, payload: Any) -> None:
        self.ui_queue.put({"type": event_type, "payload": payload})

    def log_activity(self, entry: str) -> None:
        self.activity_box.configure(state="normal")
        ts = datetime.now().strftime("%H:%M:%S")
        self.activity_box.insert("end", f"[{ts}] {entry}\n")
        self.activity_box.see("end")
        self.activity_box.configure(state="disabled")

    def _sync_neural_core(self) -> None:
        if self._is_thinking:
            self.neural_core.set_state("thinking")
        elif self._is_speaking:
            self.neural_core.set_state("speaking")
        elif self._is_listening:
            self.neural_core.set_state("listening")
        else:
            self.neural_core.set_state("standby")

    def _poll_ui_queue(self) -> None:
        while not self.ui_queue.empty():
            try:
                ev = self.ui_queue.get_nowait()
                etype = ev["type"]
                data = ev["payload"]

                if etype == "chat":
                    self.append_chat(data["sender"], data["text"], data.get("tag", "assistant"))
                elif etype == "log":
                    self.log_activity(str(data))
                elif etype == "listening":
                    text, active = data
                    self._is_listening = bool(active)
                    self.lbl_status_badge.configure(text=f"  {text.upper()}  ")
                    self.pill_listen.configure(
                        text_color=self.ACCENT_GREEN if active else self.TEXT_MUTED
                    )
                    self._sync_neural_core()
                elif etype == "thinking":
                    self._is_thinking = bool(data)
                    self.pill_think.configure(
                        text_color=self.ACCENT_AMBER if data else self.TEXT_MUTED
                    )
                    self.lbl_status_badge.configure(
                        text="  THINKING...  " if data else "  ONLINE  "
                    )
                    self._sync_neural_core()
                elif etype == "speaking":
                    self._is_speaking = bool(data)
                    self.pill_speak.configure(
                        text_color=self.ACCENT_CYAN if data else self.TEXT_MUTED
                    )
                    self._sync_neural_core()
                elif etype == "alert":
                    self.append_chat("ALERT", str(data), "system")
                    self.log_activity(f"Alert: {data}")
                    if self._active_page == "Reminders":
                        self._refresh_reminders_view()
            except queue.Empty:
                break

        self.root.after(40, self._poll_ui_queue)

    def _start_clock_loop(self) -> None:
        self.lbl_clock.configure(text=datetime.now().strftime("%a, %d %b %Y  •  %I:%M:%S %p"))
        self.root.after(1000, self._start_clock_loop)

    def _handle_close(self) -> None:
        self.neural_core.stop()
        self.on_shutdown()
        self.root.destroy()