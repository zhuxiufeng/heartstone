"""
LiveDiscoverAdvisor: Real-Time Tactical Discover & Adapt Priority Advisor for Hearthstone.
Dynamically calculates the most urgent tactical need (Survival, Board Clear, Finisher, Value)
based on active health, board attack, and hand exhaustion.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger("LiveDiscoverAdvisor")


@dataclass
class DiscoverGuidance:
    priority_tier: str              # "SURVIVAL", "BOARD_CLEAR", "BURST_FINISH", "VALUE_REFILL", "TEMPO_DEVELOP"
    priority_badge: str
    guidance_text: str
    recommended_card_types: List[str] = field(default_factory=list)
    avoid_card_types: List[str] = field(default_factory=list)


class LiveDiscoverAdvisor:
    """Evaluates in-game board state and prescribes precise discover picking directives."""

    @classmethod
    def evaluate_discover_need(
        cls,
        friendly_hp: int,
        enemy_hp: int,
        friendly_board_atk: int,
        enemy_board_atk: int,
        hand_size: int,
        is_facing_lethal: bool = False,
    ) -> DiscoverGuidance:
        # 1. Emergency Survival (Facing lethal or HP <= 10 with enemy field pressure)
        if is_facing_lethal or (friendly_hp <= 10 and enemy_board_atk >= 5):
            return DiscoverGuidance(
                priority_tier="SURVIVAL",
                priority_badge="🚨 紧急求生·优先保命",
                guidance_text="当前生命已触碰危险红线！三选一必须绝对优先抓取【嘲讽随从 / 深度冻结 / 抬血保命 / 护甲 / 冰箱】！",
                recommended_card_types=["嘲讽随从", "高额回血/叠甲", "冰冻全场/单控", "潜行/保命奥秘"],
                avoid_card_types=["纯过牌", "纯抽卡衍生物", "无嘲讽白板大哥"],
            )

        # 2. Burst Finisher (Enemy is low and can be finished soon)
        if enemy_hp <= 12 and friendly_board_atk >= 3:
            return DiscoverGuidance(
                priority_tier="BURST_FINISH",
                priority_badge="🔥 绝杀封喉·优先直伤",
                guidance_text=f"敌方仅剩 {enemy_hp} 血！绝佳斩杀窗口已开，三选一优先抓取【高爆发直伤法术 / 冲锋突袭 / 强攻武器】直接终结比赛！",
                recommended_card_types=["直伤法术", "冲锋随从", "武器直伤", "攻击力咆哮/光环Buff"],
                avoid_card_types=["慢速控场牌", "防御型嘲讽"],
            )

        # 3. Board Clear (Enemy board attack is more than 2x friendly board attack)
        if enemy_board_atk >= friendly_board_atk + 5 and enemy_board_atk >= 7:
            return DiscoverGuidance(
                priority_tier="BOARD_CLEAR",
                priority_badge="⚡ 绝境返场·优先AOE与硬解",
                guidance_text="敌方场攻占据压倒性优势！三选一优先寻找【全场AOE清场 / 单体硬解 / 突袭复数返场】夺回主动权！",
                recommended_card_types=["全场AOE清场", "单体消灭/变形硬解", "突袭/吸血随从"],
                avoid_card_types=["高费纯资源牌", "低节奏过牌"],
            )

        # 4. Value Refill (Hand is empty <= 2 cards)
        if hand_size <= 2:
            return DiscoverGuidance(
                priority_tier="VALUE_REFILL",
                priority_badge="💎 资源续航·优先过牌补充",
                guidance_text="我方手牌枯竭！三选一优先抓取【多张过牌 / 无限资源复制 / 亡语高质量大卡】以防后续回合断粮！",
                recommended_card_types=["大量过牌法术", "亡语/衍生手牌随从", "英雄牌/泰坦核心"],
                avoid_card_types=["低效单解", "一次性亏卡法术"],
            )

        # 5. Tempo Development (Default / Ahead)
        return DiscoverGuidance(
            priority_tier="TEMPO_DEVELOP",
            priority_badge="⚔️ 节奏站场·优先超模身材",
            guidance_text="当前战局处于可控节奏中，三选一优先抓取【符合法力曲线的超模随从 / 优质身材战力】持续滚雪球施压！",
            recommended_card_types=["身材超模随从", "单体控场", "圣盾/魔免随从"],
            avoid_card_types=["过窄特化针对牌"],
        )
