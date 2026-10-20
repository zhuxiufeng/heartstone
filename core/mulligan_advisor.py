"""
MulliganAdvisor: Evaluates opening hand cards and recommends KEEP or MULLIGAN
based on mana curve, initiative (first/second player with Coin), and opponent archetype.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from .card_db import CardDatabase, CardInfo

logger = logging.getLogger("MulliganAdvisor")


@dataclass
class MulliganChoice:
    card: CardInfo
    action: str         # "KEEP" (留牌) or "REPLACE" (换牌)
    priority: int       # 1 (Highest priority to keep) to 5 (Definite replace)
    reason: str         # Detailed tactical rationale


@dataclass
class MulliganAdvice:
    choices: List[MulliganChoice]
    game_plan: str      # General opening game strategy
    has_coin: bool      # True if player goes second


class MulliganAdvisor:
    """Calculates optimal opening mulligan decisions for arena games."""

    # Special arena cards worth keeping even at 3-4 mana
    HIGH_PRIORITY_KEEPS = {
        "CS2_013",  # 野性成长 (Wild Growth)
        "CS2_017",  # 变形术 (against heavy buffs, if coin)
        "EX1_277",  # 奥术飞弹
        "CS2_004",  # 真言术：盾
        "CS2_188",  # 叫嚣的矮人
        "CS2_065",  # 恐狼前锋
    }

    def __init__(self, card_db: Optional[CardDatabase] = None) -> None:
        self.card_db = card_db or CardDatabase.get_instance()

    def evaluate_mulligan(
        self,
        hand_cards: List[CardInfo],
        hero_class: str,
        opponent_class: str,
        has_coin: bool,
    ) -> MulliganAdvice:
        """
        Calculates keep/replace decision for each offered starting card.
        """
        choices: List[MulliganChoice] = []
        keep_1_drop = False
        keep_2_drop = False
        keep_3_drop = False

        # Sort candidate cards by cost to assess curve smoothly
        sorted_indices = sorted(range(len(hand_cards)), key=lambda i: hand_cards[i].cost)

        # Temporary dict to track verdicts by index
        verdicts: Dict[int, MulliganChoice] = {}

        for idx in sorted_indices:
            card = hand_cards[idx]
            cost = card.cost
            name = card.name
            c_type = getattr(card, "card_type", getattr(card, "type", "MINION")).upper()

            # Rule 1: Always keep 1-drops (minions)
            if cost == 1 and c_type == "MINION":
                keep_1_drop = True
                verdicts[idx] = MulliganChoice(
                    card=card,
                    action="KEEP",
                    priority=1,
                    reason="1费优质节奏随从，必留以确立前期场面优势。"
                )
                continue

            # Rule 2: Keep 2-drops (minions or early premium weapons)
            if cost == 2:
                if not keep_2_drop or has_coin:
                    keep_2_drop = True
                    verdicts[idx] = MulliganChoice(
                        card=card,
                        action="KEEP",
                        priority=1,
                        reason="核心2费顺滑曲线，确保第2回合不断节奏。"
                    )
                else:
                    # Already kept a 2-drop and going first without coin: replace duplicate if expensive
                    verdicts[idx] = MulliganChoice(
                        card=card,
                        action="REPLACE",
                        priority=3,
                        reason="已有更佳2费节奏，换牌寻找1费或3费卡牌。"
                    )
                continue

            # Rule 3: 3-drops
            if cost == 3:
                # With coin, or if we already have a 1 or 2 drop, keep a 3-drop for curve
                if has_coin or keep_2_drop or keep_1_drop:
                    if not keep_3_drop:
                        keep_3_drop = True
                        verdicts[idx] = MulliganChoice(
                            card=card,
                            action="KEEP",
                            priority=2,
                            reason="已有前期底牌或手握幸运币，可留作3费压制节奏。"
                        )
                    else:
                        verdicts[idx] = MulliganChoice(
                            card=card,
                            action="REPLACE",
                            priority=4,
                            reason="曲线臃肿，已有3费动作，换牌寻找更低费卡牌。"
                        )
                else:
                    verdicts[idx] = MulliganChoice(
                        card=card,
                        action="REPLACE",
                        priority=3,
                        reason="先手且无2费启动牌，贪3费容易空过导致场面崩盘，建议换牌。"
                    )
                continue

            # Rule 4: 4-drops
            if cost == 4:
                # Only keep with Coin AND having a 2-drop
                if has_coin and (keep_2_drop or keep_1_drop):
                    verdicts[idx] = MulliganChoice(
                        card=card,
                        action="KEEP",
                        priority=3,
                        reason="后手配合幸运币可在第3回合跳费拍出，完成战力跃升。"
                    )
                else:
                    verdicts[idx] = MulliganChoice(
                        card=card,
                        action="REPLACE",
                        priority=4,
                        reason="高费卡牌开局易卡手，建议换取1~2费随从。"
                    )
                continue

            # Rule 5: 5+ drops or expensive spells: Definite replace
            verdicts[idx] = MulliganChoice(
                card=card,
                action="REPLACE",
                priority=5,
                reason=f"{cost}费属于中后期战力，起手全力找1/2费曲线。"
            )

        # Restore original order
        for idx in range(len(hand_cards)):
            choices.append(verdicts[idx])

        # Generate overarching game plan
        opp_fast_classes = {"HUNTER", "ROGUE", "DEMONHUNTER", "PALADIN"}
        is_fast_opp = opponent_class.upper() in opp_fast_classes

        if has_coin:
            plan = f"【后手策略】握有幸运币。对阵{opponent_class}，若手握跳费节点可精准打出 2-2-4 或 1-3-3 节奏反客为主。"
        else:
            plan = f"【先手策略】必须确立先发优势。全力寻找 1-2-3 顺畅随从曲线，尽全力防范{opponent_class}的前期争夺。"

        if is_fast_opp:
            plan += " 对手节奏偏快，前期切忌贪牌，解场优先保血量。"

        return MulliganAdvice(choices=choices, game_plan=plan, has_coin=has_coin)
