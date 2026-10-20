"""
Unit tests for MulliganHandReader.
"""

from core.mulligan_hand_reader import MulliganHandReader, MulliganHandAnalysis, CardOrigin
from core.hand_tracker import OpponentHandCard


def test_mulligan_kept_bomb_detection():
    # Opponent kept slot 1 card from mulligan, and holds it till turn 6
    cards = [
        OpponentHandCard(slot=1, entity_id=101, turn_added=1, turns_held=5, is_mulligan_keep=True),
        OpponentHandCard(slot=2, entity_id=102, turn_added=4, turns_held=2, is_mulligan_keep=False),
    ]

    analysis: MulliganHandAnalysis = MulliganHandReader.analyze_opponent_hand(
        cards=cards,
        current_turn=6,
        opponent_class="MAGE",
    )

    assert analysis.bombs_in_hand_estimate == 1
    assert analysis.mulligan_kept_count == 1
    assert "大核" in analysis.strategic_directive or "大解" in analysis.strategic_directive
    assert analysis.slot_deductions[0].danger_level == "CRITICAL"


def test_early_mulligan_tempo():
    # Turn 2: Opponent holds mulligan keeps (1-3 drop tempo)
    cards = [
        OpponentHandCard(slot=1, entity_id=101, turn_added=1, turns_held=1, is_mulligan_keep=True),
        OpponentHandCard(slot=2, entity_id=102, turn_added=1, turns_held=1, is_mulligan_keep=True),
    ]

    analysis: MulliganHandAnalysis = MulliganHandReader.analyze_opponent_hand(
        cards=cards,
        current_turn=2,
        opponent_class="PALADIN",
    )

    assert analysis.bombs_in_hand_estimate == 0
    assert analysis.mulligan_kept_count == 2
    assert analysis.slot_deductions[0].danger_level == "LOW"
