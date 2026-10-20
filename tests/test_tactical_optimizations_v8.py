"""
Unit tests for Tactical Optimizations Suite (v8 Ultra/Pro):
1. Opponent Hand Origin & Psychological Mind-Reading
2. Hypergeometric Draw Odds & Topdeck Gamble EV
3. TiltGuard Fatigue & Consecutive Streak Protector
4. Pro Coach Natural Voice Commentary System
5. Highlight & Blunder Frame Recorder & Clip Exporter
6. Multi-Branch Decision Topology Tree Visualizer
"""

import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from pathlib import Path
import numpy as np
import pytest
from PyQt5.QtWidgets import QApplication

_qapp = QApplication.instance() or QApplication([])

from core.card_db import CardInfo
from core.hand_tracker import HandTracker
from core.hypergeometric_odds import HypergeometricOddsEngine, HypergeometricOddsReport
from core.tilt_guard import TiltGuard, TiltReport
from core.sound_engine import SoundEngine
from core.highlight_recorder import HighlightClipRecorder
from core.tactical_tree_visualizer import TacticalDecisionTree, DecisionNode
from core.action_tree_search import ActionBranch, ActionTreeResult


def test_hand_tracker_mind_reading_and_provenance():
    tracker = HandTracker()
    tracker.set_opponent_class("法师")
    tracker.init_opening_hand(card_count=4, has_coin=True)

    # 4th card is coin
    assert tracker.cards[3].is_coin is True
    assert "幸运币" in tracker.cards[3].provenance_badge

    # 1st card is mulligan kept
    assert tracker.cards[0].is_mulligan_keep is True
    assert "起手原留牌" in tracker.cards[0].provenance_badge

    # Turn passes to 5
    tracker.set_turn(5, opponent_mana=4)
    rep = tracker.get_mind_reading_report()
    assert len(rep) == 4
    assert rep[0]["turns_held"] == 4
    assert "起手" in rep[0]["provenance"]


def test_hypergeometric_odds_calculator():
    deck = [
        CardInfo(id="CS2_029", name="火球术", cost=4, card_type="SPELL", text="造成6点伤害。"),
        CardInfo(id="CS2_029", name="火球术", cost=4, card_type="SPELL", text="造成6点伤害。"),
        CardInfo(id="CS2_182", name="冰风雪人", cost=4, attack=4, health=5, card_type="MINION", text=""),
        CardInfo(id="CS2_120", name="淡水鳄", cost=2, attack=2, health=3, card_type="MINION", text=""),
        CardInfo(id="CS2_022", name="变形术", cost=4, card_type="SPELL", text="变形为1/1绵羊。"),
    ]

    # In 5-card deck with 2 Fireballs, drawing 1 card has probability 2/5 = 40.0%
    p = HypergeometricOddsEngine.calculate_prob(deck_size=5, outs=2, draws=1)
    assert p == 40.0

    # Drawing 2 cards in 5-card deck: 1 - C(3,2)/C(5,2) = 1 - 3/10 = 70.0%
    p2 = HypergeometricOddsEngine.calculate_prob(deck_size=5, outs=2, draws=2)
    assert p2 == 70.0

    report: HypergeometricOddsReport = HypergeometricOddsEngine.evaluate_deck_odds(
        remaining_deck=deck,
        enemy_hp=6, # In lethal burn range!
        friendly_hp=5,
        enemy_board_attack=10, # Facing lethal!
        draws_next_turn=1,
    )
    assert report.burn_lethal_outs >= 2
    assert report.burn_lethal_prob_pct == 40.0
    assert "孤注一掷" in report.gamble_recommendation


def test_tilt_guard_fatigue_and_streak():
    tg = TiltGuard.get_instance()
    tg.reset_session()

    # Initial state should be calm
    r1 = tg.evaluate_tilt()
    assert r1.composite_index < 30
    assert r1.is_rest_recommended is False
    assert "巅峰" in r1.tier_label

    # Simulate 3 consecutive losses with quick turns and blunders
    for _ in range(3):
        tg.record_turn_action(duration_sec=2.5, blunders=2)
        tg.record_match_finished(won=False, total_turns=7)

    r2 = tg.evaluate_tilt()
    assert r2.tilt_score >= 50
    assert r2.composite_index >= 50
    assert r2.is_rest_recommended is True
    assert "连败 3" in r2.streak_summary


def test_sound_engine_coach_directives():
    se = SoundEngine.get_instance()
    se.update_settings(sound_enabled=True, tts_enabled=False)

    # Should not throw any exception
    se.notify_coach_directive("LETHAL")
    se.notify_coach_directive("AOE", "烈焰风暴")
    se.notify_coach_directive("GAMBLE")
    se.notify_coach_directive("TILT")


def test_highlight_clip_recorder(tmp_path: Path):
    recorder = HighlightClipRecorder.get_instance()
    recorder.clear()

    # Push sample frames
    img = np.zeros((200, 300, 3), dtype=np.uint8)
    recorder.push_frame(img, turn=5, note="随从大交换")
    recorder.last_capture_time = 0.0 # Force allow next frame
    recorder.push_frame(img, turn=6, note="叫杀时刻")

    assert len(recorder.buffer) == 2

    out_file = str(tmp_path / "highlight.png")
    exported = recorder.export_highlight(
        output_path=out_file,
        event_type="LETHAL_WIN",
        title="测试高光",
        subtitle="斩杀收官",
    )
    assert exported is True
    assert os.path.exists(out_file)
    assert os.path.getsize(out_file) > 100


def test_tactical_decision_tree_topology():
    branch_a = ActionBranch(
        plan_name="方案A: 节奏展开",
        action_sequence=["打出淡水鳄", "随从走脸"],
        mana_spent=2,
        floating_mana=0,
        damage_to_face=4,
        projected_board_attack=6,
        projected_board_health=8,
        surviving_enemy_attack=2,
        ev_score=24.5,
        tactical_intent="按费拍怪",
        projected_winrate=62.0,
        resilience_score=75,
    )
    branch_b = ActionBranch(
        plan_name="方案B: 全力突击",
        action_sequence=["火球术打脸"],
        mana_spent=4,
        floating_mana=0,
        damage_to_face=6,
        projected_board_attack=4,
        projected_board_health=5,
        surviving_enemy_attack=5,
        ev_score=22.0,
        tactical_intent="抢脸搏命",
        projected_winrate=58.0,
        resilience_score=45,
    )
    tree_res = ActionTreeResult(best_branch=branch_a, alternative_branches=[branch_b])

    root = TacticalDecisionTree.build_tree(
        action_tree_res=tree_res,
        current_mana=4,
        friendly_hp=20,
        enemy_hp=12,
        opponent_class="法师",
    )
    assert root.node_type == "ROOT"
    assert len(root.children) == 2 # Branch A and Branch B
    assert len(root.children[0].children) == 2 # Opponent counter responses

    ascii_str = TacticalDecisionTree.to_ascii_tree(root)
    assert "方案A: 节奏展开" in ascii_str
    assert "方案B: 全力突击" in ascii_str

    tree_dict = TacticalDecisionTree.to_dict(root)
    assert tree_dict["node_id"] == "root"
    assert len(tree_dict["children"]) == 2
