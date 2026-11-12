"""
automation.py
Safe Windows desktop automation: browser shortcuts, allowlisted app launcher,
guarded file management, system controls, screenshots, clipboard, and startup integration.
"""

import ctypes
import os
import platform
import subprocess
import urllib.parse
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import psutil
from PIL import ImageGrab

from config import BASE_DIR, SCREENSHOTS_DIR, config


class DesktopAutomation:
    """Provides safe, allowlisted Windows desktop and browser controls."""

    # Safe Windows system/developer applications (resolved via PATH or Windows shell)
    SAFE_APPS: Dict[str, List[str]] = {
        "vscode": ["code", "Code.exe"],
        "vs code": ["code", "Code.exe"],
        "visual studio code": ["code", "Code.exe"],
        "notepad": ["notepad.exe"],
        "calculator": ["calc.exe"],
        "calc": ["calc.exe"],
        "cmd": ["cmd.exe"],
        "command prompt": ["cmd.exe"],
        "terminal": ["wt.exe", "cmd.exe"],
        "settings": ["ms-settings:"],
        "windows settings": ["ms-settings:"],
        "explorer": ["explorer.exe"],
        "file explorer": ["explorer.exe"],
        "taskmgr": ["taskmgr.exe"],
        "task manager": ["taskmgr.exe"],
        "paint": ["mspaint.exe"],
    }

    # ---------------- Browser Automation ----------------
    def try_open_website(self, target: str) -> Optional[str]:
        clean = target.strip().lower().rstrip(".")
        shortcuts = config.get("custom_shortcuts", {})

        if clean in shortcuts:
            url = shortcuts[clean]
            webbrowser.open(url)
            return f"Opening {clean.capitalize()}."

        if clean.startswith(("http://", "https://")) or (
            "." in clean and " " not in clean and not clean.endswith((".txt", ".py", ".pdf", ".docx"))
        ):
            url = clean if clean.startswith(("http://", "https://")) else f"https://{clean}"
            webbrowser.open(url)
            return f"Opening {url}."

        return None

    def search_google(self, query: str) -> str:
        encoded = urllib.parse.quote_plus(query.strip())
        webbrowser.open(f"https://www.google.com/search?q={encoded}")
        return f"Searching Google for '{query.strip()}'."

    def search_youtube(self, query: str) -> str:
        encoded = urllib.parse.quote_plus(query.strip())
        webbrowser.open(f"https://www.youtube.com/results?search_query={encoded}")
        return f"Searching YouTube for '{query.strip()}'."

    # ---------------- Application Launching ----------------
    def try_open_app(self, app_name: str) -> Optional[str]:
        key = app_name.strip().lower()
        if key not in self.SAFE_APPS:
            return None

        candidates = self.SAFE_APPS[key]
        for candidate in candidates:
            try:
                if candidate.startswith("ms-settings:"):
                    os.startfile(candidate)  # type: ignore[attr-defined]
                    return "Opening Windows Settings."
                subprocess.Popen(
                    candidate,
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return f"Launching {app_name}."
            except Exception:
                continue

        return f"Could not launch {app_name}. Ensure it is installed and available in Windows PATH."

    # ---------------- Guarded File Management ----------------
    def _resolve_safe_path(self, user_path: str) -> Path:
        root = Path(config.get("file_search_root", str(Path.home() / "Documents"))).resolve()
        candidate = Path(user_path.strip().strip('"'))
        if not candidate.is_absolute():
            candidate = (root / candidate).resolve()
        else:
            candidate = candidate.resolve()
        return candidate

    def search_files(self, filename_query: str) -> str:
        root = Path(config.get("file_search_root", str(Path.home() / "Documents")))
        if not root.exists():
            return f"Configured search directory does not exist: {root}"

        needle = filename_query.strip().lower()
        matches: List[str] = []
        for dirpath, _, filenames in os.walk(root):
            for fname in filenames:
                if needle in fname.lower():
                    matches.append(str(Path(dirpath) / fname))
                    if len(matches) >= 8:
                        break
            if len(matches) >= 8:
                break

        if not matches:
            return f"No files matching '{filename_query}' found inside {root}."
        return f"Found {len(matches)} match(es) in {root.name}:\n" + "\n".join(f"• {m}" for m in matches)

    def list_files(self, folder_arg: Optional[str] = None) -> str:
        target = self._resolve_safe_path(folder_arg) if folder_arg else Path(
            config.get("file_search_root", str(Path.home() / "Documents"))
        )
        if not target.exists() or not target.is_dir():
            return f"Directory not found: {target}"

        entries = sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))[:25]
        if not entries:
            return f"The folder '{target.name}' is empty."
        lines = [f"{'[DIR]' if e.is_dir() else '[FILE]'} {e.name}" for e in entries]
        return f"Contents of {target}:\n" + "\n".join(lines)

    def create_folder(self, folder_name: str) -> str:
        target = self._resolve_safe_path(folder_name)
        target.mkdir(parents=True, exist_ok=True)
        return f"Folder created at: {target}"

    def read_text_file(self, file_arg: str) -> str:
        target = self._resolve_safe_path(file_arg)
        if not target.exists() or not target.is_file():
            return f"File not found: {target}"
        if target.stat().st_size > 200_000:
            return "File is larger than 200 KB; refusing to dump huge file into chat."
        try:
            content = target.read_text(encoding="utf-8", errors="replace")
            return f"Contents of {target.name}:\n\n{content[:3000]}"
        except Exception as e:
            return f"Unable to read file: {e}"

    def file_info(self, file_arg: str) -> str:
        target = self._resolve_safe_path(file_arg)
        if not target.exists():
            return f"Path not found: {target}"
        stat = target.stat()
        modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        size_kb = round(stat.st_size / 1024, 2)
        return (
            f"Name: {target.name} | Type: {'Folder' if target.is_dir() else 'File'} | "
            f"Size: {size_kb} KB | Modified: {modified}"
        )

    def delete_file_confirmed(self, file_arg: str) -> str:
        target = self._resolve_safe_path(file_arg)
        if not target.exists() or not target.is_file():
            return f"File not found: {target}"
        try:
            target.unlink()
            return f"Deleted file: {target.name}"
        except Exception as e:
            return f"Failed to delete file: {e}"

    # ---------------- System Controls ----------------
    def take_screenshot(self) -> str:
        try:
            filename = f"arrow_shot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            out_path = SCREENSHOTS_DIR / filename
            img = ImageGrab.grab()
            img.save(out_path)
            return f"Screenshot saved to {out_path}."
        except Exception as e:
            return f"Failed to capture screenshot: {e}"

    def get_battery_status(self) -> str:
        battery = psutil.sensors_battery()
        if battery is None:
            return "No battery detected (running on desktop AC power)."
        plugged = "plugged in and charging" if battery.power_plugged else "running on battery"
        return f"Battery level is at {battery.percent}%, currently {plugged}."

    def get_system_info(self) -> str:
        cpu = psutil.cpu_percent(interval=0.3)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage(str(Path.home().anchor or "C:\\"))
        return (
            f"OS: {platform.system()} {platform.release()} | "
            f"CPU Usage: {cpu}% | "
            f"RAM: {mem.used // (1024**3)}/{mem.total // (1024**3)} GB ({mem.percent}%) | "
            f"Disk Used: {disk.percent}%"
        )

    def adjust_volume(self, action: str) -> str:
        """Uses Windows Virtual-Key media events (VK_VOLUME_UP/DOWN/MUTE) with zero extra dependencies."""
        VK_VOLUME_MUTE = 0xAD
        VK_VOLUME_DOWN = 0xAE
        VK_VOLUME_UP = 0xAF
        KEYEVENTF_KEYUP = 0x0002

        if action == "mute":
            ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 0, 0)
            ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, KEYEVENTF_KEYUP, 0)
            return "Toggled system audio mute."

        vk = VK_VOLUME_UP if action == "up" else VK_VOLUME_DOWN
        for _ in range(4):  # ~8% volume step
            ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
            ctypes.windll.user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
        return f"System volume {'increased' if action == 'up' else 'decreased'}."

    def read_clipboard(self) -> str:
        """Reads text from Windows clipboard safely via tkinter/ctypes."""
        import tkinter as tk
        try:
            r = tk.Tk()
            r.withdraw()
            text = r.clipboard_get()
            r.destroy()
            return text.strip() if text.strip() else "Clipboard is empty."
        except Exception:
            return "Clipboard is empty or contains non-text data."

    def shutdown_pc_confirmed(self) -> str:
        subprocess.Popen(["shutdown", "/s", "/t", "10"], shell=True)
        return "Windows will shut down in 10 seconds."

    def restart_pc_confirmed(self) -> str:
        subprocess.Popen(["shutdown", "/r", "/t", "10"], shell=True)
        return "Windows will restart in 10 seconds."

    # ---------------- Optional Windows Startup Toggle ----------------
    def set_windows_startup(self, enable: bool) -> str:
        """Creates or removes a startup launcher .bat in the user's Windows Startup folder."""
        startup_dir = Path(os.getenv("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs\Startup"
        bat_path = startup_dir / "ARROW_Assistant.bat"

        if not enable:
            if bat_path.exists():
                bat_path.unlink()
            config.set("start_on_boot", False)
            return "Disabled ARROW auto-start on Windows boot."

        venv_python = BASE_DIR / ".venv" / "Scripts" / "pythonw.exe"
        py_exec = str(venv_python) if venv_python.exists() else "pythonw"
        main_script = BASE_DIR / "main.py"

        bat_content = f'@echo off\ncd /d "{BASE_DIR}"\nstart "" "{py_exec}" "{main_script}"\n'
        bat_path.write_text(bat_content, encoding="utf-8")
        config.set("start_on_boot", True)
        return f"Enabled ARROW auto-start via {bat_path}."