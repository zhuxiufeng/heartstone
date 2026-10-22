"""
ARBoardOverlay: Augmented Reality Board Projection & Interactive Tactical Layer.
Renders holographic attack vector beams, ghost placement slots with EV indicators,
and 3D minion status auras over the Hearthstone board with interactive hover and click feedback.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    from PyQt5.QtCore import QEasingCurve, QPointF, QPropertyAnimation, QRectF, Qt, pyqtProperty, pyqtSignal
    from PyQt5.QtGui import (
        QBrush,
        QColor,
        QFont,
        QLinearGradient,
        QPainter,
        QPainterPath,
        QPen,
        QPolygonF,
        QRadialGradient,
    )
    from PyQt5.QtWidgets import QToolTip, QWidget
    PYQT_AVAILABLE = True
except ImportError:
    try:
        from PyQt6.QtCore import QEasingCurve, QPointF, QPropertyAnimation, QRectF, Qt, pyqtProperty, pyqtSignal
        from PyQt6.QtGui import (
            QBrush,
            QColor,
            QFont,
            QLinearGradient,
            QPainter,
            QPainterPath,
            QPen,
            QPolygonF,
            QRadialGradient,
        )
        from PyQt6.QtWidgets import QToolTip, QWidget
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
            def isVisible(self) -> bool:
                return False
            def setMouseTracking(self, b: bool) -> None:
                pass
            def setAttribute(self, attr: Any, on: bool = True) -> None:
                pass
        class pyqtSignal:  # type: ignore
            def __init__(self, *args: Any):
                pass
            def emit(self, *args: Any) -> None:
                pass
    class QPointF:  # type: ignore
        def __init__(self, x: float = 0.0, y: float = 0.0):
            self.x, self.y = x, y
    class QRectF:  # type: ignore
        def __init__(self, x: float = 0.0, y: float = 0.0, w: float = 0.0, h: float = 0.0):
            self.x, self.y, self.w, self.h = x, y, w, h
        def contains(self, p: Any) -> bool:
            return self.x <= getattr(p, "x", 0) <= self.x + self.w and self.y <= getattr(p, "y", 0) <= self.y + self.h


@dataclass
class VectorAttackArrow:
    """Represents a tactical attack vector from attacker to defender/hero."""
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    damage: int
    is_lethal: bool = False
    source_name: str = "我方随从"
    target_name: str = "敌方目标"
    step_order: int = 1
    description: str = ""

    def get_tooltip(self) -> str:
        lethal_tag = "【直接斩杀】" if self.is_lethal else ""
        return (
            f"步骤 {self.step_order}: {self.source_name} ➔ {self.target_name}\n"
            f"造成伤害: {self.damage} 点 {lethal_tag}\n"
            f"{self.description}"
        )


@dataclass
class GhostPlacementSlot:
    """Represents an optimal minion placement slot with EV calculation."""
    slot_index: int
    x: float
    y: float
    width: float = 72.0
    height: float = 96.0
    strategy_type: str = "防陨石"
    ev_delta: float = 0.42
    description: str = "将随从放置于此可规避流星与横扫溅射"

    def get_bounds(self) -> QRectF:
        if PYQT_AVAILABLE:
            return QRectF(self.x - self.width / 2, self.y - self.height / 2, self.width, self.height)
        return QRectF(self.x - self.width / 2, self.y - self.height / 2, self.width, self.height)


@dataclass
class MinionStatusAura:
    """Represents visual holographic status auras (Taunt, Divine Shield, Reborn, Poisonous)."""
    x: float
    y: float
    radius: float = 38.0
    status_flags: List[str] = field(default_factory=list)


class ARBoardProjectionWidget(QWidget):
    """
    AR Interactive Board Overlay.
    Projects vector arrows, ghost slots, and status auras with interactive hover and click handling.
    """
    if PYQT_AVAILABLE:
        ghost_slot_clicked = pyqtSignal(int, str)
        arrow_hovered = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.arrows: List[VectorAttackArrow] = []
        self.ghost_slots: List[GhostPlacementSlot] = []
        self.status_auras: List[MinionStatusAura] = []
        self.selected_slot_index: Optional[int] = None
        self.hovered_arrow_index: Optional[int] = None
        self.pulse_phase: float = 0.0

        if PYQT_AVAILABLE:
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.setMouseTracking(True)

    def set_tactics(
        self,
        arrows: List[VectorAttackArrow],
        ghost_slots: List[GhostPlacementSlot],
        auras: Optional[List[MinionStatusAura]] = None,
    ) -> None:
        """Updates the tactical projection data."""
        self.arrows = arrows
        self.ghost_slots = ghost_slots
        self.status_auras = auras or []
        self.update()

    def advance_pulse(self, delta: float = 0.05) -> None:
        """Advances pulse phase for glowing animations."""
        self.pulse_phase = (self.pulse_phase + delta) % (2 * math.pi)
        self.update()

    def get_hovered_arrow(self, x: float, y: float) -> Optional[int]:
        """Finds arrow closest to mouse coordinate (within threshold)."""
        for i, arr in enumerate(self.arrows):
            # Check mid point or bounding line segment
            mx = (arr.start_x + arr.end_x) / 2
            my = (arr.start_y + arr.end_y) / 2
            dist = math.hypot(x - mx, y - my)
            if dist < 45.0:
                return i
        return None

    def get_clicked_slot(self, x: float, y: float) -> Optional[GhostPlacementSlot]:
        """Finds ghost slot containing coordinate."""
        for slot in self.ghost_slots:
            rect = slot.get_bounds()
            if getattr(rect, "contains", None):
                if rect.contains(QPointF(x, y)):
                    return slot
            elif hasattr(rect, "x"):
                if (rect.x <= x <= rect.x + rect.w) and (rect.y <= y <= rect.y + rect.h):
                    return slot
        return None

    if PYQT_AVAILABLE:
        def mouseMoveEvent(self, event: Any) -> None:
            pos = event.position() if hasattr(event, "position") else event.pos()
            x, y = float(pos.x()), float(pos.y())
            arrow_idx = self.get_hovered_arrow(x, y)
            if arrow_idx != self.hovered_arrow_index:
                self.hovered_arrow_index = arrow_idx
                if arrow_idx is not None:
                    arr = self.arrows[arrow_idx]
                    self.arrow_hovered.emit(arr.get_tooltip())
                    QToolTip.showText(event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos(), arr.get_tooltip(), self)
                else:
                    self.arrow_hovered.emit("")
                    QToolTip.hideText()
                self.update()

        def mousePressEvent(self, event: Any) -> None:
            pos = event.position() if hasattr(event, "position") else event.pos()
            x, y = float(pos.x()), float(pos.y())
            slot = self.get_clicked_slot(x, y)
            if slot:
                self.selected_slot_index = slot.slot_index
                self.ghost_slot_clicked.emit(slot.slot_index, slot.strategy_type)
                self.update()

        def paintEvent(self, event: Any) -> None:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

            # 1. Render Status Auras
            for aura in self.status_auras:
                self._draw_status_aura(painter, aura)

            # 2. Render Ghost Placement Slots
            for slot in self.ghost_slots:
                self._draw_ghost_slot(painter, slot)

            # 3. Render Vector Attack Arrows
            for i, arrow in enumerate(self.arrows):
                is_hovered = (i == self.hovered_arrow_index)
                self._draw_vector_arrow(painter, arrow, is_hovered)

        def _draw_status_aura(self, painter: QPainter, aura: MinionStatusAura) -> None:
            glow_intensity = 0.6 + 0.4 * math.sin(self.pulse_phase)
            for flag in aura.status_flags:
                if flag == "TAUNT":
                    color = QColor(148, 163, 184, int(180 * glow_intensity))
                    pen = QPen(color, 3.0, Qt.PenStyle.DashDotLine)
                    painter.setPen(pen)
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                    painter.drawEllipse(QPointF(aura.x, aura.y), aura.radius, aura.radius)
                elif flag == "DIVINE_SHIELD":
                    color = QColor(251, 191, 36, int(210 * glow_intensity))
                    pen = QPen(color, 2.5)
                    painter.setPen(pen)
                    painter.drawEllipse(QPointF(aura.x, aura.y), aura.radius + 4, aura.radius + 4)
                elif flag == "REBORN":
                    color = QColor(56, 189, 248, int(190 * glow_intensity))
                    pen = QPen(color, 2.0, Qt.PenStyle.DotLine)
                    painter.setPen(pen)
                    painter.drawEllipse(QPointF(aura.x, aura.y), aura.radius + 8, aura.radius + 8)

        def _draw_ghost_slot(self, painter: QPainter, slot: GhostPlacementSlot) -> None:
            is_selected = (slot.slot_index == self.selected_slot_index)
            rect = slot.get_bounds()

            # Pulse fill
            pulse_alpha = int(45 + 25 * math.sin(self.pulse_phase + slot.slot_index))
            fill_color = QColor(56, 189, 248, pulse_alpha if not is_selected else 90)
            painter.setBrush(QBrush(fill_color))

            border_color = QColor("#38bdf8") if not is_selected else QColor("#fbbf24")
            pen = QPen(border_color, 2.0 if not is_selected else 3.0, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawRoundedRect(rect, 10.0, 10.0)

            # Strategy badge at top
            badge_rect = QRectF(rect.x() + 4, rect.y() + 4, rect.width() - 8, 20)
            painter.setBrush(QBrush(QColor(15, 23, 42, 210)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(badge_rect, 4.0, 4.0)

            painter.setFont(QFont("Microsoft YaHei", 8, QFont.Weight.Bold))
            painter.setPen(QPen(QColor("#38bdf8") if not is_selected else QColor("#fbbf24")))
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, slot.strategy_type)

            # EV gain indicator at bottom
            ev_rect = QRectF(rect.x() + 4, rect.y() + rect.height() - 22, rect.width() - 8, 18)
            painter.setBrush(QBrush(QColor(16, 185, 129, 200)))
            painter.drawRoundedRect(ev_rect, 4.0, 4.0)
            painter.setFont(QFont("Microsoft YaHei", 8, QFont.Weight.Bold))
            painter.setPen(QPen(QColor("#ffffff")))
            painter.drawText(ev_rect, Qt.AlignmentFlag.AlignCenter, f"+{slot.ev_delta:.2f} EV")

        def _draw_vector_arrow(self, painter: QPainter, arrow: VectorAttackArrow, is_hovered: bool) -> None:
            # Curved Bezier trajectory
            p1 = QPointF(arrow.start_x, arrow.start_y)
            p2 = QPointF(arrow.end_x, arrow.end_y)
            ctrl = QPointF((p1.x() + p2.x()) / 2, min(p1.y(), p2.y()) - 40.0)

            path = QPainterPath()
            path.moveTo(p1)
            path.quadTo(ctrl, p2)

            color = QColor("#fbbf24" if arrow.is_lethal else "#38bdf8")
            if is_hovered:
                color = QColor("#f43f5e")

            # Outer glow
            glow_pen = QPen(QColor(color.red(), color.green(), color.blue(), 70), 8.0)
            painter.setPen(glow_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)

            # Core beam
            core_pen = QPen(color, 3.5 if is_hovered else 2.5)
            painter.setPen(core_pen)
            painter.drawPath(path)

            # Arrowhead at p2
            angle = math.atan2(p2.y() - ctrl.y(), p2.x() - ctrl.x())
            arrow_size = 14.0 if is_hovered else 11.0
            p_left = QPointF(
                p2.x() - arrow_size * math.cos(angle - math.pi / 6),
                p2.y() - arrow_size * math.sin(angle - math.pi / 6),
            )
            p_right = QPointF(
                p2.x() - arrow_size * math.cos(angle + math.pi / 6),
                p2.y() - arrow_size * math.sin(angle + math.pi / 6),
            )
            head_poly = QPolygonF([p2, p_left, p_right])
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPolygon(head_poly)

            # Step order badge at midpoint
            mid_x, mid_y = ctrl.x(), ctrl.y() + 20
            badge_radius = 12.0
            painter.setBrush(QBrush(QColor(15, 23, 42, 230)))
            painter.setPen(QPen(color, 1.8))
            painter.drawEllipse(QPointF(mid_x, mid_y), badge_radius, badge_radius)

            painter.setFont(QFont("Microsoft YaHei", 9, QFont.Weight.Bold))
            painter.setPen(QPen(QColor("#ffffff")))
            painter.drawText(
                QRectF(mid_x - badge_radius, mid_y - badge_radius, badge_radius * 2, badge_radius * 2),
                Qt.AlignmentFlag.AlignCenter,
                str(arrow.step_order),
            )
