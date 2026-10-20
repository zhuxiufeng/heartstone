import pytest
from core.burst_damage_guard import BurstDamageGuard, BurstThreatReport
from core.live_discover_advisor import LiveDiscoverAdvisor, DiscoverGuidance
from core.variance_evaluator import VarianceEvaluator, VariancePolicyReport
from core.hand_tracker import HandTracker
from core.positioning_geometry import PositioningGeometry
from core.action_tree_search import ActionTreeSearch, ActionBranch
from core.card_db import CardInfo


def test_burst_damage_guard_critical_lethal():
    # Mage with 7 mana, 4 board atk vs friendly 11 hp
    # Empty board Mage at 7 mana has 10 burst (Fireball 6 + Frostbolt 3 + HP 1)
    # Total threat: 4 + 10 = 14 damage -> friendly hp 11 -> Deficit = 3 (CRITICAL_LETHAL)
    report = BurstDamageGuard.evaluate_threat(
        opponent_class="MAGE",
        current_turn=6, # next turn is 7
        opponent_board_atk=4,
        friendly_hp=11,
        friendly_armor=0,
        friendly_taunt_hp=0,
    )
    assert isinstance(report, BurstThreatReport)
    assert report.threat_tier == "CRITICAL_LETHAL"
    assert report.total_projected_damage == 14
    assert report.lethal_deficit == 3
    assert "🚨" in report.danger_badge
    assert "必须优先击杀" in report.survival_directive


def test_burst_damage_guard_taunt_absorption():
    # If friendly taunt absorbs 4 atk
    report = BurstDamageGuard.evaluate_threat(
        opponent_class="MAGE",
        current_turn=6,
        opponent_board_atk=4,
        friendly_hp=15,
        friendly_taunt_hp=4,
    )
    # Board damage reduced to 0, empty burst is 10, total 10 vs HP 15 -> Margin 5 (MODERATE)
    assert report.total_projected_damage == 10
    assert report.safety_margin == 5
    assert report.threat_tier == "MODERATE"


def test_live_discover_advisor_priorities():
    # 1. Survival when low HP & high enemy board
    g1 = LiveDiscoverAdvisor.evaluate_discover_need(
        friendly_hp=8,
        enemy_hp=30,
        friendly_board_atk=2,
        enemy_board_atk=8,
        hand_size=4,
    )
    assert g1.priority_tier == "SURVIVAL"
    assert "嘲讽" in g1.guidance_text

    # 2. Burst finisher when enemy is low
    g2 = LiveDiscoverAdvisor.evaluate_discover_need(
        friendly_hp=25,
        enemy_hp=8,
        friendly_board_atk=4,
        enemy_board_atk=3,
        hand_size=4,
    )
    assert g2.priority_tier == "BURST_FINISH"
    assert "直伤" in g2.guidance_text

    # 3. Board clear when heavily behind
    g3 = LiveDiscoverAdvisor.evaluate_discover_need(
        friendly_hp=20,
        enemy_hp=25,
        friendly_board_atk=2,
        enemy_board_atk=12,
        hand_size=4,
    )
    assert g3.priority_tier == "BOARD_CLEAR"
    assert "全场AOE" in g3.guidance_text

    # 4. Value refill when hand is empty
    g4 = LiveDiscoverAdvisor.evaluate_discover_need(
        friendly_hp=20,
        enemy_hp=20,
        friendly_board_atk=5,
        enemy_board_atk=5,
        hand_size=1,
    )
    assert g4.priority_tier == "VALUE_REFILL"
    assert "过牌" in g4.guidance_text


def test_variance_evaluator_policy():
    # Ahead: zero-variance
    r1 = VarianceEvaluator.evaluate_risk_policy(winrate_pct=65.0, planned_actions=["打出【奥术飞弹】"])
    assert r1.recommended_policy == "VARIANCE_FREE"
    assert r1.action_involves_rng is True
    assert "零方差" in r1.variance_directive

    # Behind: miracle line
    r2 = VarianceEvaluator.evaluate_risk_policy(winrate_pct=35.0, planned_actions=["打出【奥术飞弹】"])
    assert r2.recommended_policy == "HIGH_VARIANCE_MIRACLE"
    assert "放手一搏" in r2.variance_directive


def test_hand_tracker_reading_matrix():
    ht = HandTracker()
    ht.set_opponent_class("MAGE")
    ht.init_opening_hand(card_count=3, has_coin=True)
    ht.set_turn(5)

    matrix = ht.get_hand_reading_matrix()
    assert len(matrix) >= 2
    # Coin in slot 3
    assert any(m["slot"] == 3 and m["label"] == "🪙 幸运币" for m in matrix)
    # Mulligan keep held for 4 turns
    keep_card = next(m for m in matrix if m["slot"] == 1)
    assert "🎯" in keep_card["label"]
    assert keep_card["probability_pct"] >= 70.0
    text = ht.get_reading_matrix_text()
    assert "槽位#1" in text
