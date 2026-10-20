"""
TacticalCompass: High-Level Arena Match Posture & Strategic Compass.
Distinguishes between when to play safe, when to greed for cards, when to push tempo, and when to all-in rush.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger("TacticalCompass")


@dataclass
class TacticalCompassReport:
    mode_name: str           # "优势防翻盘", "均势贪牌续航", "均势提速抢先机", "绝境打脸搏命"
    icon: str                # "🛡️", "💎", "⚡", "🔥"
    badge_color: str         # Hex color code
    macro_directive: str     # Actionable guiding advice


class TacticalCompass:
    """Evaluates the macro battlefield to direct greed vs tempo balance."""

    @classmethod
    def evaluate_compass(
        cls,
        friendly_hp: int,
        enemy_hp: int,
        friendly_board_atk: int,
        enemy_board_atk: int,
        friendly_hand_count: int,
        enemy_hand_count: int,
        enemy_minion_count: int,
        current_turn: int,
    ) -> TacticalCompassReport:
        # 1. Desperation Face Rush Mode
        # If enemy board attack is fatal or overwhelming
        if (enemy_board_atk >= friendly_hp * 0.7 and enemy_minion_count >= 3) or (friendly_hp <= 10 and enemy_board_atk >= 8):
            return TacticalCompassReport(
                mode_name="绝境打脸搏命",
                icon="🔥",
                badge_color="#ef4444",
                macro_directive="🔥 绝境打脸搏命：场面已无法解净！除必挡嘲讽外全员走脸压血压血线，把胜负押在下回合神抽直伤绝杀！",
            )

        # 2. Advantage Play-Safe Mode
        # We have massive board, healthy HP, and enemy is starving
        if friendly_board_atk >= enemy_board_atk + 5 and friendly_hp >= 16 and enemy_hand_count <= 3:
            return TacticalCompassReport(
                mode_name="优势求稳防翻盘",
                icon="🛡️",
                badge_color="#10b981",
                macro_directive="🛡️ 优势求稳防翻盘：场面已握绝对主动权！切忌贪多走脸，优先清干净敌方每一个杂毛随从，彻底杜绝神抽光环Buff翻盘！",
            )

        # 3. Balanced Value Greed Mode
        # Friendly hand is running dangerously low, enemy board is modest
        if friendly_hand_count <= 2 and enemy_board_atk <= 5 and friendly_hp >= 18:
            return TacticalCompassReport(
                mode_name="均势贪牌补续航",
                icon="💎",
                badge_color="#38bdf8",
                macro_directive="💎 均势贪牌补续航：手牌资源面临枯竭！敌方无即刻斩杀威胁，优先执行过牌/发现补充手牌，切忌盲目倾泻最后底牌！",
            )

        # 4. Balanced Tempo Pressure Mode
        return TacticalCompassReport(
            mode_name="均势提速抢先机",
            icon="⚡",
            badge_color="#f59e0b",
            macro_directive="⚡ 均势提速抢先机：按费拍怪最大化水晶利用率！主动发起优势交换并压低敌方血线，强迫对手被动交出关键解牌！",
        )
