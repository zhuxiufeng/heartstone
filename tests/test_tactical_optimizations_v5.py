"""
Unit tests for Real-time Tactical Optimizations Suite (v5 & v6):
- Next-Turn Key Threat Cards Radar
- Draw & RNG First Directive
- Lethal Cushion & Safety Margin Analysis
- Interactive Step Checklist & Progress Tracker
- Plan A vs Plan B Dual Route Comparison
- Board Overlay AOE Breakpoint Halos & Golden Beacon
- Tactical TTS Callouts
- Negative Deduction Engine (Hand reading unplayed mana elimination)
- Ghost Board Post-Trade Preview (Surviving health & casualty projections)
- RNG & Discover Cumulative Probability Engine
- Arena 12-Win Deck Role & Tool Quota Radar
- Personal Weakness Profiler & Multi-Match History
- Mobile Companion Two-Way Control (Checklist toggle & Plan A/B switch)
"""

import json
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from pathlib import Path
import pytest
from PyQt5.QtWidgets import QApplication
_qapp = QApplication.instance() or QApplication([])

from core.burst_damage_guard import BurstDamageGuard
from core.sequence_optimizer import SequenceOptimizer
from core.ai_engine import AiEngine
from core.card_db import CardDatabase, CardInfo, FALLBACK_CARDS_SAMPLE
from core.sound_engine import SoundEngine
from core.hand_tracker import HandTracker
from core.rng_probability_engine import RngProbabilityEngine
from core.draft_quota_tracker import DraftQuotaTracker
from core.personal_weakness_profiler import PersonalWeaknessProfiler, BlunderEntry
from core.web_companion import WebCompanionServer, _CURRENT_STATE
from ui.overlay import OverlayWindow
from ui.board_overlay import BoardTacticalOverlay


def test_next_turn_key_threat_cards():
    # Test Mage with 7 mana (Flamestrike)
    mage_threats = BurstDamageGuard.get_next_turn_key_cards("MAGE", 7)
    assert len(mage_threats) > 0
    names = [t["name"] for t in mage_threats]
    assert "烈焰风暴" in names
    flamestrike = next(t for t in mage_threats if t["name"] == "烈焰风暴")
    assert flamestrike["cost"] in [7, "7", "7费"]
    assert "全场" in flamestrike["effect"]

    # Test Priest with 4 mana
    priest_threats = BurstDamageGuard.get_next_turn_key_cards("PRIEST", 4)
    assert len(priest_threats) > 0

    # Test unknown or empty
    empty_threats = BurstDamageGuard.get_next_turn_key_cards("UNKNOWN", 1)
    assert isinstance(empty_threats, list)


def test_draw_first_directive():
    optimizer = SequenceOptimizer()

    # Cards including card draw
    cards = [
        {"name": "奥术智慧", "cost": 3, "text": "抽两张牌"},
        {"name": "火球术", "cost": 4, "text": "造成6点伤害"},
    ]
    advice = optimizer.evaluate_sequence(cards, friendly_minions_can_attack=True, hero_power_available=False)
    assert advice.draw_first_directive != ""
    assert "先行" in advice.draw_first_directive or "抽牌" in advice.draw_first_directive

    # Cards without draw or RNG
    cards_nodraw = [
        {"name": "淡水鳄", "cost": 2, "text": ""},
        {"name": "冰风雪人", "cost": 4, "text": ""},
    ]
    advice_nodraw = optimizer.evaluate_sequence(cards_nodraw, friendly_minions_can_attack=True, hero_power_available=False)
    assert advice_nodraw.draw_first_directive == ""


def test_ai_engine_tactical_v5_fields():
    db = CardDatabase(auto_download=False)
    db._build_indexes(FALLBACK_CARDS_SAMPLE)
    ai = AiEngine(card_db=db, cache_enabled=False)

    hand = [
        CardInfo(id="CS2_029", name="火球术", cost=4, card_type="SPELL", text="造成6点伤害"),
        CardInfo(id="CS2_188", name="叫嚣的矮人", cost=1, attack=2, health=1, card_type="MINION", text="战吼：本回合使一个随从获得+2攻击力"),
    ]

    rec = ai.evaluate_play_turn(
        turn_number=6,
        current_mana=6,
        hand_cards=hand,
        friendly_board=["淡水鳄 (2/3)"],
        enemy_board=["冰风雪人 (4/5)"],
        opponent_class="Mage",
        friendly_hp=20,
        enemy_hp=8,
    )

    assert rec is not None
    assert isinstance(rec.checklist_steps, list)
    assert len(rec.checklist_steps) > 0
    assert isinstance(rec.next_turn_threat_cards, list)
    assert len(rec.next_turn_threat_cards) > 0
    assert hasattr(rec, "lethal_cushion")
    assert hasattr(rec, "plan_b_steps")
    assert hasattr(rec, "rng_report")
    assert hasattr(rec, "personal_weakness_reminder")


