"""
3D Parallax Hologram Card Widget (3D 陀螺仪视差卡牌与全息解构卡片)
- Simulates physical card foil sheen and 3D perspective tilt as cursor hovers over card.
- Dynamic specular highlight ray follows mouse coordinates in real-time.
- Special holographic styling for Titans (Thunder aura) and Colossals (Appendage badge).
"""

from typing import Optional
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import (
    QPainter, QColor, QLinearGradient, QRadialGradient, QBrush, QPen, QFont
)
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel


class ParallaxCardWidget(QFrame):
    """
    3D Parallax Card Widget with responsive holographic foil sheen.
    """

    def __init__(
        self,
        card_name: str,
        cost: int,
        attack: int = 0,
        health: int = 0,
        score: float = 85.0,
        is_titan: bool = False,
        is_colossal: bool = False,
        parent: Optional[QFrame] = None,
    ):
        super().__init__(parent)
        self.card_name = card_name
        self.cost = cost
        self.attack = attack
        self.health = health
        self.score = score
        self.is_titan = is_titan
        self.is_colossal = is_colossal

        self.setMouseTracking(True)
        self.setFixedHeight(72)
        self.setMinimumWidth(240)

        # Normalized mouse relative offset (-1.0 to 1.0)
        self.tilt_x = 0.0
        self.tilt_y = 0.0
        self.is_hovered = False

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        # Cost badge
        self.lbl_cost = QLabel(str(self.cost), self)
        self.lbl_cost.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        self.lbl_cost.setFixedSize(28, 28)
        self.lbl_cost.setAlignment(Qt.AlignCenter)
        self.lbl_cost.setStyleSheet("""
            background-color: #2563eb;
            color: #ffffff;
            border-radius: 14px;
            border: 1px solid #60a5fa;
        """)
        layout.addWidget(self.lbl_cost)

        # Center info
        vbox = QVBoxLayout()
        vbox.setSpacing(2)

        name_row = QHBoxLayout()
        self.lbl_name = QLabel(self.card_name, self)
        self.lbl_name.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        self.lbl_name.setStyleSheet("color: #f8fafc;")
        name_row.addWidget(self.lbl_name)

        if self.is_titan:
            lbl_tag = QLabel("⚡泰坦", self)
            lbl_tag.setStyleSheet("color: #fbbf24; font-size: 10px; font-weight: bold;")
            name_row.addWidget(lbl_tag)
        elif self.is_colossal:
            lbl_tag = QLabel("🐙巨型", self)
            lbl_tag.setStyleSheet("color: #38bdf8; font-size: 10px; font-weight: bold;")
            name_row.addWidget(lbl_tag)

        name_row.addStretch()
        vbox.addLayout(name_row)

        stats_str = f"身材: {self.attack}/{self.health}" if (self.attack > 0 or self.health > 0) else "法术/武器"
        self.lbl_stats = QLabel(stats_str, self)
        self.lbl_stats.setFont(QFont("Microsoft YaHei", 8))
        self.lbl_stats.setStyleSheet("color: #94a3b8;")
        vbox.addWidget(self.lbl_stats)

        layout.addLayout(vbox)
        layout.addStretch()

        # Score rating badge
        self.lbl_score = QLabel(f"{self.score:.1f}", self)
        self.lbl_score.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        self.lbl_score.setStyleSheet("color: #10b981;")
        layout.addWidget(self.lbl_score)

    def enterEvent(self, event) -> None:
        self.is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.is_hovered = False
        self.tilt_x = 0.0
        self.tilt_y = 0.0
        self.update()
        super().leaveEvent(event)

    def mouseMoveEvent(self, event) -> None:
        w = max(1, self.width())
        h = max(1, self.height())
        pos = event.pos()
        self.tilt_x = max(-1.0, min(1.0, (pos.x() - w / 2) / (w / 2)))
        self.tilt_y = max(-1.0, min(1.0, (pos.y() - h / 2) / (h / 2)))
        self.update()
        super().mouseMoveEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # 1. Base card frame background
        base_bg = QColor(24, 24, 30, 240)
        border_col = QColor(245, 158, 11, 140) if self.is_titan else QColor(71, 85, 105, 120)
        if self.is_hovered:
            border_col = QColor(56, 189, 248, 220)

        painter.setBrush(QBrush(base_bg))
        painter.setPen(QPen(border_col, 1.5))
        painter.drawRoundedRect(1, 1, w - 2, h - 2, 10, 10)

        # 2. Specular Holographic Sheen (Follows cursor)
        if self.is_hovered:
            sheen_x = int((w / 2) + self.tilt_x * (w / 3))
            sheen_y = int((h / 2) + self.tilt_y * (h / 3))

            grad = QRadialGradient(sheen_x, sheen_y, max(w, h) * 0.7)
            grad.setColorAt(0.0, QColor(255, 255, 255, 55))
            grad.setColorAt(0.4, QColor(245, 158, 11, 25))
            grad.setColorAt(1.0, QColor(255, 255, 255, 0))

            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(1, 1, w - 2, h - 2, 10, 10)

        super().paintEvent(event)
