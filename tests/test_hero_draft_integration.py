import pytest
from core.hero_draft_advisor import HeroDraftAdvisor
from core.log_listener import LogListener
from core.config_manager import get_default_hearthstone_log_dir, get_hearthstone_config_paths
from pathlib import Path

def test_hero_draft_advisor_evaluation():
    choices = ["死亡骑士", "法师", "战士"]
    evals = HeroDraftAdvisor.evaluate_hero_choices(choices)
    assert len(evals) == 3
    # Death Knight should be top rated (T0)
    assert evals[0].class_cn == "死亡骑士"
    assert evals[0].tier == "T0"
    assert evals[0].winrate > 55.0
    # Warrior should be lowest rated (T3)
    assert evals[2].class_cn == "战士"
    assert evals[2].tier == "T3"

def test_log_listener_session_folder_detection(tmp_path):
    logs_dir = tmp_path / "Logs"
    logs_dir.mkdir()
    
    session1 = logs_dir / "Hearthstone_2026_10_17_12_00_00"
    session1.mkdir()
    (session1 / "Arena.log").write_text("Old session\n", encoding="utf-8")

    session2 = logs_dir / "Hearthstone_2026_10_18_10_00_00"
    session2.mkdir()
    (session2 / "Arena.log").write_text("New session\n", encoding="utf-8")

    listener = LogListener(str(logs_dir))
    active_dir = listener._find_active_log_dir()
    assert active_dir == session2
