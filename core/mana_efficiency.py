"""
ManaEfficiencyOptimizer: 2-Turn Floating Mana Minimizer for Hearthstone Arena.
Calculates continuous 2-turn play sequences to maximize mana utilization and eliminate wasted crystals.
"""

from __future__ import annotations

import itertools
import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .card_db import CardInfo

logger = logging.getLogger("ManaEfficiency")


@dataclass
class ManaEfficiencyPlan:
    current_turn_plays: List[CardInfo]
    next_turn_projected_plays: List[CardInfo]
    current_spent: int
    current_max: int
    next_spent: int
    next_max: int
    total_floating_mana: int
    efficiency_pct: float
    advice_text: str
    is_zero_waste: bool = False
    flow_tag: str = ""
    step_preview: str = ""
    flow_smoothness_score: float = 0.0


class ManaEfficiencyOptimizer:
    """Calculates continuous 2-turn mana crystal utilization to eliminate idle mana."""

    @classmethod
    def calculate_2turn_efficiency(
        cls,
        hand_cards: List[CardInfo],
        current_mana: int,
        next_mana: Optional[int] = None,
    ) -> Optional[ManaEfficiencyPlan]:
        """
        Explores all valid 2-turn card play combinations and identifies lines with minimum floating mana.
        """
        if not hand_cards or current_mana <= 0:
            return None

        # Exclude Coin from standard mana calculations
        playable_pool = [c for c in hand_cards if "幸运币" not in c.name and c.id != "GAME_005"]
        if not playable_pool:
            return None

        if next_mana is None:
            next_mana = min(10, current_mana + 1)

        best_combo: Optional[Tuple[List[CardInfo], List[CardInfo]]] = None
        best_total_spent = -1
        best_floating = 999
        best_stats_deployed = -1

        # Generate candidate subsets for Turn N
        # Filter cards that cost <= current_mana
        n_candidates = [c for c in playable_pool if c.cost <= current_mana]
        if not n_candidates:
            return None

        valid_subsets_n: List[List[CardInfo]] = []
        for r in range(1, min(len(n_candidates) + 1, 4)):
            for comb in itertools.combinations(n_candidates, r):
                if sum(c.cost for c in comb) <= current_mana:
                    valid_subsets_n.append(list(comb))

        # Always include single largest affordable card if available
        for subset_n in valid_subsets_n:
            spent_n = sum(c.cost for c in subset_n)
            # Remaining hand for Turn N+1
            remaining = list(playable_pool)
            for c in subset_n:
                if c in remaining:
                    remaining.remove(c)

            # Find best play on Turn N+1 with remaining cards
            candidates_n1 = [c for c in remaining if c.cost <= next_mana]
            best_n1_subset: List[CardInfo] = []
            best_spent_n1 = 0

            # Try combinations on Turn N+1
            for r in range(1, min(len(candidates_n1) + 1, 4)):
                for comb in itertools.combinations(candidates_n1, r):
                    s = sum(c.cost for c in comb)
                    if s <= next_mana and s > best_spent_n1:
                        best_spent_n1 = s
                        best_n1_subset = list(comb)

            total_spent = spent_n + best_spent_n1
            total_avail = current_mana + next_mana
            floating = total_avail - total_spent

            # Secondary tie-breaker: total attack/health deployed
            stats = sum((c.attack or 0) + (c.health or 0) for c in subset_n + best_n1_subset)

            if (floating < best_floating) or (floating == best_floating and stats > best_stats_deployed):
                best_floating = floating
                best_total_spent = total_spent
                best_stats_deployed = stats
                best_combo = (subset_n, best_n1_subset)

        if not best_combo:
            return None

        curr_plays, next_plays = best_combo
        curr_spent = sum(c.cost for c in curr_plays)
        next_spent = sum(c.cost for c in next_plays)
        total_avail = current_mana + next_mana
        efficiency_pct = (best_total_spent / total_avail) * 100.0

        curr_names = " + ".join(f"【{c.name}】({c.cost}费)" for c in curr_plays)
        next_names = " + ".join(f"【{c.name}】({c.cost}费)" for c in next_plays) if next_plays else "依赖神抽/英雄技能"

        is_zero_waste = (best_floating == 0)
        if best_floating == 0:
            flow_tag = "💎【费率榨干 100%】"
            advice = (
                f"💎【双回合零空转打法】本回合打出 {curr_names} ({curr_spent}/{current_mana}费)；"
                f"下回合顺接 {next_names} ({next_spent}/{next_mana}费)！"
                f"连续两回合法力利用率 100%，完美榨干水晶，场面压迫力拉满！"
            )
        elif best_floating <= 1:
            flow_tag = "⚡【极速顺滑 90%+】"
            advice = (
                f"⚡【高法力效率组合】本回合打出 {curr_names}；下回合预期打出 {next_names}。"
                f"两回合总法力利用率达 **{efficiency_pct:.0f}%** (仅闲置 {best_floating} 费)，节奏极为紧凑。"
            )
        else:
            flow_tag = "💧【常规曲线】"
            advice = (
                f"💡【连续费用规划】本回合推荐打出 {curr_names}；"
                f"下回合衔接 {next_names} (两回合利用率 {efficiency_pct:.0f}%)。"
            )

        step_preview = f"T{current_mana}: {curr_names} ➔ T{next_mana}: {next_names} (损耗 {best_floating} 费)"

        return ManaEfficiencyPlan(
            current_turn_plays=curr_plays,
            next_turn_projected_plays=next_plays,
            current_spent=curr_spent,
            current_max=current_mana,
            next_spent=next_spent,
            next_max=next_mana,
            total_floating_mana=best_floating,
            efficiency_pct=efficiency_pct,
            advice_text=advice,
            is_zero_waste=is_zero_waste,
            flow_tag=flow_tag,
            step_preview=step_preview,
            flow_smoothness_score=efficiency_pct,
        )
