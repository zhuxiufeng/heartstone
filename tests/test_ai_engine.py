"""
Unit tests for AiEngine, EvaluationCache, metadata injection, and heuristic engine.
"""

from pathlib import Path
from core.ai_engine import AiEngine, EvaluationCache, AssistantMode
from core.card_db import CardDatabase, FALLBACK_CARDS_SAMPLE


def test_mana_curve_calculation():
    db = CardDatabase(auto_download=False)
    db._build_indexes(FALLBACK_CARDS_SAMPLE)

    deck = [
        db.get_by_id("CS2_188"),      # 1 cost
        db.get_by_id("CORE_CS2_039"), # 2 cost
        db.get_by_id("EX1_012"),      # 2 cost
        db.get_by_id("CS2_029"),      # 4 cost
        db.get_by_id("CS2_222"),      # 7 cost
        db.get_by_id("ICC_828"),      # 10 cost -> maps to bucket 7
    ]

    curve = AiEngine.calculate_mana_curve(deck)
    # [0, 1, 2, 3, 4, 5, 6, 7+]
    assert curve[0] == 0
    assert curve[1] == 1
    assert curve[2] == 2
    assert curve[3] == 0
    assert curve[4] == 1
    assert curve[5] == 0
    assert curve[6] == 0
    assert curve[7] == 2  # 7-cost and 10-cost both go to 7+


def test_evaluation_cache_hash_and_persistence(tmp_path: Path):
    cache_file = tmp_path / "test_cache.json"
    cache = EvaluationCache(cache_file)

    key = cache.compute_draft_hash("MAGE", [0, 1, 2, 0, 1, 0, 0, 2], ["CS2_188", "CS2_029", "CS2_222"])
    assert isinstance(key, str) and len(key) == 24

    cache.set(key, {"best_card_index": 1, "test": True})
    assert cache.get(key)["best_card_index"] == 1

    # Reload from disk
    cache2 = EvaluationCache(cache_file)
    assert cache2.get(key) is not None
    assert cache2.get(key)["test"] is True


def test_heuristic_draft_evaluation():
    db = CardDatabase(auto_download=False)
    db._build_indexes(FALLBACK_CARDS_SAMPLE)

    ai = AiEngine(card_db=db, cache_enabled=False)

    candidates = [
        db.get_by_id("CS2_188"),       # 叫嚣的矮人 (1费)
        db.get_by_id("CORE_CS2_039"),  # 风暴战斧 (2费武器)
        db.get_by_id("CS2_222"),       # 暴风城勇士 (7费)
    ]

    rec = ai.evaluate_draft_pick(
        hero_class="SHAMAN",
        candidates=candidates,
        deck_so_far=[],
    )

    assert rec is not None
    assert len(rec.cards_evaluations) == 3
    assert 0 <= rec.best_card_index <= 2
    assert rec.best_card_name in ["叫嚣的矮人", "风暴战斧", "暴风城勇士"]
    assert rec.cards_evaluations[rec.best_card_index].is_best_pick is True
    assert "第1阶段" in rec.overall_strategy


def test_draft_three_phases_and_play_hand_reading():
    db = CardDatabase(auto_download=False)
    db._build_indexes(FALLBACK_CARDS_SAMPLE)
    ai = AiEngine(card_db=db, cache_enabled=False)

    candidates = [
        db.get_by_id("CS2_188"),       # 1 cost
        db.get_by_id("CORE_CS2_039"),  # 2 cost
        db.get_by_id("CS2_222"),       # 7 cost
    ]

    # Phase 2 test (e.g. 15 cards drafted)
    deck_mid = [db.get_by_id("CS2_188")] * 15
    rec_mid = ai.evaluate_draft_pick("WARRIOR", candidates, deck_so_far=deck_mid)
    assert "第2阶段" in rec_mid.overall_strategy

    # Phase 3 test (e.g. 25 cards drafted)
    deck_late = [db.get_by_id("CS2_188")] * 25
    rec_late = ai.evaluate_draft_pick("WARRIOR", candidates, deck_so_far=deck_late)
    assert "第3阶段" in rec_late.overall_strategy

    # Test Play Turn with Hand Reading
    hand = [db.get_by_id("CS2_029")]  # Fireball
    play_rec = ai.evaluate_play_turn(
        turn_number=6,
        current_mana=6,
        hand_cards=hand,
        friendly_board=["淡水鳄 (2/3)"],
        enemy_board=["冰风雪人 (4/5)"],
        opponent_class="Mage",
        opponent_hand_warnings=["对手起手留牌已屯5回合未出！"],
        has_long_held_card=True,
    )
    assert play_rec is not None
    assert any("起手留牌" in alert for alert in play_rec.aoe_threats)
