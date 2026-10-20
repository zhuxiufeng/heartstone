"""
Unit tests for ActionTreeSearch.
"""

from core.action_tree_search import ActionTreeSearch, ActionTreeResult
from core.card_db import CardInfo


def test_action_tree_tempo_vs_rush():
    # Friendly has 2 minions (3/3 each) = 6 board atk
    # Enemy has 1 taunt minion with 2 hp, and 20 hp hero
    # Hand has a 3-cost 3/4 minion
    friendly = [
        {"name": "随从1", "atk": 3, "health": 3, "can_attack": True},
        {"name": "随从2", "atk": 3, "health": 3, "can_attack": True},
    ]
    enemy = [
        {"name": "嘲讽怪", "atk": 1, "health": 2, "taunt": True},
    ]
    hand = [
        CardInfo(id="M3", name="蜘蛛坦克", cost=3, attack=3, health=4, card_type="MINION"),
    ]

    res: ActionTreeResult = ActionTreeSearch.search_optimal_branch(
        friendly_minions=friendly,
        enemy_minions=enemy,
        hand_cards=hand,
        available_mana=3,
        friendly_hp=30,
        enemy_hp=20,
        opponent_class="MAGE",
    )

    assert res.best_branch is not None
    assert len(res.alternative_branches) >= 1
    assert "动作树最优解" in res.comparison_summary
    assert res.best_branch.ev_score > 0
