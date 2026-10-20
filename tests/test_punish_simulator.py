"""
Unit tests for PunishSimulator (Worst-case opponent on-curve counter-play evaluation).
"""

from core.punish_simulator import PunishSimulator, PunishAssessment


def test_mage_flamestrike_punish_low_resilience():
    # 3 fragile minions with 3 health against Mage going into Turn 7 (Flamestrike: 5 dmg)
    minions = [
        {"name": "淡水鳄", "attack": 2, "health": 3, "divine_shield": False},
        {"name": "叫嚣的中士", "attack": 2, "health": 1, "divine_shield": False},
        {"name": "软泥怪", "attack": 3, "health": 2, "divine_shield": False},
    ]

    res: PunishAssessment = PunishSimulator.evaluate_board_punish(
        friendly_minions=minions,
        opponent_class="Mage",
        current_turn=6,  # Next turn is Turn 7 (Flamestrike)
    )

    assert res.punish_risk_level == "CRITICAL"
    assert "烈焰风暴" in res.predicted_punish_card
    assert res.projected_surviving_minions == 0
    assert "极度高危惩罚" in res.tactical_advice


def test_board_with_divine_shield_and_deathrattle_high_resilience():
    # 2 minions with Divine Shield / Deathrattle
    minions = [
        {"name": "银色指挥官", "attack": 4, "health": 2, "divine_shield": True},
        {"name": "麦田傀儡", "attack": 2, "health": 3, "deathrattle": True},
    ]

    res = PunishSimulator.evaluate_board_punish(
        friendly_minions=minions,
        opponent_class="Mage",
        current_turn=6,
    )

    assert res.projected_surviving_minions == 2
    assert res.resilience_score > 60.0
    assert "防反手韧性" in res.tactical_advice
