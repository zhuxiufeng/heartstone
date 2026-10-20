"""
Unit tests for ManaEfficiencyOptimizer (2-Turn Floating Mana Minimizer).
"""

from core.card_db import CardInfo
from core.mana_efficiency import ManaEfficiencyOptimizer, ManaEfficiencyPlan


def _make_card(id: str, name: str, cost: int, atk: int = 2, hp: int = 2) -> CardInfo:
    return CardInfo(
        id=id,
        name=name,
        cost=cost,
        attack=atk,
        health=hp,
        durability=None,
        card_class="NEUTRAL",
        card_type="MINION",
        rarity="COMMON",
        set_name="CORE",
        text="",
        race=None,
        races=[],
        spell_school=None,
        mechanics=[],
        collectible=True,
        raw_data={},
    )


def test_perfect_zero_floating_mana():
    # Hand has: 4-cost Yeti, 5-cost Warlord, 2-cost Crocolisk
    # Current Turn = T4 (4 mana), Next Turn = T5 (5 mana)
    # Playing Yeti (4) on T4 -> Warlord (5) on T5 = 9/9 mana (100% efficiency, 0 floating mana!)
    c4 = _make_card("c4", "冰风雪人", 4, 4, 5)
    c5 = _make_card("c5", "霜狼督军", 5, 4, 4)
    c2 = _make_card("c2", "淡水鳄", 2, 2, 3)

    plan: ManaEfficiencyPlan = ManaEfficiencyOptimizer.calculate_2turn_efficiency(
        hand_cards=[c4, c5, c2],
        current_mana=4,
        next_mana=5,
    )

    assert plan is not None
    assert plan.total_floating_mana == 0
    assert plan.efficiency_pct == 100.0
    assert plan.current_spent == 4
    assert plan.next_spent == 5
    assert "零空转" in plan.advice_text
    assert plan.current_turn_plays[0].name == "冰风雪人"
    assert plan.next_turn_projected_plays[0].name == "霜狼督军"


def test_split_cost_combination():
    # Hand has: two 2-drops and one 5-drop
    # Current Turn = T4 (4 mana), Next Turn = T5 (5 mana)
    # Playing 2 + 2 = 4 on T4 -> 5 on T5 = 9/9 mana (100% efficiency)
    c2a = _make_card("c2a", "淡水鳄", 2)
    c2b = _make_card("c2b", "血沼软泥怪", 2)
    c5 = _make_card("c5", "霜狼督军", 5)

    plan = ManaEfficiencyOptimizer.calculate_2turn_efficiency(
        hand_cards=[c2a, c2b, c5],
        current_mana=4,
        next_mana=5,
    )

    assert plan is not None
    assert plan.total_floating_mana == 0
    assert len(plan.current_turn_plays) == 2
    assert plan.current_spent == 4
    assert plan.next_spent == 5
