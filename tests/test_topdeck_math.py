"""
Unit tests for TopdeckMath (Clutch Endgame Draw Probabilities & Outs Calculator).
"""

from core.card_db import CardInfo
from core.deck_tracker import DeckTracker
from core.topdeck_math import TopdeckMath, TopdeckAdvice


def _make_card(id: str, name: str, cost: int, card_type: str = "MINION", text: str = "", mechanics: list = None) -> CardInfo:
    return CardInfo(
        id=id,
        name=name,
        cost=cost,
        attack=cost,
        health=cost,
        durability=None,
        card_class="NEUTRAL",
        card_type=card_type,
        rarity="COMMON",
        set_name="CORE",
        text=text,
        race=None,
        races=[],
        spell_school=None,
        mechanics=mechanics or [],
        collectible=True,
        raw_data={},
    )


def test_empty_deck_returns_none():
    tracker = DeckTracker()
    tracker.set_draft_deck([])
    res = TopdeckMath.calculate_endgame_odds(
        deck_tracker=tracker,
        friendly_hp=10,
        enemy_hp=10,
        friendly_field_atk=3,
        enemy_field_atk=5,
        current_turn=7,
    )
    assert res is None


def test_safe_state_no_outs_returns_none():
    tracker = DeckTracker()
    deck = [_make_card(f"c_{i}", f"小兵{i}", 2) for i in range(15)]
    tracker.set_draft_deck(deck)

    # 30 HP vs 30 HP, no danger, no lethal outs
    res = TopdeckMath.calculate_endgame_odds(
        deck_tracker=tracker,
        friendly_hp=30,
        enemy_hp=30,
        friendly_field_atk=4,
        enemy_field_atk=3,
        current_turn=5,
    )
    assert res is None


def test_fatal_danger_lethal_outs():
    tracker = DeckTracker()
    # 10 cards left in deck: 2 Fireballs (6 dmg), 8 vanilla minions
    fireball = _make_card("fb", "火球术", 4, card_type="SPELL", text="造成6点伤害。")
    vanilla = _make_card("vanilla", "淡水鳄", 2)
    deck = [fireball, fireball] + [vanilla] * 8
    tracker.set_draft_deck(deck)

    # Friendly HP = 5, enemy field ATK = 8 (Fatal lethal next turn!)
    # Enemy HP = 8, friendly field ATK = 3 (Missing 5 dmg) -> Fireball deals 6 >= 5!
    res = TopdeckMath.calculate_endgame_odds(
        deck_tracker=tracker,
        friendly_hp=5,
        enemy_hp=8,
        friendly_field_atk=3,
        enemy_field_atk=8,
        current_turn=8,
    )

    assert res is not None
    assert res.remaining_deck_count == 10
    assert res.lethal_outs_count == 2
    assert res.topdeck_lethal_prob == 20.0
    assert res.recommended_line == "ALL_IN_FACE"
    assert "火球术" in res.advice_text
    assert "20.0%" in res.advice_text


def test_fatal_danger_survival_taunt_outs():
    tracker = DeckTracker()
    # 5 cards in deck: 1 Sen'jin Shieldmasta (Taunt), 4 vanilla spells
    taunt = _make_card("taunt", "森金持盾卫士", 4, mechanics=["TAUNT"])
    card2 = _make_card("c2", "奥术智慧", 3, card_type="SPELL", text="抽两张牌。")
    deck = [taunt] + [card2] * 4
    tracker.set_draft_deck(deck)

    # Friendly HP = 3, enemy field ATK = 10 (Fatal danger)
    # Enemy HP = 25, friendly field ATK = 2 (No immediate lethal)
    res = TopdeckMath.calculate_endgame_odds(
        deck_tracker=tracker,
        friendly_hp=3,
        enemy_hp=25,
        friendly_field_atk=2,
        enemy_field_atk=10,
        current_turn=9,
    )

    assert res is not None
    assert res.survival_outs_count == 1
    assert res.topdeck_survival_prob == 20.0
    assert res.recommended_line == "STABILIZE"
    assert "森金持盾卫士" in res.advice_text
