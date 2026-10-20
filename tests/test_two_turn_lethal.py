"""
Unit tests for TwoTurnLethalEngine.
"""

from core.two_turn_lethal import TwoTurnLethalEngine, TwoTurnLethalPlan
from core.card_db import CardInfo


def test_two_turn_lethal_setup():
    # Friendly has 2 minions with 4 atk each = 8 atk
    # Hand has Fireball (CS2_029, 6 dmg, 4 cost)
    # Total Turn 1 damage = 8 + 6 = 14
    # Enemy HP is 22. Turn 1 leaves enemy at 8 HP.
    # Turn 2 projected board damage = 8 + 1 (hero power) = 9 >= 8
    # 2-turn lethal should be established!
    friendly_minions = [
        {"name": "雪人", "atk": 4, "health": 5, "can_attack": True},
        {"name": "机械雪人", "atk": 4, "health": 5, "can_attack": True},
    ]
    enemy_taunts = []
    hand = [
        CardInfo(id="CS2_029", name="火球术", cost=4, card_type="SPELL"),
    ]

    plan: TwoTurnLethalPlan = TwoTurnLethalEngine.evaluate_two_turn_lethal(
        friendly_minions=friendly_minions,
        enemy_taunts=enemy_taunts,
        hand_cards=hand,
        available_mana=4,
        enemy_hp=22,
        enemy_armor=0,
        enemy_hand_count=2,
        enemy_class="HUNTER",
        hero_power_damage=1,
        friendly_hp=25,
        enemy_board_attack=4,
    )

    assert plan.is_two_turn_lethal is True
    assert plan.turn1_face_damage == 14
    assert plan.enemy_residual_hp == 8
    assert plan.projected_turn2_damage >= 8
    assert "叫杀成立" in plan.recommendation


def test_counter_lethal_prevents_two_turn_push():
    # Friendly hero at 5 HP, enemy has 7 board attack. Friendly cannot push face blindly.
    friendly_minions = [
        {"name": "大哥", "atk": 8, "health": 8, "can_attack": True},
    ]
    plan: TwoTurnLethalPlan = TwoTurnLethalEngine.evaluate_two_turn_lethal(
        friendly_minions=friendly_minions,
        enemy_taunts=[],
        hand_cards=[],
        available_mana=5,
        enemy_hp=12,
        friendly_hp=5,
        enemy_board_attack=7,
    )
    assert plan.is_two_turn_lethal is False
    assert "不可冒进" in plan.recommendation or "已对我方" in plan.recommendation
