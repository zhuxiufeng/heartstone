"""
ArchetypeSpecializer: Draft Archetype Detection & Dynamic Synergy Specialization.
Classifies draft deck at 10+ and 20+ picks into Aggro, Control, Tempo Midrange, or Tribal,
and dynamically adjusts card valuations so picks synergize with the deck's established identity.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

from .card_db import CardInfo

logger = logging.getLogger("ArchetypeSpecializer")


class ArchetypeType(Enum):
    UNDETERMINED = "UNDETERMINED"       # Picks 1-9
    AGGRO = "AGGRO"                     # 快攻抢脸
    TEMPO_MIDRANGE = "TEMPO_MIDRANGE"   # 节奏中速
    CONTROL = "CONTROL"                 # 资源控制
    TRIBAL_SYNERGY = "TRIBAL_SYNERGY"   # 种族协同


@dataclass
class ArchetypeProfile:
    archetype: ArchetypeType
    name_cn: str
    description: str
    avg_cost: float
    early_game_ratio: float            # 1-3 mana drop proportion
    removal_count: int
    dominant_tribe: Optional[str]
    advice: str


class ArchetypeSpecializer:
    """Detects draft archetype after early picks and provides tailored card score modifiers."""

    @classmethod
    def detect_archetype(cls, deck: List[CardInfo]) -> ArchetypeProfile:
        """
        Analyzes the first 10-20 cards of the draft to classify the deck's emerging strategy.
        """
        if len(deck) < 10:
            return ArchetypeProfile(
                archetype=ArchetypeType.UNDETERMINED,
                name_cn="奠基阶段",
                description="前 10 抓为单卡质量积累期，优先选择身材出色的独立强卡。",
                avg_cost=0.0,
                early_game_ratio=0.0,
                removal_count=0,
                dominant_tribe=None,
                advice="优先拿取裸下不亏的超模单卡，暂不盲目押注特定流派。",
            )

        costs = [c.cost for c in deck]
        avg_cost = sum(costs) / len(costs)
        early_count = sum(1 for c in deck if 1 <= c.cost <= 3)
        early_ratio = early_count / len(deck)
        heavy_count = sum(1 for c in deck if c.cost >= 6)

        # Count removals and board clears
        removal_count = 0
        for c in deck:
            txt = c.text or ""
            if "消灭" in txt or "对所有" in txt or "造成" in txt and c.card_type == "SPELL":
                removal_count += 1

        # Check tribal concentration
        races: Dict[str, int] = {}
        for c in deck:
            if c.race:
                races[c.race] = races.get(c.race, 0) + 1
            for r in c.races:
                races[r] = races.get(r, 0) + 1

        dominant_race = None
        for r, cnt in races.items():
            if cnt >= 4:
                dominant_race = r
                break

        # Classification logic
        if dominant_race and races[dominant_race] >= 5:
            return ArchetypeProfile(
                archetype=ArchetypeType.TRIBAL_SYNERGY,
                name_cn=f"【{dominant_race}种族协同】",
                description=f"套牌拥有多达 {races[dominant_race]} 张【{dominant_race}】组件，已形成强烈的种族呼应！",
                avg_cost=avg_cost,
                early_game_ratio=early_ratio,
                removal_count=removal_count,
                dominant_tribe=dominant_race,
                advice=f"极度优先选取与【{dominant_race}】具有联动光环、战吼增益或减费效果的随从！",
            )

        if early_ratio >= 0.55 and avg_cost <= 3.3 and heavy_count <= 2:
            return ArchetypeProfile(
                archetype=ArchetypeType.AGGRO,
                name_cn="【极限快攻 (Aggro)】",
                description=f"低费曲线占比高达 {early_ratio*100:.0f}%，平均费用仅 {avg_cost:.1f}，具备极速抢脸击杀骨架！",
                avg_cost=avg_cost,
                early_game_ratio=early_ratio,
                removal_count=removal_count,
                dominant_tribe=None,
                advice="后续抓牌强力惩罚 6+ 费高费大怪，大幅提升 1-3 费铺场与直伤爆发的抓位权重！",
            )

        if avg_cost >= 4.1 or (removal_count >= 4 and heavy_count >= 4):
            return ArchetypeProfile(
                archetype=ArchetypeType.CONTROL,
                name_cn="【资源控制 (Control)】",
                description=f"拥有 {removal_count} 张优质解牌/AOE与重型后期随从，平均费用 {avg_cost:.1f}，走大后期制胜路线！",
                avg_cost=avg_cost,
                early_game_ratio=early_ratio,
                removal_count=removal_count,
                dominant_tribe=None,
                advice="优先补充过牌引擎、大型全场AOE与高韧性嘲讽随从，规避弱小快攻随从。",
            )

        # Default Midrange
        return ArchetypeProfile(
            archetype=ArchetypeType.TEMPO_MIDRANGE,
            name_cn="【节奏中速 (Tempo Midrange)】",
            description=f"曲线平滑饱满 (2-5费均衡分布)，平均费用 {avg_cost:.1f}，标准竞技场稳健滚雪球卡组。",
            avg_cost=avg_cost,
            early_game_ratio=early_ratio,
            removal_count=removal_count,
            dominant_tribe=None,
            advice="按需修补 3 费与 4 费战力，优先选取突袭、圣盾与具备优质白吃能力的按费拍怪核心。",
        )

    @classmethod
    def evaluate_card_archetype_delta(
        cls,
        card: CardInfo,
        profile: ArchetypeProfile,
    ) -> Tuple[int, str]:
        """
        Computes dynamic score modification (-25 to +25) based on the deck's active archetype.
        """
        if profile.archetype == ArchetypeType.UNDETERMINED:
            return 0, ""

        cost = card.cost
        text = card.clean_text

        if profile.archetype == ArchetypeType.AGGRO:
            # Aggro rewards cheap minions, burn, charge, buffs
            if cost <= 2:
                return 15, "🔥【快攻契合】极低费用随从，强化前两回合铺场压迫！"
            elif cost == 3 and (card.attack or 0) >= 3:
                return 10, "🔥【快攻高攻】3费高进攻性随从，持续压迫敌方血线！"
            elif "造成" in text and "伤害" in text and card.card_type == "SPELL":
                return 16, "⚡【直伤终结】快攻不可或缺的过墙斩杀利刃！"
            elif cost >= 6:
                return -22, "⚠️【流派冲突】高费臃肿，严重拖慢快攻压制节奏，极易卡手！"

        elif profile.archetype == ArchetypeType.CONTROL:
            # Control rewards AOE, Hard Removal, Taunt, Card Draw, Big Value
            if "所有" in text and ("伤害" in text or "消灭" in text):
                return 22, "🛡️【控制核心】全场强力清场，控制卡组立足之本！"
            elif "抽" in text and "牌" in text:
                return 15, "📚【资源续航】控制流派急需的补牌手段！"
            elif "TAUNT" in card.mechanics and cost >= 5 and (card.health or 0) >= 6:
                return 16, "🏰【铜墙铁壁】重型高血嘲讽，稳固后期安全！"
            elif cost == 1 and not card.mechanics and card.card_type == "MINION":
                return -12, "⚠️【质量过低】缺乏后期价值的脆弱 1 费怪，后期抽到严重亏卡！"

        elif profile.archetype == ArchetypeType.TRIBAL_SYNERGY:
            if profile.dominant_tribe and (
                card.race == profile.dominant_tribe or profile.dominant_tribe in card.races
            ):
                return 20, f"🧬【种族联动】与套牌【{profile.dominant_tribe}】核心形成强大战术呼应！"

        elif profile.archetype == ArchetypeType.TEMPO_MIDRANGE:
            if "RUSH" in card.mechanics:
                return 14, "🐎【即时解场】突袭随从能迅速完成下场白吃，夺回场面主导权！"
            elif "DIVINE_SHIELD" in card.mechanics:
                return 12, "✨【韧性站场】圣盾随从提供极强交换韧性！"

        return 0, ""
