"""
Unit tests for LethalCalculator.
"""

import pytest
from core.card_db import CardInfo
from core.lethal_calculator import LethalCalculator, LethalResult


def test_lethal_direct_board_damage():
    calc = LethalCalculator()
    friendly_minions = [
        {"name": "石拳食人魔", "atk": 6, "can_attack": True, "windfury": False},
        {"name": "冰风雪人", "atk": 4, "can_attack": True, "windfury": False},
    ]
    enemy_taunts = []
    hand_cards = []

    res: LethalResult = calc.calculate_lethal(
        friendly_minions=friendly_minions,
        enemy_taunts=enemy_taunts,
        hand_cards=hand_cards,
        available_mana=2,
        enemy_hp=10,
        enemy_armor=0,
        hero_power_available=False,
    )

    assert res.is_lethal is True
    assert res.total_damage == 10
    assert res.board_damage == 10
    assert res.overkill == 0


def test_lethal_with_taunt_absorption():
    calc = LethalCalculator()
    friendly_minions = [
        {"name": "冰风雪人", "atk": 4, "can_attack": True, "windfury": False},
        {"name": "暴风城勇士", "atk": 6, "can_attack": True, "windfury": False},
    ]
    enemy_taunts = [{"name": "铁鬃灰熊", "health": 3}]
    hand_cards = []

    res: LethalResult = calc.calculate_lethal(
        friendly_minions=friendly_minions,
        enemy_taunts=enemy_taunts,
        hand_cards=hand_cards,
        available_mana=2,
        enemy_hp=8,
        enemy_armor=0,
        hero_power_available=False,
    )

    # Total board damage 10, taunt absorbs 3, face damage 7 < 8
    assert res.is_lethal is False
    assert res.board_damage == 7
    assert res.total_damage == 7


def test_lethal_with_burn_spells_and_hero_power():
    calc = LethalCalculator()
    fireball = CardInfo(
        id="CS2_029",
        name="火球术",
        cost=4,
        card_type="SPELL",
        card_class="MAGE",
        rarity="FREE",
    )
    frostbolt = CardInfo(
        id="CS2_024",
        name="寒冰箭",
        cost=2,
        card_type="SPELL",
        card_class="MAGE",
        rarity="FREE",
    )

    friendly_minions = []
    enemy_taunts = []
    hand_cards = [fireball, frostbolt]

    # Available mana = 8: Fireball (4) + Frostbolt (2) + Hero Power (2) = 6 + 3 + 1 = 10 dmg
    res: LethalResult = calc.calculate_lethal(
        friendly_minions=friendly_minions,
        enemy_taunts=enemy_taunts,
        hand_cards=hand_cards,
        available_mana=8,
        enemy_hp=10,
        enemy_armor=0,
        hero_class="MAGE",
        hero_power_available=True,
    )

    assert res.is_lethal is True
    assert res.hand_damage == 9
    assert res.hero_power_damage == 1
    assert res.total_damage == 10
