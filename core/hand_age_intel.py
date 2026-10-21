"""
HandAgeIntel: Opponent Hand Age & Mulligan Retention Intel Radar.
Tracks how long each card has stayed in the opponent's hand, correlates with Mulligan decisions,
and exposes "sleeping dragon" cards (high-cost sweepers or combo lethals held for multiple turns).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("HandAgeIntel")


class CardOriginType(str, Enum):
    MULLIGAN_KEPT = "MULLIGAN_KEPT"      # 起手保留
    MULLIGAN_REDRAW = "MULLIGAN_REDRAW"  # 起手换掉后抽到
    TURN_DRAW = "TURN_DRAW"              # 自然摸牌
    CREATED = "CREATED"                  # 发现/衍生牌


@dataclass
class TrackedHandCard:
    slot: int                            # 1-based index from left to right
    origin: CardOriginType
    turn_drawn: int
    hold_turns: int                      # Current turn - turn drawn
    is_dormant_threat: bool              # Held for >= 4 turns from mulligan/early turns
    predicted_category: str              # "AOE_SWEEPER", "BURST_FINISHER", "SITUATIONAL_REMOVAL", "REGULAR"
    prediction_label: str
    known_name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slot": self.slot,
            "origin": self.origin.value,
            "turn_drawn": self.turn_drawn,
            "hold_turns": self.hold_turns,
            "is_dormant_threat": self.is_dormant_threat,
            "predicted_category": self.predicted_category,
            "prediction_label": self.prediction_label,
            "known_name": self.known_name,
        }


@dataclass
class HandAgeIntelReport:
    current_turn: int
    total_hand_count: int
    mulligan_kept_count: int
    dormant_threat_count: int
    cards: List[TrackedHandCard] = field(default_factory=list)
    top_threat_summary: str = ""
    summary_markdown: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_turn": self.current_turn,
            "total_hand_count": self.total_hand_count,
            "mulligan_kept_count": self.mulligan_kept_count,
            "dormant_threat_count": self.dormant_threat_count,
            "cards": [c.to_dict() for c in self.cards],
            "top_threat_summary": self.top_threat_summary,
            "summary_markdown": self.summary_markdown,
        }


class HandAgeIntel:
    """Manages tracking of opponent hand card origins and turn age."""

    def __init__(self) -> None:
        self.cards: Dict[int, TrackedHandCard] = {}  # slot -> TrackedHandCard
        self.current_turn: int = 1

    def record_mulligan(self, hand_size: int, kept_slots: List[int]) -> None:
        """Initializes opponent's starting hand with kept and redrawn flags."""
        self.cards.clear()
        for slot in range(1, hand_size + 1):
            if slot in kept_slots:
                origin = CardOriginType.MULLIGAN_KEPT
            else:
                origin = CardOriginType.MULLIGAN_REDRAW

            self.cards[slot] = TrackedHandCard(
                slot=slot,
                origin=origin,
                turn_drawn=0,
                hold_turns=1,
                is_dormant_threat=False,
                predicted_category="REGULAR",
                prediction_label="起手牌",
            )

    def record_card_drawn(self, turn: int, is_created: bool = False, known_name: str = "") -> int:
        """Adds a newly drawn card to the right-most slot."""
        new_slot = len(self.cards) + 1
        origin = CardOriginType.CREATED if is_created else CardOriginType.TURN_DRAW
        self.cards[new_slot] = TrackedHandCard(
            slot=new_slot,
            origin=origin,
            turn_drawn=turn,
            hold_turns=0,
            is_dormant_threat=False,
            predicted_category="REGULAR",
            prediction_label="衍生卡" if is_created else "本回合抓牌",
            known_name=known_name,
        )
        return new_slot

    def record_card_played(self, slot: int) -> Optional[TrackedHandCard]:
        """Removes played card and shifts slots to the left."""
        if slot not in self.cards:
            if self.cards:
                slot = max(self.cards.keys())
            else:
                return None

        played = self.cards.pop(slot, None)
        # Shift remaining slots
        new_dict: Dict[int, TrackedHandCard] = {}
        curr_idx = 1
        for old_s in sorted(self.cards.keys()):
            card = self.cards[old_s]
            card.slot = curr_idx
            new_dict[curr_idx] = card
            curr_idx += 1
        self.cards = new_dict
        return played

    def update_turn(self, turn: int) -> HandAgeIntelReport:
        """Updates hold turns and evaluates sleeping threat cards."""
        self.current_turn = turn

        dormant_threats: List[TrackedHandCard] = []
        mulligan_kept_count = 0

        for slot, card in self.cards.items():
            card.hold_turns = max(0, self.current_turn - card.turn_drawn)

            if card.origin == CardOriginType.MULLIGAN_KEPT:
                mulligan_kept_count += 1
                if card.hold_turns >= 4:
                    card.is_dormant_threat = True
                    card.predicted_category = "AOE_SWEEPER"
                    card.prediction_label = f"起手保留已蓄力{card.hold_turns}回合 (极高危AOE/斩杀)"
                    dormant_threats.append(card)
                elif card.hold_turns >= 2:
                    card.prediction_label = f"起手保留({card.hold_turns}回合)"
            elif card.origin == CardOriginType.MULLIGAN_REDRAW:
                if card.hold_turns >= 5:
                    card.is_dormant_threat = True
                    card.predicted_category = "SITUATIONAL_REMOVAL"
                    card.prediction_label = f"调度抽到已沉睡{card.hold_turns}回合 (特定针对解牌)"
                    dormant_threats.append(card)
                else:
                    card.prediction_label = f"调度卡({card.hold_turns}回合)"
            elif card.origin == CardOriginType.CREATED:
                card.prediction_label = f"发现/衍生牌 (持有{card.hold_turns}回合)"
            else:
                card.prediction_label = f"T{card.turn_drawn}摸牌 (持有{card.hold_turns}回合)"

        sorted_cards = [self.cards[s] for s in sorted(self.cards.keys())]

        if dormant_threats:
            threat_slots = [f"#{c.slot}" for c in dormant_threats]
            top_threat = f"⚠️ 对手手牌 {', '.join(threat_slots)} 握持超 {dormant_threats[0].hold_turns} 回合未出，判定为高费绝杀/全场AOE！"
        else:
            top_threat = "对手手牌流通顺畅，暂无长时间积压的沉睡杀招。"

        md_lines = [
            f"**对手手牌心智雷达** (共 {len(sorted_cards)} 张手牌，起手保留 {mulligan_kept_count} 张):",
            f"• **沉睡高危卡**: {len(dormant_threats)} 张",
            f"• **态势洞察**: {top_threat}",
        ]
        for c in sorted_cards[:5]:
            badge = "🔥 [高危蓄力]" if c.is_dormant_threat else ""
            md_lines.append(f"  • 位置 #{c.slot}: {c.prediction_label} {badge}")

        return HandAgeIntelReport(
            current_turn=self.current_turn,
            total_hand_count=len(sorted_cards),
            mulligan_kept_count=mulligan_kept_count,
            dormant_threat_count=len(dormant_threats),
            cards=sorted_cards,
            top_threat_summary=top_threat,
            summary_markdown="\n".join(md_lines),
        )
