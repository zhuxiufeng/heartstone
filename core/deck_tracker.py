"""
DeckTracker: Tracks 30-card draft deck, played cards, and remaining deck draw probabilities.
Zero memory injection: Relies entirely on draft picks and log events.
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .card_db import CardDatabase, CardInfo

logger = logging.getLogger("DeckTracker")


@dataclass
class DeckStats:
    total_remaining: int
    minion_count: int
    spell_count: int
    weapon_count: int
    draw_odds_minion: float
    draw_odds_spell: float
    draw_odds_weapon: float
    mana_distribution: Dict[int, int]  # Cost -> count remaining
    remaining_cards: List[Tuple[CardInfo, int]]  # (CardInfo, count)


class DeckTracker:
    """Tracks initial 30-card draft deck, cards played/drawn, and computes deck draw probabilities."""

    def __init__(self, card_db: Optional[CardDatabase] = None) -> None:
        self.card_db = card_db or CardDatabase.get_instance()
        self.initial_deck: List[CardInfo] = []
        self.played_card_ids: List[str] = []
        self.drawn_card_ids: List[str] = []

    def set_draft_deck(self, cards: List[CardInfo]) -> None:
        """Initialize tracker with full draft deck."""
        self.initial_deck = list(cards)
        self.played_card_ids.clear()
        self.drawn_card_ids.clear()
        logger.info(f"Initialized deck tracker with {len(cards)} draft cards.")

    def add_draft_card(self, card: CardInfo) -> None:
        """Add a card chosen during draft."""
        self.initial_deck.append(card)

    def record_card_played(self, card_id: str) -> None:
        """Record a card played by the player."""
        self.played_card_ids.append(card_id)

    def record_card_drawn(self, card_id: str) -> None:
        """Record a card drawn into hand."""
        self.drawn_card_ids.append(card_id)

    def reset_game(self) -> None:
        """Reset match tracking while preserving the 30-card draft deck."""
        self.played_card_ids.clear()
        self.drawn_card_ids.clear()
        logger.info("Match state reset in DeckTracker.")

    def get_remaining_cards(self) -> List[CardInfo]:
        """Calculates cards remaining in the deck (initial_deck minus drawn/played)."""
        # Count original deck
        deck_counter = Counter(c.id for c in self.initial_deck)
        # Deduct drawn cards
        for cid in self.drawn_card_ids:
            if deck_counter[cid] > 0:
                deck_counter[cid] -= 1

        remaining: List[CardInfo] = []
        for card in self.initial_deck:
            if deck_counter[card.id] > 0:
                remaining.append(card)
                deck_counter[card.id] -= 1
        return remaining

    def get_stats(self) -> DeckStats:
        """Calculates detailed stats and draw probabilities."""
        remaining = self.get_remaining_cards()
        total = len(remaining)
        if total == 0:
            return DeckStats(
                total_remaining=0,
                minion_count=0,
                spell_count=0,
                weapon_count=0,
                draw_odds_minion=0.0,
                draw_odds_spell=0.0,
                draw_odds_weapon=0.0,
                mana_distribution={},
                remaining_cards=[],
            )

        minions = sum(1 for c in remaining if getattr(c, "card_type", getattr(c, "type", "")).upper() == "MINION")
        spells = sum(1 for c in remaining if getattr(c, "card_type", getattr(c, "type", "")).upper() == "SPELL")
        weapons = sum(1 for c in remaining if getattr(c, "card_type", getattr(c, "type", "")).upper() == "WEAPON")

        mana_dist: Dict[int, int] = Counter(min(c.cost, 7) for c in remaining)

        # Unique card deduplication with counts
        seen: Dict[str, Tuple[CardInfo, int]] = {}
        for c in remaining:
            if c.id in seen:
                seen[c.id] = (seen[c.id][0], seen[c.id][1] + 1)
            else:
                seen[c.id] = (c, 1)

        sorted_unique = sorted(seen.values(), key=lambda pair: (pair[0].cost, pair[0].name))

        return DeckStats(
            total_remaining=total,
            minion_count=minions,
            spell_count=spells,
            weapon_count=weapons,
            draw_odds_minion=round(minions / total * 100, 1),
            draw_odds_spell=round(spells / total * 100, 1),
            draw_odds_weapon=round(weapons / total * 100, 1),
            mana_distribution=dict(mana_dist),
            remaining_cards=sorted_unique,
        )

    def probability_of_drawing(self, card_name: str) -> float:
        """Calculate the probability of drawing card_name next turn."""
        remaining = self.get_remaining_cards()
        if not remaining:
            return 0.0
        matching = sum(1 for c in remaining if card_name.lower() in c.name.lower())
        return round(matching / len(remaining) * 100, 1)
