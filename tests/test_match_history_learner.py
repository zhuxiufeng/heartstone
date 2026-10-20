"""
Unit tests for MatchHistoryLearner.
"""

from pathlib import Path
from core.match_history_learner import MatchHistoryLearner, MatchRecord


def test_match_history_recording_and_stats(tmp_path: Path):
    test_file = tmp_path / "test_history.json"
    learner = MatchHistoryLearner(history_file=test_file)

    learner.record_match(
        result="WIN",
        friendly_hero="DEATHKNIGHT",
        opponent_hero="MAGE",
        turn_count=8,
        deck_card_ids=["OP_CARD_1", "OP_CARD_2"],
    )
    learner.record_match(
        result="LOSS",
        friendly_hero="DEATHKNIGHT",
        opponent_hero="HUNTER",
        turn_count=5,
        deck_card_ids=["BAD_CARD_1"],
    )

    stats = learner.get_summary_stats()
    assert stats["total_matches"] == 2
    assert stats["wins"] == 1
    assert stats["losses"] == 1
    assert stats["win_rate"] == 50.0


def test_adaptive_card_winrate_adjustment(tmp_path: Path):
    test_file = tmp_path / "test_history_cards.json"
    learner = MatchHistoryLearner(history_file=test_file)

    # Record 5 wins with OP_CARD
    for _ in range(5):
        learner.record_match(
            result="WIN",
            friendly_hero="MAGE",
            opponent_hero="WARRIOR",
            turn_count=10,
            deck_card_ids=["OP_CARD"],
        )

    # Record 5 losses with WEAK_CARD
    for _ in range(5):
        learner.record_match(
            result="LOSS",
            friendly_hero="MAGE",
            opponent_hero="HUNTER",
            turn_count=6,
            deck_card_ids=["WEAK_CARD"],
        )

    # OP_CARD has 100% winrate (>= 75%) -> +5.0 bonus
    assert learner.get_card_winrate_adjustment("OP_CARD") == 5.0
    # WEAK_CARD has 0% winrate (<= 30%) -> -5.0 penalty
    assert learner.get_card_winrate_adjustment("WEAK_CARD") == -5.0
    # Untracked card -> 0.0
    assert learner.get_card_winrate_adjustment("UNKNOWN") == 0.0
