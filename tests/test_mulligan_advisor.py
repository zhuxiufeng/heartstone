"""
Unit tests for MulliganAdvisor.
"""

import pytest
from core.card_db import CardInfo
from core.mulligan_advisor import MulliganAdvisor, MulliganAdvice


def test_mulligan_advisor_curve_and_coin():
    advisor = MulliganAdvisor()

    c1 = CardInfo(id="M1", name="叫嚣的矮人", cost=1, card_type="MINION", card_class="NEUTRAL", rarity="COMMON")
    c2 = CardInfo(id="M2", name="恐狼前锋", cost=2, card_type="MINION", card_class="NEUTRAL", rarity="COMMON")
    c4 = CardInfo(id="M4", name="火球术", cost=4, card_type="SPELL", card_class="MAGE", rarity="FREE")
    c7 = CardInfo(id="M7", name="暴风城勇士", cost=7, card_type="MINION", card_class="NEUTRAL", rarity="COMMON")

    # Scenario 1: Going second with Coin
    advice_coin: MulliganAdvice = advisor.evaluate_mulligan(
        hand_cards=[c1, c2, c4, c7],
        hero_class="MAGE",
        opponent_class="HUNTER",
        has_coin=True,
    )

    verdicts_coin = {c.card.id: c.action for c in advice_coin.choices}
    assert verdicts_coin["M1"] == "KEEP"      # 1-drop
    assert verdicts_coin["M2"] == "KEEP"      # 2-drop
    assert verdicts_coin["M4"] == "KEEP"      # 4-drop kept because we have coin + 2-drop
    assert verdicts_coin["M7"] == "REPLACE"   # 7-drop replaced
    assert "后手策略" in advice_coin.game_plan

    # Scenario 2: Going first without Coin
    advice_no_coin: MulliganAdvice = advisor.evaluate_mulligan(
        hand_cards=[c1, c2, c4, c7],
        hero_class="MAGE",
        opponent_class="HUNTER",
        has_coin=False,
    )

    verdicts_no_coin = {c.card.id: c.action for c in advice_no_coin.choices}
    assert verdicts_no_coin["M1"] == "KEEP"
    assert verdicts_no_coin["M2"] == "KEEP"
    assert verdicts_no_coin["M4"] == "REPLACE"  # 4-drop replaced without coin
    assert verdicts_no_coin["M7"] == "REPLACE"
    assert "先手策略" in advice_no_coin.game_plan
