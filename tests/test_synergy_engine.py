"""
Unit tests for SynergyEngine.
"""

import pytest
from core.card_db import CardInfo
from core.synergy_engine import SynergyEngine, SynergyEvaluation


def test_synergy_engine_deathrattle_and_tribal():
    engine = SynergyEngine()

    c_deathrattle1 = CardInfo(
        id="D1", name="战利品贮藏者", cost=2, card_type="MINION",
        mechanics=["DEATHRATTLE"], text="亡语：抽一张牌。"
    )
    c_deathrattle2 = CardInfo(
        id="D2", name="血蹄勇士", cost=6, card_type="MINION",
        mechanics=["DEATHRATTLE"], text="亡语：召唤一个随从。"
    )

    deck = [c_deathrattle1, c_deathrattle2]

    # Candidate that triggers deathrattle
    c_trigger = CardInfo(
        id="T1", name="死金匕首", cost=2, card_type="WEAPON",
        mechanics=[], text="攻击后触发一个友方亡语。"
    )

    eval_res: SynergyEvaluation = engine.evaluate_synergies(c_trigger, deck)
    assert eval_res.bonus_score > 0
    assert "亡语" in eval_res.synergy_type
    assert len(eval_res.partner_cards) == 2

    # Candidate Dragon with Dragon deck
    c_dragon1 = CardInfo(id="DR1", name="碧蓝幼龙", cost=5, card_type="MINION", race="DRAGON", text="")
    c_dragon2 = CardInfo(id="DR2", name="红龙", cost=9, card_type="MINION", race="DRAGON", text="")
    c_dragon3 = CardInfo(id="DR3", name="绿龙", cost=9, card_type="MINION", race="DRAGON", text="")

    dragon_deck = [c_dragon1, c_dragon2, c_dragon3]
    c_synergy_dragon = CardInfo(
        id="DS", name="黑翼腐蚀者", cost=5, card_type="MINION",
        text="战吼：如果你的手牌中有龙牌，造成3点伤害。"
    )

    eval_dragon = engine.evaluate_synergies(c_synergy_dragon, dragon_deck)
    assert eval_dragon.bonus_score > 0
    assert "龙配合" in eval_dragon.synergy_type
