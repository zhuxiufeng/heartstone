"""
Unit tests for BlunderShield (Live Operational Misplay Interceptor).
"""

from core.card_db import CardInfo
from core.blunder_shield import BlunderShield, BlunderAlert


def _make_card(id: str, name: str, cost: int, text: str = "", mechanics: list = None) -> CardInfo:
    return CardInfo(
        id=id,
        name=name,
        cost=cost,
        attack=cost,
        health=cost,
        durability=None,
        card_class="NEUTRAL",
        card_type="MINION",
        rarity="COMMON",
        set_name="CORE",
        text=text,
        race=None,
        races=[],
        spell_school=None,
        mechanics=mechanics or [],
        collectible=True,
        raw_data={},
    )


def test_buff_before_attack_interceptor():
    abusive = _make_card("abusive", "叫嚣的中士", 1, text="战吼：在本回合中，使一个随从获得+2攻击力。")
    minions = [{"name": "淡水鳄", "attack": 2, "health": 3, "can_attack": True}]

    alerts = BlunderShield.scan_for_blunders(
        hand_cards=[abusive],
        friendly_minions=minions,
        enemy_secrets_count=0,
        available_mana=2,
        hero_power_available=True,
    )

    types = [a.blunder_type for a in alerts]
    assert "BUFF_BEFORE_ATTACK" in types
    assert any("先增益后攻击" in a.alert_title for a in alerts)


def test_draw_first_interceptor():
    intellect = _make_card("intellect", "奥术智慧", 3, text="抽两张牌。")
    yeti = _make_card("yeti", "冰风雪人", 4)

    alerts = BlunderShield.scan_for_blunders(
        hand_cards=[intellect, yeti],
        friendly_minions=[],
        enemy_secrets_count=0,
        available_mana=5,
        hero_power_available=True,
    )

    types = [a.blunder_type for a in alerts]
    assert "DRAW_FIRST" in types
    assert any("先过牌探查" in a.alert_title for a in alerts)


def test_secret_testing_with_small_minion():
    small_guy = {"name": "小野猪", "attack": 1, "can_attack": True}
    big_guy = {"name": "暴风城勇士", "attack": 6, "can_attack": True}

    alerts = BlunderShield.scan_for_blunders(
        hand_cards=[],
        friendly_minions=[small_guy, big_guy],
        enemy_secrets_count=1,
        available_mana=3,
        hero_power_available=True,
    )

    types = [a.blunder_type for a in alerts]
    assert "SECRET_CHECK" in types
    assert any("用小怪测奥秘" in a.alert_title for a in alerts)
