"""
Tests for v22 First-Principles Ultimate Suite:
1. Tactical Ghost Board Simulation (鬼影实机沙盘预演)
2. Opponent Next-Turn Punish Envelope & Safe HP Ceiling (敌方下轮极限威慑包络线)
3. Zero-Leak Mana Audit & Curve Weaving Engine (法力无损转化与技能穿插审计)
4. Miracle Out Inversion Filter & Clutch Draw Odds (绝境神抽逆转抽滤雷达)
5. Temporal Action Bottleneck & Saturation Guard (武器与频次瓶颈饱和熔断器)
6. Full AI Engine Draft & Play Turn Integrations
"""

import pytest
from core.ai_engine import AiEngine, CardEvaluation, PlayRecommendation
from core.card_db import CardInfo
from core.tactical_ghost_board import TacticalGhostBoardSimulator, GhostBoardSnapshot
from core.opponent_punish_envelope import OpponentPunishEnvelopeCalculator, OpponentPunishEnvelope
from core.zero_leak_mana_auditor import ZeroLeakManaAuditor, ManaLeakAuditResult
from core.miracle_out_filter import MiracleOutFilter, MiracleOutReport
from core.temporal_bottleneck_guard import TemporalBottleneckGuard, SaturationAssessment


def test_tactical_ghost_board_simulation():
    """Verify terminal delta simulation accurately calculates minion stats, trades, and face damage."""
    f_minions = [
        {"name": "随从A", "attack": 3, "health": 2},
        {"name": "随从B", "attack": 4, "health": 5},
    ]
    e_minions = [
        {"name": "敌随从1", "attack": 2, "health": 3},
    ]
    played = [
        {"name": "新援军", "attack": 2, "health": 3},
    ]
    trades = ["随从A 换 敌随从1"]

    snap: GhostBoardSnapshot = TacticalGhostBoardSimulator.simulate_turn_outcome(
        friendly_minions=f_minions,
        enemy_minions=e_minions,
        played_minions=played,
        optimal_trades=trades,
        face_damage=4,
        current_mana=5,
        spent_mana=3,
        enemy_hp=20,
    )

    assert snap.is_enemy_cleared is True
    assert snap.enemy_hp_remaining == 16
    assert snap.mana_spent == 3
    assert snap.mana_remaining == 2
    assert len(snap.surviving_enemies) == 0
    # Surviving friendly should include SurvivingMinion with attack/health
    assert any(m.name == "随从B" for m in snap.surviving_friendly)
    assert any(m.name == "新援军" for m in snap.surviving_friendly)
    assert "🔮 战后预演" in snap.holographic_summary_badge
    assert "<b>🔮 战后终局沙盘预演:</b>" in snap.terminal_delta_display


def test_opponent_punish_envelope_calculation():
    """Verify worst-case punish envelope computes max burst, removal, and safe HP threshold."""
    # Test Mage turn 7: Flamestrike (4 dmg AOE) and Fireball (6 dmg removal)
    env_mage = OpponentPunishEnvelopeCalculator.calculate_envelope(
        opponent_class="MAGE",
        current_turn_mana=6,
        enemy_board_attack=5,
    )
    assert env_mage.next_turn_mana == 7
    assert env_mage.opponent_class == "MAGE"
    assert env_mage.max_burst_face >= 11  # 5 board atk + 6 fireball
    assert env_mage.max_single_removal_dmg >= 6
    assert env_mage.max_aoe_dmg >= 4
    assert env_mage.safe_minion_hp_threshold >= 7  # > 6 single removal
    assert "🛡️ 下轮敌方威慑包络" in env_mage.envelope_badge

    # Test Hunter turn 4: Kill Command (5 dmg), Quick Shot (3 dmg)
    env_hunter = OpponentPunishEnvelopeCalculator.calculate_envelope(
        opponent_class="HUNTER",
        current_turn_mana=3,
        enemy_board_attack=3,
    )
    assert env_hunter.next_turn_mana == 4
    assert env_hunter.max_burst_face >= 8  # 3 board + 5 kill command