def test_step_checklist_matching():
    steps = [
        "打出【法力浮龙】 (消耗 1 费)",
        "打出【火球术】",
        "随从 3/2 攻击 敌方英雄",
        "使用【英雄技能】",
    ]

    # No cards played yet
    completed_0 = OverlayWindow._get_completed_step_indices(steps, [])
    assert len(completed_0) == 0

    # Player played Fireball
    completed_1 = OverlayWindow._get_completed_step_indices(steps, ["火球术"])
    assert completed_1 == {1}

    # Player played Mana Wyrm then Fireball
    completed_2 = OverlayWindow._get_completed_step_indices(steps, ["法力浮龙", "火球术"])
    assert completed_2 == {0, 1}


def test_tactical_callouts():
    sound = SoundEngine()
    sound.notify_tactical_callout("先过牌再出牌")
    sound.notify_tactical_callout("全员走脸压血")
    sound.notify_tactical_callout("准备斩杀")


# =========================================================================
# Advanced Optimization Unit Tests (Negative Deduction, Ghost Board, RNG, Quota, Profiler, Two-Way Web)
# =========================================================================

def test_hand_tracker_negative_deduction():
    ht = HandTracker()
    ht.init_opening_hand(card_count=3, has_coin=True)
    assert len(ht.cards) == 3

    # Opponent passes with 2 mana and 3 mana unspent
    ht.record_turn_mana_passed(2)
    ht.record_turn_mana_passed(3)

    # Cards 0 and 1 were opening keeps and not played at 2/3 mana
    assert "2费站场随从" in ht.cards[0].excluded_roles
    assert "3费站场随从" in ht.cards[0].excluded_roles
    assert "排除" in ht.cards[0].negative_deduction_note

    deductions = ht.get_negative_deductions()
    assert len(deductions) >= 2
    assert deductions[0]["slot"] in (1, 2)
    assert "排除" in deductions[0]["deduction"]


def test_ghost_board_post_trade_preview():
    overlay = BoardTacticalOverlay()
    overlay._friendly_minions = [
        {"name": "淡水鳄", "atk": 2, "health": 3},
        {"name": "法力浮龙", "atk": 1, "health": 3},
    ]
    overlay._enemy_minions = [
        {"name": "叫嚣的矮人", "atk": 2, "health": 1},
    ]
    overlay._optimal_trades = ["淡水鳄 攻击 叫嚣的矮人"]

    f_ghosts, e_ghosts = overlay._compute_ghost_board()
    # Crocodile attacked 2/1 Abusive Sergeant -> takes 2 damage -> post_hp = 1, survives
    assert f_ghosts[0]["survived"] is True
    assert f_ghosts[0]["post_hp"] == 1
    # Abusive Sergeant is killed
    assert e_ghosts[0]["killed"] is True

    summary = overlay.get_ghost_board_summary()
    assert "淡水鳄 (2/1)" in summary
    assert "叫嚣的矮人" in summary


