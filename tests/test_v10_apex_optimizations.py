"""
Unit tests for v10 Apex Grandmaster Edition optimizations:
1. Live Topdeck & Miracle Out Matrix
2. Multi-Turn Lookahead & Counter-Response Forecaster
3. Adaptive Game Phase State Machine
4. Tactical Leak Buster & Missed Lethal Detector
5. Capsule HUD & Global Hotkeys
6. Dual-Language i18n Localization Engine
"""

import json
from unittest.mock import MagicMock
import pytest

from core.card_db import CardInfo
from core.topdeck_matrix import TopdeckMatrix, TopdeckMatrixReport
from core.multi_turn_lookahead import MultiTurnLookahead, LookaheadForecastReport
from core.game_phase_machine import GamePhaseMachine, GamePhase
from core.leak_buster import LeakBuster, LeakType, LeakAuditSummary
from core.capsule_hud import CapsuleHUD, CapsuleDisplayData
from core.global_hotkeys import GlobalHotkeyManager, HotkeyID
from core.i18n_engine import I18nEngine, t
from core.web_companion import WebCompanionServer


def _make_dummy_card(card_id: str, name: str, cost: int, card_type: str = "MINION", text: str = "", attack: int = 3, health: int = 3, mechanics=None):
    return CardInfo(
        id=card_id,
        name=name,
        cost=cost,
        card_type=card_type,
        text=text,
        attack=attack,
        health=health,
        rarity="COMMON",
        card_class="MAGE",
        mechanics=mechanics or [],
    )


def test_topdeck_matrix_lethal_and_miracle():
    fireball = _make_dummy_card("FB", "火球术", 4, card_type="SPELL", text="造成6点伤害")
    flamestrike = _make_dummy_card("FS", "烈焰风暴", 7, card_type="SPELL", text="对所有敌方随从造成5点伤害")
    chillwind = _make_dummy_card("CY", "冰风雪人", 4, card_type="MINION", text="", attack=4, health=5)
    high_cost = _make_dummy_card("HC", "海巨人", 10, card_type="MINION", text="", attack=8, health=8)

    remaining = [
        (fireball, 1),
        (flamestrike, 1),
        (chillwind, 2),
        (high_cost, 1),
    ]

    # Enemy at 5 HP, player has 0 board atk, 5 mana next turn (can cast Fireball 4 mana for 6 dmg -> Lethal!)
    rep = TopdeckMatrix.evaluate(
        remaining_cards=remaining,
        friendly_hp=20,
        enemy_hp=5,
        friendly_field_atk=0,
        enemy_field_atk=4,
        available_mana=4,  # next turn 5
        draw_count=1,
    )

    assert rep.total_remaining == 5
    assert rep.spell_count == 2
    assert rep.minion_count == 3
    assert len(rep.miracle_outs) >= 1
    assert rep.miracle_outs[0].card_name == "火球术"
    assert rep.miracle_outs[0].tag == "终结斩杀"
    assert rep.p_draw_any_miracle_pct == pytest.approx(20.0, 0.1)
    assert "火球术" in rep.summary_markdown


def test_topdeck_matrix_survival_miracle():
    flamestrike = _make_dummy_card("FS", "烈焰风暴", 7, card_type="SPELL", text="对所有敌方随从造成5点伤害")
    wisp = _make_dummy_card("WP", "小精灵", 0, card_type="MINION", text="", attack=1, health=1)
    remaining = [
        (flamestrike, 1),
        (wisp, 3),
    ]

    # Friendly HP = 4, enemy has 10 field attack (Fatal danger!), mana = 8
    rep = TopdeckMatrix.evaluate(
        remaining_cards=remaining,
        friendly_hp=4,
        enemy_hp=30,
        friendly_field_atk=2,
        enemy_field_atk=10,
        available_mana=8,
        draw_count=2,
    )

    assert len(rep.miracle_outs) == 1
    assert rep.miracle_outs[0].card_name == "烈焰风暴"
    assert rep.miracle_outs[0].category == "AOE_CLEAR"
    # Drawing 2 cards from 4 remaining where 1 is miracle out: 1 - C(3,2)/C(4,2) = 1 - 3/6 = 50%
    assert rep.p_draw_any_miracle_pct == pytest.approx(50.0, 0.1)


def test_multi_turn_lookahead():
    friendly = [
        {"attack": 3, "health": 3},
        {"attack": 4, "health": 4},
        {"attack": 2, "health": 2},
    ]
    enemy = [
        {"attack": 4, "health": 4},
    ]

    # Turn 6 vs Mage (Mage turn 7 Flamestrike hits for 5)
    rep = MultiTurnLookahead.evaluate_horizon(
        friendly_minions=friendly,
        enemy_minions=enemy,
        friendly_hp=25,
        enemy_hp=20,
        opponent_class="Mage",
        current_turn=6,
    )

    assert rep.current_turn == 6
    assert rep.opponent_class == "MAGE"
    assert len(rep.candidate_outcomes) == 3
    # Swarm vs Tempo Develop vs Trade
    strategies = [c.play_strategy for c in rep.candidate_outcomes]
    assert "SWARM_EXPAND" in strategies
    assert "TEMPO_DEVELOP" in strategies
    assert "DEFENSIVE_TRADE" in strategies

    # In turn 6 against Mage Flamestrike, Swarm has critical/risky punish
    swarm_candidate = next(c for c in rep.candidate_outcomes if c.play_strategy == "SWARM_EXPAND")
    assert swarm_candidate.t1_opponent_counter_card == "烈焰风暴"
    assert "烈焰风暴" in rep.forecast_table_ascii
    assert rep.anti_punish_plan_b != ""


