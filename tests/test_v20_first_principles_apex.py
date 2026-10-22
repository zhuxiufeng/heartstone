"""
Unit and integration tests for v20 First-Principles Apex Evolution.
Covers the 5 core First-Principles features:
1. Guaranteed Two-Turn Lethal Lockout (次轮必杀锁定推演器)
2. Zero-Friction 2-Turn Mana Flow Optimizer (跨回合费率榨干与顺滑度推演)
3. Dynamic "Who's the Beatdown" Pivot Alert (攻守易势转折点瞬态雷达)
4. In-Match Discover Tri-Pick Lens (实战「发现」三选一即时透镜)
5. Minimum Regret Secret Probing Sequencer (最小期望代价奥秘拆解时序链)
6. Overlay Window v20 Cockpit Integration
"""

from __future__ import annotations

import pytest

try:
    from PyQt5.QtWidgets import QApplication
except ImportError:
    try:
        from PyQt6.QtWidgets import QApplication
    except ImportError:
        QApplication = None

from core.ai_engine import AiEngine
from core.card_db import CardDatabase, CardInfo
from core.config_manager import ConfigManager
from core.live_discover_advisor import LiveDiscoverAdvisor, DiscoverTriPickResult
from core.log_listener import LogListener
from core.mana_efficiency import ManaEfficiencyOptimizer, ManaEfficiencyPlan
from core.ocr_engine import OcrWorker
from core.posture_engine import DynamicPivotTracker, PostureAssessment, PostureEngine
from core.secret_tracker import SecretTracker, TriggerType
from core.two_turn_lethal import TwoTurnLethalEngine, TwoTurnLethalPlan
from ui.overlay import OverlayWindow


@pytest.fixture(scope="session")
def qapp():
    if QApplication is None:
        return None
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


def test_two_turn_lethal_lockout():
    """Verify guaranteed two-turn lethal lockout triggers when margin is solid."""
    friendly_minions = [
        {"name": "石拳食人魔", "atk": 6, "health": 7, "can_attack": True},
        {"name": "冰风雪人", "atk": 4, "health": 5, "can_attack": True},
    ]
    enemy_taunts = []
    hand = [
        CardInfo(id="CS2_029", name="火球术", cost=4, card_type="SPELL"),
    ]

    # Friendly board atk = 10, Fireball = 6, total Turn 1 = 16.
    # Enemy HP = 22 -> residual HP = 6.
    # Turn 2 projected board damage = 10 >= 6.
    # Enemy is Hunter (no heal/armor hero power), hand count = 2.
    plan: TwoTurnLethalPlan = TwoTurnLethalEngine.evaluate_two_turn_lethal(
        friendly_minions=friendly_minions,
        enemy_taunts=enemy_taunts,
        hand_cards=hand,
        available_mana=4,
        enemy_hp=22,
        enemy_armor=0,
        enemy_hand_count=2,
        enemy_class="HUNTER",
        hero_power_damage=1,
        friendly_hp=28,
        enemy_board_attack=5,
    )

    assert plan.is_two_turn_lethal is True
    assert plan.is_guaranteed_lockout is True
    assert "次轮必杀锁定" in plan.lockout_badge
    assert "全员打脸直接压制" in plan.lockout_directive
    assert plan.enemy_residual_hp == 6
    assert plan.projected_turn2_damage >= 10


def test_mana_flow_zero_floating_optimizer():
    """Verify 2-turn zero floating mana calculation and flow tag."""
    # Hand has a 3-cost and a 4-cost minion
    hand = [
        CardInfo(id="1", name="3费随从", cost=3, attack=3, health=4),
        CardInfo(id="2", name="4费随从", cost=4, attack=4, health=5),
    ]

    plan: ManaEfficiencyPlan = ManaEfficiencyOptimizer.calculate_2turn_efficiency(
        hand_cards=hand,
        current_mana=3,
        next_mana=4,
    )

    assert plan is not None
    assert plan.is_zero_waste is True
    assert plan.total_floating_mana == 0
    assert plan.efficiency_pct == 100.0
    assert "费率榨干 100%" in plan.flow_tag
    assert "3费随从" in plan.step_preview
    assert "4费随从" in plan.step_preview


