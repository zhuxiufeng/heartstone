"""
TemporalBottleneckGuard: Temporal Action Bottleneck & Saturation Guard (武器与频次瓶颈饱和熔断器).
Enforces physical action-frequency limits on weapons (1 swing/turn), duplicate secrets,
and heavy bomb card clogging during arena drafting.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .card_db import CardInfo

logger = logging.getLogger("TemporalBottleneckGuard")


@dataclass
class SaturationAssessment:
    is_saturated: bool
    score_delta: float
    saturation_type: str          # "WEAPON_BOTTLENECK", "SECRET_DUPLICATE", "HEAVY_BOMB_CLOG", "NONE"
    saturation_tag: str
    advice: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_saturated": self.is_saturated,
            "score_delta": self.score_delta,
            "saturation_type": self.saturation_type,
            "saturation_tag": self.saturation_tag,
            "advice": self.advice,
        }


class TemporalBottleneckGuard:
    """Detects temporal bottlenecks and diminishing returns during arena drafting."""

    @classmethod
    def evaluate_card_saturation(
        cls,
        candidate_card: CardInfo,
        deck_so_far: List[CardInfo],
    ) -> SaturationAssessment:
        c_type = getattr(candidate_card, "card_type", "")
        c_cost = getattr(candidate_card, "cost", 0)
        c_name = getattr(candidate_card, "name", "")
        c_mechanics = getattr(candidate_card, "mechanics", [])

        # 1. Weapon Action-Frequency Bottleneck (Max 1 swing per turn)
        if c_type == "WEAPON":
            existing_weapons = [c for c in deck_so_far if getattr(c, "card_type", "") == "WEAPON"]
            weapon_count = len(existing_weapons)
            if weapon_count >= 2:
                penalty = -18.0 if weapon_count == 2 else -26.0
                tag = f"⛔【武器物理频次饱和 · 边际 {penalty:.0f}分】"
                advice = (
                    f"套牌中已有 {weapon_count} 把武器！英雄每回合只能挥砍一次，"
                    "武器无法同时装备，多把武器同时在手会导致手牌严重死卡！"
                )
                return SaturationAssessment(
                    is_saturated=True,
                    score_delta=penalty,
                    saturation_type="WEAPON_BOTTLENECK",
                    saturation_tag=tag,
                    advice=advice,
                )

        # 2. Secret Duplicate Conflict (Cannot have two identical secrets active)
        if "SECRET" in c_mechanics or "奥秘" in getattr(candidate_card, "text", ""):
            identical_secrets = [c for c in deck_so_far if getattr(c, "name", "") == c_name]
            if len(identical_secrets) >= 1:
                return SaturationAssessment(
                    is_saturated=True,
                    score_delta=-14.0,
                    saturation_type="SECRET_DUPLICATE",
                    saturation_tag="⛔【同名奥秘机制冲突 · 边际 -14分】",
                    advice=f"已有同名奥秘【{c_name}】！炉石机制禁止同时悬挂两个同名奥秘，第二张常年卡死无法打出！",
                )

        # 3. Heavy Bomb Temporal Clog (Cards cost >= 8)
        if c_cost >= 8:
            heavy_cards = [c for c in deck_so_far if getattr(c, "cost", 0) >= 8]
            if len(heavy_cards) >= 3:
                return SaturationAssessment(
                    is_saturated=True,
                    score_delta=-16.0,
                    saturation_type="HEAVY_BOMB_CLOG",
                    saturation_tag="⛔【高费终结者饱和 · 边际 -16分】",
                    advice=(
                        f"套牌已有 {len(heavy_cards)} 张 8+ 费高费大哥！"
                        "前期极易多张卡手导致前 5 回合空过直接崩盘，严禁继续补充高费！"
                    ),
                )

        return SaturationAssessment(
            is_saturated=False,
            score_delta=0.0,
            saturation_type="NONE",
            saturation_tag="",
            advice="该单卡频次正常，无手牌堵塞风险。",
        )
