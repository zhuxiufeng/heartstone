"""
Unit tests for SequenceOptimizer.
"""

from core.sequence_optimizer import SequenceOptimizer


def test_sequence_optimizer_draw_first():
    seq = SequenceOptimizer()
    cards = [
        {"name": "石拳食人魔", "cost": 6, "text": "无效果"},
        {"name": "奥术智慧", "cost": 3, "text": "抽两张牌。"},
    ]
    advice = seq.evaluate_sequence(planned_cards=cards)
    assert advice.has_info_draw is True
    # Arcane Intellect should be priority over summon
    first_step = advice.recommended_sequence[0]
    assert "奥术智慧" in first_step or "抽" in first_step


def test_sequence_optimizer_aoe_before_summon_warning():
    seq = SequenceOptimizer()
    cards = [
        {"name": "淡水鳄", "cost": 2, "text": ""},
        {"name": "地狱烈焰", "cost": 4, "text": "对所有角色造成3点伤害。"},
    ]
    advice = seq.evaluate_sequence(planned_cards=cards)
    assert len(advice.critical_warnings) > 0
    assert any("地狱烈焰" in w and "先清场" in w or "严禁" in w for w in advice.critical_warnings)
