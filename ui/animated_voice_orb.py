"""
Interactive Animated Voice Orb (灵动声音微粒球与声波律动交互)
- Siri/Jarvis inspired fluid pulsating particle orb widget.
- Reacts dynamically to 4 vocal emotional states:
  1. IDLE: Serene cyan pulse
  2. SPEAKING: Multi-wave kinetic audio expansion
  3. LISTENING: Mystical purple neon
  4. COMFORT: Warm golden healing amber glow
- Smooth 30fps radial gradient rendering.
"""

from enum import Enum
import math
from typing import Optional
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPainter, QRadialGradient, QColor, QPen, QBrush
from PyQt5.QtWidgets import QWidget


class OrbVisualState(str, Enum):
    IDLE = "IDLE"            # 静止幽蓝
    SPEAKING = "SPEAKING"    # 说话声浪
    LISTENING = "LISTENING"  # 聆听紫光
    COMFORT = "COMFORT"      # 治愈暖金


class AnimatedVoiceOrb(QWidget):
    """
    Fluid animated voice orb for AI vocal companion status.
    """

    sig_clicked = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None, size: int = 36):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)

        self.current_state = OrbVisualState.IDLE
        self.phase = 0.0
        self.amplitude = 0.5  # 0.0 to 1.0

        # Animation timer ~30 FPS
        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(33)
        self.anim_timer.timeout.connect(self._on_tick)
        self.anim_timer.start()

    def set_state(self, state: OrbVisualState) -> None:
        if self.current_state != state:
            self.current_state = state
            self.update()

    def set_amplitude(self, amp: float) -> None:
        self.amplitude = max(0.1, min(1.0, amp))

    def _on_tick(self) -> None:
        self.phase = (self.phase + 0.08) % (2 * math.pi)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = h / 2.0
        r_base = min(w, h) / 2.5

        # Pulse wave offset
        pulse = math.sin(self.phase) * (3.0 * self.amplitude)
        r = r_base + pulse

        # Determine color palette
        if self.current_state == OrbVisualState.SPEAKING:
            core_col = QColor(56, 189, 248)    # Cyan
            outer_col = QColor(99, 102, 241, 0) # Indigo fade
        elif self.current_state == OrbVisualState.LISTENING:
            core_col = QColor(192, 132, 252)   # Purple
            outer_col = QColor(168, 85, 247, 0)
        elif self.current_state == OrbVisualState.COMFORT:
            core_col = QColor(251, 191, 36)    # Amber
            outer_col = QColor(245, 158, 11, 0)
        else:  # IDLE
            core_col = QColor(71, 85, 105)     # Slate
            outer_col = QColor(30, 41, 59, 0)

        # 1. Outer glow halo
        halo_grad = QRadialGradient(cx, cy, r * 1.4)
        halo_grad.setColorAt(0.0, QColor(core_col.red(), core_col.green(), core_col.blue(), 140))
        halo_grad.setColorAt(1.0, outer_col)
        painter.setBrush(QBrush(halo_grad))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(int(cx - r * 1.3), int(cy - r * 1.3), int(r * 2.6), int(r * 2.6))

        # 2. Concentric animated ripple ring
        ripple_r = r_base + (math.sin(self.phase + 1.0) * 4.0 * self.amplitude)
        pen_ripple = QPen(QColor(core_col.red(), core_col.green(), core_col.blue(), 90), 1.2)
        painter.setPen(pen_ripple)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(int(cx - ripple_r), int(cy - ripple_r), int(ripple_r * 2), int(ripple_r * 2))

        # 3. Inner glowing core
        core_grad = QRadialGradient(cx, cy, r * 0.7)
        core_grad.setColorAt(0.0, QColor(255, 255, 255, 230))
        core_grad.setColorAt(0.6, core_col)
        core_grad.setColorAt(1.0, QColor(core_col.red(), core_col.green(), core_col.blue(), 180))
        painter.setBrush(QBrush(core_grad))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(int(cx - r * 0.6), int(cy - r * 0.6), int(r * 1.2), int(r * 1.2))

    def mousePressEvent(self, event) -> None:
        self.sig_clicked.emit()
        super().mousePressEvent(event)
