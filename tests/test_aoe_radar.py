"""
Unit tests for AoeRadar.
"""

from core.aoe_radar import AoeRadar


def test_aoe_radar_mage_flamestrike():
    radar = AoeRadar()
    # Turn 6 against Mage -> Mage has 7 mana on turn 7 -> Flamestrike is accessible!
    friendly = [
        {"name": "机械雪人", "health": 5, "divine_shield": False},
        {"name": "淡水鳄", "health": 3, "divine_shield": False},
        {"name": "工程师学徒", "health": 1, "divine_shield": False},
    ]
    threats = radar.evaluate_threats("Mage", current_turn=6, friendly_minions=friendly)
    assert len(threats) > 0
    # Flamestrike hits for 5 damage -> kills all 3 minions!
    flamestrike_threat = next((t for t in threats if "烈焰风暴" in t.spell.name), None)
    assert flamestrike_threat is not None
    assert flamestrike_threat.mana_accessible is True
    assert flamestrike_threat.minions_killed_count == 3
    assert flamestrike_threat.danger_level == "CRITICAL"


def test_aoe_radar_divine_shield_protection():
    radar = AoeRadar()
    # Friendly has divine shields -> Flamestrike damage is absorbed!
    friendly = [
        {"name": "银色指挥官", "health": 2, "divine_shield": True},
        {"name": "烈日行者", "health": 5, "divine_shield": True},
    ]
    threats = radar.evaluate_threats("Mage", current_turn=6, friendly_minions=friendly)
    # Divine shields prevent death from non-destroy damage
    flamestrike_threat = next((t for t in threats if "烈焰风暴" in t.spell.name), None)
    # Since 0 killed, shouldn't be high danger
    assert flamestrike_threat is None or flamestrike_threat.minions_killed_count == 0


def test_aoe_radar_long_held_card_threat():
    radar = AoeRadar()
    friendly = [
        {"name": "淡水鳄", "health": 2, "divine_shield": False},
        {"name": "叫嚣的矮人", "health": 1, "divine_shield": False},
    ]
    # Blizzard at turn 5 -> kills both
    threats = radar.evaluate_threats("Mage", current_turn=5, friendly_minions=friendly, has_long_held_card=True)
    blizzard_threat = next((t for t in threats if "暴风雪" in t.spell.name), None)
    assert blizzard_threat is not None
    assert "蓄力多轮" in blizzard_threat.warning_advice
