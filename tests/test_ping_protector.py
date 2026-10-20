"""
Unit tests for PingProtector (Ping-Resistant Trading Engine).
"""

from core.ping_protector import PingProtector, PingProtectionAdvice


def test_ping_classes_recognition():
    assert PingProtector.is_ping_class("MAGE") is True
    assert PingProtector.is_ping_class("法师") is True
    assert PingProtector.is_ping_class("Rogue") is True
    assert PingProtector.is_ping_class("潜行者") is True
    assert PingProtector.is_ping_class("Druid") is True
    assert PingProtector.is_ping_class("Demon Hunter") is True
    assert PingProtector.is_ping_class("Death Knight") is True
    assert PingProtector.is_ping_class("Priest") is False
    assert PingProtector.is_ping_class("Warrior") is False


def test_vulnerable_1hp_trade_penalty():
    # Minion with 4 attack survives with 1 HP against Mage
    adv: PingProtectionAdvice = PingProtector.evaluate_trade_residual(
        attacker_name="冰风雪人",
        attacker_atk=4,
        attacker_rem_hp=1,
        attacker_has_shield=False,
        opponent_class="Mage",
    )
    assert adv.is_vulnerable is True
    assert adv.penalty_score < -20.0
    assert "防补刀警报" in adv.warning_text


def test_safe_2hp_trade_reward():
    adv: PingProtectionAdvice = PingProtector.evaluate_trade_residual(
        attacker_name="冰风雪人",
        attacker_atk=4,
        attacker_rem_hp=2,
        attacker_has_shield=False,
        opponent_class="Mage",
    )
    assert adv.is_vulnerable is False
    assert adv.penalty_score > 0
    assert "防补刀安全" in adv.warning_text


def test_divine_shield_immunity():
    adv: PingProtectionAdvice = PingProtector.evaluate_trade_residual(
        attacker_name="银色十子军",
        attacker_atk=3,
        attacker_rem_hp=1,
        attacker_has_shield=True,
        opponent_class="Mage",
    )
    assert adv.is_vulnerable is False
    assert adv.penalty_score == 0.0