def test_beatdown_pivot_alert_transition():
    """Verify dynamic posture flip detection from CONTROL to AGGRESSIVE."""
    DynamicPivotTracker.reset()

    # Turn N: Defensive control state
    control_assessment = PostureAssessment(
        posture_mode="CONTROL",
        friendly_clock_turns=6,
        enemy_threat_turns=4,
        tempo_score=-2.0,
        card_advantage=0,
        recommended_focus="控场防守",
        detailed_reasoning="场面落后",
    )
    alert1 = DynamicPivotTracker.detect_pivot(
        current=control_assessment,
        enemy_hand_count=4,
        friendly_hp=22,
        enemy_hp=30,
    )
    # First turn sets baseline
    assert alert1.has_pivoted is False

    # Turn N+1: Enemy exhausted hand, player established lethal clock <= 2
    aggro_assessment = PostureAssessment(
        posture_mode="AGGRESSIVE",
        friendly_clock_turns=2,
        enemy_threat_turns=5,
        tempo_score=6.0,
        card_advantage=3,
        recommended_focus="突击抢脸",
        detailed_reasoning="2回合叫杀",
    )
    alert2 = DynamicPivotTracker.detect_pivot(
        current=aggro_assessment,
        enemy_hand_count=1,
        friendly_hp=20,
        enemy_hp=12,
    )

    assert alert2.has_pivoted is True
    assert alert2.pivot_type == "PIVOT_TO_OFFENSE"
    assert "全面转攻" in alert2.banner_badge
    assert "从防守全面转入抢脸" in alert2.action_directive


def test_live_discover_tri_pick_lens():
    """Verify in-match discover tri-pick evaluates cards against active needs."""
    cards = ["火球术", "变羊术", "奥术智慧"]

    # Scenario: Enemy at 10 HP, friendly board attack 6 -> BURST_FINISH need!
    res: DiscoverTriPickResult = LiveDiscoverAdvisor.evaluate_tri_pick(
        candidate_cards=cards,
        friendly_hp=24,
        enemy_hp=10,
        friendly_board_atk=6,
        enemy_board_atk=3,
        hand_size=4,
        available_mana=4,
    )

    assert res.guidance.priority_tier == "BURST_FINISH"
    assert res.best_card is not None
    assert res.best_card.name == "火球术"
    assert res.best_card.tier == "S"
    assert res.best_card.is_best_pick is True
    assert res.lead_margin > 0.0
    assert "实战发现首选: 火球术" in res.verdict_directive
    assert len(res.evaluations) == 3


def test_secret_probing_minimum_regret_sequence():
    """Verify optimal minimum-regret sequence for dismantling opponent secrets."""
    tracker = SecretTracker()
    tracker.add_opponent_secret("MAGE", turn=3)

    friendly_minions = [
        {"name": "白银之手新兵", "atk": 1, "health": 1, "can_attack": True},
        {"name": "提里奥弗丁", "atk": 6, "health": 6, "can_attack": True},
    ]
    hand = [
        CardInfo(id="GAME_005", name="幸运币", cost=0, card_type="SPELL"),
        CardInfo(id="CS2_029", name="火球术", cost=4, card_type="SPELL"),
        CardInfo(id="EX1_019", name="精灵弓箭手", cost=1, card_type="MINION"),
    ]

    probing = tracker.generate_probing_sequence(
        friendly_minions=friendly_minions,
        hand_cards=hand,
        available_mana=4,
    )

    assert probing.has_active_secrets is True
    assert len(probing.steps) >= 3

    # Step 1 must be lowest attack minion face attack (1/1 recruit)
    step1 = probing.steps[0]
    assert step1.action_type == "ATTACK_HERO"
    assert "白银之手新兵" in step1.target_card_or_minion
    assert "1攻" in step1.instruction or "1 攻" in step1.instruction

    # Step 2 should bait spell counter with coin
    step2 = probing.steps[1]
    assert step2.action_type == "CAST_SPELL"
    assert "幸运币" in step2.target_card_or_minion

    # Step 3 should probe objection with low cost minion
    step3 = probing.steps[2]
    assert step3.action_type == "PLAY_MINION"
    assert "精灵弓箭手" in step3.target_card_or_minion


def test_overlay_v20_cockpit_integration(qapp):
    """Verify UI Overlay incorporates all 5 First-Principles Cockpit elements."""
    cfg = ConfigManager("/tmp/test_v20_cfg.json")
    cdb = CardDatabase(auto_download=False)
    cdb.load()
    ai = AiEngine(card_db=cdb)
    ll = LogListener(log_dir="/tmp", card_db=cdb)
    ocr = OcrWorker(card_db=cdb)

    win = OverlayWindow(cfg, cdb, ai, ll, ocr)
    win.show()
    win._switch_to_play_view()

    # 1. Check UI elements exist
    assert hasattr(win, "beatdown_pivot_lbl")
    assert hasattr(win, "secret_probing_lbl")
    assert hasattr(win, "tab_discover_btn")
    assert hasattr(win, "discover_tri_frame")

    # 2. Test Discover Drawer Tab Switch
    win._switch_intel_tab("DISCOVER")
    assert win.discover_tri_frame.isHidden() is False
    assert win.deck_frame.isHidden() is True
    assert win.hand_frame.isHidden() is True

    # 3. Test Discover Triple Simulation
    win._simulate_discover_tri_pick(["火球术", "变羊术", "奥术智慧"])
    assert win.discover_tri_cards_layout.count() == 3
    assert "火球术" in win.discover_tri_verdict_lbl.text()

    win.close()