def test_game_phase_machine_transitions():
    # Mulligan
    mulligan = GamePhaseMachine.evaluate(current_turn=0, friendly_hp=30, enemy_hp=30)
    assert mulligan.phase == GamePhase.MULLIGAN
    assert mulligan.tempo_weight > mulligan.card_advantage_weight

    # Early Game
    early = GamePhaseMachine.evaluate(current_turn=2, friendly_hp=30, enemy_hp=30)
    assert early.phase == GamePhase.EARLY_GAME
    assert early.tempo_weight >= 1.8

    # Mid Game
    mid = GamePhaseMachine.evaluate(current_turn=6, friendly_hp=30, enemy_hp=30)
    assert mid.phase == GamePhase.MID_GAME

    # Late Game
    late = GamePhaseMachine.evaluate(current_turn=9, friendly_hp=30, enemy_hp=30)
    assert late.phase == GamePhase.LATE_GAME
    assert late.face_pressure_weight > late.tempo_weight

    # Fatigue
    fatigue = GamePhaseMachine.evaluate(current_turn=14, remaining_deck_count=1, friendly_hp=20, enemy_hp=8)
    assert fatigue.phase == GamePhase.FATIGUE
    assert fatigue.face_pressure_weight >= 2.0

    # Low HP in Fatigue: survival weight spikes
    fatigue_low = GamePhaseMachine.evaluate(current_turn=14, remaining_deck_count=1, friendly_hp=8, enemy_hp=8)
    assert fatigue_low.survival_weight > 2.0


def test_leak_buster_missed_lethal_and_sequencing():
    actions = [
        # Played minion first
        {"type": "PLAY_CARD", "name": "淡水鳄", "card_type": "MINION"},
        # Then drew cards
        {"type": "PLAY_CARD", "name": "奥术智慧", "card_type": "SPELL"},
    ]

    leaks = LeakBuster.audit_turn(
        turn=5,
        action_sequence=actions,
        start_mana=5,
        spent_mana=5,
        enemy_hp=8,
        board_total_lethal_damage=12,  # had lethal!
    )

    types = [l.leak_type for l in leaks]
    assert LeakType.MISSED_LETHAL in types
    assert LeakType.SUBOPTIMAL_DRAW_ORDER in types

    # Match audit summary
    turns_data = [
        {
            "turn": 5,
            "actions": actions,
            "start_mana": 5,
            "spent_mana": 5,
            "enemy_hp": 8,
            "board_lethal_damage": 12,
        }
    ]
    summary = LeakBuster.audit_match(turns_data, result="LOSS")
    assert summary.total_leaks >= 2
    assert summary.leak_score < 70.0
    assert "Sequencing" in summary.radar_scores
    assert "LethalAwareness" in summary.radar_scores


def test_capsule_hud_formatting():
    data = CapsuleHUD.format_display(
        has_lethal=True,
        lethal_desc="场面直伤完全斩杀",
        primary_action="火球术打脸",
        winrate_pct=88.5,
        miracle_card="烈焰风暴",
        miracle_pct=25.0,
        is_capsule_active=True,
    )

    assert data.has_lethal is True
    assert "⚡斩杀!" in data.status_summary_line
    assert "火球术打脸" in data.status_summary_line
    assert "胜率88%" in data.status_summary_line
    assert "神抽:烈焰风暴(25%)" in data.status_summary_line
    d = data.to_dict()
    assert d["is_capsule_active"] is True
    assert d["winrate_pct"] == 88.5


def test_global_hotkeys_and_i18n():
    # Global hotkey manager
    mgr = GlobalHotkeyManager.get_instance()
    executed = []

    def _sample_cb():
        executed.append("TRIGGERED")

    mgr.register_callback(HotkeyID.TOGGLE_OVERLAY, _sample_cb)
    res = mgr.simulate_trigger(HotkeyID.TOGGLE_OVERLAY)
    assert res is True
    assert "TRIGGERED" in executed

    # I18n engine
    i18n = I18nEngine.get_instance()
    i18n.set_locale("zh-CN")
    assert i18n.translate("app_title") == "炉石传说 竞技场大师 AI 助手"
    assert t("topdeck_miracle") == "翻盘神抽"

    # Switch to English
    i18n.set_locale("en-US")
    assert i18n.translate("app_title") == "Hearthstone Arena Grandmaster AI"
    assert t("topdeck_miracle") == "Miracle Out"

    # Reset back to zh-CN
    i18n.set_locale("zh-CN")


def test_web_companion_v10_state_and_endpoints():
    WebCompanionServer.update_state({
        "game_phase": "MID_GAME",
        "game_phase_zh": "中期资源交换",
        "game_phase_weights": {"tempo": 1.3, "face_pressure": 1.0},
        "leak_score": 92.5,
        "leak_grade": "S 宗师无暇",
        "capsule_summary": "⚡斩杀! | 火球打脸 | 胜率95%",
    })

    st = WebCompanionServer.get_state()
    assert st["game_phase"] == "MID_GAME"
    assert st["leak_score"] == 92.5
    assert "⚡斩杀!" in st["capsule_summary"]
