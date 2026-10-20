"""
WinRateEstimator: Multi-Factor Probabilistic Game Win Rate (Win%) Estimator.
Calibrates competitive arena win probabilities across multi-dimensional state vectors:
1. Health Differential & Lethal Clock
2. Board Attack & Minion Presence
3. Card Advantage & Hand Attrition
4. Immediate & Two-Turn Lethal Thresholds
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any, Dict

logger = logging.getLogger("WinRateEstimator")


@dataclass
class WinRateReport:
    winrate_pct: float             # e.g. 74.2 (%)
    win_tier: str                  # "DOMINANT (胜券在握)", "FAVORED (优势)", "BALANCED (均势)", "UNDERDOG (劣势)", "CRITICAL (绝境)"
    confidence_level: str          # "HIGH", "MEDIUM"
    key_advantage_factor: str      # e.g. "场面攻击力压制 (+12点)"


class WinRateEstimator:
    """Estimates concrete game-win percentage from strategic board vectors."""

    @classmethod
    def calculate_winrate(
        cls,
        friendly_hp: int,
        enemy_hp: int,
        friendly_board_atk: int,
        enemy_board_atk: int,
        friendly_minion_count: int,
        enemy_minion_count: int,
        friendly_hand_count: int,
        enemy_hand_count: int,
        current_turn: int = 5,
        has_immediate_lethal: bool = False,
        has_two_turn_lethal: bool = False,
    ) -> WinRateReport:
        # Immediate Lethal shortcut
        if has_immediate_lethal:
            return WinRateReport(
                winrate_pct=100.0,
                win_tier="DOMINANT (胜券在握)",
                confidence_level="HIGH",
                key_advantage_factor="本回合已达成绝杀！",
            )

        if friendly_hp <= 0:
            return WinRateReport(
                winrate_pct=0.0,
                win_tier="CRITICAL (绝境)",
                confidence_level="HIGH",
                key_advantage_factor="我方血量已归零",
            )

        # Multi-factor logistic regression logit
        hp_delta = friendly_hp - enemy_hp
        atk_delta = friendly_board_atk - enemy_board_atk
        board_delta = friendly_minion_count - enemy_minion_count
        hand_delta = friendly_hand_count - enemy_hand_count

        logit = 0.0
        logit += hp_delta * 0.075
        logit += atk_delta * 0.160
        logit += board_delta * 0.280
        logit += hand_delta * 0.320

        # Late-game urgency scaling
        if current_turn >= 8:
            logit += atk_delta * 0.08  # Board attack matters much more late game

        if has_two_turn_lethal:
            logit += 1.85

        # Critical danger penalties
        if friendly_hp <= 8 and enemy_board_atk >= friendly_hp:
            logit -= 2.50

        # Sigmoid probability
        try:
            prob = 1.0 / (1.0 + math.exp(-logit))
        except OverflowError:
            prob = 0.0 if logit < 0 else 1.0

        winrate = round(prob * 100.0, 1)
        winrate = max(1.0, min(99.0, winrate))

        # Classify Tier
        if winrate >= 80.0:
            tier = "DOMINANT (胜券在握)"
        elif winrate >= 62.0:
            tier = "FAVORED (显著优势)"
        elif winrate >= 45.0:
            tier = "BALANCED (均势博弈)"
        elif winrate >= 25.0:
            tier = "UNDERDOG (局势落后)"
        else:
            tier = "CRITICAL (绝境濒危)"

        # Determine dominant driver
        if atk_delta >= 4:
            driver = f"场面场攻压制 (+{atk_delta}点)"
        elif hp_delta >= 10:
            driver = f"血量大幅领先 (+{hp_delta}血)"
        elif hand_delta >= 2:
            driver = f"手牌资源富余 (+{hand_delta}张)"
        elif atk_delta <= -4:
            driver = f"场面严重落后 (少{abs(atk_delta)}场攻)"
        else:
            driver = "均势拉锯状态"

        return WinRateReport(
            winrate_pct=winrate,
            win_tier=tier,
            confidence_level="HIGH" if abs(winrate - 50.0) >= 20.0 else "MEDIUM",
            key_advantage_factor=driver,
        )
