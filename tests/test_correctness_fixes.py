"""
Regression tests for data-correctness fixes:
1. Deck-dependent odds use the real remaining deck, never the hand.
2. Unknown minion stats are flagged instead of silently guessed.
3. Ghost board consumes structured TradeAction objects and the trade plan's face damage.
"""

from core.ai_engine import AiEngine
from core.card_db import CardInfo
from core.tactical_ghost_board import TacticalGhostBoardSimulator
from core.trade_optimizer import TradeAction


def _fireball():
    return CardInfo(id="CS2_029", name="火球术", cost=4, card_type="SPELL")


def test_miracle_outs_ignore_hand_cards_without_deck():
    """A Fireball in HAND must not be reported as a topdeck out."""
    engine = AiEngine(api_key=None)
    rec = engine.evaluate_play_turn(
        turn_number=8, current_mana=8, hand_cards=[_fireball()],
        friendly_board=[], enemy_board=["狂暴者 (9/9)", "狂暴者 (9/9)"],
        opponent_class="WARRIOR", friendly_hp=10, enemy_hp=5, use_llm=False,
    )
    outs = [o.card_name for o in rec.miracle_out_report.miracle_outs]
    assert "火球术" not in outs
    assert any("未提供剩余牌库" in w for w in rec.data_warnings)


def test_miracle_outs_use_real_remaining_deck():
    engine = AiEngine(api_key=None)
    raptor = CardInfo(id="CS2_120", name="淡水鳄", cost=2, card_type="MINION", attack=2, health=3)
    deck = [_fireball()] + [raptor] * 9
    rec = engine.evaluate_play_turn(
        turn_number=8, current_mana=8, hand_cards=[],
        friendly_board=[], enemy_board=["狂暴者 (9/9)", "狂暴者 (9/9)"],
        opponent_class="WARRIOR", friendly_hp=10, enemy_hp=5, use_llm=False,
        remaining_deck=deck,
    )
    fb = next(o for o in rec.miracle_out_report.miracle_outs if o.card_name == "火球术")
    assert fb.copies_remaining == 1
    assert fb.draw_probability_pct == 10.0


def test_unknown_minion_stats_are_flagged():
    engine = AiEngine(api_key=None)
    rec = engine.evaluate_play_turn(
        turn_number=5, current_mana=5, hand_cards=[],
        friendly_board=["神秘随从"], enemy_board=["淡水鳄 (2/3)"],
        opponent_class="MAGE", use_llm=False, remaining_deck=[],
    )
    assert rec.data_complete is False
    assert any("身材未识别" in w for w in rec.data_warnings)


def test_known_stats_are_complete():
    engine = AiEngine(api_key=None)
    rec = engine.evaluate_play_turn(
        turn_number=5, current_mana=5, hand_cards=[],
        friendly_board=["冰风雪人 (4/5)"], enemy_board=["淡水鳄 (2/3)"],
        opponent_class="MAGE", use_llm=False, remaining_deck=[],
    )
    assert rec.data_complete is True


def test_ghost_board_matches_structured_trades_by_name():
    """The trade must hit the named target, not simply the first enemy in the list."""
    f = [{"name": "冰风雪人", "attack": 4, "health": 5}]
    e = [{"name": "小鬼", "attack": 1, "health": 1}, {"name": "淡水鳄", "attack": 2, "health": 3}]
    act = TradeAction(
        attacker_name="冰风雪人 (4/5)", target_name="淡水鳄 (2/0)", action_type="favorable_trade",
        damage_dealt=4, attacker_survives=True, attacker_remaining_hp=3, target_killed=True,
        priority_score=1.0, description="",
    )
    snap = TacticalGhostBoardSimulator.simulate_turn_outcome(
        friendly_minions=f, enemy_minions=e, trade_actions=[act], face_damage=0,
    )
    remaining = [m.name for m in snap.surviving_enemies]
    assert remaining == ["小鬼"]
    assert snap.surviving_friendly[0].health == 3
