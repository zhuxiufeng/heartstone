"""
StreamerHUD: Streamer Minimal Mode & OBS Studio Transparent Broadcast Layer.
Provides one-click privacy and HUD minimization for streamers, automated rolling AI commentary ticker,
and zero-alpha browser source configuration for OBS Studio / live broadcasting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    from PyQt5.QtCore import QPointF, QRectF, Qt, QTimer, pyqtSignal
    from PyQt5.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPen
    from PyQt5.QtWidgets import QWidget
    PYQT_AVAILABLE = True
except ImportError:
    try:
        from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer, pyqtSignal
        from PyQt6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPen
        from PyQt6.QtWidgets import QWidget
        PYQT_AVAILABLE = True
    except ImportError:
        PYQT_AVAILABLE = False
        class QWidget:  # type: ignore
            def __init__(self, parent: Any = None):
                self.parent = parent
            def update(self) -> None:
                pass
            def setVisible(self, v: bool) -> None:
                pass
            def setFixedHeight(self, h: int) -> None:
                pass
            def setAttribute(self, attr: Any, on: bool = True) -> None:
                pass
        class pyqtSignal:  # type: ignore
            def __init__(self, *args: Any):
                pass
            def emit(self, *args: Any) -> None:
                pass


@dataclass
class TickerItem:
    """Represents a ticker message for streamer broadcast."""
    text: str
    category: str = "TACTICAL"  # TACTICAL, HYPE, LETHAL, QUIP
    color_hex: str = "#38bdf8"


class StreamerHUDController:
    """Controls streamer mode state, message filtering, and OBS integration."""

    def __init__(self):
        self.is_streamer_mode_active: bool = False
        self.ticker_messages: List[TickerItem] = [
            TickerItem("🤖 战局全维推演引擎就绪", "TACTICAL", "#38bdf8"),
            TickerItem("⚡ 实时监测敌方手牌与斩杀线", "TACTICAL", "#10b981"),
        ]
        self.current_ticker_index: int = 0

    def toggle_streamer_mode(self) -> bool:
        self.is_streamer_mode_active = not self.is_streamer_mode_active
        return self.is_streamer_mode_active

    def set_streamer_mode(self, active: bool) -> None:
        self.is_streamer_mode_active = active

    def add_ticker_message(self, text: str, category: str = "TACTICAL") -> None:
        colors = {
            "LETHAL": "#f59e0b",
            "HYPE": "#a855f7",
            "QUIP": "#ec4899",
            "TACTICAL": "#38bdf8",
        }
        self.ticker_messages.append(TickerItem(text, category, colors.get(category, "#38bdf8")))
        if len(self.ticker_messages) > 15:
            self.ticker_messages.pop(0)

    def get_current_ticker(self) -> Optional[TickerItem]:
        if not self.ticker_messages:
            return None
        return self.ticker_messages[self.current_ticker_index % len(self.ticker_messages)]

    def advance_ticker(self) -> Optional[TickerItem]:
        if not self.ticker_messages:
            return None
        self.current_ticker_index = (self.current_ticker_index + 1) % len(self.ticker_messages)
        return self.get_current_ticker()

    def filter_confidential_state(self, full_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Strips private mental tilt warnings and internal debug traces for broadcast.
        """
        filtered = dict(full_state)
        if self.is_streamer_mode_active:
            # Mask internal anti-tilt and private notes
            filtered["tilt_status"] = ""
            filtered["personal_habit_reminder"] = ""
            filtered["is_streamer_mode"] = True
        else:
            filtered["is_streamer_mode"] = False
        return filtered

    def get_obs_browser_config(self) -> Dict[str, Any]:
        """Returns OBS Browser Source setup properties."""
        return {
            "url": "http://127.0.0.1:8899/obs",
            "recommended_width": 460,
            "recommended_height": 220,
            "fps": 30,
            "css": "body { background-color: rgba(0, 0, 0, 0); margin: 0px auto; overflow: hidden; }",
        }


class StreamerTickerWidget(QWidget):
    """
    Compact rolling ticker banner for livestream viewer engagement.
    """
    if PYQT_AVAILABLE:
        ticker_clicked = pyqtSignal()

    def __init__(self, controller: StreamerHUDController, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.controller = controller
        if PYQT_AVAILABLE:
            self.setFixedHeight(30)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.timer = QTimer(self)
            self.timer.timeout.connect(self._on_timer)
            self.timer.start(4000)

    def _on_timer(self) -> None:
        self.controller.advance_ticker()
        self.update()

    if PYQT_AVAILABLE:
        def mousePressEvent(self, event: Any) -> None:
            self.controller.advance_ticker()
            self.ticker_clicked.emit()
            self.update()

        def paintEvent(self, event: Any) -> None:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

            w, h = float(self.width()), float(self.height())
            bg_rect = QRectF(0, 0, w, h)

            # Capsule background
            painter.setBrush(QBrush(QColor(15, 23, 42, 220)))
            painter.setPen(QPen(QColor(56, 189, 248, 80), 1.0))
            painter.drawRoundedRect(bg_rect, 6.0, 6.0)

            item = self.controller.get_current_ticker()
            if item:
                painter.setFont(QFont("Microsoft YaHei", 9, QFont.Weight.Bold))
                painter.setPen(QPen(QColor(item.color_hex)))
                painter.drawText(
                    QRectF(10, 0, w - 20, h),
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                    item.text,
                )
