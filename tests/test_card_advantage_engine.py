"""
Unit tests for CardAdvantageEngine (Hand Starvation, Choke Clock & Anti-Overextend).
"""

from core.card_advantage_engine import CardAdvantageEngine, ResourceAdvantagePlan, ResourceState


def test_choke_out_mode_when_enemy_hand_starved():
    # Enemy has only 1 card on Turn 6
    plan: ResourceAdvantagePlan = CardAdvantageEngine.evaluate_resource_dynamics(
        friendly_hand_count=5,
        enemy_hand_count=1,
        friendly_board_count=3,
        enemy_hp=18,
        turn_number=6,
    )

    assert plan.state == ResourceState.CHOKE_OUT
    assert plan.choke_pressure_active is True
    assert "断牌压迫" in plan.strategic_directive


def test_anti_overextend_when_enemy_holds_full_hand():
    # Enemy holds 7 cards, friendly board already has 4 minions
    plan: ResourceAdvantagePlan = CardAdvantageEngine.evaluate_resource_dynamics(
        friendly_hand_count=3,
        enemy_hand_count=7,
        friendly_board_count=4,
        enemy_hp=26,
        turn_number=5,
    )

    assert plan.state == ResourceState.ANTI_OVEREXTEND
    assert plan.anti_overextend_warning is True
    assert "防过度投资" in plan.strategic_directive