def test_zero_leak_mana_auditor():
    """Verify mana leak auditor detects wasted mana and recommends hero power weaving or cheap filler."""
    # Case 1: 100% mana utilization
    res1 = ZeroLeakManaAuditor.audit_mana_spending(
        available_mana=5,
        spent_mana=5,
        hand_cards=[],
        hero_power_cost=2,
        hero_power_available=True,
    )
    assert res1.has_leak is False
    assert res1.leak_mana == 0
    assert res1.mana_utilization_pct == 100.0
    assert "100% 水晶无损兑现" in res1.audit_tag

    # Case 2: 2 mana leaked with hero power available
    res2 = ZeroLeakManaAuditor.audit_mana_spending(
        available_mana=6,
        spent_mana=4,
        hand_cards=[],
        hero_power_cost=2,
        hero_power_available=True,
    )
    assert res2.has_leak is True
    assert res2.leak_mana == 2
    assert "英雄技能" in res2.weaving_advice

    # Case 3: 1 mana leaked with a 1-cost filler in hand
    c1 = CardInfo(id="CS2_189", name="精灵弓箭手", cost=1, card_type="MINION", attack=1, health=1)
    res3 = ZeroLeakManaAuditor.audit_mana_spending(
        available_mana=4,
        spent_mana=3,
        hand_cards=[c1],
        hero_power_cost=2,
        hero_power_available=False,
    )
    assert res3.has_leak is True
    assert res3.leak_mana == 1
    assert "精灵弓箭手" in res3.weaving_advice


def test_miracle_out_inversion_filter():
    """Verify miracle out filter activates when behind/facing lethal and computes draw odds."""
    # Deck with lethal outs
    fireball = CardInfo(id="CS2_029", name="火球术", cost=4, card_type="SPELL")
    raptor = CardInfo(id="CS2_120", name="淡水鳄", cost=2, card_type="MINION")
    rem_cards = [(fireball, 1), (raptor, 9)]  # total 10 cards, 1 Fireball

    # Normal state (winrate 60%, no lethal danger) -> should NOT trigger miracle mode
    rep_normal = MiracleOutFilter.evaluate_miracle_outs(
        winrate_pct=60.0,
        remaining_cards=rem_cards,
        player_hp=25,
        enemy_hp=6,
        friendly_board_atk=0,
        enemy_board_atk=4,
    )
    assert rep_normal.is_in_miracle_mode is False
    assert len(rep_normal.miracle_outs) == 0

    # Critical losing state (winrate 28%, enemy HP 6) -> Fireball is lethal out!
    rep_miracle = MiracleOutFilter.evaluate_miracle_outs(
        winrate_pct=28.0,
        remaining_cards=rem_cards,
        player_hp=12,
        enemy_hp=6,
        friendly_board_atk=0,
        enemy_board_atk=15,  # facing lethal
    )
    assert rep_miracle.is_in_miracle_mode is True
    assert len(rep_miracle.miracle_outs) >= 1
    out_cards = [o.card_name for o in rep_miracle.miracle_outs]
    assert "火球术" in out_cards
    # 1 copy in 10 cards = 10.0% draw odds
    fb_out = next(o for o in rep_miracle.miracle_outs if o.card_name == "火球术")
    assert fb_out.draw_probability_pct == 10.0
    assert "LETHAL_OUT" in fb_out.out_type
    assert "神抽逆转路线" in rep_miracle.banner_text or "绝境" in rep_miracle.banner_text


def test_temporal_bottleneck_guard():
    """Verify saturation guard applies diminishing returns to duplicate weapons, secrets, and bombs."""
    w1 = CardInfo(id="CS2_106", name="炽炎战斧", cost=3, card_type="WEAPON")
    w2 = CardInfo(id="CS2_112", name="奥金斧", cost=5, card_type="WEAPON")
    deck_with_2_weapons = [w1, w2]

    # Candidate 3rd weapon
    w3 = CardInfo(id="EX1_411", name="血吼", cost=7, card_type="WEAPON")
    sat_weapon = TemporalBottleneckGuard.evaluate_card_saturation(w3, deck_with_2_weapons)
    assert sat_weapon.is_saturated is True
    assert sat_weapon.saturation_type == "WEAPON_BOTTLENECK"
    assert sat_weapon.score_delta < 0
    assert "武器物理频次饱和" in sat_weapon.saturation_tag

    # Candidate duplicate secret
    s1 = CardInfo(id="EX1_294", name="寒冰护体", cost=3, card_type="SPELL", mechanics=["SECRET"])
    sat_secret = TemporalBottleneckGuard.evaluate_card_saturation(s1, [s1])
    assert sat_secret.is_saturated is True
    assert sat_secret.saturation_type == "SECRET_DUPLICATE"
    assert sat_secret.score_delta == -14.0

    # Candidate 4th heavy bomb (cost >= 8)
    b1 = CardInfo(id="CS2_186", name="奥术巨人", cost=8, card_type="MINION")
    b2 = CardInfo(id="EX1_561", name="阿莱克丝塔萨", cost=9, card_type="MINION")
    b3 = CardInfo(id="EX1_572", name="伊瑟拉", cost=9, card_type="MINION")
    b4 = CardInfo(id="CS2_200", name="岩浆暴怒者", cost=8, card_type="MINION")
    sat_bomb = TemporalBottleneckGuard.evaluate_card_saturation(b4, [b1, b2, b3])
    assert sat_bomb.is_saturated is True
    assert sat_bomb.saturation_type == "HEAVY_BOMB_CLOG"
    assert sat_bomb.score_delta == -16.0


