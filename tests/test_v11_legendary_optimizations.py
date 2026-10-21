"""
Unit tests for v11 Legendary Horizon Edition optimizations:
1. Secret & Deathrattle Cascade Simulator
2. Opponent Hand Age & Mulligan Retention Intel Radar
3. Mobile Two-Way Interactive Remote Controller
4. Interactive Voice Q&A & AI Esports Caster
5. 11-Class Matchup Matrix & Virtual Sandbox
6. Arena Career Vault & Shareable Infographic
"""

import tempfile
from pathlib import Path
import pytest

from core.card_db import CardInfo
from core.secret_deathrattle_simulator import SecretDeathrattleSimulator, SecretCascadeReport
from core.hand_age_intel import HandAgeIntel, CardOriginType
from core.mobile_remote_controller import MobileRemoteController, RemoteCommandType
from core.esports_caster import EsportsCaster, CasterEventType
from core.deck_matchup_sandbox import DeckMatchupSandbox, DeckMatchupReport
from core.arena_career_vault import ArenaCareerVault, ArenaRunRecord


def _make_dummy_card(card_id: str, name: str, cost: int, card_type: str = "MINION", text: str = "", attack: int = 3, health: int = 3):
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
        mechanics=[],
    )


def test_secret_deathrattle_simulator():
    # 1. Probing order with Vaporize and Explosive Trap
    active_secrets = ["蒸发", "爆炸陷阱"]
    friendly_minions = [
        {"name": "小精灵", "attack": 1, "health": 1},
        {"name": "海巨人", "attack": 8, "health": 8},
    ]
    rep = SecretDeathrattleSimulator.evaluate_probing_order(
        active_secrets=active_secrets,
        friendly_minions=friendly_minions,
        friendly_hand=[{"name": "奥术飞弹", "type": "SPELL", "cost": 1}],
        friendly_hp=15,
    )

    assert len(rep.probing_plans) >= 2
    # Should recommend using lowest attack minion (小精灵) to probe face to avoid losing 8/8 Sea Giant to Vaporize
    face_plan = next(p for p in rep.probing_plans if p.action_type == "ATTACK_HERO")
    assert "小精灵" in face_plan.recommended_minion_used
    assert "蒸发" in face_plan.worst_case_punish

    # 2. Deathrattle cascade with Abomination (2 AOE dmg) and Haunted Creeper (2 spiders)
    dying = [
        {"name": "憎恶", "attack": 4, "health": 4, "text": "亡语：对全场所有角色造成2点伤害"},
        {"name": "鬼灵爬行者", "attack": 1, "health": 2, "text": "亡语：召唤2只1/1鬼灵蜘蛛"},
    ]
    friendly_board = [
        {"name": "雪人", "attack": 4, "health": 5},
        {"name": "鱼人宝宝", "attack": 1, "health": 1},  # will die to 2 aoe
    ]
    cascade = SecretDeathrattleSimulator.simulate_deathrattle_cascade(dying, friendly_board, [])
    assert cascade.total_aoe_damage == 2
    assert "1/1 鬼灵蜘蛛" in cascade.spawned_tokens
    # Yeti (5 hp) survives with 3 hp, Murloc (1 hp) dies
    assert len(cascade.surviving_friendly_minions) == 1
    assert cascade.surviving_friendly_minions[0]["health"] == 3


def test_hand_age_intel():
    intel = HandAgeIntel()
    # 4 cards in hand, kept slots #1 and #3
    intel.record_mulligan(hand_size=4, kept_slots=[1, 3])
    assert intel.cards[1].origin == CardOriginType.MULLIGAN_KEPT
    assert intel.cards[2].origin == CardOriginType.MULLIGAN_REDRAW

    # Advance to turn 5: slot #1 has been held for 5 turns -> should be flagged as dormant threat!
    rep = intel.update_turn(turn=5)
    assert rep.dormant_threat_count >= 1
    assert rep.cards[0].is_dormant_threat is True
    assert "起手保留" in rep.cards[0].prediction_label

    # Opponent plays card from slot 1 -> slot 2 moves to slot 1
    played = intel.record_card_played(slot=1)
    assert played.origin == CardOriginType.MULLIGAN_KEPT
    assert len(intel.cards) == 3
    assert intel.cards[1].slot == 1


def test_mobile_remote_controller():
    controller = MobileRemoteController.get_instance()
    actions_called = []

    def _sample_toggle(params):
        actions_called.append("TOGGLED")
        return {"active": True}

    controller.register_handler(RemoteCommandType.TOGGLE_OVERLAY, _sample_toggle)

    res = controller.dispatch("TOGGLE_OVERLAY")
    assert res.status == "ok"
    assert res.payload.get("active") is True
    assert "TOGGLED" in actions_called

    # Unsupported command
    bad_res = controller.dispatch("NON_EXISTENT_COMMAND")
    assert bad_res.status == "unsupported"


def test_esports_caster():
    # 1. Voice Q&A for lethal
    ans_lethal = EsportsCaster.answer_voice_query(
        "小助手能斩杀吗",
        {"is_lethal": True, "enemy_hp": 8},
    )
    assert ans_lethal.intent == "CHECK_LETHAL"
    assert ans_lethal.short_verdict == "可以斩杀！"

    # 2. Voice Q&A for Face vs Trade
    ans_face = EsportsCaster.answer_voice_query(
        "现在该打脸还是解场",
        {"posture_mode": "AGGRESSIVE", "enemy_hp": 14},
    )
    assert ans_face.intent == "FACE_OR_TRADE"
    assert "打脸" in ans_face.short_verdict

    # 3. Commentary
    comm = EsportsCaster.get_commentary(CasterEventType.TOPDECK_MIRACLE)
    assert "神抽" in comm.headline
    assert comm.energy_level in ("HIGH", "EXTREME", "LEGENDARY")


def test_deck_matchup_sandbox():
    cards = [
        (_make_dummy_card("C1", "随从1", 2), 6),
        (_make_dummy_card("C2", "随从2", 3), 6),
        (_make_dummy_card("C3", "随从3", 4), 6),
        (_make_dummy_card("C4", "随从4", 5), 6),
        (_make_dummy_card("C5", "随从5", 7), 6),
    ]

    rep = DeckMatchupSandbox.evaluate_deck(cards)
    assert rep.total_cards_evaluated == 30
    assert len(rep.class_matchups) == 11
    assert "MAGE" in rep.class_matchups
    assert "HUNTER" in rep.class_matchups
    assert rep.overall_mean_winrate_pct > 30.0
    assert rep.best_matchup_class != ""


def test_arena_career_vault():
    with tempfile.TemporaryDirectory() as tmp_dir:
        file_path = Path(tmp_dir) / "test_career.json"
        vault = ArenaCareerVault(file_path=file_path)

        vault.record_run(hero_class="Mage", wins=12, losses=1, mvp_card="火球术")
        vault.record_run(hero_class="Paladin", wins=7, losses=3, mvp_card="奉献")

        summary = vault.get_summary()
        assert summary.total_runs == 2
        assert summary.total_wins == 19
        assert summary.total_losses == 4
        assert summary.twelve_win_trophies == 1
        assert summary.average_wins_per_run == 9.5

        # Check infographic generation
        html = vault.generate_shareable_infographic_html()
        assert "12胜" in html
        assert "MAGE" in html
