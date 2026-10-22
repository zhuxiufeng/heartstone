"""
Unit tests for v15 Cosmic Singularity (神域奇点版) optimizations:
1. Micro-Meta Climate Radar & Live Deck Drift
2. Deep Secret & Cascade Causal Forest
3. Bio-Feedback Tilt & Flow State Guardian
4. Opponent Hover Telemetry & Intent Radar
5. Auto Highlight Reel & Shorts Generator
6. Universal Battlegrounds Mode Reactor
"""

import pytest

from core.micro_meta_climate import (
    MicroMetaClimateRadar, MicroMetaReport, MetaClimateType, ClimateDriftMultipliers
)
from core.secret_causal_forest import (
    SecretCausalForest, OptimalProbeSequence, SecretProbeStep, ProbeActionType
)
from core.flow_tilt_guardian import (
    FlowTiltGuardian, FlowTiltStatus, TiltRiskTier
)
from core.hover_intent_radar import (
    HoverIntentRadar, OpponentIntentAlert, SubconsciousIntent
)
from core.auto_highlight_reel import (
    AutoHighlightReel, HighlightReelPackage, HighlightClimaxType, StoryboardFrame
)
from core.battlegrounds_mode_reactor import (
    BattlegroundsModeReactor, BGsReactorReport, BGsCompType, TavernUpgradeEV, CombatSimulationResult
)


def test_micro_meta_climate():
    # 1. Aggro overload scenario
    aggro_matches = [
        {"opp_class": "Hunter", "opp_archetype": "AGGRO_FACE", "duration_turns": 5},
        {"opp_class": "DemonHunter", "opp_archetype": "AGGRO_PIRATE", "duration_turns": 6},
        {"opp_class": "Hunter", "opp_archetype": "FACE_HUNTER", "duration_turns": 5},
        {"opp_class": "Paladin", "opp_archetype": "AGGRO_PALADIN", "duration_turns": 6},
        {"opp_class": "Priest", "opp_archetype": "CONTROL_PRIEST", "duration_turns": 14},
    ]
    rep_aggro = MicroMetaClimateRadar.analyze_recent_meta(aggro_matches)
    assert rep_aggro.climate_type == MetaClimateType.AGGRO_OVERLOAD
    assert rep_aggro.aggro_ratio_pct >= 60.0
    assert rep_aggro.multipliers.anti_aggro_removal >= 1.30
    assert "快攻" in rep_aggro.mulligan_adjustment_advice

    # 2. Control attrition scenario
    ctrl_matches = [
        {"opp_class": "Warrior", "opp_archetype": "CONTROL_WARRIOR", "duration_turns": 13},
        {"opp_class": "Priest", "opp_archetype": "CONTROL_PRIEST", "duration_turns": 15},
        {"opp_class": "DeathKnight", "opp_archetype": "BLOOD_DK", "duration_turns": 12},
    ]
    rep_ctrl = MicroMetaClimateRadar.analyze_recent_meta(ctrl_matches)
    assert rep_ctrl.climate_type == MetaClimateType.CONTROL_ATTRITION
    assert rep_ctrl.multipliers.greed_value_generation >= 1.30

    # 3. Default empty matches
    rep_default = MicroMetaClimateRadar.analyze_recent_meta([])
    assert rep_default.climate_type == MetaClimateType.BALANCED_ECOSYSTEM


def test_secret_causal_forest():
    friendly_board = [
        {"name": "企鹅小怪", "attack": 1, "health": 1, "can_attack": True},
        {"name": "石拳食人魔", "attack": 6, "health": 7, "can_attack": True},
    ]
    friendly_hand = ["幸运币", "步兵随从", "火球术"]

    # Test Mage with 2 secrets
    seq_mage = SecretCausalForest.calculate_optimal_probes(
        active_secret_count=2,
        opponent_class="Mage",
        friendly_board=friendly_board,
        friendly_hand=friendly_hand,
        available_mana=6,
    )
    assert len(seq_mage.steps) == 3
    # Step 1: Cast coin to test Counterspell
    assert seq_mage.steps[0].probe_type == ProbeActionType.CAST_CHEAP_SPELL
    assert "币" in seq_mage.steps[0].card_or_source_name
    # Step 2: Play low cost minion to test Objection
    assert seq_mage.steps[1].probe_type == ProbeActionType.PLAY_LOW_COST_MINION
    # Step 3: Attack face with pawn
    assert seq_mage.steps[2].probe_type == ProbeActionType.ATTACK_FACE_WITH_PAWN
    assert seq_mage.steps[2].card_or_source_name == "企鹅小怪"

    # Test Hunter secrets
    seq_hunter = SecretCausalForest.calculate_optimal_probes(
        active_secret_count=2,
        opponent_class="Hunter",
        friendly_board=friendly_board,
        friendly_hand=friendly_hand,
    )
    assert seq_hunter.steps[0].probe_type == ProbeActionType.ATTACK_FACE_WITH_PAWN


