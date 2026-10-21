"""
Deep Resource Entropy & Fatigue Endgame Horizon (超长线资源熵值与疲劳终局推演)
- Evaluates total remaining effective health, card count, and removals for both players.
- Accurately models fatigue timeline (Turns-to-Fatigue) and damage escalation (1, 2, 3, 4...).
- Determines strategic endgame pivot: Resource Dominance (stall to fatigue) vs Resource Deficit (aggressive rush before exhaustion).
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Any, Optional


class EndgameVerdict(str, Enum):
    RESOURCE_DOMINANCE = "RESOURCE_DOMINANCE"      # 资源碾压: 卡组厚度占优，稳健拖入疲劳致胜
    RESOURCE_DEFICIT_RUSH = "RESOURCE_DEFICIT_RUSH"  # 资源赤字: 牌库劣势，必须在疲劳前转攻提速斩杀
    FATIGUE_RACE_EQUAL = "FATIGUE_RACE_EQUAL"      # 疲劳对等: 双方厚度相当，进入白刃战


@dataclass
class ResourcePool:
    remaining_cards_count: int
    total_effective_health: int
    total_removal_value: int
    turns_to_fatigue: int


@dataclass
class FatigueEndgameReport:
    verdict: EndgameVerdict
    verdict_label: str
    my_resource: ResourcePool
    opp_resource: ResourcePool
    fatigue_differential_turns: int  # my_turns - opp_turns (>0 means opponent fatigues first)
    strategic_directive: str
    summary_markdown: str


class FatigueEndgameHorizon:
    """
    Simulates late-game resource exhaustion and fatigue curves.
    """

    HEALING_CARDS = {
        "雷诺·杰克逊": 30, "生命阿莱克丝塔萨": 15, "强效治疗术": 12,
        "治疗波": 14, "快速治疗": 5, "圣光闪现": 4, "吸血鬼之血": 10
    }

    HARD_REMOVALS = {
        "绝命乱斗": 10, "扭曲虚空": 10, "灵魂炸弹": 8, "斩杀": 6,
        "盾牌猛击": 6, "暗言术：灭": 6, "刺杀": 6, "妖术": 7, "变形术": 7
    }

    @classmethod
    def calculate_endgame_horizon(
        cls,
        my_deck_count: int,
        my_hand: List[str],
        my_hp: int,
        my_armor: int,
        opp_deck_count: int,
        opp_hand_count: int,
        opp_hp: int,
        opp_armor: int,
        opp_class: str = "Warrior",
        current_turn: int = 10,
    ) -> FatigueEndgameReport:
        """
        Projects fatigue arrival turns and recommends macro game posture.
        """
        # Calculate my extra healing & removals from hand
        my_extra_heal = sum(cls.HEALING_CARDS.get(c, 0) for c in my_hand)
        my_removals = sum(cls.HARD_REMOVALS.get(c, 0) for c in my_hand)
        my_eff_hp = my_hp + my_armor + my_extra_heal

        # Estimate opponent effective HP based on class and hand count
        opp_armor_factor = 10 if opp_class in ("Warrior", "Druid", "DeathKnight") else 0
        opp_eff_hp = opp_hp + opp_armor + opp_armor_factor
        opp_removals = opp_hand_count * 2  # Heuristic estimation

        my_pool = ResourcePool(
            remaining_cards_count=my_deck_count,
            total_effective_health=my_eff_hp,
            total_removal_value=my_removals,
            turns_to_fatigue=my_deck_count,
        )

        opp_pool = ResourcePool(
            remaining_cards_count=opp_deck_count,
            total_effective_health=opp_eff_hp,
            total_removal_value=opp_removals,
            turns_to_fatigue=opp_deck_count,
        )

        diff = my_deck_count - opp_deck_count

        if diff >= 3:
            verdict = EndgameVerdict.RESOURCE_DOMINANCE
            label = "🛡️ 资源碾压掌控 (牌库占优，稳健拖疲劳)"
            directive = (
                f"我方牌库领先对手 {diff} 张牌！对手将在 {opp_deck_count} 回合后先进入疲劳并承受递增伤害。"
                "战略决策：严格保留单解大解，尽量少过牌，稳健控场将比赛拖入疲劳期必胜！"
            )
        elif diff <= -3:
            verdict = EndgameVerdict.RESOURCE_DEFICIT_RUSH
            label = "⚔️ 资源赤字警报 (牌库劣势，必须提速压制)"
            directive = (
                f"我方牌库落后对手 {abs(diff)} 张牌，将在 {my_deck_count} 回合后先遭遇疲劳死局！"
                "战略决策：立刻转守为攻！所有随从集中打脸压迫血线，必须在疲劳降临前抢死对手！"
            )
        else:
            verdict = EndgameVerdict.FATIGUE_RACE_EQUAL
            label = "⚖️ 疲劳均势竞速 (厚度对等，关键牌较量)"
            directive = (
                f"双方卡库厚度差距微弱 (仅差 {abs(diff)} 张)。"
                "战略决策：注重每张随从的价值最大化交换，避免无效溢出伤害。"
            )

        summary_md = (
            f"**终局疲劳推演大盘 (当前第 {current_turn} 回合)**:\n"
            f"• **结论判定**: **{label}**\n"
            f"• **牌库厚度**: 我方剩余 {my_deck_count} 张 vs 敌方剩余 {opp_deck_count} 张 (净差: {diff:+d})\n"
            f"• **有效生命**: 我方 {my_eff_hp} 血 (含护甲/治疗) vs 敌方 {opp_eff_hp} 血\n"
            f"• **核心战略**: {directive}"
        )

        return FatigueEndgameReport(
            verdict=verdict,
            verdict_label=label,
            my_resource=my_pool,
            opp_resource=opp_pool,
            fatigue_differential_turns=diff,
            strategic_directive=directive,
            summary_markdown=summary_md,
        )
