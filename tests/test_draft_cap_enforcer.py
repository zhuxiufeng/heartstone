"""
Unit tests for DraftCapEnforcer.
"""

from core.draft_cap_enforcer import DraftCapEnforcer, DraftCapModifier
from core.card_db import CardInfo


def test_heavy_bomb_overload():
    # Deck already has three 7+ drops
    deck = [
        CardInfo(id="BOMB1", name="大螺丝", cost=8, card_type="MINION"),
        CardInfo(id="BOMB2", name="红龙", cost=9, card_type="MINION"),
        CardInfo(id="BOMB3", name="巨人", cost=10, card_type="MINION"),
    ]
    candidate = CardInfo(id="BOMB4", name="死亡之翼", cost=10, card_type="MINION")

    mod: DraftCapModifier = DraftCapEnforcer.evaluate_card_caps(candidate, deck)
    assert mod.score_delta <= -18.0
    assert mod.is_hard_cap_violation is True
    assert any("超载" in r for r in mod.reasons)


def test_early_drop_urgency_bonus():
    # Pick 22, only two 2-drops drafted
    deck = [
        CardInfo(id=f"CARD_{i}", name=f"卡牌{i}", cost=3 + (i % 4), card_type="MINION")
        for i in range(20)
    ]
    # Add two 2-drops
    deck.append(CardInfo(id="D1", name="淡水鳄", cost=2, card_type="MINION"))
    deck.append(CardInfo(id="D2", name="迅猛龙", cost=2, card_type="MINION"))

    candidate = CardInfo(id="D3", name="年轻的女祭司", cost=2, card_type="MINION")
    mod: DraftCapModifier = DraftCapEnforcer.evaluate_card_caps(candidate, deck)

    assert mod.score_delta >= 14.0
    assert any("极度匮乏" in r for r in mod.reasons)


def test_spell_overload_penalty():
    # Deck with 10 spells
    deck = [
        CardInfo(id=f"SPELL_{i}", name=f"法术{i}", cost=2, card_type="SPELL")
        for i in range(10)
    ]
    candidate = CardInfo(id="EXTRA_SPELL", name="奥术智慧", cost=3, card_type="SPELL")

    mod: DraftCapModifier = DraftCapEnforcer.evaluate_card_caps(candidate, deck)
    assert mod.score_delta <= -16.0
    assert mod.is_hard_cap_violation is True
