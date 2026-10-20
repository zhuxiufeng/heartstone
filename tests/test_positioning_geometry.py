"""
Unit tests for PositioningGeometry.
"""

from core.positioning_geometry import PositioningGeometry, PositioningAdvice


def test_empty_board_placement():
    adv = PositioningGeometry.calculate_optimal_placement(
        board=[],
        new_minion={"name": "淡水鳄", "atk": 2, "health": 3},
    )
    assert adv.recommended_slot == 0


def test_magnetic_fusion_placement():
    board = [
        {"name": "雪人", "atk": 4, "health": 5, "is_mech": False},
        {"name": "量产型恐吓机", "atk": 3, "health": 1, "is_mech": True},
    ]
    adv = PositioningGeometry.calculate_optimal_placement(
        board=board,
        new_minion={"name": "奇利亚斯", "atk": 3, "health": 2, "is_magnetic": True},
    )
    assert adv.is_magnetic_fuse is True
    assert adv.recommended_slot == 1
    assert "磁力合体" in adv.strategic_rationale


def test_divine_shield_buffer_placement():
    # When playing a Divine Shield minion, it should be placed next to highest attack minion to shield from Meteor/Cone
    board = [
        {"name": "杂毛A", "atk": 1, "health": 1},
        {"name": "风暴骑士", "atk": 6, "health": 5},
    ]
    adv = PositioningGeometry.calculate_optimal_placement(
        board=board,
        new_minion={"name": "银色侍从", "atk": 1, "health": 1, "divine_shield": True},
    )
    assert adv.recommended_slot == 2
    assert "缓冲盾" in adv.strategic_rationale or "防流星" in adv.threat_mitigated
