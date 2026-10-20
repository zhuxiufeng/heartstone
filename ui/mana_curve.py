"""
ManaCurveWidget: Visualizes Hearthstone deck mana curve (0 to 7+ mana cost).
Displays stylish vertical progress bars with card count badges and mana crystal icons.
"""

from __future__ import annotations

from typing import List

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)


class SingleBarWidget(QWidget):
    """Vertical bar representing a single mana cost slot."""

    def __init__(self, cost_label: str, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.cost_label = cost_label
        self.count = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(3)
        layout.setAlignment(Qt.AlignBottom | Qt.AlignHCenter)

        # Card count label on top of bar
        self.count_lbl = QLabel("0", self)
        self.count_lbl.setAlignment(Qt.AlignCenter)
        self.count_lbl.setStyleSheet("color: #78716c; font-size: 11px;")
        layout.addWidget(self.count_lbl)

        # Vertical bar
        self.bar = QProgressBar(self)
        self.bar.setOrientation(Qt.Vertical)
        self.bar.setRange(0, 10)  # Max display range
        self.bar.setValue(0)
        self.bar.setTextVisible(False)
        self.bar.setFixedWidth(18)
        self.bar.setFixedHeight(65)
        self.bar.setStyleSheet("""
            QProgressBar {
                background-color: rgba(20, 20, 24, 200);
                border: 1px solid rgba(120, 113, 108, 0.35);
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:1, x2:0, y2:0,
                    stop:0 #b45309, stop:0.55 #f59e0b, stop:1 #fde047);
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.bar, alignment=Qt.AlignHCenter)

        # Cost label at bottom
        self.cost_lbl = QLabel(cost_label, self)
        self.cost_lbl.setAlignment(Qt.AlignCenter)
        self.cost_lbl.setStyleSheet("""
            color: #fef3c7;
            font-size: 11px;
            font-weight: bold;
            background: rgba(120, 53, 15, 0.45);
            border: 1px solid rgba(245, 158, 11, 0.35);
            border-radius: 3px;
            padding: 1px 3px;
        """)
        layout.addWidget(self.cost_lbl)

    def set_count(self, count: int, max_count: int = 10) -> None:
        self.count = count
        self.count_lbl.setText(str(count))
        self.bar.setRange(0, max(5, max_count))
        self.bar.setValue(count)

        # Highlight when cards are present
        if count > 0:
            self.count_lbl.setStyleSheet("color: #fbbf24; font-size: 11px; font-weight: bold;")
        else:
            self.count_lbl.setStyleSheet("color: #78716c; font-size: 11px;")


class ManaCurveWidget(QFrame):
    """Complete 8-slot mana curve container (0, 1, 2, 3, 4, 5, 6, 7+)."""

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(28, 25, 23, 210);
                border: 1px solid rgba(245, 158, 11, 0.35);
                border-radius: 8px;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 6, 8, 6)
        main_layout.setSpacing(4)

        # Header title
        header_layout = QHBoxLayout()
        title_lbl = QLabel("📊 法力曲线 (Mana Curve)", self)
        title_lbl.setStyleSheet("color: #fbbf24; font-size: 12px; font-weight: bold;")
        self.total_cards_lbl = QLabel("已抓: 0/30", self)
        self.total_cards_lbl.setStyleSheet("color: #d6d3d1; font-size: 11px;")

        header_layout.addWidget(title_lbl)
        header_layout.addStretch()
        header_layout.addWidget(self.total_cards_lbl)
        main_layout.addLayout(header_layout)

        # Bars layout
        bars_layout = QHBoxLayout()
        bars_layout.setSpacing(2)
        bars_layout.setContentsMargins(0, 0, 0, 0)

        labels = ["0", "1", "2", "3", "4", "5", "6", "7+"]
        self.bars: List[SingleBarWidget] = []
        for lbl in labels:
            bar_widget = SingleBarWidget(lbl, self)
            self.bars.append(bar_widget)
            bars_layout.addWidget(bar_widget)

        main_layout.addLayout(bars_layout)

    def update_curve(self, curve: List[int], total_cards: int = 0) -> None:
        """Update all 8 bar heights and total card count."""
        max_in_curve = max(curve) if curve else 1
        for idx, bar in enumerate(self.bars):
            val = curve[idx] if idx < len(curve) else 0
            bar.set_count(val, max_in_curve)

        self.total_cards_lbl.setText(f"已抓: {total_cards}/30")
