"""
Unit tests for v14 Transcendent Intelligence (高维智能版) optimizations:
1. Mental Model & Strategic Bluffing Engine
2. Tactical Setup & Baiting Planner
3. Desperation & Miracle Line Inversion
4. Self-Evolving Reinforcement & Personalized Blindspots
5. Deep Resource Entropy & Fatigue Endgame Horizon
6. Interactive Full-Duplex Voice Brain
"""

import pytest

from core.mental_bluff_engine import (
    MentalBluffEngine, OpponentMentalProfile, OpponentStyle, BluffOpportunity
)
from core.tactical_setup_planner import (
    TacticalSetupPlanner, TacticalSetupPlan, SetupCategory, SetupStep
)
from core.miracle_inversion_engine import (
    MiracleInversionEngine, MiracleGamblePath, RiskAttitude
)
from core.self_evolving_reinforcement import (
    SelfEvolvingReinforcement, CardEvolvingWeight, PersonalBlindspot
)
from core.fatigue_endgame_horizon import (
    FatigueEndgameHorizon, FatigueEndgameReport, EndgameVerdict, ResourcePool
)
from core.interactive_voice_brain import (
    InteractiveVoiceBrain, VoiceBrainResponse, VoiceIntent
)


def test_mental_bluff_engine():
    # 1. Aggressive rusher history
    aggro_history = [
        {"duration_sec": 12.0, "card_hovers": 1, "face_attacks": 4, "trade_attacks": 0, "blunders": 0},
        {"duration_sec": 14.0, "card_hovers": 0, "face_attacks": 3, "trade_attacks": 0, "blunders": 0},
    ]
    prof_aggro = MentalBluffEngine.analyze_opponent_style(aggro_history)
    assert prof_aggro.style == OpponentStyle.AGGRESSIVE_RUSHER
    assert prof_aggro.bait_tolerance_factor >= 1.2

    # 2. Meticulous control history
    ctrl_history = [
        {"duration_sec": 42.0, "card_hovers": 5, "face_attacks": 0, "trade_attacks": 3, "blunders": 0},
        {"duration_sec": 38.0, "card_hovers": 4, "face_attacks": 1, "trade_attacks": 4, "blunders": 0},
    ]
    prof_ctrl = MentalBluffEngine.analyze_opponent_style(ctrl_history)
    assert prof_ctrl.style == OpponentStyle.METICULOUS_CONTROL
    assert prof_ctrl.bluff_vulnerability_score >= 0.7

    # 3. Evaluate bluff when behind against control
    bluff_ctrl = MentalBluffEngine.evaluate_strategic_bluff(
        player_health=14,
        opponent_health=18,
        board_attack=14,  # Looks very close to lethal
        hand_damage_available=0,
        opponent_profile=prof_ctrl,
        current_winrate=35.0,  # Behind
    )
    assert bluff_ctrl.is_viable is True
    assert bluff_ctrl.bluff_ev > 10.0
    assert "虚张声势" in bluff_ctrl.bluff_action

    # 4. Evaluate bluff when ahead
    bluff_ahead = MentalBluffEngine.evaluate_strategic_bluff(
        player_health=28,
        opponent_health=12,
        board_attack=10,
        hand_damage_available=4,
        opponent_profile=prof_ctrl,
        current_winrate=75.0,
    )
    assert bluff_ahead.is_viable is False


def test_tactical_setup_planner():
    friendly_board = [
        {"name": "淡水鳄", "attack": 2, "health": 3, "can_attack": True}
    ]
    enemy_board = [
        {"name": "暴风城勇士", "attack": 6, "health": 6}
    ]
    friendly_hand = ["横扫", "布莱恩·铜须", "阿曼苏尔", "幸运币"]

    plans = TacticalSetupPlanner.plan_setup_lines(
        friendly_board=friendly_board,
        enemy_board=enemy_board,
        friendly_hand=friendly_hand,
        current_mana=3,
        next_turn_mana=4,
    )

    assert len(plans) >= 2
    # Verify Damage Preparation Plan: 2 atk chips 6 hp down to 4 hp for next turn 4-dmg Swipe
    dmg_plan = next((p for p in plans if p.category == SetupCategory.DAMAGE_PREPARATION), None)
    assert dmg_plan is not None
    assert "淡水鳄" in dmg_plan.name
    assert "横扫" in dmg_plan.name
    assert len(dmg_plan.steps) == 2

    # Verify Bait Plan: Bronzebeard baits for Aman'Thul
    bait_plan = next((p for p in plans if p.category == SetupCategory.BAIT_REMOVAL), None)
    assert bait_plan is not None
    assert "布莱恩·铜须" in bait_plan.name
    assert "阿曼苏尔" in bait_plan.name


