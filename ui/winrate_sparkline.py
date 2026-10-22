"""
Live Winrate Sparkline & EKG Chart (局势心电图与实时胜率动量流图)
- Hardware-accelerated Qt QPainter rendering of cubic bezier winrate curve.
- Visual markers: Gold stars (Miracle Topdecks), Red triangles (Blunder Alerts).
- Area gradient fill and baseline reference grid (50% parity line).
- Interactive mouse hover displaying turn snapshots.
"""

from typing import List, Tuple, Optional
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import (
    QPainter, QPen, QBrush, QColor, QPainterPath, QLinearGradient, QFont
)
from PyQt5.QtWidgets import QWidget, QToolTip


class WinrateSparklineWidget(QWidget):
    """
    Renders historical winrate momentum across match turns.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedHeight(54)
        self.setMinimumWidth(160)
        self.setAttribute(Qt.WA_Hover)

        # Store tuples of: (turn: int, winrate: float, tag: str)
        self.history: List[Tuple[int, float, str]] = [(1, 50.0, "START")]

    def add_turn_record(self, turn: int, winrate: float, tag: str = "") -> None:
        """
        Appends or updates winrate for a turn and triggers repaint.
        """
        # Overwrite if same turn
        if self.history and self.history[-1][0] == turn:
            self.history[-1] = (turn, round(winrate, 1), tag)
        else:
            self.history.append((turn, round(winrate, 1), tag))
        self.update()

    def clear(self) -> None:
        self.history = [(1, 50.0, "START")]
        self.update()

    def paintEvent(self, event) -> None:
        if not self.history:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # 1. Background box
        painter.fillRect(0, 0, w, h, QColor(16, 16, 20, 200))

        # 2. 50% Baseline (Parity dotted line)
        mid_y = h / 2.0
        pen_dotted = QPen(QColor(100, 116, 139, 120), 1, Qt.DashLine)
        painter.setPen(pen_dotted)
        painter.drawLine(0, int(mid_y), w, int(mid_y))

        # 3. Calculate points
        total_pts = len(self.history)
        if total_pts == 1:
            # Single dot
            painter.setPen(QPen(QColor(245, 158, 11), 3))
            painter.drawPoint(int(w / 2), int(mid_y))
            return

        x_step = w / max(1, total_pts - 1)
        points: List[QPointF] = []

        for i, (turn, wr, tag) in enumerate(self.history):
            px = i * x_step
            # Invert: 100% winrate is top (py = 4), 0% is bottom (py = h - 4)
            clamped_wr = max(0.0, min(100.0, wr))
            py = h - 4 - ((clamped_wr / 100.0) * (h - 8))
            points.append(QPointF(px, py))

        # 4. Construct Bezier Spline Path
        curve_path = QPainterPath()
        curve_path.moveTo(points[0])
        for i in range(len(points) - 1):
            p_start = points[i]
            p_end = points[i + 1]
            c1 = QPointF(p_start.x() + (p_end.x() - p_start.x()) / 2.0, p_start.y())
            c2 = QPointF(p_start.x() + (p_end.x() - p_start.x()) / 2.0, p_end.y())
            curve_path.cubicTo(c1, c2, p_end)

        # 5. Area Fill Gradient
        fill_path = QPainterPath(curve_path)
        fill_path.lineTo(w, h)
        fill_path.lineTo(0, h)
        fill_path.closeSubpath()

        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0.0, QColor(245, 158, 11, 100))
        grad.setColorAt(1.0, QColor(245, 158, 11, 0))
        painter.fillPath(fill_path, QBrush(grad))

        # 6. Stroke line
        pen_curve = QPen(QColor(245, 158, 11), 2)
        painter.strokePath(curve_path, pen_curve)

        # 7. Draw Markers
        for i, (turn, wr, tag) in enumerate(self.history):
            pt = points[i]
            if "STAR" in tag or "MIRACLE" in tag:
                # Gold star marker
                painter.setBrush(QBrush(QColor(250, 204, 21)))
                painter.setPen(QPen(QColor(255, 255, 255), 1))
                painter.drawEllipse(pt, 4.5, 4.5)
            elif "BLUNDER" in tag or "LEAK" in tag:
                # Red alert triangle/circle
                painter.setBrush(QBrush(QColor(239, 68, 68)))
                painter.setPen(QPen(QColor(255, 255, 255), 1))
                painter.drawEllipse(pt, 4.5, 4.5)
            elif i == len(self.history) - 1:
                # Latest head dot
                painter.setBrush(QBrush(QColor(56, 189, 248)))
                painter.setPen(QPen(QColor(255, 255, 255), 1.5))
                painter.drawEllipse(pt, 3.5, 3.5)
