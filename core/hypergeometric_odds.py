"""
HypergeometricOddsEngine: Exact Hypergeometric Probability Distribution & Topdeck EV Calculator.
Calculates mathematical probability of drawing key outs (lethal burn, survival taunt, wipe AOE)
from remaining deck and balances High-Risk Gamble EV vs Passive Safe EV.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .card_db import CardInfo

logger = logging.getLogger("HypergeometricOdds")


@dataclass
class HypergeometricOddsReport:
    remaining_deck_size: int
    burn_lethal_outs: int
    burn_lethal_prob_pct: float
    taunt_survival_outs: int
    taunt_survival_prob_pct: float
    aoe_clear_outs: int
    aoe_clear_prob_pct: float
    gamble_recommendation: str
    topdeck_ev_verdict: str
    key_out_names: List[str] = field(default_factory=list)


class HypergeometricOddsEngine:
    """Calculates hypergeometrical draw odds for arena deck states."""

    @staticmethod
    def calculate_prob(deck_size: int, outs: int, draws: int = 1) -> float:
        """Computes P(X >= 1) = 1 - (C(N-K, n) / C(N, n))."""
        if deck_size <= 0 or outs <= 0 or draws <= 0:
            return 0.0
        if outs >= deck_size:
            return 100.0
        n_draws = min(draws, deck_size)
        try:
            total_ways = math.comb(deck_size, n_draws)
            miss_ways = math.comb(max(0, deck_size - outs), n_draws)
            hit_prob = 1.0 - (miss_ways / total_ways)
            return round(max(0.0, min(100.0, hit_prob * 100.0)), 1)
        except Exception:
            return 0.0

    @classmethod
    def evaluate_deck_odds(
        cls,
        remaining_deck: List[CardInfo],
        enemy_hp: int = 30,
        friendly_hp: int = 30,
        enemy_board_attack: int = 0,
        draws_next_turn: int = 1,
    ) -> HypergeometricOddsReport:
        deck_size = len(remaining_deck)
        if deck_size == 0:
            return HypergeometricOddsReport(
                remaining_deck_size=0,
                burn_lethal_outs=0,
                burn_lethal_prob_pct=0.0,
                taunt_survival_outs=0,
                taunt_survival_prob_pct=0.0,
                aoe_clear_outs=0,
                aoe_clear_prob_pct=0.0,
                gamble_recommendation="牌库已空 (疲劳阶段)",
                topdeck_ev_verdict="牌库枯竭，已进入疲劳倒数。",
            )

        # Categorize outs in remaining deck
        burn_cards = []
        taunt_cards = []
        aoe_cards = []

        for c in remaining_deck:
            txt = (getattr(c, "text", "") or "") + " " + getattr(c, "clean_text", "")
            name = getattr(c, "name", "")
            # Direct burn / charge lethal outs
            if any(kw in txt or kw in name for kw in ["造成", "伤害", "火球", "斩杀", "杀戮", "冲锋", "打"]):
                burn_cards.append(name)
            # Taunt outs
            if "嘲讽" in txt or "TAUNT" in getattr(c, "mechanics", []):
                taunt_cards.append(name)
            # AOE clear outs
            if any(kw in txt or kw in name for kw in ["所有敌方随从", "全场", "烈焰风暴", "暴风雪", "奉献", "新星", "乱斗", "邪爆", "地狱烈焰"]):
                aoe_cards.append(name)

        p_burn = cls.calculate_prob(deck_size, len(burn_cards), draws_next_turn)
        p_taunt = cls.calculate_prob(deck_size, len(taunt_cards), draws_next_turn)
        p_aoe = cls.calculate_prob(deck_size, len(aoe_cards), draws_next_turn)

        # Strategic Gamble EV vs Safe EV
        is_facing_lethal = (enemy_board_attack >= friendly_hp)
        can_gamble_win = (enemy_hp <= 8 and len(burn_cards) > 0)

        if is_facing_lethal and can_gamble_win:
            gamble_rec = f"🔥 强烈建议孤注一掷！牌库余 {len(burn_cards)} 张斩杀牌，下轮神抽绝杀率 {p_burn}%，被动苟活必被踢死！"
            verdict = f"【搏命决策】牌库抽斩杀率 {p_burn}% > 苟活期望，全力抢脸！"
        elif is_facing_lethal and len(taunt_cards) > 0:
            gamble_rec = f"🛡️ 生死防守关头！下轮摸嘲讽保命概率 {p_taunt}% (牌库余{len(taunt_cards)}张嘲讽)"
            verdict = f"【保命决策】全员必须优先解场，为摸到嘲讽争取时间！"
        elif can_gamble_win and p_burn >= 30.0:
            gamble_rec = f"⚔️ 优势压制！下轮神抽直伤绝杀率 {p_burn}%，可适当走脸控血！"
            verdict = f"【提速决策】敌方进入直伤射程，神抽斩杀期望较高。"
        else:
            gamble_rec = f"⚖️ 牌库平稳运作中 (神抽率: 直伤 {p_burn}% / 嘲讽 {p_taunt}% / AOE {p_aoe}%)"
            verdict = "【稳健控场】按部就班积累场面价值，不盲目透支资源。"

        key_outs = list(dict.fromkeys(burn_cards[:3] + taunt_cards[:2] + aoe_cards[:2]))

        return HypergeometricOddsReport(
            remaining_deck_size=deck_size,
            burn_lethal_outs=len(burn_cards),
            burn_lethal_prob_pct=p_burn,
            taunt_survival_outs=len(taunt_cards),
            taunt_survival_prob_pct=p_taunt,
            aoe_clear_outs=len(aoe_cards),
            aoe_clear_prob_pct=p_aoe,
            gamble_recommendation=gamble_rec,
            topdeck_ev_verdict=verdict,
            key_out_names=key_outs,
        )
