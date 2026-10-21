"""
ConfigManager: Manages local configuration for Hearthstone Arena AI Assistant.
Handles reading and writing config.json, environment variable fallbacks,
and auto-detection of Hearthstone log paths.
"""

from __future__ import annotations

import json
import os
import platform
import sys
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_CONFIG: Dict[str, Any] = {
    # Gemini AI configuration
    "gemini_api_key": "",
    "gemini_model": "gemini-2.0-flash",
    "gemini_temperature": 0.3,
    
    # Hearthstone log path
    "hearthstone_log_dir": "",
    
    # OCR and perception configuration
    "ocr_lang": "chi_sim+eng",
    "ocr_poll_interval_ms": 1000,
    "animation_lock_duration_sec": 2.5,  # Anti-debouncing state lock (~2.5s)
    "tesseract_cmd": "",  # Custom tesseract path if needed
    
    # Window matching
    "window_title": "Hearthstone",
    "window_class": "UnityWndClass",
    
    # Overlay UI configuration
    "overlay_x": 1400,
    "overlay_y": 60,
    "overlay_width": 480,
    "overlay_height": 720,
    "wide_overlay_width": 640,
    "overlay_opacity": 0.92,
    "click_through": False,
    "always_on_top": True,
    "follow_game_desktop": True,  # Only display on the virtual desktop where Hearthstone is present
    
    # v10 Apex additions: i18n, capsule HUD, global hotkeys
    "locale": "zh-CN",
    "capsule_mode": False,
    "global_hotkeys_enabled": True,
    "hotkey_toggle_overlay": "Ctrl+Shift+H",
    "hotkey_toggle_tree": "Ctrl+Shift+T",
    "hotkey_snapshot": "Ctrl+Shift+S",
    
    # Performance & caching
    "evaluation_cache_enabled": True,
    "debug_mode": False,
}


def get_default_hearthstone_log_dir() -> str:
    """Attempt to detect default Hearthstone log directory across platforms."""
    system = platform.system()
    if system == "Windows":
        # Check standard installation directories first
        candidates = [
            Path(r"C:\Program Files (x86)\Hearthstone\Logs"),
            Path(r"C:\Program Files\Hearthstone\Logs"),
            Path(r"D:\Hearthstone\Logs"),
            Path(r"E:\Hearthstone\Logs"),
        ]
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if local_app_data:
            candidates.append(Path(local_app_data) / "Blizzard" / "Hearthstone" / "Logs")

        for c in candidates:
            if c.exists():
                return str(c)

        # Fallback to AppData if none exist yet
        if local_app_data:
            return str(Path(local_app_data) / "Blizzard" / "Hearthstone" / "Logs")
        return r"C:\Program Files (x86)\Hearthstone\Logs"

    elif system == "Darwin":
        candidate = Path.home() / "Library" / "Logs" / "Blizzard" / "Hearthstone"
        if candidate.exists():
            return str(candidate)
    elif system == "Linux":
        # Common Wine / Proton / Lutris paths
        candidates = [
            Path("/mnt/c/Program Files (x86)/Hearthstone/Logs"),
            Path.home() / ".wine" / "drive_c" / "users" / os.environ.get("USER", "user") / "AppData" / "Local" / "Blizzard" / "Hearthstone" / "Logs",
            Path.home() / ".local" / "share" / "Steam" / "steamapps" / "compatdata" / "2861690" / "pfx" / "drive_c" / "users" / "steamuser" / "AppData" / "Local" / "Blizzard" / "Hearthstone" / "Logs",
        ]
        for c in candidates:
            if c.exists():
                return str(c)

    # Fallback to local logs directory for development/simulation
    local_logs = Path("./logs").resolve()
    return str(local_logs)


