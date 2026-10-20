"""
CoinOptimizer: Strategic planner for the Coin in Hearthstone Arena.
Calculates seamless mana curves for player going second to close the 45% vs 55% win rate disparity.
Eliminates typical misplays like coining Turn 1 without a follow-up 2-drop.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

from .card_db import CardInfo

logger = logging.getLogger("CoinOptimizer")


@dataclass
class CoinStrategy:
    recommended_coin_turn: int      # Which turn to use Coin (1, 2, 3, etc.)
    target_card_name: str           # Card to accelerate with the Coin
    curve_pattern: str              # Projected sequence e.g. "T2跳3 -> T3顺出3 -> T4拍4"
    advice: str                     # Clear user guidance
    should_coin_now: bool           # True if current turn is the prime moment
    waste_warning: bool             # True if coining right now will cause subsequent curve drought


class CoinOptimizer:
    """Evaluates hand cards and determines the single highest-winrate moment to spend the Coin."""

    @staticmethod
    def calculate_strategy(
        hand_cards: List[CardInfo],
        current_turn: int,
        has_coin: bool,
    ) -> Optional[CoinStrategy]:
        """
        Analyzes hand mana curve to find the optimal Coin acceleration turn.
        """
        if not has_coin:
            return None

        # Filter minions and active playable cards
        playable = [c for c in hand_cards if "幸运币" not in c.name and c.id != "GAME_005"]
        if not playable:
            return CoinStrategy(
                recommended_coin_turn=current_turn,
                target_card_name="暂无随从",
                curve_pattern="留币等待",
                advice="当前手牌无有效随从，保留幸运币防范中后期断节奏或配合战吼/法术。",
                should_coin_now=False,
                waste_warning=False,
            )

        costs = [c.cost for c in playable]
        cost_counts = {}
        for c in costs:
            cost_counts[c] = cost_counts.get(c, 0) + 1

        # Scenario 1: Double 3-drops, NO 2-drop (Classic Arena Dilemma)
        # Ideal: T1 pass -> T2 Coin into 3-drop -> T3 natural 3-drop -> T4 4-drop
        if cost_counts.get(3, 0) >= 2 and cost_counts.get(2, 0) == 0:
            best_3 = next((c for c in playable if c.cost == 3), playable[0])
            should_now = current_turn == 2
            warning = current_turn == 1  # Coining T1 into a 2-drop you don't have is fatal
            advice = (
                f"🪙【硬币规划】当前有两张 3 费无 2 费！最优时机：第 2 回合跳币拍【{best_3.name}】，"
                f"第 3 回合顺出第二张 3 费！严禁第 1 回合乱交币导致第 2 回合空过！"
            )
            return CoinStrategy(
                recommended_coin_turn=2,
                target_card_name=best_3.name,
                curve_pattern="T2跳3 -> T3顺出3 -> T4展开",
                advice=advice,
                should_coin_now=should_now,
                waste_warning=warning,
            )

        # Scenario 2: Double 2-drops (Fast Tempo Acceleration)
        # Ideal: T1 Coin into 2-drop -> T2 natural 2-drop -> T3 3-drop
        if cost_counts.get(2, 0) >= 2 and current_turn == 1:
            best_2 = next((c for c in playable if c.cost == 2), playable[0])
            advice = (
                f"⚡【硬币时机成熟】手牌拥有两张 2 费随从！推荐【第 1 回合立即跳币】下【{best_2.name}】，"
                f"第 2 回合顺出第二张 2 费，实现 1-2 回合双倍场面碾压！"
            )
            return CoinStrategy(
                recommended_coin_turn=1,
                target_card_name=best_2.name,
                curve_pattern="T1跳2 -> T2顺出2 -> T3压制",
                advice=advice,
                should_coin_now=True,
                waste_warning=False,
            )

        # Scenario 3: Double 4-drops, has a 2-drop
        # Ideal: T1 pass -> T2 play 2-drop -> T3 Coin into 4-drop -> T4 natural 4-drop
        if cost_counts.get(4, 0) >= 2 and cost_counts.get(2, 0) >= 1:
            best_4 = next((c for c in playable if c.cost == 4), playable[0])
            should_now = current_turn == 3
            advice = (
                f"🛡️【硬币中盘提速】手牌拥有强力 4 费核心！推荐第 2 回合正常下 2 费，"
                f"【第 3 回合跳币拍出 4 费【{best_4.name}】】，第 4 回合继续下 4 费夺取绝对场控！"
            )
            return CoinStrategy(
                recommended_coin_turn=3,
                target_card_name=best_4.name,
                curve_pattern="T2下2 -> T3跳4 -> T4顺拍4",
                advice=advice,
                should_coin_now=should_now,
                waste_warning=current_turn < 3,
            )

        # Scenario 4: Turn 1 with single 2-drop and no 1-drop
        # If we have 1-drop -> T1 play 1-drop; if no 1-drop and 1x 2-drop and 1x 3-drop
        # Coining 2-drop on T1 is OK ONLY if T2 we have another 2-drop or hero power is good
        if current_turn == 1:
            has_1 = cost_counts.get(1, 0) > 0
            has_2 = cost_counts.get(2, 0) > 0
            if has_1:
                return CoinStrategy(
                    recommended_coin_turn=2,
                    target_card_name="保留给中盘",
                    curve_pattern="T1下1费 -> 留币提速",
                    advice="第 1 回合正常打出 1 费随从，硬币保留在 3 费或 4 费跳大怪抢节奏。",
                    should_coin_now=False,
                    waste_warning=True,
                )
            if has_2 and cost_counts.get(2, 0) == 1 and cost_counts.get(3, 0) == 0:
                return CoinStrategy(
                    recommended_coin_turn=2,
                    target_card_name="不建议T1跳币",
                    curve_pattern="T1空过 -> T2顺拍2",
                    advice="⚠️ 仅有 1 张 2 费且无 3 费！严禁第 1 回合跳币，否则第 2 回合空过直接崩盘！留到第 2 回合正常下怪。",
                    should_coin_now=False,
                    waste_warning=True,
                )

        # General greedy acceleration
        target = min(playable, key=lambda c: abs(c.cost - (current_turn + 1)))
        should_now = target.cost == current_turn + 1
        return CoinStrategy(
            recommended_coin_turn=target.cost - 1,
            target_card_name=target.name,
            curve_pattern=f"跳费出 {target.cost} 费【{target.name}】",
            advice=f"建议在当前或下回合跳币拍出 {target.cost} 费【{target.name}】，抢先占据场面主动权。" if should_now else "保留硬币，等待关键高费随从或战吼配合。",
            should_coin_now=should_now,
            waste_warning=False,
        )
