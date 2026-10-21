"""
GlobalHotkeyManager: System-Wide Hotkey Listener and Dispatcher.
Registers Windows global hotkeys (Ctrl+Shift+H, Ctrl+Shift+T, Ctrl+Shift+S)
with graceful headless fallback for Linux/WSL and headless test environments.
"""

from __future__ import annotations

import ctypes
import logging
import platform
import threading
from typing import Callable, Dict, Optional

logger = logging.getLogger("GlobalHotkeys")


class HotkeyID:
    TOGGLE_OVERLAY = 1001   # Ctrl+Shift+H
    TOGGLE_TREE = 1002      # Ctrl+Shift+T
    SNAPSHOT_ANALYSIS = 1003  # Ctrl+Shift+S


# Windows API constants
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312

VK_H = 0x48
VK_T = 0x54
VK_S = 0x53


class GlobalHotkeyManager:
    """Manages low-latency system-wide global hotkeys with Windows win32 API."""

    _instance: Optional[GlobalHotkeyManager] = None

    def __init__(self) -> None:
        self._callbacks: Dict[int, Callable[[], None]] = {}
        self._is_running = False
        self._thread: Optional[threading.Thread] = None
        self._thread_id: Optional[int] = None
        self._is_windows = platform.system() == "Windows" and hasattr(ctypes, "windll")

    @classmethod
    def get_instance(cls) -> GlobalHotkeyManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_callback(self, hotkey_id: int, callback: Callable[[], None]) -> None:
        self._callbacks[hotkey_id] = callback

    def simulate_trigger(self, hotkey_id: int) -> bool:
        """Directly triggers a registered hotkey callback (useful in tests and menus)."""
        cb = self._callbacks.get(hotkey_id)
        if cb:
            try:
                cb()
                return True
            except Exception as e:
                logger.error(f"Error in simulated hotkey callback {hotkey_id}: {e}")
        return False

    def start(self) -> bool:
        if self._is_running:
            return True

        if not self._is_windows:
            logger.info("GlobalHotkeyManager: Non-Windows platform or headless; using simulated/Qt shortcut mode.")
            self._is_running = True
            return True

        self._is_running = True
        self._thread = threading.Thread(target=self._win32_message_loop, daemon=True, name="Win32HotkeyLoop")
        self._thread.start()
        return True

    def stop(self) -> None:
        self._is_running = False
        if self._is_windows and self._thread_id:
            try:
                WM_QUIT = 0x0012
                ctypes.windll.user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
            except Exception:
                pass
        self._thread = None
        self._thread_id = None

    def _win32_message_loop(self) -> None:
        try:
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            self._thread_id = kernel32.GetCurrentThreadId()

            # Register standard hotkeys
            # Ctrl + Shift + H
            user32.RegisterHotKey(None, HotkeyID.TOGGLE_OVERLAY, MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT, VK_H)
            # Ctrl + Shift + T
            user32.RegisterHotKey(None, HotkeyID.TOGGLE_TREE, MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT, VK_T)
            # Ctrl + Shift + S
            user32.RegisterHotKey(None, HotkeyID.SNAPSHOT_ANALYSIS, MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT, VK_S)

            logger.info("GlobalHotkeyManager: Windows global hotkeys registered successfully.")

            class MSG(ctypes.Structure):
                _fields_ = [
                    ("hwnd", ctypes.c_void_p),
                    ("message", ctypes.c_uint),
                    ("wParam", ctypes.c_void_p),
                    ("lParam", ctypes.c_void_p),
                    ("time", ctypes.c_ulong),
                    ("pt_x", ctypes.c_long),
                    ("pt_y", ctypes.c_long),
                ]

            msg = MSG()
            while self._is_running:
                # GetMessage blocks until a message arrives
                ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if ret == 0 or ret == -1:
                    break

                if msg.message == WM_HOTKEY:
                    hotkey_id = int(msg.wParam)
                    cb = self._callbacks.get(hotkey_id)
                    if cb:
                        try:
                            cb()
                        except Exception as e:
                            logger.error(f"Error executing hotkey callback {hotkey_id}: {e}")

                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))

            # Cleanup
            user32.UnregisterHotKey(None, HotkeyID.TOGGLE_OVERLAY)
            user32.UnregisterHotKey(None, HotkeyID.TOGGLE_TREE)
            user32.UnregisterHotKey(None, HotkeyID.SNAPSHOT_ANALYSIS)
        except Exception as e:
            logger.warning(f"GlobalHotkeyManager message loop exited: {e}")
        finally:
            self._is_running = False