def test_flow_tilt_guardian():
    # 1. Optimal zen state
    zen = FlowTiltGuardian.evaluate_player_state(
        loss_streak=0,
        avg_turn_sec=28.0,
        click_jitter_apm=75.0,
        consecutive_matches=2,
    )
    assert zen.tilt_tier == TiltRiskTier.OPTIMAL_ZEN
    assert zen.flow_score >= 80.0
    assert zen.is_intervention_needed is False

    # 2. High tilt alert state
    tilt = FlowTiltGuardian.evaluate_player_state(
        loss_streak=3,
        avg_turn_sec=6.5,
        click_jitter_apm=220.0,
        consecutive_matches=7,
    )
    assert tilt.tilt_tier == TiltRiskTier.HIGH_TILT_ALERT
    assert tilt.is_intervention_needed is True
    assert tilt.recommended_cooldown_sec >= 30
    assert "深呼吸" in tilt.spoken_comfort_line


def test_hover_intent_radar():
    friendly_board = [
        {"name": "泰坦阿曼苏尔", "attack": 3, "health": 8},
        {"name": "淡水鳄", "attack": 2, "health": 3},
    ]

    # 1. Burst lethal math: 3 sweeps to player face
    events_burst = [
        {"target_type": "HERO_FACE", "action": "SWEEP_ARROW"},
        {"target_type": "HERO_FACE", "action": "SWEEP_ARROW"},
        {"target_type": "HERO_FACE", "action": "SWEEP_ARROW"},
    ]
    alert_burst = HoverIntentRadar.analyze_hover_telemetry(
        hover_events=events_burst,
        player_health=14,
        friendly_board=friendly_board,
    )
    assert alert_burst.intent == SubconsciousIntent.BURST_LETHAL_MATH
    assert alert_burst.threat_tier == "CRITICAL"
    assert "斩杀" in alert_burst.warning_spoken_line

    # 2. Hard removal targeting: hovered on Aman'Thul for 3.0s
    events_removal = [
        {"target_type": "MINION", "target_name": "泰坦阿曼苏尔", "duration_sec": 3.0},
    ]
    alert_removal = HoverIntentRadar.analyze_hover_telemetry(
        hover_events=events_removal,
        player_health=25,
        friendly_board=friendly_board,
    )
    assert alert_removal.intent == SubconsciousIntent.HARD_REMOVAL_TARGETING
    assert alert_removal.target_entity == "泰坦阿曼苏尔"

    # 3. Hesitation pass: switched hand cards 5 times
    events_hesitation = [
        {"action": "HOVER_CARD"},
        {"action": "HOVER_CARD"},
        {"action": "HOVER_CARD"},
        {"action": "HOVER_CARD"},
        {"action": "HOVER_CARD"},
    ]
    alert_hesitation = HoverIntentRadar.analyze_hover_telemetry(
        hover_events=events_hesitation,
        player_health=25,
        friendly_board=friendly_board,
    )
    assert alert_hesitation.intent == SubconsciousIntent.HESITATION_PASS


def test_auto_highlight_reel():
    turn_snapshots = [
        {"turn": 4, "friendly_hp": 22, "winrate_delta": 5.0, "card_played": "冰霜新星"},
        {"turn": 6, "friendly_hp": 3, "winrate_delta": 45.0, "card_played": "雷诺·杰克逊"},
        {"turn": 8, "friendly_hp": 15, "winrate_delta": 35.0, "card_played": "火球术斩杀"},
    ]

    reel = AutoHighlightReel.generate_highlight_reel(
        match_id="match_test_001",
        turn_snapshots=turn_snapshots,
        match_result="VICTORY",
    )

    assert reel.climax_type == HighlightClimaxType.COMEBACK_CLIMAX
    assert reel.drama_score >= 90.0
    assert "锁血翻盘" in reel.title
    assert len(reel.storyboard) == 3
    assert reel.export_filename == "highlight_match_test_001.mp4"


def test_battlegrounds_mode_reactor():
    # 1. Comp identification (Mech)
    mech_board = [
        {"name": "偏折机器人", "race": "MECH", "attack": 3, "health": 2},
        {"name": "量产型恐吓机", "race": "MECH", "attack": 3, "health": 1},
    ]
    comp = BattlegroundsModeReactor.identify_composition(mech_board)
    assert comp == BGsCompType.MECH

    # 2. Tavern turn evaluation (Healthy, should upgrade to Tier 3)
    rep_healthy = BattlegroundsModeReactor.evaluate_tavern_turn(
        current_tier=2,
        upgrade_cost=4,
        available_gold=5,
        hero_health=32,
        board_minions=mech_board,
    )
    assert rep_healthy.upgrade_eval.should_upgrade_now is True
    assert "升至 3 本" in rep_healthy.upgrade_eval.recommendation_label

    # 3. Tavern turn evaluation (Low HP, stay and stabilize)
    rep_critical = BattlegroundsModeReactor.evaluate_tavern_turn(
        current_tier=3,
        upgrade_cost=6,
        available_gold=7,
        hero_health=12,
        board_minions=mech_board,
    )
    assert rep_critical.upgrade_eval.should_upgrade_now is False
    assert "停留搜牌稳血" in rep_critical.upgrade_eval.recommendation_label

    # 4. Combat simulation
    assert rep_healthy.combat_sim.win_pct >= 0.0
    assert rep_healthy.combat_sim.loss_pct >= 0.0
    assert "最左侧" in rep_healthy.combat_sim.positioning_advice