def test_rng_probability_engine():
    # Variable damage: Crackle 3-6 damage vs 4 HP
    odds = RngProbabilityEngine.evaluate_variable_damage("连环爆裂", 3, 6, "冰风雪人", 4)
    # Outcomes: 3 (fail), 4 (kill), 5 (kill), 6 (kill) -> 3/4 = 0.75
    assert odds.kill_probability == 0.75
    assert odds.survival_probability == 0.25
    assert "优势博弈" in odds.tactical_verdict

    # Missile hits: Arcane Missiles (3 missiles) vs 1 HP minion when 2 total targets exist
    missile = RngProbabilityEngine.evaluate_missile_hits(missiles_count=3, target_name="报告兵", target_hp=1, other_targets_count=1)
    # p = 0.5, P(at least 1 hit in 3 missiles) = 1 - 0.5^3 = 0.875
    assert abs(missile.kill_probability - 0.875) < 1e-4

    # Discover pool odds: 3-card pick
    disc = RngProbabilityEngine.evaluate_discover_pool("MAGE")
    assert disc.hard_removal_odds_pct > 0.0
    assert disc.aoe_clear_odds_pct > 0.0
    assert "三选一命中概率" in disc.summary_text

    # Scan hand for RNG
    hand = [CardInfo(id="GVG_038", name="连环爆裂", cost=2, card_type="SPELL", text="造成3到6点伤害")]
    enemies = [{"name": "雪人", "health": 4}]
    rep = RngProbabilityEngine.scan_hand_for_rng(hand, enemies, "SHAMAN")
    assert rep is not None
    assert rep.damage_odds is not None
    assert "连环爆裂" in rep.summary_badge


def test_draft_quota_tracker():
    tracker = DraftQuotaTracker()
    card_early = CardInfo(id="CS2_120", name="淡水鳄", cost=2, attack=2, health=3, card_type="MINION", text="")
    roles = tracker.classify_card(card_early)
    assert roles["early_tempo"] is True
    assert roles["hard_removal"] is False

    card_removal = CardInfo(id="CS2_022", name="变形术", cost=4, card_type="SPELL", text="使一个随从变形为1/1的绵羊。")
    roles_rem = tracker.classify_card(card_removal)
    assert roles_rem["hard_removal"] is True

    # Check deck quotas with empty deck at pick 20
    empty_deck = []
    quota_report = tracker.evaluate_deck_quotas(empty_deck, pick_number=20)
    assert len(quota_report.quotas) > 0
    assert quota_report.short_status_strip != ""
    assert "战术短板" in quota_report.most_urgent_need

    # Bonus evaluation: urgent deficit bonus should be positive (+14) when lacking hard removal at pick 20
    deck_midway = [card_early] * 19
    bonus = tracker.calculate_quota_score_bonus(card_removal, deck_midway, pick_number=20)
    assert bonus >= 14


def test_personal_weakness_profiler(tmp_path: Path):
    test_file = tmp_path / "test_weakness.json"
    profiler = PersonalWeaknessProfiler(file_path=test_file)

    blunders = [
        BlunderEntry(turn=4, blunder_type="MANA_WASTE", description="空耗3点法力未转技能", impact_score=6),
        BlunderEntry(turn=5, blunder_type="MANA_WASTE", description="空耗2点法力", impact_score=5),
        BlunderEntry(turn=7, blunder_type="AOE_OVEREXTEND", description="对阵法师过铺被烈焰风暴全清", impact_score=8),
    ]

    profiler.record_match_blunders(
        match_id="M_TEST_01",
        hero_class="法师",
        opponent_class="牧师",
        result="LOSS",
        total_turns=8,
        blunders=blunders,
    )

    diagnosis = profiler.diagnose_weaknesses()
    assert diagnosis.total_matches == 1
    assert diagnosis.total_turns_analyzed == 8
    assert diagnosis.category_counts["MANA_WASTE"] == 2
    assert len(diagnosis.top_blind_spots) > 0

    # Test real-time turn alert
    alert = profiler.get_realtime_turn_alert(turn=4, current_mana=4, opponent_class="牧师")
    assert alert is not None
    assert "个人习惯提醒" in alert


def test_web_companion_two_way_interaction():
    WebCompanionServer.update_state({
        "mode": "PLAY",
        "turn": 3,
        "mana": 3,
        "max_mana": 3,
        "plan_a_steps": ["打出淡水鳄", "攻击敌方随从"],
        "plan_b_steps": ["转英雄技能点脸"],
    })

    state = WebCompanionServer.get_state()
    assert state["turn"] == 3
    assert len(state["plan_a_steps"]) == 2

    # Simulate mobile client toggling checklist item
    checked_set = set(state.get("checked_steps", []))
    checked_set.add(0)
    WebCompanionServer.update_state({"checked_steps": sorted(list(checked_set))})
    assert WebCompanionServer.get_state()["checked_steps"] == [0]

    # Simulate mobile client switching to Plan B
    WebCompanionServer.update_state({"active_plan": "B"})
    assert WebCompanionServer.get_state()["active_plan"] == "B"
