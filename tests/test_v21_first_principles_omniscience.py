"""
Tests for v21 First-Principles Omniscience Suite & Real-Time Live Win Rate Telemetry:
1. Live Win Rate Telemetry Gauge & Delta Momentum
2. Minimax AOE Overextension Guard & Breakpoint Fuse
3. Bayesian Hand Role Fingerprinting & Retention Age
4. Fatigue & Endgame Horizon Calculator
5. Draft Dynamic Archetype Convergence & Marginal Synergy Delta
6. AI Engine Play Turn Integration
"""

import pytest
from core.ai_engine import AiEngine, CardEvaluation, PlayRecommendation
from core.aoe_radar import AOEOverextensionGuard, OverextensionAssessment
from core.card_db import CardInfo
from core.fatigue_endgame_horizon import FatigueEndgameHorizon, FatigueEndgameReport, EndgameVerdict
from core.hand_age_intel import HandAgeIntel, HandAgeIntelReport, CardOriginType
from core.variance_evaluator import VarianceEvaluator, VariancePolicyReport
from core.winrate_estimator import WinRateEstimator, WinRateReport


def test_live_winrate_estimator_and_delta():
    """Verify WinRateEstimator returns accurate real-time win rate, key driver and tier."""
    report = WinRateEstimator.calculate_winrate(
        friendly_hp=28,
        enemy_hp=14,
        friendly_board_atk=7,
        enemy_board_atk=1,
        friendly_minion_count=2,
        enemy_minion_count=1,
        friendly_hand_count=5,
        enemy_hand_count=2,
        current_turn=6,
        has_immediate_lethal=False,
    )
    assert report.winrate_pct >= 65.0
    assert "优势" in report.win_tier or "胜券在握" in report.win_tier or "DOMINANT" in report.win_tier or "FAVORED" in report.win_tier
    assert report.key_advantage_factor != ""

    # Test lethal shortcut clamps to 100%
    lethal_report = WinRateEstimator.calculate_winrate(
        friendly_hp=10,
        enemy_hp=5,
        friendly_board_atk=6,
        enemy_board_atk=0,
        friendly_minion_count=2,
        enemy_minion_count=0,
        friendly_hand_count=1,
        enemy_hand_count=1,
        current_turn=6,
        has_immediate_lethal=True,
    )
    assert lethal_report.winrate_pct == 100.0


def test_aoe_overextension_guard():
    """Verify AOE Overextension Guard detects breakpoint fuse against signature AOEs."""
    # Friendly board with 4 minions vulnerable to Flamestrike (4 damage AOE)
    vulnerable_minions = [
        {"name": "Murloc Raider", "attack": 2, "health": 1},
        {"name": "Bloodfen Raptor", "attack": 3, "health": 2},
        {"name": "River Crocolisk", "attack": 2, "health": 3},
        {"name": "Chillwind Yeti", "attack": 4, "health": 4},
    ]

    assessment = AOEOverextensionGuard.check_overextension(
        friendly_minions=vulnerable_minions,
        opponent_class="MAGE",
        next_turn_mana=7,
        enemy_hp=20,
    )

    assert assessment.is_overextended is True
    assert assessment.risk_level in ["CRITICAL_FUSE", "WARNING"]
    assert assessment.lethal_wipe_pct >= 60.0
    assert "熔断" in assessment.fuse_alert_text or "警报" in assessment.fuse_alert_text
    assert "烈焰风暴" in assessment.signature_threat_aoe

    # Board with high health minions should be SAFE
    resilient_minions = [
        {"name": "Boulderfist Ogre", "attack": 6, "health": 7},
        {"name": "Ironbark Protector", "attack": 8, "health": 8},
    ]
    safe_assessment = AOEOverextensionGuard.check_overextension(
        friendly_minions=resilient_minions,
        opponent_class="MAGE",
        next_turn_mana=7,
        enemy_hp=20,
    )
    assert safe_assessment.is_overextended is False
    assert safe_assessment.risk_level == "SAFE"


def test_bayesian_hand_fingerprinting():
    """Verify Bayesian Hand Role Fingerprinting accurately categorizes long-held cards."""
    intel = HandAgeIntel()

    # Slot 1 kept in mulligan, slot 2 redrawn, slot 3 drawn on turn 2
    intel.record_mulligan(hand_size=2, kept_slots=[1])
    intel.record_card_drawn(turn=2, is_created=False)
    intel.record_card_drawn(turn=3, is_created=True)

    # Fast forward to turn 6
    report = intel.update_turn(6)
    assert len(report.cards) >= 3

    slot1_card = next(c for c in report.cards if c.slot == 1)
    assert slot1_card.hold_turns >= 4
    assert slot1_card.is_dormant_threat is True
    assert "硬解/全场AOE" in slot1_card.bayesian_role_badge
    assert slot1_card.bayesian_prob_pct >= 85
    assert "严禁单核裸下" in slot1_card.counter_strategy

    slot4_card = next(c for c in report.cards if c.slot == 4)
    assert "衍生" in slot4_card.bayesian_role_badge