def test_miracle_inversion_engine():
    # 1. Absolute control when ahead
    res_ahead = MiracleInversionEngine.evaluate_game_attitude(
        winrate_pct=82.0,
        player_hp=28,
        enemy_hp=10,
        enemy_board_attack=3,
        player_board_attack=8,
    )
    assert res_ahead.risk_attitude == RiskAttitude.ABSOLUTE_CONTROL
    assert res_ahead.is_miracle_needed is False

    # 2. Balanced EV in even match
    res_mid = MiracleInversionEngine.evaluate_game_attitude(
        winrate_pct=52.0,
        player_hp=20,
        enemy_hp=20,
        enemy_board_attack=6,
        player_board_attack=6,
    )
    assert res_mid.risk_attitude == RiskAttitude.BALANCED_EV

    # 3. Miracle gamble in desperate state
    res_desp = MiracleInversionEngine.evaluate_game_attitude(
        winrate_pct=12.0,
        player_hp=8,
        enemy_hp=14,
        enemy_board_attack=15,  # Fatal threat on board
        player_board_attack=8,
        deck_remaining=["火球术", "寒冰箭"],
    )
    assert res_desp.risk_attitude == RiskAttitude.MIRACLE_GAMBLE
    assert res_desp.is_miracle_needed is True
    assert "火球术" in res_desp.required_topdecks
    assert res_desp.winrate_gain_pct > 0.0


def test_self_evolving_reinforcement(tmp_path):
    storage_file = str(tmp_path / "test_blindspots.json")
    ser = SelfEvolvingReinforcement(storage_path=storage_file)

    # 1. Self play evolving weights
    cards = ["奥术智慧", "火球术", "白板随从"]
    weights = ser.run_local_self_play(cards, simulations=30)
    assert "奥术智慧" in weights
    assert weights["奥术智慧"].evolving_delta > 0.0
    assert weights["奥术智慧"].meta_affinity_trend == "UPWARD"
    assert weights["白板随从"].evolving_delta < 0.0

    # 2. Blindspots recording
    ser.record_match_blunder("GREEDY_FACE")
    ser.record_match_blunder("GREEDY_FACE")
    ser.record_match_blunder("GREEDY_FACE")
    warnings = ser.get_active_blindspot_warnings()
    greedy_warn = next(w for w in warnings if w.category == "GREEDY_FACE")
    assert greedy_warn.occurrence_count == 3
    assert greedy_warn.severity_level == "CRITICAL"


def test_fatigue_endgame_horizon():
    # 1. Resource Dominance: my deck has 10 cards, opponent has 2 cards
    rep_dom = FatigueEndgameHorizon.calculate_endgame_horizon(
        my_deck_count=10,
        my_hand=["雷诺·杰克逊", "绝命乱斗"],
        my_hp=25,
        my_armor=5,
        opp_deck_count=2,
        opp_hand_count=3,
        opp_hp=16,
        opp_armor=0,
    )
    assert rep_dom.verdict == EndgameVerdict.RESOURCE_DOMINANCE
    assert rep_dom.fatigue_differential_turns == 8
    assert "疲劳" in rep_dom.strategic_directive

    # 2. Resource Deficit: my deck has 1 card, opponent has 7 cards
    rep_def = FatigueEndgameHorizon.calculate_endgame_horizon(
        my_deck_count=1,
        my_hand=[],
        my_hp=15,
        my_armor=0,
        opp_deck_count=7,
        opp_hand_count=5,
        opp_hp=22,
        opp_armor=0,
    )
    assert rep_def.verdict == EndgameVerdict.RESOURCE_DEFICIT_RUSH
    assert "转守为攻" in rep_def.strategic_directive
    assert "提速" in rep_def.verdict_label


def test_interactive_voice_brain():
    # 1. Lethal check query
    state_lethal = {
        "lethal_info": {"has_lethal": True, "total_damage": 32},
        "opponent_health": 24,
    }
    ans1 = InteractiveVoiceBrain.answer_query("大师，这把能斩杀吗？", state_lethal)
    assert ans1.intent == VoiceIntent.LETHAL_CHECK
    assert "斩杀确定" in ans1.spoken_answer
    assert ans1.tactical_action_ref == "EXECUTE_LETHAL"

    # 2. Removal advice query
    state_threat = {"enemy_threat_level": "CRITICAL"}
    ans2 = InteractiveVoiceBrain.answer_query("现在要不要交绝命乱斗解场？", state_threat)
    assert ans2.intent == VoiceIntent.REMOVAL_ADVICE
    assert "果断打出核心解牌" in ans2.spoken_answer

    # 3. Miracle query
    state_miracle = {"winrate": 14.0}
    ans3 = InteractiveVoiceBrain.answer_query("我们还有希望翻盘吗？", state_miracle)
    assert ans3.intent == VoiceIntent.MIRACLE_LINE
    assert "全员走脸拼死一搏" in ans3.spoken_answer

    # 4. Draft synergy query
    ans4 = InteractiveVoiceBrain.answer_query("这张牌能配合什么？", {})
    assert ans4.intent == VoiceIntent.DRAFT_SYNERGY
    assert "体系闭环" in ans4.spoken_answer