def test_ai_engine_v22_draft_pick_integration():
    """Verify AiEngine.evaluate_draft_pick penalizes saturated cards via TemporalBottleneckGuard."""
    engine = AiEngine(api_key=None)

    # Deck with 2 weapons
    w1 = CardInfo(id="CS2_106", name="炽炎战斧", cost=3, card_type="WEAPON")
    w2 = CardInfo(id="CS2_112", name="奥金斧", cost=5, card_type="WEAPON")
    existing_deck = [w1, w2]

    # Candidate picks: a 3rd weapon vs normal minion vs normal spell
    pick_weapon = CardInfo(id="EX1_411", name="血吼", cost=7, card_type="WEAPON")
    pick_minion = CardInfo(id="CS2_182", name="冰风雪人", cost=4, card_type="MINION", attack=4, health=5)
    pick_spell = CardInfo(id="CS2_022", name="变形术", cost=4, card_type="SPELL")

    rec = engine.evaluate_draft_pick(
        hero_class="WARRIOR",
        candidates=[pick_weapon, pick_minion, pick_spell],
        deck_so_far=existing_deck,
        use_llm=False,
    )
    evals = rec.cards_evaluations
    assert len(evals) == 3

    weapon_eval = next(e for e in evals if e.card_name == "血吼")
    assert weapon_eval.saturation_assessment is not None
    assert weapon_eval.saturation_assessment.is_saturated is True
    assert "武器物理频次饱和" in weapon_eval.saturation_assessment.saturation_tag
    assert any("武器物理频次饱和" in p for p in weapon_eval.pros)


def test_ai_engine_v22_play_turn_integration():
    """Verify AiEngine.evaluate_play_turn computes and attaches all 4 turn-level first-principles models."""
    engine = AiEngine(api_key=None)

    c1 = CardInfo(id="CS2_029", name="火球术", cost=4, card_type="SPELL")
    c2 = CardInfo(id="CS2_120", name="淡水鳄", cost=2, card_type="MINION", attack=2, health=3)
    hand = [c1, c2]

    f_board = ["随从A (3/3)"]
    e_board = ["敌方步兵 (2/2)"]

    rec: PlayRecommendation = engine.evaluate_play_turn(
        turn_number=6,
        current_mana=6,
        hand_cards=hand,
        friendly_board=f_board,
        enemy_board=e_board,
        opponent_class="MAGE",
        friendly_hp=20,
        enemy_hp=10,
        use_llm=False,
    )

    # 1. Tactical Ghost Board Snapshot
    assert rec.ghost_board_snapshot is not None
    assert isinstance(rec.ghost_board_snapshot, GhostBoardSnapshot)
    assert "🔮 战后预演" in rec.ghost_board_snapshot.holographic_summary_badge

    # 2. Opponent Punish Envelope
    assert rec.opponent_punish_envelope is not None
    assert isinstance(rec.opponent_punish_envelope, OpponentPunishEnvelope)
    assert rec.opponent_punish_envelope.opponent_class == "MAGE"
    assert rec.opponent_punish_envelope.next_turn_mana == 7
    assert rec.opponent_punish_envelope.safe_minion_hp_threshold >= 5

    # 3. Zero Leak Mana Audit
    assert rec.mana_leak_audit is not None
    assert isinstance(rec.mana_leak_audit, ManaLeakAuditResult)

    # 4. Miracle Out Report
    assert rec.miracle_out_report is not None
    assert isinstance(rec.miracle_out_report, MiracleOutReport)
