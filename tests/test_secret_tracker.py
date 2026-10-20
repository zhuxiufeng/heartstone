"""
Unit tests for SecretTracker.
"""

import pytest
from core.secret_tracker import SecretTracker, TriggerType


def test_secret_tracker_elimination():
    tracker = SecretTracker()
    secret_id = tracker.add_opponent_secret("MAGE", turn=3)
    assert len(tracker.active_secrets) == 1

    # Initially all Mage secrets possible
    cand_init = tracker.get_possible_secrets(secret_id)[secret_id]
    assert any(c.name == "法术反制" for c in cand_init)
    assert any(c.name == "镜像实体" for c in cand_init)

    # Cast a spell: doesn't trigger secret -> Eliminate "法术反制" and "净天圣步"
    tracker.on_game_action(TriggerType.CAST_SPELL)
    cand_after_spell = tracker.get_possible_secrets(secret_id)[secret_id]
    names_after_spell = [c.name for c in cand_after_spell]

    assert "法术反制" not in names_after_spell
    assert "净天圣步" not in names_after_spell
    assert "镜像实体" in names_after_spell

    # Play a minion: doesn't trigger secret -> Eliminate "镜像实体", "爆炸符文", "异议"
    tracker.on_game_action(TriggerType.PLAY_MINION)
    cand_after_minion = tracker.get_possible_secrets(secret_id)[secret_id]
    names_after_minion = [c.name for c in cand_after_minion]

    assert "镜像实体" not in names_after_minion
    assert "爆炸符文" not in names_after_minion
    assert "异议" not in names_after_minion

    # Summary text should reflect status
    summary = tracker.get_summary_text()
    assert "敌方当前挂有 1 个奥秘" in summary
    assert "已排除" in summary


def test_secret_tracker_reset():
    tracker = SecretTracker()
    tracker.add_opponent_secret("HUNTER", turn=2)
    assert len(tracker.active_secrets) == 1
    tracker.reset()
    assert len(tracker.active_secrets) == 0
    assert tracker.get_summary_text() == "当前敌方头上无奥秘。"