def test_fatigue_endgame_horizon():
    """Verify Fatigue and Endgame Horizon Clock calculates accurate clock turns and verdicts."""
    # Deck exhausted, opponent has 0 cards left, we have 1 card left
    fatigue_report = FatigueEndgameHorizon.calculate_endgame_horizon(
        my_deck_count=4,
        my_hand=["火球术", "寒冰箭"],
        my_hp=25,
        my_armor=0,
        opp_deck_count=1,
        opp_hand_count=1,
        opp_hp=8,
        opp_armor=0,
        opp_class="WARRIOR",
        current_turn=14,
    )
    assert fatigue_report.opp_clock_turns <= 3
    assert fatigue_report.verdict in [EndgameVerdict.RESOURCE_DOMINANCE, EndgameVerdict.FATIGUE_RACE_EQUAL]
    assert "疲劳" in fatigue_report.verdict_label or "掌控" in fatigue_report.verdict_label


def test_draft_marginal_synergy_and_archetype_convergence():
    """Verify Dynamic Archetype Convergence calculates marginal synergy delta and archetype fit tag."""
    engine = AiEngine()

    card_2drop = CardInfo(
        id="CS2_120",
        name="河道鳄鱼",
        cost=2,
        card_type="MINION",
        rarity="FREE",
        card_class="NEUTRAL",
        attack=2,
        health=3,
        text="",
        mechanics=["BEAST"],
    )

    card_expensive = CardInfo(
        id="CS2_182",
        name="冰风雪人",
        cost=4,
        card_type="MINION",
        rarity="COMMON",
        card_class="NEUTRAL",
        attack=4,
        health=5,
        text="",
        mechanics=[],
    )

    # Deck with 12 picks and congested 4-drops
    congested_deck = [card_expensive] * 6 + [card_2drop] * 2 + [card_expensive] * 3

    draft_rec = engine.evaluate_draft_pick(
        hero_class="HUNTER",
        candidates=[card_2drop, card_expensive],
        deck_so_far=congested_deck,
        use_llm=False,
    )
    evals = draft_rec.cards_evaluations

    # 4-drop should be penalized for curve congestion
    yeti_eval = next(e for e in evals if e.card_name == "冰风雪人")
    assert yeti_eval.marginal_delta <= -10.0
    assert "拥堵" in yeti_eval.archetype_fit_tag

    # 2-drop should be rewarded for filling critical missing 2-drop curve
    croc_eval = next(e for e in evals if e.card_name == "河道鳄鱼")
    assert croc_eval.marginal_delta >= 10.0
    assert "急缺补强" in croc_eval.archetype_fit_tag


def test_ai_engine_play_turn_v21_integration():
    """Verify evaluate_play_turn integrates all 5 First-Principles features and live win rate."""
    engine = AiEngine()

    hand_card = CardInfo(
        id="CS2_029",
        name="火球术",
        cost=4,
        card_type="SPELL",
        rarity="FREE",
        card_class="MAGE",
        attack=None,
        health=None,
        text="造成6点伤害。",
        mechanics=[],
    )

    rec: PlayRecommendation = engine.evaluate_play_turn(
        turn_number=7,
        current_mana=7,
        hand_cards=[hand_card],
        friendly_board=["冰风雪人(4/5)", "淡水鳄(2/3)"],
        enemy_board=["闪金镇步兵(1/2)"],
        opponent_class="PRIEST",
        friendly_hp=26,
        enemy_hp=12,
        use_llm=False,
    )

    # Live Win Rate verification
    assert rec.live_winrate_report is not None
    assert rec.live_winrate_pct >= 50.0
    assert rec.live_winrate_tier != ""
    assert rec.live_winrate_driver != ""

    # Overextension Guard verification
    assert rec.overextension_assessment is not None
    assert isinstance(rec.overextension_assessment, OverextensionAssessment)

    # Fatigue Endgame verification
    assert rec.fatigue_endgame_report is not None
    assert isinstance(rec.fatigue_endgame_report, FatigueEndgameReport)

    # Bayesian Hand Intel verification
    assert rec.bayesian_hand_report is not None
    assert isinstance(rec.bayesian_hand_report, HandAgeIntelReport)
