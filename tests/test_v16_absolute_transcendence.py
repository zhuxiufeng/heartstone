"""
Unit tests for v16 Absolute Transcendence (无极造物版) optimizations:
1. Multi-Agent Council of Champions
2. Webcam Gaze & Blindspot Attention Tracker
3. Multi-Persona Dynamic Voice Matrix
4. Acoustic Emotion & Voice Stress Guard
5. Genetic Deck Architect & Counter-Meta Synthesizer
6. Cross-TCG Universal Theory Engine
"""

import pytest

from core.council_of_champions import (
    CouncilOfChampions, CouncilDebateReport, ChampionPersona, DebateVerdict, ChampionAdvise
)
from core.gaze_attention_tracker import (
    GazeAttentionTracker, GazeTrackingReport, ScreenRegion, RegionAttentionData
)
from core.persona_voice_matrix import (
    PersonaVoiceMatrix, PersonaMatrixResponse, VoicePersona
)
from core.acoustic_emotion_guard import (
    AcousticEmotionGuard, AcousticEmotionReport, AcousticState
)
from core.genetic_deck_architect import (
    GeneticDeckArchitect, SynthesizedDeck
)
from core.universal_tcg_theory import (
    UniversalTcgTheoryEngine, UniversalTheoryReport, TCGAxiomType
)


def test_council_of_champions():
    # 1. Unanimous Aggro when enemy is low and within board reach
    rep_aggro = CouncilOfChampions.convene_council(
        player_hp=20,
        enemy_hp=10,
        board_total_attack=12,
        enemy_threat_level="LOW",
        winrate_pct=22.0,
    )
    assert rep_aggro.verdict == DebateVerdict.UNANIMOUS_AGGRO
    assert "走脸" in rep_aggro.final_recommended_action
    assert rep_aggro.council_consensus_score >= 85.0
    assert len(rep_aggro.opinions) == 3

    # 2. Unanimous Control when lethal threat on enemy board
    rep_ctrl = CouncilOfChampions.convene_council(
        player_hp=8,
        enemy_hp=28,
        board_total_attack=5,
        enemy_threat_level="CRITICAL",
        winrate_pct=45.0,
    )
    assert rep_ctrl.verdict == DebateVerdict.UNANIMOUS_CONTROL
    assert "清光" in rep_ctrl.final_recommended_action

    # 3. Split Council Consensus in mid-game
    rep_split = CouncilOfChampions.convene_council(
        player_hp=25,
        enemy_hp=25,
        board_total_attack=7,
        enemy_threat_level="MODERATE",
        winrate_pct=55.0,
    )
    assert rep_split.verdict == DebateVerdict.SPLIT_COUNCIL_CONSENSUS
    assert rep_split.council_consensus_score > 70.0


def test_gaze_attention_tracker():
    # 1. High-risk visual blindspot: enemy has secrets, player neglected for 12 seconds
    samples_blindspot = [
        {"region": "PLAYER_HAND", "seconds_unattended": 1.0},
        {"region": "ENEMY_BOARD", "seconds_unattended": 2.0},
        {"region": "ENEMY_SECRETS", "seconds_unattended": 14.0},
    ]
    rep_bs = GazeAttentionTracker.evaluate_gaze_distribution(
        gaze_samples=samples_blindspot,
        enemy_has_secrets=True,
    )
    assert rep_bs.active_blindspot_alert is True
    assert "奥秘" in rep_bs.speech_warning
    assert rep_bs.regions[ScreenRegion.ENEMY_SECRETS.value].is_blindspot_alert is True

    # 2. Normal balanced gaze
    rep_normal = GazeAttentionTracker.evaluate_gaze_distribution(
        enemy_has_secrets=False,
        enemy_has_taunt_or_poison=False,
    )
    assert rep_normal.active_blindspot_alert is False
    assert rep_normal.focus_stability_score >= 80.0


