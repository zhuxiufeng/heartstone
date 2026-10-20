"""
Unit tests for MatchupBlueprintEngine (11-class matchup tactical blueprints).
"""

from core.matchup_blueprint import MatchupBlueprintEngine, MatchupStrategy


def test_mage_matchup_flamestrike_and_ping():
    strat: MatchupStrategy = MatchupBlueprintEngine.get_matchup_strategy(
        opponent_class="Mage",
        current_turn=7,
        friendly_board=["淡水鳄 (2/3)", "冰风雪人 (4/5)"],
        enemy_board=[],
        friendly_hp=25,
        enemy_hp=20,
    )
    assert strat.opponent_class_name == "法师"
    assert strat.ping_threat_active is True
    assert "烈焰风暴" in (strat.turn_danger_alert or "")
    assert "火冲" in strat.core_gameplan or "残血" in strat.core_gameplan


def test_paladin_crusader_aura_alert():
    strat = MatchupBlueprintEngine.get_matchup_strategy(
        opponent_class="圣骑士",
        current_turn=4,
        friendly_board=[],
        enemy_board=["白银之手新兵 (1/1)"],
        friendly_hp=30,
        enemy_hp=30,
    )
    assert strat.opponent_class_name == "圣骑士"
    assert "十字军光环" in (strat.turn_danger_alert or "")
    assert "绝不留单怪" in strat.special_tactics[0] or "杂毛" in strat.core_gameplan


def test_shaman_bloodlust_burst_warning():
    strat = MatchupBlueprintEngine.get_matchup_strategy(
        opponent_class="SHAMAN",
        current_turn=5,
        friendly_board=[],
        enemy_board=["灼热图腾 (1/1)", "石爪图腾 (0/2)", "火舌图腾 (0/3)"],
        friendly_hp=15,
        enemy_hp=25,
    )
    assert strat.opponent_class_name == "萨满祭司"
    assert "嗜血警报" in strat.burst_danger_warning
    assert "+9" in strat.burst_danger_warning


def test_deathknight_and_demonhunter_ping_recognition():
    dk_strat = MatchupBlueprintEngine.get_matchup_strategy(
        opponent_class="DEATHKNIGHT",
        current_turn=5,
        friendly_board=[],
        enemy_board=[],
        friendly_hp=20,
        enemy_hp=20,
    )
    assert dk_strat.ping_threat_active is True
    assert "邪爆" in (dk_strat.turn_danger_alert or "")

    dh_strat = MatchupBlueprintEngine.get_matchup_strategy(
        opponent_class="DEMONHUNTER",
        current_turn=3,
        friendly_board=[],
        enemy_board=[],
        friendly_hp=20,
        enemy_hp=20,
    )
    assert dh_strat.ping_threat_active is True
