"""
Unit tests for HandTracker.
"""

import pytest
from core.hand_tracker import HandTracker


def test_hand_tracker_lifecycle():
    tracker = HandTracker()

    # Opponent went second with 4 cards (including Coin)
    tracker.init_opening_hand(card_count=4, has_coin=True)
    assert len(tracker.cards) == 4

    # Slot 4 is the coin
    assert tracker.cards[3].is_coin is True
    assert tracker.cards[0].is_mulligan_keep is True

    # Advance to turn 5
    tracker.set_turn(5)
    assert tracker.cards[0].turns_held == 4

    # Opponent generates a card via discovery
    created_card = tracker.record_card_drawn(creator="暗影视界")
    assert len(tracker.cards) == 5
    assert created_card.creator_card == "暗影视界"

    # Opponent plays the Coin
    played = tracker.record_card_played(slot=4)
    assert played is not None
    assert played.is_coin is True
    assert len(tracker.cards) == 4

    summary = tracker.get_summary()
    assert summary["total_count"] == 4
    assert summary["created_count"] == 1
    assert summary["has_coin"] is False

    display = tracker.get_display_text()
    assert "敌方手牌: 4 张" in display
    assert "暗影视界" in display


def test_hand_tracker_threat_warnings():
    tracker = HandTracker()
    tracker.init_opening_hand(card_count=3, has_coin=False)
    tracker.set_turn(6)  # Held for 5 turns

    assert tracker.has_long_held_cards(min_turns=4) is True
    warnings = tracker.get_threat_warnings()
    assert len(warnings) > 0
    assert "极大概率是关键高费大解" in warnings[0]
