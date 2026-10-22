"""
RadialProbabilityCompass: 360-degree Polar Probability Dial & Topdeck Gauge.
Renders polar mana distribution sectors, topdeck lethal needle, and fatigue danger ring
with interactive sector hovering and needle mode toggling.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

try:
    from PyQt5.QtCore import QPointF, QRectF, Qt, pyqtProperty, pyqtSignal
    from PyQt5.QtGui import (
        QBrush,
        QColor,
        QFont,
        QLinearGradient,
        QPainter,
        QPainterPath,
        QPen,
        QRadialGradient,
    )
    from PyQt5.QtWidgets import QToolTip, QWidget
    PYQT_AVAILABLE = True
except ImportError:
    try:
        from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtProperty, pyqtSignal
        from PyQt6.QtGui import (
            QBrush,
            QColor,
            QFont,
            QLinearGradient,
            QPainter,
            QPainterPath,
            QPen,
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
            def setMinimumSize(self, w: int, h: int) -> None:
                pass
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


@dataclass
class ManaSectorData:
    """Represents a mana slice in the radial compass."""
    mana_cost: int
    card_count: int
    total_deck: int
    card_names: List[str] = field(default_factory=list)
    color_hex: str = "#38bdf8"

    @property
    def probability(self) -> float:
        if self.total_deck <= 0:
            return 0.0
        return self.card_count / self.total_deck


class RadialProbabilityCompassWidget(QWidget):
    """
    360° Polar Probability Dial.
    Features mana curve sectors, center lethal gauge needle, and fatigue danger outer ring.
    """
    if PYQT_AVAILABLE:
        sector_hovered = pyqtSignal(int, int, list)
        mode_toggled = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.sectors: List[ManaSectorData] = []
        self.total_cards: int = 0
        self.topdeck_lethal_pct: float = 38.5
        self.topdeck_survival_pct: float = 62.0
        self.active_mode: str = "LETHAL"  # "LETHAL" or "SURVIVAL"
        self.fatigue_turns_left: int = 8
        self.fatigue_next_dmg: int = 0
        self.hovered_mana: Optional[int] = None
        self.needle_angle_current: float = 0.0
        self.needle_angle_target: float = 0.0

        if PYQT_AVAILABLE:
            self.setMinimumSize(180, 180)
            self.setMouseTracking(True)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def set_data(
        self,
        deck_distribution: Dict[int, List[str]],
        lethal_pct: float = 40.0,
        survival_pct: float = 60.0,
        fatigue_turns: int = 8,
        fatigue_dmg: int = 0,
    ) -> None:
        """Sets deck distribution and recalculates sectors."""
        self.total_cards = sum(len(cards) for cards in deck_distribution.values())
        self.topdeck_lethal_pct = max(0.0, min(100.0, lethal_pct))
        self.topdeck_survival_pct = max(0.0, min(100.0, survival_pct))
        self.fatigue_turns_left = fatigue_turns
        self.fatigue_next_dmg = fatigue_dmg

        # Standard mana palette
        palette = {
            1: "#38bdf8", 2: "#0284c7", 3: "#06b6d4", 4: "#10b981",
            5: "#059669", 6: "#eab308", 7: "#f59e0b", 8: "#ea580c",
            9: "#ef4444", 10: "#8b5cf6"
        }

        sectors = []
        for mana in range(1, 11):
            names = deck_distribution.get(mana, [])
            if names:
                color = palette.get(mana, "#94a3b8")
                sectors.append(ManaSectorData(
                    mana_cost=mana,
                    card_count=len(names),
                    total_deck=self.total_cards,
                    card_names=names,
                    color_hex=color,
                ))
        self.sectors = sectors
        self.update_needle_target()
        self.update()

    def update_needle_target(self) -> None:
        pct = self.topdeck_lethal_pct if self.active_mode == "LETHAL" else self.topdeck_survival_pct
        # Target angle: maps 0~100% to -120 deg to +120 deg (span 240 deg)
        self.needle_angle_target = -120.0 + (pct / 100.0) * 240.0
        self.needle_angle_current = self.needle_angle_target

    def toggle_mode(self) -> str:
        """Toggles between LETHAL and SURVIVAL probability."""
        self.active_mode = "SURVIVAL" if self.active_mode == "LETHAL" else "LETHAL"
        self.update_needle_target()
        if PYQT_AVAILABLE:
            self.mode_toggled.emit(self.active_mode)
        self.update()
        return self.active_mode

    def get_sector_at(self, x: float, y: float, cx: float, cy: float, radius: float) -> Optional[ManaSectorData]:
        """Calculates which mana sector contains mouse point."""
        dx, dy = x - cx, y - cy
        dist = math.hypot(dx, dy)
        if dist < radius * 0.35 or dist > radius:
            return None

        # Angle in degrees [0, 360) clockwise from 12 o'clock
        angle_rad = math.atan2(dy, dx)
        angle_deg = math.degrees(angle_rad) + 90.0
        if angle_deg < 0:
            angle_deg += 360.0

        if not self.sectors or self.total_cards <= 0:
            return None

        current_deg = 0.0
        for sec in self.sectors:
            span = (sec.card_count / self.total_cards) * 360.0
            if current_deg <= angle_deg <= current_deg + span:
                return sec
            current_deg += span
        return None

    if PYQT_AVAILABLE:
        def mouseMoveEvent(self, event: Any) -> None:
            pos = event.position() if hasattr(event, "position") else event.pos()
            cx, cy = self.width() / 2, self.height() / 2
            radius = min(cx, cy) - 10
            sec = self.get_sector_at(float(pos.x()), float(pos.y()), cx, cy, radius)

            hovered_mana = sec.mana_cost if sec else None
            if hovered_mana != self.hovered_mana:
                self.hovered_mana = hovered_mana
                if sec:
                    names_preview = "、".join(sec.card_names[:4])
                    if len(sec.card_names) > 4:
                        names_preview += f" 等 {len(sec.card_names)} 张"
                    tip = f"💎 {sec.mana_cost} 费卡牌: {sec.card_count} 张 ({sec.probability*100:.1f}%)\n{names_preview}"
                    self.sector_hovered.emit(sec.mana_cost, sec.card_count, sec.card_names)
                    QToolTip.showText(event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos(), tip, self)
                else:
                    self.sector_hovered.emit(0, 0, [])
                    QToolTip.hideText()
                self.update()

        def mousePressEvent(self, event: Any) -> None:
            pos = event.position() if hasattr(event, "position") else event.pos()
            cx, cy = self.width() / 2, self.height() / 2
            dist = math.hypot(float(pos.x()) - cx, float(pos.y()) - cy)
            # Center click toggles mode
            if dist <= min(cx, cy) * 0.35:
                self.toggle_mode()

        def paintEvent(self, event: Any) -> None:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

            cx = self.width() / 2.0
            cy = self.height() / 2.0
            radius = min(cx, cy) - 12.0
            inner_radius = radius * 0.45

            # 1. Outer Fatigue Warning Ring
            self._draw_fatigue_ring(painter, cx, cy, radius + 6)

            # 2. Polar Mana Sectors
            self._draw_mana_sectors(painter, cx, cy, inner_radius, radius)

            # 3. Center Lethal Needle Dial
            self._draw_center_needle(painter, cx, cy, inner_radius)

        def _draw_fatigue_ring(self, painter: QPainter, cx: float, cy: float, outer_r: float) -> None:
            if self.fatigue_turns_left <= 3 or self.fatigue_next_dmg > 0:
                pen = QPen(QColor("#ef4444"), 3.0, Qt.PenStyle.DashLine)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(QPointF(cx, cy), outer_r, outer_r)

        def _draw_mana_sectors(self, painter: QPainter, cx: float, cy: float, in_r: float, out_r: float) -> None:
            if not self.sectors or self.total_cards <= 0:
                # Empty state circle
                painter.setBrush(QBrush(QColor(30, 41, 59, 180)))
                painter.setPen(QPen(QColor("#475569"), 1.5))
                painter.drawEllipse(QPointF(cx, cy), out_r, out_r)
                return

            start_angle = 90.0 * 16  # Qt uses 1/16th degrees, 12 o'clock is 90 deg
            for sec in self.sectors:
                span_angle = - (sec.card_count / self.total_cards) * 360.0 * 16
                is_hovered = (sec.mana_cost == self.hovered_mana)
                cur_out_r = out_r + (4.0 if is_hovered else 0.0)

                color = QColor(sec.color_hex)
                if is_hovered:
                    color = color.lighter(130)

                painter.setBrush(QBrush(color))
                painter.setPen(QPen(QColor(15, 23, 42, 220), 1.5))
                painter.drawPie(
                    QRectF(cx - cur_out_r, cy - cur_out_r, cur_out_r * 2, cur_out_r * 2),
                    int(start_angle),
                    int(span_angle),
                )
                start_angle += span_angle

        def _draw_center_needle(self, painter: QPainter, cx: float, cy: float, in_r: float) -> None:
            # Dark dial background
            grad = QRadialGradient(cx, cy, in_r)
            grad.setColorAt(0.0, QColor(30, 41, 59, 240))
            grad.setColorAt(1.0, QColor(15, 23, 42, 255))
            painter.setBrush(QBrush(grad))
            painter.setPen(QPen(QColor("#38bdf8" if self.active_mode == "LETHAL" else "#10b981"), 2.0))
            painter.drawEllipse(QPointF(cx, cy), in_r, in_r)

            # Center text: percentage and mode
            pct = self.topdeck_lethal_pct if self.active_mode == "LETHAL" else self.topdeck_survival_pct
            mode_zh = "斩杀神抽" if self.active_mode == "LETHAL" else "解场苟活"

            painter.setFont(QFont("Microsoft YaHei", 9, QFont.Weight.Bold))
            painter.setPen(QPen(QColor("#ffffff")))
            painter.drawText(
                QRectF(cx - in_r, cy - 14, in_r * 2, 16),
                Qt.AlignmentFlag.AlignCenter,
                f"{pct:.1f}%",
            )
            painter.setFont(QFont("Microsoft YaHei", 7, QFont.Weight.Normal))
            painter.setPen(QPen(QColor("#94a3b8")))
            painter.drawText(
                QRectF(cx - in_r, cy + 4, in_r * 2, 14),
                Qt.AlignmentFlag.AlignCenter,
                mode_zh,
            )

            # Needle pointer
            needle_rad = math.radians(self.needle_angle_target - 90.0)
            needle_len = in_r * 0.85
            tip_x = cx + needle_len * math.cos(needle_rad)
            tip_y = cy + needle_len * math.sin(needle_rad)

            needle_pen = QPen(QColor("#f59e0b" if self.active_mode == "LETHAL" else "#34d399"), 2.5)
            painter.setPen(needle_pen)
            painter.drawLine(QPointF(cx, cy), QPointF(tip_x, tip_y))