def get_hearthstone_config_paths() -> List[Path]:
    """Return all viable paths to Hearthstone's log.config file."""
    paths: List[Path] = []
    system = platform.system()
    if system == "Windows":
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if local_app_data:
            paths.append(Path(local_app_data) / "Blizzard" / "Hearthstone" / "log.config")
        paths.append(Path(r"C:\Program Files (x86)\Hearthstone\log.config"))
        paths.append(Path(r"C:\Program Files\Hearthstone\log.config"))
    elif system == "Darwin":
        paths.append(Path.home() / "Library" / "Preferences" / "Blizzard" / "Hearthstone" / "log.config")
    elif system == "Linux":
        paths.append(Path("/mnt/c/Users/sageb/AppData/Local/Blizzard/Hearthstone/log.config"))
        paths.append(Path("/mnt/c/Program Files (x86)/Hearthstone/log.config"))
    return paths


def get_hearthstone_config_path() -> Optional[Path]:
    """Return primary path to Hearthstone's log.config file."""
    paths = get_hearthstone_config_paths()
    return paths[0] if paths else None


class ConfigManager:
    """Manages application configuration with persistence to JSON file."""

    def __init__(self, config_path: str = "config.json") -> None:
        p = Path(config_path)
        if not p.is_absolute():
            if getattr(sys, "frozen", False):
                p = Path(sys.executable).resolve().parent / config_path
            else:
                p = Path(__file__).resolve().parent.parent / config_path
        self.config_file = p.resolve()
        self._data: Dict[str, Any] = {}
        self.load()

    def load(self) -> Dict[str, Any]:
        """Loads configuration from disk, applying defaults and environment overrides."""
        merged = dict(DEFAULT_CONFIG)
        if not merged["hearthstone_log_dir"]:
            merged["hearthstone_log_dir"] = get_default_hearthstone_log_dir()

        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    disk_data = json.load(f)
                    if isinstance(disk_data, dict):
                        merged.update(disk_data)
            except Exception as e:
                print(f"[ConfigManager] Warning: Failed to parse {self.config_file}: {e}. Using defaults.")

        # Environment variable override for API key
        env_key = os.environ.get("GEMINI_API_KEY")
        if env_key and not merged.get("gemini_api_key"):
            merged["gemini_api_key"] = env_key

        self._data = merged
        # Ensure config file exists
        if not self.config_file.exists():
            self.save()
        return self._data

    def save(self) -> None:
        """Persists current configuration to disk safely."""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            temp_file = self.config_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
            temp_file.replace(self.config_file)
        except Exception as e:
            print(f"[ConfigManager] Error saving config to {self.config_file}: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any, auto_save: bool = True) -> None:
        self._data[key] = value
        if auto_save:
            self.save()

    def update(self, updates: Dict[str, Any], auto_save: bool = True) -> None:
        self._data.update(updates)
        if auto_save:
            self.save()

    def as_dict(self) -> Dict[str, Any]:
        return dict(self._data)

    def ensure_log_config(self) -> bool:
        """
        Creates or updates log.config for Hearthstone so Power.log, Arena.log, LoadingScreen, and Zone are generated.
        Writes to both AppData and Hearthstone game directory.
        Returns True if log.config was created in at least one location.
        """
        paths = get_hearthstone_config_paths()
        if not paths:
            return False

        desired_sections = """[Power]
LogLevel=1
FilePrinting=true
ConsolePrinting=false
ScreenPrinting=false

[Arena]
LogLevel=1
FilePrinting=true
ConsolePrinting=false
ScreenPrinting=false

[LoadingScreen]
LogLevel=1
FilePrinting=true
ConsolePrinting=false
ScreenPrinting=false

[Zone]
LogLevel=1
FilePrinting=true
ConsolePrinting=false
ScreenPrinting=false
"""
        any_success = False
        for p in paths:
            try:
                p.parent.mkdir(parents=True, exist_ok=True)
                with open(p, "w", encoding="utf-8") as f:
                    f.write(desired_sections)
                any_success = True
            except Exception as e:
                print(f"[ConfigManager] Notice: Could not write log.config at {p}: {e}")
        return any_success
