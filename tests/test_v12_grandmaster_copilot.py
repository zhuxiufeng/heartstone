"""
Unit tests for v12 Grandmaster Co-Pilot System (全知大师副驾系统):
1. Master Co-Pilot Sequential Step Engine
2. Pre-Cast Millisecond Blunder Interceptor
3. Dynamic Mid-Turn Re-Planning Pivot Engine
4. Conversational TTS Streamer with Emergency Preemption
5. AR Tactical Laser & Arrow Guidance
6. Web Companion Real-Time Co-Pilot Endpoints
"""

import pytest

from core.master_copilot import MasterCoPilotEngine, CoPilotTurnPlan, CoPilotStep, CoPilotStepType
from core.pre_cast_blunder_interceptor import PreCastBlunderInterceptor, BlunderInterceptAlert, InterceptType
from core.mid_turn_pivot_engine import MidTurnPivotEngine
from core.conversational_tts_streamer import ConversationalTtsStreamer
from core.web_companion import WebCompanionServer


def test_master_copilot_step_plan_building():
    action_seq = [
        "奥术智慧抽牌",
        "用 3/2 随从攻击敌方 2/1",
        "下 4/5 冰风雪人",
        "全员随从走脸",
    ]

    plan = MasterCoPilotEngine.build_step_plan(
        action_sequence=action_seq,
        trading_plan="优先白吃控场",
        had_lethal=False,
        friendly_hp=25,
        enemy_hp=20,
        mana=7,
        turn=5,
    )

    assert plan.turn_number == 5
    assert len(plan.steps) == 4
    # Step 1 should be DRAW_FIRST
    assert plan.steps[0].step_type == CoPilotStepType.DRAW_FIRST
    assert "过牌" in plan.steps[0].conversational_voice
    assert plan.steps[0].status == "IN_PROGRESS"

    # Step 2 should be TRADE_MINION
    assert plan.steps[1].step_type == CoPilotStepType.TRADE_MINION

    # Step advancing
    active_before = plan.get_active_step()
    assert active_before.step_number == 1

    next_step = plan.advance()
    assert next_step.step_number == 2
    assert plan.steps[0].status == "COMPLETED"
    assert plan.steps[1].status == "IN_PROGRESS"


def test_pre_cast_blunder_interceptor():
    # 1. Missed Lethal Interception
    # Player has 14 damage against 10 enemy HP, but aims at a minion
    alert_lethal = PreCastBlunderInterceptor.check_action(
        intended_action_type="ATTACK",
        intended_source_name="海巨人 (8/8)",
        intended_target_name="敌方嘲讽怪 (3/4)",
        enemy_hp=10,
        board_total_lethal_damage=14,
    )
    assert alert_lethal is not None
    assert alert_lethal.intercept_type == InterceptType.MISSED_LETHAL
    assert "直接走脸就斩杀" in alert_lethal.voice_shout

    # 2. Draw Before Play Interception
    hand = [
        {"name": "奥术智慧", "cost": 3},
        {"name": "淡水鳄", "cost": 2},
    ]
    alert_draw = PreCastBlunderInterceptor.check_action(
        intended_action_type="PLAY_CARD",
        intended_source_name="淡水鳄",
        intended_target_name="棋盘",
        enemy_hp=30,
        hand_cards=hand,
        available_mana=4,
    )
    assert alert_draw is not None
    assert alert_draw.intercept_type == InterceptType.DRAW_BEFORE_PLAY
    assert "过牌" in alert_draw.voice_shout

    # 3. Divine Shield Overkill
    alert_shield = PreCastBlunderInterceptor.check_action(
        intended_action_type="ATTACK",
        intended_source_name="暴龙王克鲁什",
        intended_target_name="圣盾护卫",
        enemy_hp=30,
        target_has_divine_shield=True,
        source_attack=8,
    )
    assert alert_shield is not None
    assert alert_shield.intercept_type == InterceptType.DIVINE_SHIELD_OVERKILL
    assert "别拿主力大怪撞圣盾" in alert_shield.voice_shout


def test_mid_turn_pivot_engine():
    # Start with a normal trading plan
    plan = MasterCoPilotEngine.build_step_plan(
        action_sequence=["奥术智慧抽牌", "3/2换2/1"],
        trading_plan="控场",
        had_lethal=False,
        friendly_hp=20,
        enemy_hp=10,
        mana=5,
        turn=4,
    )

    # Player executes Step 1 (draws cards), drawing Fireball (6 dmg) with 4 board attack -> 6+4=10 = EXACT LETHAL!
    plan.advance()

    pivoted_plan = MidTurnPivotEngine.evaluate_pivot(
        plan=plan,
        event_type="CARD_DRAWN",
        drawn_card_name="火球术",
        drawn_card_damage=6,
        enemy_hp=10,
        friendly_board_attack=4,
        available_mana=4,
    )

    assert pivoted_plan.is_lethal_turn is True
    # The remaining steps should be modified into Fireball face + All minions attack face
    active_step = pivoted_plan.get_active_step()
    assert "火球术" in active_step.action_text
    assert active_step.step_type == CoPilotStepType.PLAY_SPELL


def test_conversational_tts_streamer():
    spoken_lines = []

    def _mock_speaker(text: str):
        spoken_lines.append(text)

    streamer = ConversationalTtsStreamer.get_instance()
    streamer.set_speaker_func(_mock_speaker)

    # 1. Macro overview
    res_macro = streamer.speak_macro_overview("回合开始，优先解场。")
    assert res_macro is True
    assert "回合开始" in spoken_lines[-1]

    # 2. Emergency blunder interrupt
    res_emergency = streamer.speak_blunder_intercept("住手！直接走脸就斩杀了！")
    assert res_emergency is True
    assert "住手！直接走脸就斩杀了！" in spoken_lines[-1]


def test_web_companion_copilot_endpoints():
    # Setup test plan
    plan = MasterCoPilotEngine.build_step_plan(
        action_sequence=["抽牌", "打脸"],
        had_lethal=True,
        enemy_hp=5,
    )
    MasterCoPilotEngine.get_instance().load_turn_plan(plan)
    WebCompanionServer.update_state({"copilot_plan": plan.to_dict()})

    state = WebCompanionServer.get_state()
    assert "copilot_plan" in state
    c_plan = state["copilot_plan"]
    assert c_plan["is_lethal_turn"] is True
    assert len(c_plan["steps"]) == 2
