"""
Unit tests for PostureEngine.
"""

from core.posture_engine import PostureEngine


def test_posture_engine_aggressive():
    engine = PostureEngine()
    # Friendly has 15 attack, enemy has 12 hp -> Friendly clock = 1 turn!
    res = engine.assess_posture(
        friendly_hp=25,
        enemy_hp=12,
        friendly_board_attack=15,
        enemy_board_attack=4,
        friendly_hand_count=3,
        enemy_hand_count=3,
    )
    assert res.posture_mode == "AGGRESSIVE"
    assert res.friendly_clock_turns == 1
    assert "斩杀" in res.recommended_focus or "抢脸" in res.recommended_focus


def test_posture_engine_control_on_threat():
    engine = PostureEngine()
    # Friendly has only 5 hp, enemy has 8 attack -> Enemy kills in 1 turn!
    res = engine.assess_posture(
        friendly_hp=5,
        enemy_hp=25,
        friendly_board_attack=4,
        enemy_board_attack=8,
        friendly_hand_count=2,
        enemy_hand_count=4,
    )
    assert res.posture_mode == "CONTROL"
    assert res.enemy_threat_turns == 1
    assert "防守" in res.recommended_focus or "解场" in res.recommended_focus


def test_posture_engine_all_in():
    engine = PostureEngine()
    # Friendly hand is 1 card, enemy hand is 4 cards, enemy HP is 14
    res = engine.assess_posture(
        friendly_hp=20,
        enemy_hp=14,
        friendly_board_attack=6,
        enemy_board_attack=3,
        friendly_hand_count=1,
        enemy_hand_count=4,
    )
    assert res.posture_mode == "ALL_IN"
