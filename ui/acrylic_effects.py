"""
Native Acrylic Glass & Breathing Aura Border (原生毛玻璃亚克力与呼吸流光边框)
- Injects Windows 11 DWM Mica / Acrylic translucent glass blur via ctypes.
- Gracefully falls back to high-end CSS backdrop glassmorphism on Linux/WSL/legacy Windows.
- Provides dynamic pulsating aura glow shaders for game-state alerts (Lethal, Blunder, Miracle, Zen).
"""

import ctypes
from enum import Enum
import math
import platform
from typing import Optional, Tuple
from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QPen, QRadialGradient


class AuraState(str, Enum):
    IDLE_CYBER = "IDLE_CYBER"          # 常态典雅黑金
    LETHAL_GOLD = "LETHAL_GOLD"        # 斩杀激昂流金
    BLUNDER_RED = "BLUNDER_RED"        # 伏笔警报赤红
    MIRACLE_PURPLE = "MIRACLE_PURPLE"  # 奇迹逆转暗紫
    ZEN_EMERALD = "ZEN_EMERALD"        # 禅意沉静翡翠


class AcrylicGlassHelper:
    """
    Applies native Windows 11 Acrylic/Mica effect or CSS glass fallback.
    """

    DWMWA_SYSTEMBACKDROP_TYPE = 38
    DWMSBT_ACRYLIC = 3
    DWMSBT_MICA = 2

    @classmethod
    def apply_acrylic(cls, window_hwnd: int, dark_mode: bool = True) -> bool:
        """
        Attempts to enable Windows 11 Desktop Window Manager acrylic backdrop.
        """
        if platform.system() != "Windows" or not hasattr(ctypes, "windll"):
            return False

        try:
            hwnd = int(window_hwnd)
            dwmapi = ctypes.windll.dwmapi

            # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            dark_flag = ctypes.c_int(1 if dark_mode else 0)
            dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark_flag), ctypes.sizeof(dark_flag))

            # Enable Acrylic backdrop (Win 11 22H2+)
            backdrop_type = ctypes.c_int(cls.DWMSBT_ACRYLIC)
            res = dwmapi.DwmSetWindowAttribute(
                hwnd, cls.DWMWA_SYSTEMBACKDROP_TYPE, ctypes.byref(backdrop_type), ctypes.sizeof(backdrop_type)
            )
            return res == 0
        except Exception:
            return False

    @classmethod
    def get_glass_stylesheet(cls, aura: AuraState = AuraState.IDLE_CYBER, glow_phase: float = 0.5) -> str:
        """
        Returns high-end responsive glassmorphism stylesheet.
        """
        # Pulsing opacity calculation: 0.35 to 0.85
        pulse_alpha = 0.4 + 0.35 * (0.5 + 0.5 * math.sin(glow_phase * 2 * math.pi))

        if aura == AuraState.LETHAL_GOLD:
            border = f"rgba(245, 158, 11, {pulse_alpha:.2f})"
            glow_shadow = "0 0 16px rgba(245, 158, 11, 0.65)"
            bg = "rgba(22, 18, 10, 240)"
        elif aura == AuraState.BLUNDER_RED:
            border = f"rgba(239, 68, 68, {pulse_alpha:.2f})"
            glow_shadow = "0 0 18px rgba(239, 68, 68, 0.75)"
            bg = "rgba(28, 12, 14, 245)"
        elif aura == AuraState.MIRACLE_PURPLE:
            border = f"rgba(168, 85, 247, {pulse_alpha:.2f})"
            glow_shadow = "0 0 16px rgba(168, 85, 247, 0.60)"
            bg = "rgba(20, 14, 28, 240)"
        elif aura == AuraState.ZEN_EMERALD:
            border = f"rgba(16, 185, 129, {pulse_alpha:.2f})"
            glow_shadow = "0 0 14px rgba(16, 185, 129, 0.50)"
            bg = "rgba(10, 24, 18, 240)"
        else:  # IDLE_CYBER
            border = f"rgba(245, 158, 11, {max(0.35, pulse_alpha * 0.65):.2f})"
            glow_shadow = "0 0 10px rgba(0, 0, 0, 0.60)"
            bg = "rgba(18, 18, 22, 235)"

        return (
            f"background-color: {bg}; "
            f"border: 1.8px solid {border}; "
            f"border-radius: 14px; "
        )


class BreathingAuraController(QObject):
    """
    Coordinates smooth 30fps border breathing pulsating animation.
    """

    sig_aura_updated = pyqtSignal(str)  # Emits new stylesheet

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.current_state = AuraState.IDLE_CYBER
        self.phase = 0.0
        self.step = 0.05

        self.timer = QTimer(self)
        self.timer.setInterval(33)  # ~30 fps
        self.timer.timeout.connect(self._on_tick)

    def set_state(self, state: AuraState) -> None:
        if self.current_state != state:
            self.current_state = state
            self.phase = 0.0
            if state != AuraState.IDLE_CYBER and not self.timer.isActive():
                self.timer.start()
            elif state == AuraState.IDLE_CYBER and self.timer.isActive():
                # Allow one update then stop timer to save CPU
                self._on_tick()
                self.timer.stop()

    def _on_tick(self) -> None:
        self.phase = (self.phase + self.step) % 1.0
        qss = AcrylicGlassHelper.get_glass_stylesheet(self.current_state, self.phase)
        self.sig_aura_updated.emit(qss)
