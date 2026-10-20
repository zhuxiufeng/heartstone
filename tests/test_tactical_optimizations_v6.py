"""
Unit tests for Real-time Tactical Optimizations Suite (v6 Advanced Phase):
- Matchup Specific Micro-Meta Synergy & Arena Rotation Bias
- Board Resilience & Anti-Wipe Monte Carlo Simulation
- Hands-Free Voice Commander Speech Keyword Dispatcher
- 12-Win Championship DNA Rating & Victory Infographic Exporter
- Rope Emergency Quick-Reboot Macro
- Hover Sandbox Live Preview Simulation
"""

import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from pathlib import Path
import pytest
from PyQt5.QtWidgets import QApplication

_qapp = QApplication.instance() or QApplication([])

from core.card_db import CardInfo
from core.matchup_micro_meta import MatchupMicroMetaEngine
from core.board_resilience_evaluator import BoardResilienceEvaluator
from core.voice_commander import VoiceCommander
from core.championship_dna_exporter import ChampionshipDnaExporter
from core.reboot_macro import RebootMacro
from ui.board_overlay import BoardTacticalOverlay


def test_matchup_micro_meta_aggro_control():
    aoe_card = CardInfo(id="CS2_032", name="烈焰风暴", cost=7, card_type="SPELL", text="对所有敌方随从造成4点伤害。")
    # Against Hunter (Aggro), AOE should get significant score boost (+10)
    res_aggro = MatchupMicroMetaEngine.evaluate_card_matchup_delta(aoe_card, "HUNTER")
    assert res_aggro.score_delta >= 10
    assert "克星" in res_aggro.meta_tag

    # High cost vanilla minion against Hunter should get penalized (-10)
    fat_card = CardInfo(id="CS2_186", name="作战傀儡", cost=7, attack=7, health=7, card_type="MINION", text="")
    res_fat = MatchupMicroMetaEngine.evaluate_card_matchup_delta(fat_card, "HUNTER")
    assert res_fat.score_delta <= -10

    # Draw card against Priest (Control) should get bonus (+10)
    draw_card = CardInfo(id="CS2_023", name="奥术智慧", cost=3, card_type="SPELL", text="抽两张牌。")
    res_ctrl = MatchupMicroMetaEngine.evaluate_card_matchup_delta(draw_card, "PRIEST")
    assert res_ctrl.score_delta >= 10
    assert "续航" in res_ctrl.meta_tag

    # Arena rotation draft meta bias for deathrattle (anti-AOE)
    dr_card = CardInfo(id="FP1_007", name="蛛魔之卵", cost=2, attack=0, health=2, card_type="MINION", text="亡语：召唤一个4/4的蛛魔。")
    meta_bias = MatchupMicroMetaEngine.evaluate_draft_meta_bias("法师", dr_card)
    assert meta_bias.score_delta > 0
    assert "防清场" in meta_bias.meta_tag


def test_board_resilience_evaluator():
    # 1. High resilience board (thick minions + deathrattle + hand refill)
    high_board = [
        {"name": "凯恩·血蹄", "health": 5, "atk": 4, "deathrattle": True},
        {"name": "烈日行者", "health": 5, "atk": 4, "shield": True},
        {"name": "冰风雪人", "health": 5, "atk": 4},
    ]
    rep_high = BoardResilienceEvaluator.evaluate_board_resilience(
        friendly_minions=high_board,
        remaining_hand_size=4,
        opponent_class="Mage",
        opponent_mana=7, # Flamestrike
    )
    assert rep_high.resilience_score >= 70
    assert rep_high.resilience_tier in ("HIGH_RESILIENCE", "BALANCED")
    assert rep_high.wipe_survivor_count >= 2
    assert "韧性" in rep_high.badge_text

    # 2. Vulnerable board (low health + 0 cards in hand)
    low_board = [
        {"name": "鱼人宝宝", "health": 1, "atk": 1},
        {"name": "叫嚣的矮人", "health": 1, "atk": 2},
    ]
    rep_low = BoardResilienceEvaluator.evaluate_board_resilience(
        friendly_minions=low_board,
        remaining_hand_size=0,
        opponent_class="Mage",
        opponent_mana=7,
    )
    assert rep_low.resilience_score < 50
    assert rep_low.resilience_tier == "VULNERABLE_RISK"
    assert "脆弱" in rep_low.detailed_verdict


def test_voice_commander_commands():
    commander = VoiceCommander.get_instance()
    dispatched = []

    def on_cmd(k, t):
        dispatched.append(k)

    commander.register_callback(on_cmd)

    # Test "方案B"
    cmd_b = commander.process_text_input("请切换到方案b")
    assert cmd_b == "PLAN_A" or cmd_b == "PLAN_B"
    assert "PLAN_B" in dispatched

    # Test "打勾"
    cmd_check = commander.process_text_input("已经完成打勾")
    assert cmd_check == "CHECK_STEP"

    # Test "算斩杀"
    cmd_lethal = commander.process_text_input("帮我计算斩杀线")
    assert cmd_lethal == "CHECK_LETHAL"

    # Test "防AOE"
    cmd_aoe = commander.process_text_input("看一下对面下回合高危牌防aoe")
    assert cmd_aoe == "CHECK_AOE"


def test_championship_dna_evaluation_and_export(tmp_path: Path):
    deck = [
        CardInfo(id="CS2_022", name="变形术", cost=4, card_type="SPELL", text="使一个随从变形为1/1的绵羊。"),
        CardInfo(id="CS2_120", name="淡水鳄", cost=2, attack=2, health=3, card_type="MINION", text="野兽"),
        CardInfo(id="CS2_023", name="奥术智慧", cost=3, card_type="SPELL", text="抽两张牌。"),
        CardInfo(id="CS2_182", name="冰风雪人", cost=4, attack=4, health=5, card_type="MINION", text=""),
    ] * 6 # 24 cards

    report = ChampionshipDnaExporter.evaluate_deck_dna(deck, "法师")
    assert report.dna_score >= 60
    assert len(report.strengths) > 0
    assert report.tactical_verdict != ""

    # Test image poster export
    out_img = str(tmp_path / "victory_poster.png")
    exported = ChampionshipDnaExporter.export_victory_infographic(
        output_path=out_img,
        deck=deck,
        hero_class="法师",
        wins=12,
        losses=1,
    )
    assert exported is True
    assert os.path.exists(out_img)
    assert os.path.getsize(out_img) > 1000


def test_reboot_macro_execution():
    # In Linux test environment, should gracefully simulate reboot
    res = RebootMacro.execute_rope_emergency_reboot()
    assert res is True


def test_board_overlay_hover_sandbox():
    overlay = BoardTacticalOverlay()
    overlay._enemy_minions = [
        {"name": "叫嚣的矮人", "health": 1, "atk": 2},
        {"name": "冰风雪人", "health": 5, "atk": 4},
    ]

    # Test hover AOE spell (烈焰风暴 4 damage)
    overlay.set_hovered_card("烈焰风暴", "对所有敌方随从造成4点伤害。")
    assert overlay._hover_damage == 4
    assert overlay._hover_is_aoe is True

    # Test hover direct damage spell (火球术 6 damage)
    overlay.set_hovered_card("火球术", "造成6点伤害。")
    assert overlay._hover_damage == 6
    assert overlay._hover_is_aoe is False

    # Test hover reset
    overlay.set_hovered_card("")
    assert overlay._hover_damage == 0
