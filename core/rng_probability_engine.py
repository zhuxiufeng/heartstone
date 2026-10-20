"""
RngProbabilityEngine: Precise RNG and Discover pool cumulative probability evaluator.
Provides exact mathematical odds for variable damage spells, multi-target missile hits,
and Discover card category outcomes.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("RngProbabilityEngine")


@dataclass
class VariableDamageOdds:
    card_name: str
    target_name: str
    target_hp: int
    min_damage: int
    max_damage: int
    kill_probability: float      # 0.0 to 1.0
    survival_probability: float  # 0.0 to 1.0
    avg_damage: float
    tactical_verdict: str


@dataclass
class MissileTargetOdds:
    target_name: str
    target_hp: int
    kill_probability: float      # Exact binomial/multinomial kill probability
    expected_hits: float


@dataclass
class DiscoverCategoryOdds:
    hero_class: str
    discover_source: str
    taunt_odds_pct: float
    hard_removal_odds_pct: float
    direct_burn_odds_pct: float
    aoe_clear_odds_pct: float
    summary_text: str


@dataclass
class RngProbabilityReport:
    damage_odds: Optional[VariableDamageOdds] = None
    missile_odds: List[MissileTargetOdds] = field(default_factory=list)
    discover_odds: Optional[DiscoverCategoryOdds] = None
    summary_badge: str = ""
    actionable_directive: str = ""


# Class specific base pool estimations in current arena rotation
CLASS_DISCOVER_DISTRIBUTION: Dict[str, Dict[str, float]] = {
    "MAGE": {"taunt": 0.12, "removal": 0.28, "burn": 0.35, "aoe": 0.22},
    "PRIEST": {"taunt": 0.18, "removal": 0.42, "burn": 0.15, "aoe": 0.25},
    "WARLOCK": {"taunt": 0.20, "removal": 0.30, "burn": 0.22, "aoe": 0.28},
    "PALADIN": {"taunt": 0.32, "removal": 0.22, "burn": 0.14, "aoe": 0.18},
    "HUNTER": {"taunt": 0.10, "removal": 0.25, "burn": 0.45, "aoe": 0.12},
    "WARRIOR": {"taunt": 0.35, "removal": 0.38, "burn": 0.10, "aoe": 0.20},
    "SHAMAN": {"taunt": 0.24, "removal": 0.32, "burn": 0.30, "aoe": 0.24},
    "ROGUE": {"taunt": 0.08, "removal": 0.36, "burn": 0.38, "aoe": 0.10},
    "DRUID": {"taunt": 0.30, "removal": 0.25, "burn": 0.18, "aoe": 0.15},
    "DEATHKNIGHT": {"taunt": 0.28, "removal": 0.35, "burn": 0.20, "aoe": 0.26},
    "DEMONHUNTER": {"taunt": 0.12, "removal": 0.28, "burn": 0.40, "aoe": 0.18},
}


class RngProbabilityEngine:
    """Calculates exact cumulative probabilities for random outcomes and discover pools."""

    @classmethod
    def evaluate_variable_damage(
        cls,
        card_name: str,
        min_dmg: int,
        max_dmg: int,
        target_name: str,
        target_hp: int,
    ) -> VariableDamageOdds:
        """Calculates discrete probability of lethal elimination with variable damage."""
        if max_dmg < min_dmg:
            min_dmg, max_dmg = max_dmg, min_dmg

        possible_outcomes = list(range(min_dmg, max_dmg + 1))
        total_outcomes = len(possible_outcomes)
        lethal_outcomes = sum(1 for d in possible_outcomes if d >= target_hp)
        kill_prob = lethal_outcomes / total_outcomes if total_outcomes > 0 else 0.0
        surv_prob = 1.0 - kill_prob
        avg_dmg = sum(possible_outcomes) / total_outcomes if total_outcomes > 0 else min_dmg

        if kill_prob >= 0.99:
            verdict = f"🎯 必杀 (100% 击杀【{target_name}】)"
        elif kill_prob >= 0.65:
            verdict = f"🎲 优势博弈 (成功击杀率 {kill_prob*100:.0f}%，留残血率 {surv_prob*100:.0f}%)"
        elif kill_prob > 0.0:
            verdict = f"⚠️ 劣势赌博 (仅 {kill_prob*100:.0f}% 概率击杀，建议优先稳定解法)"
        else:
            verdict = f"🛡️ 无法击杀 (最大伤害 {max_dmg} < 目标血量 {target_hp})"

        return VariableDamageOdds(
            card_name=card_name,
            target_name=target_name,
            target_hp=target_hp,
            min_damage=min_dmg,
            max_damage=max_dmg,
            kill_probability=kill_prob,
            survival_probability=surv_prob,
            avg_damage=avg_dmg,
            tactical_verdict=verdict,
        )

    @classmethod
    def evaluate_missile_hits(
        cls,
        missiles_count: int,
        target_name: str,
        target_hp: int,
        other_targets_count: int,
    ) -> MissileTargetOdds:
        """
        Calculates exact binomial distribution probability of scoring >= target_hp hits.
        total_targets = 1 (target) + other_targets_count
        """
        total_targets = max(1, 1 + other_targets_count)
        p = 1.0 / total_targets
        n = missiles_count

        # Probability of getting at least target_hp hits
        if target_hp > n:
            kill_prob = 0.0
        else:
            # P(X >= k) = sum_{j=k}^n C(n, j) * p^j * (1-p)^(n-j)
            prob_at_least = 0.0
            for j in range(target_hp, n + 1):
                comb = math.comb(n, j)
                prob_at_least += comb * (p ** j) * ((1.0 - p) ** (n - j))
            kill_prob = min(1.0, max(0.0, prob_at_least))

        expected_hits = n * p

        return MissileTargetOdds(
            target_name=target_name,
            target_hp=target_hp,
            kill_probability=kill_prob,
            expected_hits=expected_hits,
        )

    @classmethod
    def evaluate_discover_pool(
        cls,
        hero_class: str,
        discover_source: str = "发现法术",
    ) -> DiscoverCategoryOdds:
        """
        Calculates cumulative 3-card pick probability across tactical archetypes:
        P(at least 1 hit in 3 choices) = 1 - (1 - P_single)^3
        """
        norm_class = (hero_class or "MAGE").upper().strip()
        dist = CLASS_DISCOVER_DISTRIBUTION.get(norm_class, CLASS_DISCOVER_DISTRIBUTION["MAGE"])

        def _at_least_one(p_single: float) -> float:
            return round((1.0 - (1.0 - p_single) ** 3) * 100.0, 1)

        taunt_odds = _at_least_one(dist["taunt"])
        removal_odds = _at_least_one(dist["removal"])
        burn_odds = _at_least_one(dist["burn"])
        aoe_odds = _at_least_one(dist["aoe"])

        summary = (
            f"🔮【{discover_source}】三选一命中概率: "
            f"硬解 {removal_odds}% | AOE {aoe_odds}% | 直伤 {burn_odds}% | 嘲讽 {taunt_odds}%"
        )

        return DiscoverCategoryOdds(
            hero_class=norm_class,
            discover_source=discover_source,
            taunt_odds_pct=taunt_odds,
            hard_removal_odds_pct=removal_odds,
            direct_burn_odds_pct=burn_odds,
            aoe_clear_odds_pct=aoe_odds,
            summary_text=summary,
        )

    @classmethod
    def scan_hand_for_rng(
        cls,
        hand_cards: List[Any],
        enemy_minions: List[Dict[str, Any]],
        hero_class: str = "MAGE",
    ) -> Optional[RngProbabilityReport]:
        """Scans hand for active RNG/Discover cards and matches against highest priority enemy."""
        report = RngProbabilityReport()
        found_rng = False

        # 1. Check for variable damage cards
        priority_enemy = enemy_minions[0] if enemy_minions else {"name": "敌方随从", "health": 3}
        e_hp = priority_enemy.get("health", 3)
        e_name = priority_enemy.get("name", "敌方随从")

        for c in hand_cards:
            c_name = getattr(c, "name", str(c))
            c_text = getattr(c, "text", "") or ""

            # Check variable damage pattern (e.g. 连环爆裂, 闪电箭, 伤害范围)
            if "3到6" in c_text or "3-6" in c_text or "连环爆裂" in c_name:
                report.damage_odds = cls.evaluate_variable_damage(c_name, 3, 6, e_name, e_hp)
                report.summary_badge = f"🎲【{c_name}】{report.damage_odds.tactical_verdict}"
                found_rng = True
                break
            elif "奥术飞弹" in c_name:
                other_count = len(enemy_minions) # includes enemy hero
                report.missile_odds.append(cls.evaluate_missile_hits(3, e_name, e_hp, other_count))
                m_odd = report.missile_odds[0]
                report.summary_badge = f"🎯【奥术飞弹】击杀【{e_name}】率: {m_odd.kill_probability*100:.1f}% (期望命中 {m_odd.expected_hits:.1f} 发)"
                found_rng = True
                break
            elif "发现" in c_text or "发现" in c_name or "远古雕文" in c_name:
                report.discover_odds = cls.evaluate_discover_pool(hero_class, c_name)
                report.summary_badge = report.discover_odds.summary_text
                found_rng = True
                break

        return report if found_rng else None
