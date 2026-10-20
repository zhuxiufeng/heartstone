"""
Unit tests for ConfigManager.
"""

import json
from pathlib import Path

from core.config_manager import ConfigManager, DEFAULT_CONFIG


def test_config_defaults(tmp_path: Path):
    cfg_file = tmp_path / "test_config.json"
    mgr = ConfigManager(str(cfg_file))
    
    assert mgr.get("gemini_model") == "gemini-2.0-flash"
    assert mgr.get("animation_lock_duration_sec") == 2.5
    assert cfg_file.exists()


def test_config_update_and_persist(tmp_path: Path):
    cfg_file = tmp_path / "test_config.json"
    mgr = ConfigManager(str(cfg_file))
    
    mgr.set("gemini_model", "gemini-1.5-pro")
    mgr.update({"overlay_opacity": 0.85, "click_through": True})
    
    # Reload from disk
    mgr2 = ConfigManager(str(cfg_file))
    assert mgr2.get("gemini_model") == "gemini-1.5-pro"
    assert mgr2.get("overlay_opacity") == 0.85
    assert mgr2.get("click_through") is True
