"""
Unit tests for CoinOptimizer (Arena Coin Curve Acceleration & Strategy).
"""

from core.card_db import CardInfo
from core.coin_optimizer import CoinOptimizer, CoinStrategy


def _make_card(id: str, name: str, cost: int) -> CardInfo:
    return CardInfo(
        id=id,
        name=name,
        cost=cost,
        attack=cost,
        health=cost,
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


def test_no_coin():
    cards = [_make_card("c1", "随从1", 2), _make_card("c2", "随从2", 3)]
    res = CoinOptimizer.calculate_strategy(cards, current_turn=1, has_coin=False)
    assert res is None


def test_empty_playable_hand():
    coin = _make_card("GAME_005", "幸运币", 0)
    res = CoinOptimizer.calculate_strategy([coin], current_turn=1, has_coin=True)
    assert res is not None
    assert res.curve_pattern == "留币等待"
    assert not res.should_coin_now


def test_double_3_drops_no_2_drop():
    c3a = _make_card("c3a", "苦痛侍僧", 3)
    c3b = _make_card("c3b", "大地之环先知", 3)
    coin = _make_card("GAME_005", "幸运币", 0)
    hand = [c3a, c3b, coin]

    # Turn 1: should NOT coin, waste warning true
    t1_strat = CoinOptimizer.calculate_strategy(hand, current_turn=1, has_coin=True)
    assert t1_strat is not None
    assert t1_strat.recommended_coin_turn == 2
    assert not t1_strat.should_coin_now
    assert t1_strat.waste_warning

    # Turn 2: SHOULD coin now!
    t2_strat = CoinOptimizer.calculate_strategy(hand, current_turn=2, has_coin=True)
    assert t2_strat is not None
    assert t2_strat.recommended_coin_turn == 2
    assert t2_strat.should_coin_now
    assert not t2_strat.waste_warning
    assert "T2跳3 -> T3顺出3" in t2_strat.curve_pattern


def test_double_2_drops_tempo():
    c2a = _make_card("c2a", "淡水鳄", 2)
    c2b = _make_card("c2b", "血沼软泥怪", 2)
    c4 = _make_card("c4", "冰风雪人", 4)
    coin = _make_card("GAME_005", "幸运币", 0)
    hand = [c2a, c2b, c4, coin]

    # Turn 1: prime coin turn into double 2-drops
    strat = CoinOptimizer.calculate_strategy(hand, current_turn=1, has_coin=True)
    assert strat is not None
    assert strat.recommended_coin_turn == 1
    assert strat.should_coin_now
    assert not strat.waste_warning
    assert "T1跳2" in strat.curve_pattern


def test_double_4_drops_with_2_drop():
    c2 = _make_card("c2", "淡水鳄", 2)
    c4a = _make_card("c4a", "冰风雪人", 4)
    c4b = _make_card("c4b", "森金持盾卫士", 4)
    coin = _make_card("GAME_005", "幸运币", 0)
    hand = [c2, c4a, c4b, coin]

    # Turn 3: should coin into 4-drop
    strat = CoinOptimizer.calculate_strategy(hand, current_turn=3, has_coin=True)
    assert strat is not None
    assert strat.recommended_coin_turn == 3
    assert strat.should_coin_now
    assert "T3跳4" in strat.curve_pattern
