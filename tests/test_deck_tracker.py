"""
Unit tests for DeckTracker.
"""

import pytest
from core.card_db import CardInfo
from core.deck_tracker import DeckTracker, DeckStats


def test_deck_tracker_stats():
    tracker = DeckTracker()

    c_minion = CardInfo(id="M1", name="小软", cost=2, card_type="MINION", card_class="NEUTRAL", rarity="COMMON")
    c_spell = CardInfo(id="S1", name="火球", cost=4, card_type="SPELL", card_class="MAGE", rarity="COMMON")
    c_weapon = CardInfo(id="W1", name="战斧", cost=2, card_type="WEAPON", card_class="WARRIOR", rarity="COMMON")

    # 10 minions, 6 spells, 4 weapons = 20 cards
    deck = [c_minion] * 10 + [c_spell] * 6 + [c_weapon] * 4
    tracker.set_draft_deck(deck)

    stats: DeckStats = tracker.get_stats()
    assert stats.total_remaining == 20
    assert stats.minion_count == 10
    assert stats.spell_count == 6
    assert stats.weapon_count == 4
    assert stats.draw_odds_minion == 50.0
    assert stats.draw_odds_spell == 30.0
    assert stats.draw_odds_weapon == 20.0
    assert tracker.probability_of_drawing("火球") == 30.0

    # Draw 2 spells and 1 minion
    tracker.record_card_drawn("S1")
    tracker.record_card_drawn("S1")
    tracker.record_card_drawn("M1")

    stats2 = tracker.get_stats()
    assert stats2.total_remaining == 17
    assert stats2.spell_count == 4
    assert stats2.minion_count == 9

    # Reset game preserves draft deck
    tracker.reset_game()
    stats_reset = tracker.get_stats()
    assert stats_reset.total_remaining == 20
