"""
PingProtector: Ping-Resistant Trading Engine for Hearthstone Arena.
Calculates post-combat residual minion health against classes with 1-damage ping hero powers
(Mage, Rogue, Druid, Demon Hunter, Death Knight) to prevent devastating free-trade tempo losses.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("PingProtector")


@dataclass
class PingProtectionAdvice:
    is_vulnerable: bool              # True if leaving a minion at 1 HP without Divine Shield
    penalty_score: float             # Negative score adjustment for the trade
    warning_text: str                # Guidance to display to the user
    suggested_alternative: str       # Alternative combat advice


class PingProtector:
    """Evaluates minion health residuals against 1-damage hero power ping classes."""

    PING_CLASSES = {
        "mage", "法师",
        "rogue", "潜行者", "盗贼",
        "druid", "德鲁伊",
        "demonhunter", "demon hunter", "恶魔猎手",
        "deathknight", "death knight", "死亡骑士",
    }

    @classmethod
    def is_ping_class(cls, opponent_class: str) -> bool:
        if not opponent_class:
            return False
        clean = opponent_class.lower().replace(" ", "").replace("_", "")
        return any(p in clean for p in cls.PING_CLASSES)

    @classmethod
    def evaluate_trade_residual(
        cls,
        attacker_name: str,
        attacker_atk: int,
        attacker_rem_hp: int,
        attacker_has_shield: bool,
        opponent_class: str,
    ) -> PingProtectionAdvice:
        """
        Assesses if a trade leaves a friendly minion dangerously exposed to hero power ping.
        """
        if not cls.is_ping_class(opponent_class):
            return PingProtectionAdvice(
                is_vulnerable=False,
                penalty_score=0.0,
                warning_text="",
                suggested_alternative="",
            )

        # If minion died in combat or has divine shield, ping doesn't apply
        if attacker_rem_hp <= 0 or attacker_has_shield:
            return PingProtectionAdvice(
                is_vulnerable=False,
                penalty_score=0.0,
                warning_text="",
                suggested_alternative="",
            )

        # Danger case: Survives with exactly 1 HP!
        if attacker_rem_hp == 1:
            # The higher the minion's attack, the bigger the tempo loss if pinged!
            # Losing a 1/1 to ping is normal; losing a 4/1 or 5/1 to a 2-mana hero power is game-losing!
            penalty = -15.0 - (attacker_atk * 5.0)
            warning = (
                f"⚠️【防补刀警报】{attacker_name} 交换后仅剩 1 点生命值！"
                f"下回合会被【{opponent_class}】英雄技能 (火冲/匕首/变脸/突袭) 0手牌消耗无损白吃！"
            )
            alt = "若有其他选择，优先选择保留 ≥ 2 血的随从交换，或将 1 血怪送入敌方高威胁随从换掉！"
            return PingProtectionAdvice(
                is_vulnerable=True,
                penalty_score=penalty,
                warning_text=warning,
                suggested_alternative=alt,
            )

        # Safe: 2+ HP
        return PingProtectionAdvice(
            is_vulnerable=False,
            penalty_score=5.0,  # Positive incentive for retaining 2+ HP
            warning_text=f"🛡️ [防补刀安全] 交换后剩余 {attacker_rem_hp} 血，成功避开敌方技能斩杀线！",
            suggested_alternative="",
        )
