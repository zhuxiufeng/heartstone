"""
Dynamic Island Capsule HUD 2.0 (灵动岛交互式通知胶囊)
- Minimal 34px pill HUD displaying turn, lethal deficit, and winrate.
- Fluidly morphs/expands into a spacious notification card when crucial in-game events fire
  (Lethal spotted, Pre-cast blunder intercepted, Opponent counting burst, Topdeck miracle).
- Automatically retracts after 3-4 seconds with smooth easing.
"""

from typing import Optional
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QRect, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPainter, QBrush, QPen
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QGraphicsDropShadowEffect
)


class DynamicIslandCapsule(QWidget):
    """
    Fluid dynamic island capsule for Hearthstone live notifications.
    """

    COLLAPSED_WIDTH = 280
    COLLAPSED_HEIGHT = 36
    EXPANDED_WIDTH = 420
    EXPANDED_HEIGHT = 105

    sig_clicked = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SubWindow)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._is_expanded = False
        self._turn = 1
        self._lethal = 0
        self._winrate = 50.0

        # Auto-collapse timer
        self.collapse_timer = QTimer(self)
        self.collapse_timer.setSingleShot(True)
        self.collapse_timer.timeout.connect(self.collapse)

        self._init_ui()

    def _init_ui(self) -> None:
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 6, 10, 6)
        self.main_layout.setSpacing(4)

        # 1. Collapsed pill row
        self.pill_row = QHBoxLayout()
        self.pill_row.setContentsMargins(0, 0, 0, 0)

        self.lbl_status = QLabel("T1 | 斩杀: -- | 胜率: 50.0%", self)
        self.lbl_status.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        self.lbl_status.setStyleSheet("color: #f59e0b;")

        self.lbl_icon = QLabel("⚡", self)
        self.lbl_icon.setFont(QFont("Microsoft YaHei", 10))

        self.pill_row.addWidget(self.lbl_icon)
        self.pill_row.addWidget(self.lbl_status)
        self.pill_row.addStretch()

        self.main_layout.addLayout(self.pill_row)

        # 2. Expanded notification content (hidden by default)
        self.lbl_title = QLabel("", self)
        self.lbl_title.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        self.lbl_title.setStyleSheet("color: #ef4444;")
        self.lbl_title.setVisible(False)

        self.lbl_detail = QLabel("", self)
        self.lbl_detail.setFont(QFont("Microsoft YaHei", 8))
        self.lbl_detail.setStyleSheet("color: #e2e8f0;")
        self.lbl_detail.setWordWrap(True)
        self.lbl_detail.setVisible(False)

        self.main_layout.addWidget(self.lbl_title)
        self.main_layout.addWidget(self.lbl_detail)

        self.resize(self.COLLAPSED_WIDTH, self.COLLAPSED_HEIGHT)
        self._apply_style(is_alert=False)

    def _apply_style(self, is_alert: bool = False, alert_color: str = "#ef4444") -> None:
        border_col = alert_color if is_alert else "rgba(245, 158, 11, 0.6)"
        bg_col = "rgba(18, 18, 24, 245)" if not is_alert else "rgba(30, 14, 18, 250)"
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_col};
                border: 1.5px solid {border_col};
                border-radius: {18 if not self._is_expanded else 14}px;
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
        """)

    def update_metrics(self, turn: int, lethal: int, winrate: float) -> None:
        self._turn = turn
        self._lethal = lethal
        self._winrate = winrate
        lethal_str = f"{lethal}点" if lethal > 0 else "无"
        self.lbl_status.setText(f"T{turn} | 斩杀: {lethal_str} | 胜率: {winrate:.1f}%")

    def show_alert(
        self,
        title: str,
        message: str,
        alert_color: str = "#ef4444",
        duration_ms: int = 3500,
    ) -> None:
        """
        Morphs island into expanded alert card.
        """
        self._is_expanded = True
        self.lbl_title.setText(title)
        self.lbl_title.setStyleSheet(f"color: {alert_color}; font-weight: bold;")
        self.lbl_title.setVisible(True)

        self.lbl_detail.setText(message)
        self.lbl_detail.setVisible(True)

        self.resize(self.EXPANDED_WIDTH, self.EXPANDED_HEIGHT)
        self._apply_style(is_alert=True, alert_color=alert_color)

        self.collapse_timer.start(duration_ms)

    def collapse(self) -> None:
        """
        Retracts island back to ultra-compact pill.
        """
        self._is_expanded = False
        self.lbl_title.setVisible(False)
        self.lbl_detail.setVisible(False)

        self.resize(self.COLLAPSED_WIDTH, self.COLLAPSED_HEIGHT)
        self._apply_style(is_alert=False)

    def mousePressEvent(self, event) -> None:
        self.sig_clicked.emit()
        super().mousePressEvent(event)
