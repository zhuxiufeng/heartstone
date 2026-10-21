"""
Unit tests for v13 Supreme Omniscience (寰宇全知版) optimizations:
1. Neural Hidden Hand Silhouette & Heat Matrix
2. Future Pick Forecaster & Archetype Locking Engine
3. Interactive 'What If' Sandbox & Branch Explorer
4. Instant Card Lens & Deep Deconstruction Magnifier
5. Zero-Cloud Pure Local Decision Engine
6. Post-Match Talkshow Podcast Narrator
"""

import pytest

from core.card_db import CardInfo
from core.neural_hand_silhouette import NeuralHandSilhouette, HandSilhouetteReport
from core.future_pick_forecaster import FuturePickForecaster, DraftArchetype, FutureForecastReport
from core.what_if_sandbox import WhatIfSandbox, WhatIfSimulationReport
from core.instant_card_lens import InstantCardLens, CardLensBreakdown
from core.zero_cloud_engine import ZeroCloudEngine, ZeroCloudDecision
from core.post_match_talkshow import PostMatchTalkshow, TalkshowScriptReport


def _make_dummy_card(card_id: str, name: str, cost: int, card_type: str = "MINION", text: str = "", race: str = "", rarity: str = "COMMON"):
    return CardInfo(
        id=card_id,
        name=name,
        cost=cost,
        card_type=card_type,
        text=text,
        race=race,
        rarity=rarity,
        card_class="NEUTRAL",
        mechanics=[],
    )


def test_neural_hand_silhouette():
    hand_info = [
        {"slot": 1, "hold_turns": 5, "origin": "MULLIGAN_KEPT"},
        {"slot": 2, "hold_turns": 1, "origin": "TURN_DRAW"},
    ]

    rep = NeuralHandSilhouette.evaluate_hand_silhouette(
        opponent_class="Mage",
        hand_cards_info=hand_info,
        current_turn=6,
    )

    assert rep.total_hand_count == 2
    assert 1 in rep.critical_threat_slots
    slot1 = rep.slots[0]
    assert slot1.primary_prediction.card_name == "烈焰风暴"
    assert slot1.primary_prediction.probability_pct > 70.0
    assert slot1.primary_prediction.danger_tier == "CRITICAL"


def test_future_pick_forecaster():
    # Drafted deck with 4 mechs
    drafted = [
        _make_dummy_card("M1", "微型机甲", 2, race="MECHANICAL"),
        _make_dummy_card("M2", "收割机", 4, race="MECHANICAL"),
        _make_dummy_card("M3", "机械袋鼠", 1, race="MECHANICAL"),
        _make_dummy_card("M4", "发条强盗", 3, race="MECHANICAL"),
    ]

    candidates = [
        _make_dummy_card("C1", "机械巨熊", 5, race="MECHANICAL", text="战吼：发现一张机械牌"),
        _make_dummy_card("C2", "暴风城勇士", 7, text="光环：其他随从+1/+1"),
        _make_dummy_card("C3", "鱼人掠夺者", 1, race="MURLOC"),
    ]

    rep = FuturePickForecaster.evaluate_forecast(
        candidates=candidates,
        drafted_deck=drafted,
        current_pick=12,
    )

    assert rep.detected_archetype == DraftArchetype.MECH_TEMPO
    assert rep.archetype_lock_confidence_pct >= 80.0
    assert rep.best_pick_name == "机械巨熊"
    assert rep.remaining_picks == 18


def test_what_if_sandbox():
    rep = WhatIfSandbox.simulate_what_if(
        turn=6,
        actual_action_desc="全军走脸抢血8点",
        what_if_action_desc="稳健白吃控场",
        start_friendly_hp=20,
        start_enemy_hp=15,
        start_friendly_board_atk=8,
        start_enemy_board_atk=6,
        opponent_has_aoe_next_turn=True,
    )

    assert rep.branching_turn == 6
    assert len(rep.baseline_branch.horizon_states) == 3
    assert len(rep.what_if_branch.horizon_states) == 3
    assert rep.verdict in ("PARALLEL_SUPERIOR", "PARALLEL_INFERIOR", "EQUAL")
    assert "对战基准" in rep.comparison_table_ascii or "实战基准" in rep.comparison_table_ascii


def test_instant_card_lens():
    lens_titan = InstantCardLens.inspect("生命守卫者阿曼苏尔 (泰坦)")
    assert lens_titan.danger_tier == "EXTREME"
    assert "优先单解" in lens_titan.tactical_advice

    lens_fireball = InstantCardLens.inspect("火球术")
    assert lens_fireball.mana_cost == 4 or lens_fireball.mana_cost == 5
    assert lens_fireball.arena_winrate_impact_pct > 5.0


def test_zero_cloud_engine():
    # 1. Immediate Lethal Test (Offline)
    friendly_minions = [{"name": "海巨人", "attack": 8, "health": 8}]
    friendly_hand = [{"name": "火球术", "type": "SPELL", "damage": 6, "cost": 4, "text": "造成6点伤害"}]
    enemy_minions = []

    dec_lethal = ZeroCloudEngine.evaluate_offline(
        friendly_minions=friendly_minions,
        enemy_minions=enemy_minions,
        friendly_hand=friendly_hand,
        friendly_hp=30,
        enemy_hp=12,  # 8 + 6 = 14 >= 12
        available_mana=4,
        turn=6,
    )

    assert dec_lethal.is_lethal is True
    assert dec_lethal.projected_winrate_pct == 100.0
    assert dec_lethal.execution_latency_ms < 5.0  # < 5ms local CPU execution!

    # 2. Offline Board Trading Test
    enemy_m = [{"name": "敌方3/2", "attack": 3, "health": 2}]
    friendly_m = [{"name": "我方3/4", "attack": 3, "health": 4}]
    dec_trade = ZeroCloudEngine.evaluate_offline(
        friendly_minions=friendly_m,
        enemy_minions=enemy_m,
        friendly_hand=[],
        friendly_hp=20,
        enemy_hp=20,
        available_mana=2,
        turn=3,
    )
    assert dec_trade.is_lethal is False
    assert any("白吃" in a for a in dec_trade.action_sequence)


def test_post_match_talkshow():
    # Win with 0 blunders -> Grade S
    report_win = PostMatchTalkshow.generate_talkshow(
        result="WIN",
        total_turns=8,
        blunder_count=0,
        mvp_card="火球术",
        turning_point_turn=7,
    )
    assert "S" in report_win.match_grade
    assert "火球术" in report_win.podcast_audio_script
    assert len(report_win.podcast_audio_script) > 50

    # Loss with blunders -> Grade C
    report_loss = PostMatchTalkshow.generate_talkshow(
        result="LOSS",
        total_turns=6,
        blunder_count=3,
        turning_point_turn=4,
    )
    assert "C" in report_loss.match_grade
    assert "伏笔" in report_loss.podcast_audio_script
