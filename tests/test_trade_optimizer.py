"""
Unit tests for TradeOptimizer.
"""

from core.trade_optimizer import TradeOptimizer, MinionState


def test_trade_optimizer_favorable_trade():
    optimizer = TradeOptimizer()
    friendly = [
        {"name": "淡水鳄", "attack": 2, "health": 3, "can_attack": True},
    ]
    enemy = [
        {"name": "战利品贮藏者", "attack": 2, "health": 1, "taunt": False},
    ]
    plan = optimizer.calculate_trades(friendly, enemy, enemy_hero_health=30)
    assert len(plan.actions) == 1
    action = plan.actions[0]
    assert action.action_type == "favorable_trade"
    assert action.attacker_survives is True
    assert action.target_killed is True
    assert "淡水鳄" in action.attacker_name
    assert "战利品贮藏者" in action.target_name


def test_trade_optimizer_taunt_priority():
    optimizer = TradeOptimizer()
    friendly = [
        {"name": "狼骑兵", "attack": 3, "health": 1, "can_attack": True},
    ]
    enemy = [
        {"name": "持盾卫士", "attack": 0, "health": 4, "taunt": True},
        {"name": "法力浮龙", "attack": 1, "health": 3, "taunt": False},
    ]
    plan = optimizer.calculate_trades(friendly, enemy, enemy_hero_health=10)
    # Must attack taunt first!
    assert len(plan.actions) == 1
    assert "持盾卫士" in plan.actions[0].target_name
    assert plan.actions[0].action_type == "taunt_break"


def test_trade_optimizer_face_lethal():
    optimizer = TradeOptimizer()
    friendly = [
        {"name": "暴龙王克鲁什", "attack": 8, "health": 8, "can_attack": True},
        {"name": "火元素", "attack": 6, "health": 5, "can_attack": True},
    ]
    enemy = []
    # Enemy HP is 12, total attack is 14 -> Full Face Lethal!
    plan = optimizer.calculate_trades(friendly, enemy, enemy_hero_health=12)
    assert plan.total_face_damage == 14
    assert "发现斩杀线" in plan.tactical_summary or "终结对局" in plan.tactical_summary
    assert all(a.action_type == "face" for a in plan.actions)
