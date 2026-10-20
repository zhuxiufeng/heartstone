"""
BoardTacticalOverlay: In-Game Transparent Canvas Projecting Tactical Vectors & Badges directly on Hearthstone Board.
Renders:
1. Dynamic Tactical Arrows (Trades ⚔️, Face Rush 🎯, Targeted Spells ⚡)
2. Minion Status Badges (Taunts 🛡️, High Priority Removal ⚔️, Safe Face 🎯)
3. Safe Placement Bracket (Optimal geometric slot minimizing AOE punish)
Transparent and click-through (Qt.WindowTransparentForInput) so game controls remain 100% responsive.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import QWidget

try:
    from core.window_finder import WindowFinder, WindowRect
except (ImportError, ValueError):
    from ..core.window_finder import WindowFinder, WindowRect

logger = logging.getLogger("BoardTacticalOverlay")


class BoardTacticalOverlay(QWidget):
    """Transparent click-through canvas overlaying the active Hearthstone game window."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.SubWindow |
            Qt.WindowTransparentForInput  # Allows all clicks to pass through to Hearthstone!
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        self._enabled = True
        self._friendly_minions: List[Dict[str, Any]] = []
        self._enemy_minions: List[Dict[str, Any]] = []
        self._optimal_trades: List[str] = []
        self._play_actions: List[str] = []
        self._recommended_slot: int = -1
        self._enemy_hp: int = 30
        self._is_lethal: bool = False
        self._lethal_damage: int = 0
        self._aoe_threat_damage: int = 0
        self._hover_card_name: str = ""
        self._hover_damage: int = 0
        self._hover_is_aoe: bool = False

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        if not enabled:
            self.hide()
        else:
            self.show()

    def sync_to_window(self, win: Optional[WindowRect]) -> None:
        if not win or not self._enabled:
            self.hide()
            return
        if self.geometry() != (win.left, win.top, win.width, win.height):
            self.setGeometry(win.left, win.top, win.width, win.height)
        if not self.isVisible() and self._enabled:
            self.show()
            self.update()

    def update_board_tactics(
        self,
        friendly_minions: List[Any],
        enemy_minions: List[Any],
        optimal_trades: List[str],
        play_actions: List[str],
        recommended_slot: int = -1,
        enemy_hp: int = 30,
        is_lethal: bool = False,
        lethal_damage: int = 0,
        aoe_threat_damage: int = 0,
    ) -> None:
        """Updates real-time minion state, lethal aura, and tactical arrows to paint."""
        new_friendly = [self._normalize_minion(m) for m in friendly_minions]
        new_enemy = [self._normalize_minion(m) for m in enemy_minions]
        
        # Performance: Fast fingerprint check to skip redundant translucent window repaints
        f_sig = tuple((m.get("name"), m.get("atk"), m.get("health")) for m in new_friendly)
        e_sig = tuple((m.get("name"), m.get("atk"), m.get("health")) for m in new_enemy)
        state_key = (
            f_sig, e_sig, tuple(optimal_trades or ()), tuple(play_actions or ()),
            recommended_slot, enemy_hp, is_lethal, lethal_damage, aoe_threat_damage
        )
        if state_key == getattr(self, "_last_board_tactics_key", None):
            return
        self._last_board_tactics_key = state_key

        self._friendly_minions = new_friendly
        self._enemy_minions = new_enemy
        self._optimal_trades = optimal_trades or []
        self._play_actions = play_actions or []
        self._recommended_slot = recommended_slot
        self._enemy_hp = enemy_hp
        self._is_lethal = is_lethal
        self._lethal_damage = lethal_damage
        self._aoe_threat_damage = aoe_threat_damage
        self.update()

    @staticmethod
    def _normalize_minion(item: Any) -> Dict[str, Any]:
        if isinstance(item, dict):
            return item
        s = str(item)
        atk = 2
        hp = 2
        is_taunt = "嘲讽" in s
        if "(" in s and "/" in s:
            try:
                stats = s.split("(")[1].split(")")[0]
                parts = stats.split("/")
                atk = int(parts[0].strip().split()[-1])
                hp = int(parts[1].strip().split()[0])
            except Exception:
                pass
        name = s.split("(")[0].strip()
        return {"name": name, "atk": atk, "health": hp, "taunt": is_taunt, "can_attack": True}

    def set_hovered_card(self, card_name: str, card_text: str = "") -> None:
        """Sets hovered card for live sandbox battlefield simulation."""
        if self._hover_card_name == card_name and not card_name:
            return
        if self._hover_card_name == card_name and self._hover_damage > 0:
            return  # Already configured for this card

        self._hover_card_name = card_name
        self._hover_damage = 0
        self._hover_is_aoe = False

        if not card_name:
            self.update()
            return

        text = (card_text or "").lower()
        name = card_name.lower()
        if any(kw in text or kw in name for kw in ["全场", "所有", "烈焰风暴", "奉献", "暴风雪", "神圣新星"]):
            self._hover_is_aoe = True
            if "烈焰风暴" in name or "4点" in text:
                self._hover_damage = 4
            elif "全场打2" in text or "2点" in text or "奉献" in name or "新星" in name:
                self._hover_damage = 2
            elif "打3" in text or "3点" in text:
                self._hover_damage = 3
            else:
                self._hover_damage = 2
        elif any(kw in text or kw in name for kw in ["造成", "伤害", "火球", "寒冰箭", "打"]):
            if "火球" in name or "6点" in text:
                self._hover_damage = 6
            elif "寒冰箭" in name or "3点" in text:
                self._hover_damage = 3
            elif "4点" in text:
                self._hover_damage = 4
            else:
                self._hover_damage = 3

        self.update()

    def _compute_ghost_board(self) -> Tuple[Dict[int, Dict[str, Any]], Dict[int, Dict[str, Any]]]:
        """
        Computes projected post-trade board state ('Ghost Board').
        Returns:
            friendly_ghosts: {idx: {"post_hp": int, "survived": bool, "involved": bool}}
            enemy_ghosts: {idx: {"killed": bool, "involved": bool}}
        """
        f_ghosts = {j: {"post_hp": m.get("health", 2), "survived": True, "involved": False} for j, m in enumerate(self._friendly_minions)}
        e_ghosts = {i: {"killed": False, "involved": False} for i, em in enumerate(self._enemy_minions)}

        if not self._optimal_trades:
            return f_ghosts, e_ghosts

        for trade_str in self._optimal_trades:
            f_idx = -1
            e_idx = -1
            for j, fm in enumerate(self._friendly_minions):
                fn = fm.get("name", "")
                if fn and fn in trade_str:
                    f_idx = j
                    break
            for i, em in enumerate(self._enemy_minions):
                en = em.get("name", "")
                if en and en in trade_str:
                    e_idx = i
                    break

            if f_idx >= 0 and e_idx >= 0:
                f_ghosts[f_idx]["involved"] = True
                e_ghosts[e_idx]["involved"] = True
                f_hp = f_ghosts[f_idx]["post_hp"]
                e_atk = self._enemy_minions[e_idx].get("atk", 1)
                rem_hp = f_hp - e_atk
                f_ghosts[f_idx]["post_hp"] = rem_hp
                f_ghosts[f_idx]["survived"] = (rem_hp > 0)
                e_ghosts[e_idx]["killed"] = True
            elif f_idx >= 0 and ("换掉" in trade_str or "解掉" in trade_str):
                f_ghosts[f_idx]["involved"] = True
                f_ghosts[f_idx]["post_hp"] = max(0, f_ghosts[f_idx]["post_hp"] - 2)
                f_ghosts[f_idx]["survived"] = (f_ghosts[f_idx]["post_hp"] > 0)

        return f_ghosts, e_ghosts

    def get_ghost_board_summary(self) -> str:
        """Formats human-readable summary of post-trade ghost board state."""
        f_ghosts, e_ghosts = self._compute_ghost_board()
        survivors = []
        friendly_losses = []
        for j, fm in enumerate(self._friendly_minions):
            info = f_ghosts.get(j, {})
            name = fm.get("name", "随从")
            atk = fm.get("atk", 1)
            if info.get("survived", True):
                survivors.append(f"{name} ({atk}/{info.get('post_hp', 1)})")
            else:
                friendly_losses.append(name)

        enemy_killed = []
        for i, em in enumerate(self._enemy_minions):
            info = e_ghosts.get(i, {})
            if info.get("killed", False):
                enemy_killed.append(em.get("name", "敌方随从"))

        parts = []
        if survivors:
            parts.append(f"友方存活: {', '.join(survivors)}")
        if friendly_losses:
            parts.append(f"我方牺牲: {', '.join(friendly_losses)}")
        if enemy_killed:
            parts.append(f"敌方击灭: {', '.join(enemy_killed)}")

        return " | ".join(parts) if parts else "无需复杂随从交换"

    def paintEvent(self, event) -> None:
        if not self._enabled or (not self._friendly_minions and not self._enemy_minions and not self._play_actions):
            return

        w = self.width()
        h = self.height()
        if w < 100 or h < 100:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        # 1. Coordinate Anchor Points
        enemy_hero_pos = QPointF(w * 0.50, h * 0.19)
        hand_pos = QPointF(w * 0.38, h * 0.90)
        e_row_y = h * 0.43
        f_row_y = h * 0.58

        # Minion slot calculations
        n_enemy = len(self._enemy_minions)
        enemy_coords: List[QPointF] = []
        if n_enemy > 0:
            spacing = min(w * 0.08, (w * 0.60) / max(n_enemy, 1))
            for i in range(n_enemy):
                x = w * 0.50 + (i - (n_enemy - 1) / 2.0) * spacing
                enemy_coords.append(QPointF(x, e_row_y))

        m_friend = len(self._friendly_minions)
        friend_coords: List[QPointF] = []
        if m_friend > 0:
            spacing = min(w * 0.08, (w * 0.60) / max(m_friend, 1))
            for j in range(m_friend):
                x = w * 0.50 + (j - (m_friend - 1) / 2.0) * spacing
                friend_coords.append(QPointF(x, f_row_y))

        # 1.5. Draw Enemy Hero Danger / Lethal Zone
        if self._is_lethal or self._enemy_hp <= 12:
            tag_text = f"🔥 斩杀线! ({self._lethal_damage}伤)" if self._is_lethal else f"🎯 绝杀线 (HP: {self._enemy_hp})"
            tag_color = QColor(220, 38, 38, 240) if self._is_lethal else QColor(234, 88, 12, 220)
            self._draw_pill_badge(painter, enemy_hero_pos.x(), enemy_hero_pos.y() - 44, tag_text, tag_color, QColor("#ffffff"))

            pen_ring = QPen(QColor(239, 68, 68, 160), 3.0, Qt.DashLine)
            painter.setPen(pen_ring)
            painter.setBrush(QBrush(QColor(239, 68, 68, 25)))
            painter.drawEllipse(enemy_hero_pos, 46, 46)

        # 1.8. Compute Ghost Board Post-Trade State
        f_ghosts, e_ghosts = self._compute_ghost_board()

        # 2. Draw Enemy Minion Badges & Ghost Elimination
        font_badge = QFont("Microsoft YaHei UI", 9, QFont.Bold)
        painter.setFont(font_badge)

        for i, m in enumerate(self._enemy_minions):
            pos = enemy_coords[i]
            is_taunt = m.get("taunt", False) or "嘲讽" in m.get("name", "")
            is_priority = any(m.get("name", "") in t for t in self._optimal_trades)
            eg = e_ghosts.get(i, {})

            if is_priority or is_taunt:
                pen_target = QPen(QColor(245, 158, 11, 150), 2.5, Qt.DotLine)
                painter.setPen(pen_target)
                painter.setBrush(QBrush(QColor(245, 158, 11, 25)))
                painter.drawEllipse(pos, 32, 32)

            if eg.get("killed", False):
                self._draw_pill_badge(painter, pos.x(), pos.y() - 36, "💥 残局必灭", QColor(147, 51, 234, 235), QColor("#ffffff"))
            elif is_taunt:
                self._draw_pill_badge(painter, pos.x(), pos.y() - 36, "🛡️ 嘲讽·必过", QColor(220, 38, 38, 230), QColor("#ffffff"))
            elif is_priority:
                self._draw_pill_badge(painter, pos.x(), pos.y() - 36, "⚔️ 优先解掉", QColor(217, 119, 6, 230), QColor("#ffffff"))
            else:
                self._draw_pill_badge(painter, pos.x(), pos.y() - 36, "🎯 可无视", QColor(71, 85, 105, 200), QColor("#e2e8f0"))

        # 3. Draw Friendly Minion Badges, Ghost Survival & AOE Breakpoint Warning
        for j, m in enumerate(self._friendly_minions):
            pos = friend_coords[j]
            f_atk = m.get("atk", m.get("attack", 0))
            f_hp = m.get("health", m.get("hp", 0))
            fg = f_ghosts.get(j, {})

            is_free_traded = False
            for em in self._enemy_minions:
                e_atk = em.get("atk", em.get("attack", 0))
                e_hp = em.get("health", em.get("hp", 0))
                if e_atk >= f_hp and e_hp > f_atk:
                    is_free_traded = True
                    break

            if fg.get("involved", False):
                if fg.get("survived", False):
                    self._draw_pill_badge(painter, pos.x(), pos.y() - 34, f"👻 残局:{f_atk}/{fg['post_hp']}", QColor(8, 145, 178, 240), QColor("#ffffff"))
                else:
                    self._draw_pill_badge(painter, pos.x(), pos.y() - 34, "💀 残局换死", QColor(185, 28, 28, 240), QColor("#ffffff"))
            elif any("增益我方" in act and m.get("name", "") in act for act in self._play_actions):
                self._draw_pill_badge(painter, pos.x(), pos.y() - 32, "⚔️ +2攻击增益", QColor(14, 165, 233, 230), QColor("#ffffff"))

            if is_free_traded:
                pen_vuln = QPen(QColor(236, 72, 153, 180), 2.8, Qt.DashLine)
                painter.setPen(pen_vuln)
                painter.setBrush(QBrush(QColor(236, 72, 153, 30)))
                painter.drawEllipse(pos, 32, 32)
                self._draw_pill_badge(painter, pos.x(), pos.y() + 32, "⚠️ 易被白吃", QColor(190, 24, 93, 230), QColor("#ffffff"))
            elif self._aoe_threat_damage > 0:
                if f_hp <= self._aoe_threat_damage:
                    pen_aoe = QPen(QColor(239, 68, 68, 220), 2.8, Qt.DashLine)
                    painter.setPen(pen_aoe)
                    painter.setBrush(QBrush(QColor(239, 68, 68, 35)))
                    painter.drawEllipse(pos, 32, 32)
                    self._draw_pill_badge(painter, pos.x(), pos.y() + 32, f"⚠️ 危险血线 (≤{self._aoe_threat_damage})", QColor(220, 38, 38, 240), QColor("#ffffff"))
                else:
                    self._draw_pill_badge(painter, pos.x(), pos.y() + 32, f"🛡️ 安全存活 (>{self._aoe_threat_damage})", QColor(16, 185, 129, 210), QColor("#ffffff"))
            else:
                self._draw_pill_badge(painter, pos.x(), pos.y() + 32, "⚡ 攻击准备", QColor(16, 185, 129, 210), QColor("#ffffff"))

        # Safe Placement Bracket Indicator (Golden Beacon)
        if 0 <= self._recommended_slot <= m_friend:
            spacing = min(w * 0.08, (w * 0.60) / max(m_friend, 1))
            slot_x = w * 0.50 + (self._recommended_slot - 0.5 - (m_friend - 1) / 2.0) * spacing
            self._draw_placement_bracket(painter, slot_x, f_row_y)

        # 4. Draw Dynamic Curved Tactical Vectors (Arrows)
        # Trades: Minion -> Minion
        if friend_coords and enemy_coords and self._optimal_trades:
            f_pt = friend_coords[0]
            # Find matching enemy taunt or priority
            e_pt = enemy_coords[0]
            for i, em in enumerate(self._enemy_minions):
                if em.get("taunt", False) or any(em.get("name", "") in t for t in self._optimal_trades):
                    e_pt = enemy_coords[i]
                    break
            self._draw_tactical_arrow(painter, f_pt, e_pt, QColor("#fbbf24"), "⚔️ 换掉嘲讽")

        # Face Rush: Minion -> Enemy Hero
        if len(friend_coords) > 1 or (friend_coords and not self._optimal_trades):
            f_pt = friend_coords[-1]
            self._draw_tactical_arrow(painter, f_pt, enemy_hero_pos, QColor("#ef4444"), "🎯 走脸压血")

        # Hand Direct Damage / Targeted Spell
        has_spell = any("打出" in act and ("定向打击" in act or "抢脸" in act or "火球" in act or "寒冰箭" in act) for act in self._play_actions)
        if has_spell:
            target_pt = enemy_coords[0] if (enemy_coords and any(em.get("taunt", False) for em in self._enemy_minions)) else enemy_hero_pos
            self._draw_tactical_arrow(painter, hand_pos, target_pt, QColor("#38bdf8"), "⚡ 定向直伤")

        # 5. Live Hover Sandbox Battlefield Preview
        if self._hover_damage > 0:
            banner_text = f"🔬 悬停沙盒验算: 【{self._hover_card_name}】{'全场' if self._hover_is_aoe else '定向'}伤害 -{self._hover_damage}"
            self._draw_pill_badge(painter, w * 0.50, h * 0.32, banner_text, QColor(2, 132, 199, 240), QColor("#ffffff"))

            if self._hover_is_aoe and enemy_coords:
                for i, em in enumerate(self._enemy_minions):
                    pos = enemy_coords[i]
                    hp = em.get("health", em.get("hp", 3))
                    rem_hp = hp - self._hover_damage
                    if rem_hp <= 0:
                        self._draw_pill_badge(painter, pos.x(), pos.y() + 32, f"💥 验算全清 (-{self._hover_damage})", QColor(220, 38, 38, 240), QColor("#ffffff"))
                    else:
                        self._draw_pill_badge(painter, pos.x(), pos.y() + 32, f"⚠️ 验算残血 ({rem_hp}血)", QColor(217, 119, 6, 240), QColor("#ffffff"))
            elif not self._hover_is_aoe:
                target_pt = enemy_coords[0] if enemy_coords else enemy_hero_pos
                self._draw_tactical_arrow(painter, hand_pos, target_pt, QColor("#38bdf8"), f"🔬 验算打击 -{self._hover_damage}")
                self._draw_pill_badge(painter, target_pt.x(), target_pt.y() - 38, f"🎯 验算伤害: -{self._hover_damage}", QColor(14, 165, 233, 240), QColor("#ffffff"))

        painter.end()

    def _draw_pill_badge(self, painter: QPainter, cx: float, cy: float, text: str, bg_color: QColor, text_color: QColor) -> None:
        bw = max(78, len(text) * 11 + 14)
        bh = 20
        rect = QRectF(cx - bw / 2, cy - bh / 2, bw, bh)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(rect, 10, 10)

        painter.setPen(text_color)
        painter.drawText(rect, Qt.AlignCenter, text)

    def _draw_placement_bracket(self, painter: QPainter, x: float, y: float) -> None:
        pen = QPen(QColor("#f59e0b"), 2.8, Qt.SolidLine)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(245, 158, 11, 40)))
        slot_rect = QRectF(x - 24, y - 36, 48, 72)
        painter.drawRoundedRect(slot_rect, 8, 8)

        # Beacon downward indicator and label
        self._draw_pill_badge(painter, x, y - 52, "▼ 最佳落点 ▼", QColor(217, 119, 6, 240), QColor("#ffffff"))

        font = QFont("Microsoft YaHei UI", 7, QFont.Bold)
        painter.setFont(font)
        painter.setPen(QColor("#fef3c7"))
        lbl_rect = QRectF(x - 60, y + 40, 120, 16)
        painter.drawText(lbl_rect, Qt.AlignCenter, "⭐ 防AOE/几何最优")

    def _draw_tactical_arrow(self, painter: QPainter, start: QPointF, end: QPointF, color: QColor, label: str = "") -> None:
        """Draws a smooth anti-aliased quadratic bezier vector with an arrowhead and badge."""
        ctrl_x = (start.x() + end.x()) / 2.0
        ctrl_y = (start.y() + end.y()) / 2.0 - 30.0  # Arc upward
        ctrl = QPointF(ctrl_x, ctrl_y)

        path = QPainterPath()
        path.moveTo(start)
        path.quadTo(ctrl, end)

        # Glow / shadow stroke
        pen_glow = QPen(QColor(color.red(), color.green(), color.blue(), 60), 7)
        painter.setPen(pen_glow)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)

        # Main solid core
        pen_core = QPen(color, 3.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen_core)
        painter.drawPath(path)

        # Draw Arrowhead at End Point
        angle = math.atan2(end.y() - ctrl.y(), end.x() - ctrl.x())
        arrow_size = 14
        p1 = QPointF(
            end.x() - arrow_size * math.cos(angle - math.pi / 6),
            end.y() - arrow_size * math.sin(angle - math.pi / 6),
        )
        p2 = QPointF(
            end.x() - arrow_size * math.cos(angle + math.pi / 6),
            end.y() - arrow_size * math.sin(angle + math.pi / 6),
        )

        arrow_head = QPainterPath()
        arrow_head.moveTo(end)
        arrow_head.lineTo(p1)
        arrow_head.lineTo(p2)
        arrow_head.closeSubpath()

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(color))
        painter.drawPath(arrow_head)

        # Draw midpoint label pill
        if label:
            mid_x = (start.x() + 2 * ctrl.x() + end.x()) / 4.0
            mid_y = (start.y() + 2 * ctrl.y() + end.y()) / 4.0
            lbl_w = 66
            lbl_h = 18
            lbl_rect = QRectF(mid_x - lbl_w / 2, mid_y - lbl_h / 2, lbl_w, lbl_h)
            painter.setBrush(QBrush(QColor(15, 23, 42, 220)))
            painter.setPen(QPen(color, 1.2))
            painter.drawRoundedRect(lbl_rect, 9, 9)

            painter.setPen(QColor("#ffffff"))
            font = QFont("Microsoft YaHei UI", 8, QFont.Bold)
            painter.setFont(font)
            painter.drawText(lbl_rect, Qt.AlignCenter, label)
