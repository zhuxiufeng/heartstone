"""
PreCastBlunderInterceptor: Millisecond-Level Pre-Drop Tactical Blunder Shield.
Monitors in-flight player actions and sounds high-priority emergency voice & visual alarms
before irreversible blunders are committed (e.g., trading when lethal is available, not drawing first).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("PreCastBlunderInterceptor")


class InterceptType(str, Enum):
    MISSED_LETHAL = "MISSED_LETHAL"
    DRAW_BEFORE_PLAY = "DRAW_BEFORE_PLAY"
    DIVINE_SHIELD_OVERKILL = "DIVINE_SHIELD_OVERKILL"
    AURA_BEFORE_ATTACK = "AURA_BEFORE_ATTACK"
    AOE_OVEREXTEND = "AOE_OVEREXTEND"


@dataclass
class BlunderInterceptAlert:
    is_critical: bool
    intercept_type: InterceptType
    warning_title: str
    voice_shout: str
    corrective_action: str
    hazard_color: str = "#ef4444"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_critical": self.is_critical,
            "intercept_type": self.intercept_type.value,
            "warning_title": self.warning_title,
            "voice_shout": self.voice_shout,
            "corrective_action": self.corrective_action,
            "hazard_color": self.hazard_color,
        }


class PreCastBlunderInterceptor:
    """Detects immediate tactical errors and issues instant voice & UI stop commands."""

    AURA_BUFF_NAMES = ["暴风城勇士", "十字军光环", "嗜血", "野蛮咆哮", "火舌图腾", "战歌指挥官"]
    DRAW_SPELL_NAMES = ["奥术智慧", "滋养", "疾跑", "严正警戒", "痛苦诅咒", "抽一张牌", "过牌", "追踪术"]

    @classmethod
    def check_action(
        cls,
        intended_action_type: str,     # "ATTACK", "PLAY_CARD"
        intended_source_name: str,
        intended_target_name: str,
        enemy_hp: int,
        board_total_lethal_damage: int = 0,
        hand_cards: Optional[List[Dict[str, Any]]] = None,
        available_mana: int = 1,
        target_has_divine_shield: bool = False,
        source_attack: int = 0,
        has_minion_attacked_this_turn: bool = False,
        opponent_has_heavy_aoe_next_turn: bool = False,
        friendly_minion_count: int = 0,
    ) -> Optional[BlunderInterceptAlert]:
        hand_cards = hand_cards or []

        # 1. Missed Lethal Interception
        # If lethal is available and user is attacking a minion rather than face
        if board_total_lethal_damage >= enemy_hp and enemy_hp > 0:
            if intended_action_type == "ATTACK" and "英雄" not in intended_target_name:
                return BlunderInterceptAlert(
                    is_critical=True,
                    intercept_type=InterceptType.MISSED_LETHAL,
                    warning_title="⚡ 绝杀战机拦截！直接斩杀！",
                    voice_shout="住手！直接走脸就斩杀了，不用解场！",
                    corrective_action=f"全部随从攻击敌方英雄，伤害 ({board_total_lethal_damage}) ≥ 敌方血量 ({enemy_hp})！",
                    hazard_color="#f59e0b",
                )

        # 2. Draw Before Play Interception
        # If user is playing a minion/damage spell while having a playable draw card
        if intended_action_type == "PLAY_CARD" and not any(k in intended_source_name for k in cls.DRAW_SPELL_NAMES):
            playable_draw_cards = [
                c.get("name", "")
                for c in hand_cards
                if any(k in c.get("name", "") for k in cls.DRAW_SPELL_NAMES)
                and c.get("cost", 99) <= available_mana
            ]
            if playable_draw_cards:
                draw_name = playable_draw_cards[0]
                return BlunderInterceptAlert(
                    is_critical=False,
                    intercept_type=InterceptType.DRAW_BEFORE_PLAY,
                    warning_title="🛑 次序伏笔拦截：请先过牌！",
                    voice_shout=f"等等！先打【{draw_name}】过牌，看抓到什么再出怪！",
                    corrective_action=f"撤回出牌，优先施放【{draw_name}】拓展战术分支。",
                    hazard_color="#3b82f6",
                )

        # 3. Divine Shield Overkill
        if intended_action_type == "ATTACK" and target_has_divine_shield and source_attack >= 4:
            return BlunderInterceptAlert(
                is_critical=False,
                intercept_type=InterceptType.DIVINE_SHIELD_OVERKILL,
                warning_title="🛡️ 圣盾损耗拦截！",
                voice_shout="别拿主力大怪撞圣盾！先用杂毛或技能点掉圣盾！",
                corrective_action=f"【{intended_source_name}】攻击力高达 {source_attack} 点，请改用1攻随从或英雄技能破圣盾。",
                hazard_color="#ef4444",
            )

        # 4. Aura Before Attack Interception
        if intended_action_type == "ATTACK" and not has_minion_attacked_this_turn:
            playable_aura = [
                c.get("name", "")
                for c in hand_cards
                if any(k in c.get("name", "") for k in cls.AURA_BUFF_NAMES)
                and c.get("cost", 99) <= available_mana
            ]
            if playable_aura:
                aura_name = playable_aura[0]
                return BlunderInterceptAlert(
                    is_critical=False,
                    intercept_type=InterceptType.AURA_BEFORE_ATTACK,
                    warning_title="⚔️ 光环后置伏笔拦截！",
                    voice_shout=f"等等！先下【{aura_name}】，全员吃到攻击力加成再打！",
                    corrective_action=f"先打出【{aura_name}】，为全体随从附加攻击力后再行攻击。",
                    hazard_color="#fbbf24",
                )

        # 5. Overextend into heavy AOE
        if intended_action_type == "PLAY_CARD" and opponent_has_heavy_aoe_next_turn and friendly_minion_count >= 4:
            return BlunderInterceptAlert(
                is_critical=False,
                intercept_type=InterceptType.AOE_OVEREXTEND,
                warning_title="⚠️ 防清场纪律预警！",
                voice_shout="注意克制！对面下回合有重磅全场清场，留手牌防一波！",
                corrective_action="场上攻击频率已足够压制，建议保留手牌作为返场资源。",
                hazard_color="#a855f7",
            )

        return None
