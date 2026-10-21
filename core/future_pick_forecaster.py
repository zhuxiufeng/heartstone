"""
FuturePickForecaster: Multi-Turn Draft Synergy Lever & Archetype Locking Engine.
Simulates future 10-20 draft picks, calculates Expected Future Leverage (EFL),
and dynamically re-weights card tiers when deck archetype locks into a dominant tribal/tempo style.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .card_db import CardInfo

logger = logging.getLogger("FuturePickForecaster")


class DraftArchetype(str, Enum):
    MECH_TEMPO = "MECH_TEMPO"          # 机械铺场节奏
    SPELL_BURN = "SPELL_BURN"          # 法术直伤控场
    DRAGON_CONTROL = "DRAGON_CONTROL"  # 巨龙后期控制
    BEAST_MIDRANGE = "BEAST_MIDRANGE"  # 野兽中速突袭
    UNDEAD_SWARM = "UNDEAD_SWARM"      # 亡灵亡语滚雪球
    BALANCED_TEMPO = "BALANCED_TEMPO"  # 均势万能曲线


@dataclass
class CandidateFutureValue:
    card: CardInfo
    base_tier_score: float
    immediate_synergy_score: float
    expected_future_leverage: float    # Future multiplier gain percentage (+/- %)
    total_projected_value: float
    locked_archetype_bonus: float
    recommendation_verdict: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "card_id": self.card.id,
            "card_name": self.card.name,
            "cost": self.card.cost,
            "base_score": round(self.base_tier_score, 1),
            "immediate_synergy": round(self.immediate_synergy_score, 1),
            "future_leverage_pct": round(self.expected_future_leverage, 1),
            "total_projected_value": round(self.total_projected_value, 1),
            "archetype_bonus": round(self.locked_archetype_bonus, 1),
            "verdict": self.recommendation_verdict,
        }


@dataclass
class FutureForecastReport:
    current_pick_number: int
    remaining_picks: int
    detected_archetype: DraftArchetype
    archetype_lock_confidence_pct: float
    candidates_analysis: List[CandidateFutureValue]
    best_pick_name: str
    strategic_future_advice: str
    summary_markdown: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_pick": self.current_pick_number,
            "remaining_picks": self.remaining_picks,
            "archetype": self.detected_archetype.value,
            "archetype_confidence_pct": round(self.archetype_lock_confidence_pct, 1),
            "best_pick": self.best_pick_name,
            "advice": self.strategic_future_advice,
            "candidates": [c.to_dict() for c in self.candidates_analysis],
            "summary_markdown": self.summary_markdown,
        }


class FuturePickForecaster:
    """Calculates forward-looking synergy value for draft picks."""

    @classmethod
    def evaluate_forecast(
        cls,
        candidates: List[CardInfo],
        drafted_deck: List[CardInfo],
        current_pick: int = 12,
    ) -> FutureForecastReport:
        remaining_picks = max(0, 30 - current_pick)

        # 1. Detect current archetype tendencies from drafted deck
        mech_count = sum(1 for c in drafted_deck if (c.race == "MECHANICAL" or "MECH" in (c.races or [])))
        dragon_count = sum(1 for c in drafted_deck if (c.race == "DRAGON" or "DRAGON" in (c.races or [])))
        beast_count = sum(1 for c in drafted_deck if (c.race == "BEAST" or "BEAST" in (c.races or [])))
        spell_count = sum(1 for c in drafted_deck if c.card_type == "SPELL")

        archetype = DraftArchetype.BALANCED_TEMPO
        confidence = 45.0

        if current_pick >= 8:
            if mech_count >= 4:
                archetype = DraftArchetype.MECH_TEMPO
                confidence = min(95.0, 50.0 + mech_count * 9.0)
            elif dragon_count >= 3:
                archetype = DraftArchetype.DRAGON_CONTROL
                confidence = min(90.0, 45.0 + dragon_count * 12.0)
            elif beast_count >= 4:
                archetype = DraftArchetype.BEAST_MIDRANGE
                confidence = min(90.0, 45.0 + beast_count * 10.0)
            elif spell_count >= 6:
                archetype = DraftArchetype.SPELL_BURN
                confidence = min(88.0, 40.0 + spell_count * 7.0)

        # 2. Evaluate candidates with Future Leverage
        analyzed_candidates: List[CandidateFutureValue] = []

        for card in candidates:
            base_score = 65.0
            r_upper = (card.rarity or "COMMON").upper()
            if r_upper == "LEGENDARY":
                base_score = 88.0
            elif r_upper == "EPIC":
                base_score = 78.0
            elif r_upper == "RARE":
                base_score = 72.0

            # Immediate synergy with existing deck
            immediate_syn = 0.0
            card_race = (card.race or "").upper()
            card_races = [r.upper() for r in (card.races or [])]
            card_text = card.clean_text or card.text or ""

            if card_race == "MECHANICAL" or "MECH" in card_races:
                immediate_syn += mech_count * 2.5
            if card_race == "DRAGON" or "DRAGON" in card_races:
                immediate_syn += dragon_count * 3.0
            if card_race == "BEAST" or "BEAST" in card_races:
                immediate_syn += beast_count * 2.2
            if card.card_type == "SPELL":
                immediate_syn += spell_count * 1.5

            # Expected Future Leverage (EFL) across remaining picks
            # If this card provides a strong tag enabler (e.g. Mech/Dragon) and we have remaining picks
            future_leverage = 0.0
            if remaining_picks > 5:
                if any(k in card_text for k in ["抽牌", "发现", "具有+"]):
                    future_leverage += 12.0
                if card_race in ("MECHANICAL", "DRAGON", "BEAST"):
                    future_leverage += 10.0 + (remaining_picks * 0.4)

            # Archetype Match Bonus
            arch_bonus = 0.0
            if archetype == DraftArchetype.MECH_TEMPO and (card_race == "MECHANICAL" or "MECH" in card_races):
                arch_bonus = 15.0
            elif archetype == DraftArchetype.DRAGON_CONTROL and (card_race == "DRAGON" or "DRAGON" in card_races):
                arch_bonus = 14.0
            elif archetype == DraftArchetype.BEAST_MIDRANGE and (card_race == "BEAST" or "BEAST" in card_races):
                arch_bonus = 13.0
            elif archetype == DraftArchetype.SPELL_BURN and card.card_type == "SPELL":
                arch_bonus = 12.0

            total_val = base_score + immediate_syn + future_leverage + arch_bonus
            verdict = "核心首选" if total_val >= 90 else ("优质支柱" if total_val >= 75 else "过渡卡牌")

            analyzed_candidates.append(
                CandidateFutureValue(
                    card=card,
                    base_tier_score=base_score,
                    immediate_synergy_score=immediate_syn,
                    expected_future_leverage=future_leverage,
                    total_projected_value=total_val,
                    locked_archetype_bonus=arch_bonus,
                    recommendation_verdict=verdict,
                )
            )

        analyzed_candidates.sort(key=lambda c: -c.total_projected_value)
        best = analyzed_candidates[0]

        advice = (
            f"当前卡组倾向于【{archetype.value}】(锁定置信度 {confidence:.0f}%)。"
            f"剩余 {remaining_picks} 抓中，优先推荐【{best.card.name}】，"
            f"可为未来选牌注入 +{best.expected_future_leverage:.1f}% 期望协同杠杆。"
        )

        md_lines = [
            f"**选牌未来期望沙盘** (当前第 {current_pick}/30 抓，剩余 {remaining_picks} 抓):",
            f"• **卡组形态锁定**: **{archetype.value}** (置信度 `{confidence:.0f}%`)",
            f"• 👑 **未来价值首选**: **{best.card.name}** (全局收益分 **{best.total_projected_value:.1f}**)",
            f"• 💡 **沙盘战略推演**: {advice}",
        ]

        return FutureForecastReport(
            current_pick_number=current_pick,
            remaining_picks=remaining_picks,
            detected_archetype=archetype,
            archetype_lock_confidence_pct=confidence,
            candidates_analysis=analyzed_candidates,
            best_pick_name=best.card.name,
            strategic_future_advice=advice,
            summary_markdown="\n".join(md_lines),
        )
