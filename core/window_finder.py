"""
WindowFinder: Handles cross-platform game window locating and dynamic coordinate scaling.
Uses pywin32 on Windows for exact client area calculation, with robust fallbacks
for testing and Linux/macOS environments.
"""

from __future__ import annotations

import logging
import platform
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("WindowFinder")


@dataclass
class WindowRect:
    left: int
    top: int
    width: int
    height: int

    @property
    def x(self) -> int:
        return self.left

    @property
    def y(self) -> int:
        return self.top

    @property
    def w(self) -> int:
        return self.width

    @property
    def h(self) -> int:
        return self.height

    @property
    def right(self) -> int:
        return self.left + self.width

    @property
    def bottom(self) -> int:
        return self.top + self.height

    def to_mss_dict(self) -> Dict[str, int]:
        """Convert to mss monitor dict format."""
        return {"top": self.top, "left": self.left, "width": self.width, "height": self.height}


class WindowFinder:
    """Locates Hearthstone game window and calculates normalized sub-regions."""

    def __init__(self, title: str = "Hearthstone", class_name: str = "UnityWndClass") -> None:
        self.title = title
        self.class_name = class_name
        self.system = platform.system()
        self._last_rect: Optional[WindowRect] = None

    def find_window(self) -> Optional[WindowRect]:
        """Finds Hearthstone client coordinates."""
        if self.system == "Windows":
            return self._find_windows()
        else:
            return self._find_generic()

    def _find_windows(self) -> Optional[WindowRect]:
        """Windows native client rect calculation using win32gui."""
        try:
            import win32gui
            # Try by Unity class name & title first
            hwnd = win32gui.FindWindow("UnityWndClass", "Hearthstone")
            if not hwnd:
                hwnd = win32gui.FindWindow("UnityWndClass", "炉石传说")
            if not hwnd:
                hwnd = win32gui.FindWindow("UnityWndClass", None)
            if not hwnd:
                def enum_callback(h, matches):
                    if win32gui.IsWindowVisible(h):
                        cls = win32gui.GetClassName(h)
                        t = win32gui.GetWindowText(h)
                        if cls == "UnityWndClass" or t in ["Hearthstone", "炉石传说"]:
                            matches.append(h)
                matches: List[int] = []
                win32gui.EnumWindows(enum_callback, matches)
                if matches:
                    hwnd = matches[0]

            if not hwnd:
                return None

            self._last_hwnd = hwnd

            # Get client rect (excludes borders and title bar)
            client_left, client_top, client_right, client_bottom = win32gui.GetClientRect(hwnd)
            # Map client (0,0) to screen coordinates
            screen_x, screen_y = win32gui.ClientToScreen(hwnd, (0, 0))
            width = client_right - client_left
            height = client_bottom - client_top

            if width <= 0 or height <= 0:
                return None

            rect = WindowRect(left=screen_x, top=screen_y, width=width, height=height)
            self._last_rect = rect
            return rect
        except ImportError:
            logger.debug("pywin32 not installed. Using generic window bounds.")
            return self._find_generic()
        except Exception as e:
            logger.error(f"Error querying Windows window: {e}")
            return self._find_generic()

    def grab_window_image(self, win: Optional[WindowRect] = None):
        """
        Captures window frame in <10ms via Win32 PrintWindow directly from window DC.
        Falls back to mss desktop region grab.
        """
        if self.system == "Windows":
            hwnd = getattr(self, "_last_hwnd", None)
            if not hwnd:
                self._find_windows()
                hwnd = getattr(self, "_last_hwnd", None)

            if hwnd:
                try:
                    import ctypes
                    from ctypes import wintypes
                    import numpy as np

                    user32 = ctypes.windll.user32
                    gdi32 = ctypes.windll.gdi32

                    rect = wintypes.RECT()
                    user32.GetClientRect(hwnd, ctypes.byref(rect))
                    w = rect.right - rect.left
                    h = rect.bottom - rect.top

                    if w > 0 and h > 0:
                        hwnd_dc = user32.GetDC(hwnd)
                        mem_dc = gdi32.CreateCompatibleDC(hwnd_dc)
                        bitmap = gdi32.CreateCompatibleBitmap(hwnd_dc, w, h)
                        gdi32.SelectObject(mem_dc, bitmap)

                        # PW_RENDERFULLCONTENT = 2
                        res = user32.PrintWindow(hwnd, mem_dc, 2)
                        if not res:
                            res = user32.PrintWindow(hwnd, mem_dc, 0)

                        class BITMAPINFOHEADER(ctypes.Structure):
                            _fields_ = [
                                ('biSize', wintypes.DWORD),
                                ('biWidth', wintypes.LONG),
                                ('biHeight', wintypes.LONG),
                                ('biPlanes', wintypes.WORD),
                                ('biBitCount', wintypes.WORD),
                                ('biCompression', wintypes.DWORD),
                                ('biSizeImage', wintypes.DWORD),
                                ('biXPelsPerMeter', wintypes.LONG),
                                ('biYPelsPerMeter', wintypes.LONG),
                                ('biClrUsed', wintypes.DWORD),
                                ('biClrImportant', wintypes.DWORD)
                            ]

                        class BITMAPINFO(ctypes.Structure):
                            _fields_ = [('bmiHeader', BITMAPINFOHEADER), ('bmiColors', wintypes.DWORD * 3)]

                        bmi = BITMAPINFO()
                        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
                        bmi.bmiHeader.biWidth = w
                        bmi.bmiHeader.biHeight = -h  # top-down
                        bmi.bmiHeader.biPlanes = 1
                        bmi.bmiHeader.biBitCount = 32
                        bmi.bmiHeader.biCompression = 0

                        buffer = (ctypes.c_ubyte * (w * h * 4))()
                        gdi32.GetDIBits(mem_dc, bitmap, 0, h, ctypes.byref(buffer), ctypes.byref(bmi), 0)

                        gdi32.DeleteObject(bitmap)
                        gdi32.DeleteDC(mem_dc)
                        user32.ReleaseDC(hwnd, hwnd_dc)

                        if res:
                            img = np.frombuffer(buffer, dtype=np.uint8).reshape((h, w, 4))
                            return img[:, :, :3]
                except Exception as e:
                    logger.debug(f"ctypes PrintWindow capture fallback to mss: {e}")

        # Fallback to mss
        try:
            import mss
            import numpy as np
            if win is None:
                win = self.find_window()
            if not win:
                return None
            with mss.mss() as sct:
                shot = sct.grab(win.to_mss_dict())
                arr = np.array(shot)
                return arr[:, :, :3]
        except Exception as e:
            logger.debug(f"mss capture fallback: {e}")
            return None

    def _find_generic(self) -> Optional[WindowRect]:
        """Generic fallback for development, testing, and Linux/macOS environments."""
        if self._last_rect:
            return self._last_rect

        # Default standard 1920x1080 window for mock or screen capture
        self._last_rect = WindowRect(left=0, top=0, width=1920, height=1080)
        return self._last_rect

    def set_mock_rect(self, rect: WindowRect) -> None:
        """Sets a mock window rectangle for automated testing."""
        self._last_rect = rect

    @staticmethod
    def get_draft_card_name_regions(win: WindowRect) -> List[WindowRect]:
        """
        Calculates the 3 card title banner regions in Arena draft mode.
        Normalized relative coordinates are calibrated against Hearthstone's 16:9 Arena draft UI.
        
        Cards are positioned at:
        - Card 1 (Left):   Center ~ 28.5% width, banner y ~ 51.5% - 56.5% height
        - Card 2 (Middle): Center ~ 50.0% width, banner y ~ 51.5% - 56.5% height
        - Card 3 (Right):  Center ~ 71.5% width, banner y ~ 51.5% - 56.5% height
        """
        # Relative boundaries for card title text banners:
        # (rel_x, rel_y, rel_w, rel_h)
        rel_banners = [
            (0.205, 0.505, 0.160, 0.065),  # Left card title
            (0.420, 0.505, 0.160, 0.065),  # Middle card title
            (0.635, 0.505, 0.160, 0.065),  # Right card title
        ]

        regions = []
        for rx, ry, rw, rh in rel_banners:
            regions.append(
                WindowRect(
                    left=int(win.left + rx * win.width),
                    top=int(win.top + ry * win.height),
                    width=int(rw * win.width),
                    height=int(rh * win.height),
                )
            )
        return regions

    @staticmethod
    def get_draft_hero_name_regions(win: WindowRect) -> List[WindowRect]:
        """
        Calculates the 3 hero name banner regions in Arena hero draft mode (opening 1-out-of-3).
        In Hearthstone, hero name banners are located below the round hero portrait medallions (~68%-76% y).
        """
        rel_banners = [
            (0.220, 0.680, 0.160, 0.080),  # Left hero name banner
            (0.420, 0.680, 0.160, 0.080),  # Center hero name banner
            (0.620, 0.680, 0.160, 0.080),  # Right hero name banner
        ]
        return [
            WindowRect(
                left=int(win.left + rx * win.width),
                top=int(win.top + ry * win.height),
                width=int(rw * win.width),
                height=int(rh * win.height),
            )
            for rx, ry, rw, rh in rel_banners
        ]

    @staticmethod
    def get_draft_full_card_regions(win: WindowRect) -> List[WindowRect]:
        """Full card bounding boxes for the 3 arena draft choices."""
        rel_cards = [
            (0.180, 0.280, 0.210, 0.440),
            (0.395, 0.280, 0.210, 0.440),
            (0.610, 0.280, 0.210, 0.440),
        ]
        return [
            WindowRect(
                left=int(win.left + rx * win.width),
                top=int(win.top + ry * win.height),
                width=int(rw * win.width),
                height=int(rh * win.height),
            )
            for rx, ry, rw, rh in rel_cards
        ]
