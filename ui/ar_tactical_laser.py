"""
ARTacticalLaser: Augmented Reality Holographic Arrow & Laser Guidance Layer.
Renders glowing numbered action badges (①, ②, ③) and curved bezier tactical attack arrows
directly over the Hearthstone board to guide the player's micro-execution.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

try:
    from PyQt6.QtCore import QPointF, QRectF, Qt
    from PyQt6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
except ImportError:
    pass


class ARTacticalLaserRenderer:
    """Draws augmented reality arrows, step badges, and blunder hazards."""

    @classmethod
    def render_overlay(
        cls,
        painter: QPainter,
        width: int,
        height: int,
        steps: List[Dict[str, Any]],
        active_step_index: int = 0,
        blunder_alert: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not steps or width <= 0 or height <= 0:
            return

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        # 1. Render Blunder Hazard Banner if active
        if blunder_alert:
            hazard_color = QColor(blunder_alert.get("hazard_color", "#ef4444"))
            banner_rect = QRectF(width * 0.2, height * 0.08, width * 0.6, 54)
            # Semi-transparent red background
            painter.setBrush(QBrush(QColor(15, 23, 42, 230)))
            pen = QPen(hazard_color, 2.5)
            painter.setPen(pen)
            painter.drawRoundedRect(banner_rect, 10, 10)

            # Text
            painter.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
            painter.drawText(
                QRectF(width * 0.2, height * 0.08 + 6, width * 0.6, 22),
                Qt.AlignmentFlag.AlignCenter,
                blunder_alert.get("warning_title", "⚠️ 伏笔紧急拦截！"),
            )
            painter.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Normal))
            painter.setPen(QPen(QColor("#f8fafc")))
            painter.drawText(
                QRectF(width * 0.2, height * 0.08 + 28, width * 0.6, 20),
                Qt.AlignmentFlag.AlignCenter,
                blunder_alert.get("corrective_action", ""),
            )

        # 2. Render each step arrow and badge
        for idx, step in enumerate(steps):
            is_active = (idx == active_step_index)
            is_completed = (idx < active_step_index)

            if is_completed:
                continue  # don't clutter with already finished steps

            coords = step.get("ar_coords", {})
            sx = coords.get("start_x", 0.5) * width
            sy = coords.get("start_y", 0.7) * height
            ex = coords.get("end_x", 0.5) * width
            ey = coords.get("end_y", 0.3) * height

            # Color scheme
            if is_active:
                arrow_color = QColor("#38bdf8") if not step.get("is_critical_micro") else QColor("#f59e0b")
                arrow_width = 3.5
            else:
                arrow_color = QColor(148, 163, 184, 160)
                arrow_width = 2.0

            # Draw curved bezier path
            path = QPainterPath()
            path.moveTo(sx, sy)
            ctrl_x = (sx + ex) / 2.0 + (width * 0.05 if sx < ex else -width * 0.05)
            ctrl_y = (sy + ey) / 2.0
            path.quadTo(ctrl_x, ctrl_y, ex, ey)

            pen = QPen(arrow_color, arrow_width)
            if not is_active:
                pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)

            # Draw Arrow Head at target
            cls._draw_arrow_head(painter, ctrl_x, ctrl_y, ex, ey, arrow_color, 12 if is_active else 8)

            # Draw Numbered Badge at start
            badge_radius = 16 if is_active else 12
            badge_rect = QRectF(sx - badge_radius, sy - badge_radius, badge_radius * 2, badge_radius * 2)

            painter.setPen(QPen(arrow_color, 2))
            painter.setBrush(QBrush(QColor(15, 23, 42, 230)))
            painter.drawEllipse(badge_rect)

            painter.setFont(QFont("Microsoft YaHei", 10 if is_active else 8, QFont.Weight.Bold))
            painter.setPen(QPen(arrow_color))
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, str(step.get("step_number", idx + 1)))

    @staticmethod
    def _draw_arrow_head(painter: QPainter, from_x: float, from_y: float, to_x: float, to_y: float, color: QColor, size: float = 10) -> None:
        angle = math.atan2(to_y - from_y, to_x - from_x)
        p1 = QPointF(to_x, to_y)
        p2 = QPointF(to_x - size * math.cos(angle - math.pi / 6), to_y - size * math.sin(angle - math.pi / 6))
        p3 = QPointF(to_x - size * math.cos(angle + math.pi / 6), to_y - size * math.sin(angle + math.pi / 6))

        path = QPainterPath()
        path.moveTo(p1)
        path.lineTo(p2)
        path.lineTo(p3)
        path.closeSubpath()

        painter.setPen(QPen(color, 1))
        painter.setBrush(QBrush(color))
        painter.drawPath(path)