def test_persona_voice_matrix():
    # 1. Test 4 persona speeches on LETHAL_CLIMAX
    ctx = {"action": "打脸", "card": "火球术"}
    res_coach = PersonaVoiceMatrix.render_voice("LETHAL_CLIMAX", ctx, VoicePersona.PRO_COACH)
    assert "斩杀确定" in res_coach.spoken_line
    assert res_coach.active_persona == VoicePersona.PRO_COACH

    res_caster = PersonaVoiceMatrix.render_voice("LETHAL_CLIMAX", ctx, VoicePersona.HYPE_CASTER)
    assert "斩杀了" in res_caster.spoken_line

    res_buddy = PersonaVoiceMatrix.render_voice("LETHAL_CLIMAX", ctx, VoicePersona.SARCASTIC_BUDDY)
    assert "踢脸" in res_buddy.spoken_line

    res_zen = PersonaVoiceMatrix.render_voice("LETHAL_CLIMAX", ctx, VoicePersona.ZEN_MASTER)
    assert "万法归一" in res_zen.spoken_line

    # 2. Automatic Zen Master intervention when tilted
    res_tilted = PersonaVoiceMatrix.render_voice(
        "GENERAL_STEP", ctx, VoicePersona.PRO_COACH, is_player_tilted=True
    )
    assert res_tilted.active_persona == VoicePersona.ZEN_MASTER
    assert res_tilted.auto_switched_due_to_tilt is True
    assert "心若止水" in res_tilted.spoken_line


def test_acoustic_emotion_guard():
    # 1. Calm state
    rep_calm = AcousticEmotionGuard.analyze_voice_telemetry(
        pitch_jitter=0.03,
        sigh_detected=False,
        speech_wpm=110.0,
        peak_volume_db=-24.0,
    )
    assert rep_calm.state == AcousticState.CALM_SERENE
    assert rep_calm.frustration_index < 30.0

    # 2. Sigh depressed state
    rep_sigh = AcousticEmotionGuard.analyze_voice_telemetry(
        pitch_jitter=0.08,
        sigh_detected=True,
        speech_wpm=100.0,
        peak_volume_db=-18.0,
    )
    assert rep_sigh.state == AcousticState.HEAVY_SIGH_DEPRESSED
    assert rep_sigh.frustration_index >= 50.0
    assert "叹气" in rep_sigh.comfort_response

    # 3. Explosive rage state
    rep_rage = AcousticEmotionGuard.analyze_voice_telemetry(
        pitch_jitter=0.35,
        sigh_detected=False,
        speech_wpm=220.0,
        peak_volume_db=-3.0,
    )
    assert rep_rage.state == AcousticState.EXPLOSIVE_RAGE
    assert rep_rage.frustration_index >= 75.0
    assert "战术暂停" in rep_rage.action_protocol


def test_genetic_deck_architect():
    # 1. Anti-Aggro synthesis
    deck_aggro = GeneticDeckArchitect.synthesize_counter_deck(
        target_class="Priest",
        climate_type="AGGRO_OVERLOAD",
        generations=20,
    )
    assert "反快攻" in deck_aggro.deck_name
    assert deck_aggro.fitness_score >= 75.0
    assert len(deck_aggro.card_names) == 30
    assert deck_aggro.deckstring.startswith("AAEBA")

    # 2. Anti-Control synthesis
    deck_ctrl = GeneticDeckArchitect.synthesize_counter_deck(
        target_class="Warrior",
        climate_type="CONTROL_ATTRITION",
        generations=15,
    )
    assert "破控" in deck_ctrl.deck_name


def test_universal_tcg_theory():
    # 1. Tempo Initiative Axiom (MTG)
    rep_tempo = UniversalTcgTheoryEngine.evaluate_board_philosophy(
        player_hp=25,
        enemy_hp=12,
        my_board_mana_value=12,
        enemy_board_mana_value=4,
        my_hand_count=3,
        enemy_hand_count=3,
    )
    assert rep_tempo.dominant_axiom == TCGAxiomType.TEMPO_INITIATIVE
    assert "万智牌" in rep_tempo.origin_game
    assert "先攻" in rep_tempo.philosophical_doctrine

    # 2. Life as Resource Axiom (Shadowverse / MTG)
    rep_life = UniversalTcgTheoryEngine.evaluate_board_philosophy(
        player_hp=28,
        enemy_hp=26,
        my_board_mana_value=6,
        enemy_board_mana_value=6,
        my_hand_count=2,
        enemy_hand_count=6,
    )
    assert rep_life.dominant_axiom == TCGAxiomType.LIFE_AS_RESOURCE
    assert "卖血" in rep_life.tactical_execution_directive

    # 3. Card Entropy Axiom (Yu-Gi-Oh!)
    rep_card = UniversalTcgTheoryEngine.evaluate_board_philosophy(
        player_hp=16,
        enemy_hp=18,
        my_board_mana_value=6,
        enemy_board_mana_value=5,
        my_hand_count=7,
        enemy_hand_count=3,
    )
    assert rep_card.dominant_axiom == TCGAxiomType.CARD_ENTROPY
    assert "游戏王" in rep_card.origin_game
