"""
MonteCarloVarEngine: High-Performance Monte Carlo RNG Simulation & Value-at-Risk (VaR) Engine.
Simulates 10,000 random combat/damage iterations to compute empirical distribution:
- P10 (VaR Floor / Conservative worst-case 10%)
- P50 (Median expectation)
- P90 (Ceiling / High-roll 90%)
- Exact Board Clear & Lethal Probabilities
- ASCII Empirical Density Histogram
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("MonteCarloVar")


@dataclass
class TargetState:
    name: str
    hp: int
    is_hero: bool = False
    divine_shield: bool = False


@dataclass
class MonteCarloVarReport:
    action_name: str
    simulations_run: int
    p10_kills: int             # Worst 10% floor on total minions killed
    p50_kills: int             # Median kills
    p90_kills: int             # Best 90% ceiling kills
    clear_probability_pct: float # Probability all enemy minions die
    lethal_probability_pct: float # Probability enemy hero dies
    expected_face_damage: float
    expected_board_damage: float
    risk_profile: str          # "LOW_RISK_CERTAINTY", "CALCULATED_GAMBLE", "HIGH_RISK_DESPERATION"
    risk_badge: str
    ascii_histogram: str
    strategic_verdict: str


class MonteCarloVarEngine:
    """
    Simulates random damage dispersal (Arcane Missiles, Mad Bomber, Avenging Wrath, Lightning Storm)
    across enemy targets.
    """

    @classmethod
    def simulate_random_missiles(
        cls,
        action_name: str,
        missile_count: int,
        damage_per_missile: int,
        enemy_minions: List[Dict[str, Any]],  # [{"name": str, "hp": int, "divine_shield": bool}]
        enemy_hero_hp: int,
        can_hit_friendly: bool = False,
        friendly_minions: Optional[List[Dict[str, Any]]] = None,
        iterations: int = 10000,
    ) -> MonteCarloVarReport:
        """
        Executes Monte Carlo sampling of random missile impacts.
        """
        if iterations <= 0:
            iterations = 10000

        total_minions = len(enemy_minions)
        kill_counts = [0] * (total_minions + 1)
        full_clears = 0
        lethals = 0
        total_face_dmg = 0
        total_board_dmg = 0

        # Run vectorized/fast simulation loops
        for _ in range(iterations):
            # Clone targets for this trial
            minion_hps = [max(1, m.get("hp", 1)) for m in enemy_minions]
            minion_shields = [bool(m.get("divine_shield", False)) for m in enemy_minions]
            hero_hp = enemy_hero_hp

            # Missiles fired sequentially
            for _m in range(missile_count):
                # Valid alive targets
                alive_minion_indices = [i for i, hp in enumerate(minion_hps) if hp > 0]
                total_alive_targets = len(alive_minion_indices) + 1  # +1 for enemy hero

                choice = random.randint(0, total_alive_targets - 1)
                if choice < len(alive_minion_indices):
                    target_idx = alive_minion_indices[choice]
                    if minion_shields[target_idx]:
                        minion_shields[target_idx] = False
                    else:
                        minion_hps[target_idx] -= damage_per_missile
                        total_board_dmg += damage_per_missile
                else:
                    hero_hp -= damage_per_missile
                    total_face_dmg += damage_per_missile

            # Evaluate end of trial
            killed = sum(1 for hp in minion_hps if hp <= 0)
            kill_counts[killed] += 1
            if total_minions > 0 and killed == total_minions:
                full_clears += 1
            if hero_hp <= 0:
                lethals += 1

        # Calculate Percentiles (P10, P50, P90)
        # Cumulative distribution
        cum = 0
        p10 = 0
        p50 = 0
        p90 = total_minions
        p10_found = False
        p50_found = False

        for k in range(total_minions + 1):
            cum += kill_counts[k]
            cum_pct = cum / iterations
            if not p10_found and cum_pct >= 0.10:
                p10 = k
                p10_found = True
            if not p50_found and cum_pct >= 0.50:
                p50 = k
                p50_found = True
            if cum_pct >= 0.90:
                p90 = k
                break

        clear_pct = round((full_clears / iterations) * 100.0, 1)
        lethal_pct = round((lethals / iterations) * 100.0, 1)
        avg_face = round(total_face_dmg / iterations, 1)
        avg_board = round(total_board_dmg / iterations, 1)

        # Risk Classification
        if clear_pct >= 75.0 or lethal_pct >= 75.0:
            profile = "LOW_RISK_CERTAINTY"
            badge = "🛡️ 高概率确定收割 (P50 达成率高)"
            verdict = f"期望清场概率高达 {clear_pct}%，下限可杀 {p10} 怪，极大概率稳定斩杀/清场！"
        elif clear_pct >= 40.0 or lethal_pct >= 40.0:
            profile = "CALCULATED_GAMBLE"
            badge = "⚖️ 均势博弈·期望可观"
            verdict = f"清场率 {clear_pct}% (P10保底击杀{p10}怪 / P50击杀{p50}怪 / P90击杀{p90}怪)，值得投资。"
        else:
            profile = "HIGH_RISK_DESPERATION"
            badge = "🔥 孤注一掷·绝境搏命"
            verdict = f"全清概率仅 {clear_pct}%，仅在局势严重落后无解时作为绝命拼脸手段！"

        # Generate ASCII Histogram
        hist_parts = []
        max_cnt = max(kill_counts) if max(kill_counts) > 0 else 1
        for k in range(total_minions + 1):
            bar_len = int((kill_counts[k] / max_cnt) * 8)
            bar_str = "■" * bar_len + "□" * (8 - bar_len)
            pct = round((kill_counts[k] / iterations) * 100.0)
            hist_parts.append(f"杀{k}怪: [{bar_str}] {pct}%")
        ascii_hist = " | ".join(hist_parts)

        return MonteCarloVarReport(
            action_name=action_name,
            simulations_run=iterations,
            p10_kills=p10,
            p50_kills=p50,
            p90_kills=p90,
            clear_probability_pct=clear_pct,
            lethal_probability_pct=lethal_pct,
            expected_face_damage=avg_face,
            expected_board_damage=avg_board,
            risk_profile=profile,
            risk_badge=badge,
            ascii_histogram=ascii_hist,
            strategic_verdict=verdict,
        )

    @classmethod
    def simulate_aoe_damage_roll(
        cls,
        spell_name: str,
        min_dmg: int,
        max_dmg: int,
        enemy_minions: List[Dict[str, Any]],
        iterations: int = 10000,
    ) -> MonteCarloVarReport:
        """
        Simulates variable AOE damage (e.g., Lightning Storm: 2-3 damage to all minions).
        """
        total_minions = len(enemy_minions)
        kill_counts = [0] * (total_minions + 1)
        full_clears = 0

        for _ in range(iterations):
            killed = 0
            for m in enemy_minions:
                hp = m.get("hp", 1)
                shield = m.get("divine_shield", False)
                dmg_roll = random.randint(min_dmg, max_dmg)
                if not shield and dmg_roll >= hp:
                    killed += 1
            kill_counts[killed] += 1
            if total_minions > 0 and killed == total_minions:
                full_clears += 1

        clear_pct = round((full_clears / iterations) * 100.0, 1)

        # Percentiles
        cum = 0
        p10, p50, p90 = 0, 0, total_minions
        p10_f, p50_f = False, False
        for k in range(total_minions + 1):
            cum += kill_counts[k]
            cum_pct = cum / iterations
            if not p10_f and cum_pct >= 0.10:
                p10 = k
                p10_f = True
            if not p50_f and cum_pct >= 0.50:
                p50 = k
                p50_f = True
            if cum_pct >= 0.90:
                p90 = k
                break

        badge = "🎲 AOE点伤浮动期望"
        verdict = f"{spell_name} (伤害 {min_dmg}~{max_dmg})：全清率 {clear_pct}%，P10保底清 {p10} 怪，中位数 P50 清 {p50} 怪。"

        # ASCII
        hist_parts = []
        max_cnt = max(kill_counts) if max(kill_counts) > 0 else 1
        for k in range(total_minions + 1):
            bar_len = int((kill_counts[k] / max_cnt) * 6)
            pct = round((kill_counts[k] / iterations) * 100.0)
            hist_parts.append(f"杀{k}: {'■' * bar_len} {pct}%")
        ascii_hist = " | ".join(hist_parts)

        return MonteCarloVarReport(
            action_name=spell_name,
            simulations_run=iterations,
            p10_kills=p10,
            p50_kills=p50,
            p90_kills=p90,
            clear_probability_pct=clear_pct,
            lethal_probability_pct=0.0,
            expected_face_damage=0.0,
            expected_board_damage=round((min_dmg + max_dmg) / 2.0 * total_minions, 1),
            risk_profile="CALCULATED_GAMBLE" if clear_pct >= 50 else "HIGH_RISK_DESPERATION",
            risk_badge=badge,
            ascii_histogram=ascii_hist,
            strategic_verdict=verdict,
        )
