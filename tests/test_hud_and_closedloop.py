"""
Unit tests for HUD Simplification (Zen HUD Mode) and Effect Measurement Closedloop.
"""

import pytest
from unittest.mock import MagicMock
from core.duckdb_manager import DuckDBManager
from core.turn_replayer import MatchReplaySummary, TurnReviewNode


@pytest.fixture(autouse=True)
def clean_duckdb():
    DuckDBManager.reset_instance()
    yield
    DuckDBManager.reset_instance()


def test_zen_hud_mode_toggle():
    """Verify Zen Focus HUD correctly toggles visibility of secondary panels."""
    from PyQt5.QtWidgets import QApplication, QWidget
    import sys

    app = QApplication.instance() or QApplication(sys.argv)

    # Minimal mock overlay with the necessary widgets
    class MockOverlay:
        def __init__(self):
            self.is_zen_hud = False
            self.zen_hud_btn = MagicMock()
            self.drawer_bar = MagicMock()
            self.intel_container = MagicMock()
            self.threat_radar_frame = MagicMock()
            self.play_trade_frame = MagicMock()
            self.winrate_sparkline = MagicMock()
            self.posture_frame = MagicMock()
            self.status_updates = []

        def _on_status_updated(self, msg: str):
            self.status_updates.append(msg)

    # Import the exact method logic
    from ui.overlay import OverlayWindow
    mock = MockOverlay()

    # Toggle to Zen Mode
    OverlayWindow._toggle_zen_hud(mock)
    assert mock.is_zen_hud is True
    mock.zen_hud_btn.setText.assert_called_with("⚡ 极简")
    mock.drawer_bar.hide.assert_called()
    mock.intel_container.hide.assert_called()
    mock.threat_radar_frame.hide.assert_called()
    mock.play_trade_frame.hide.assert_called()
    mock.winrate_sparkline.hide.assert_called()
    mock.posture_frame.hide.assert_called()
    assert any("极简对局模式" in s for s in mock.status_updates)

    # Toggle back to Detailed Mode
    OverlayWindow._toggle_zen_hud(mock)
    assert mock.is_zen_hud is False
    mock.zen_hud_btn.setText.assert_called_with("🎯 极简")
    mock.drawer_bar.show.assert_called()
    mock.intel_container.show.assert_called()
    mock.winrate_sparkline.show.assert_called()
    mock.posture_frame.show.assert_called()
    assert any("完整推演面板" in s for s in mock.status_updates)


def test_effect_measurement_closedloop_end_to_end():
    """Verify full end-to-end flow of match settlement recording and effectiveness analytics."""
    db = DuckDBManager(in_memory=True)

    # Ingest 3 matches with varying compliance and outcomes
    m1_nodes = [
        TurnReviewNode(turn_number=1, mana=1, max_mana=1, friendly_hp=30, enemy_hp=30, score=100, action_grade="✅ 最佳"),
        TurnReviewNode(turn_number=2, mana=2, max_mana=2, friendly_hp=30, enemy_hp=26, score=90, action_grade="✅ 最佳", had_lethal=True),
    ]
    db.record_match_replay("M1", 10.0, "WIN", "MAGE", "HUNTER", MatchReplaySummary(result="WIN", total_turns=2, overall_accuracy_pct=95.0, grade_tier="S", turn_nodes=m1_nodes))

    m2_nodes = [
        TurnReviewNode(turn_number=1, mana=1, max_mana=1, friendly_hp=30, enemy_hp=30, score=85, action_grade="✅ 最佳"),
        TurnReviewNode(turn_number=2, mana=2, max_mana=2, friendly_hp=28, enemy_hp=24, score=80, action_grade="⚖️ 良好"),
    ]
    db.record_match_replay("M2", 20.0, "WIN", "PALADIN", "WARRIOR", MatchReplaySummary(result="WIN", total_turns=2, overall_accuracy_pct=82.5, grade_tier="A", turn_nodes=m2_nodes))

    m3_nodes = [
        TurnReviewNode(turn_number=1, mana=1, max_mana=1, friendly_hp=30, enemy_hp=30, score=20, action_grade="❌ 严重伏笔"),
        TurnReviewNode(turn_number=2, mana=2, max_mana=2, friendly_hp=15, enemy_hp=20, score=30, action_grade="❌ 严重伏笔", had_lethal=True),
    ]
    db.record_match_replay("M3", 30.0, "LOSS", "ROGUE", "DRUID", MatchReplaySummary(result="LOSS", total_turns=2, overall_accuracy_pct=25.0, grade_tier="D", turn_nodes=m3_nodes))

    report = db.query_ai_effectiveness_report()
    assert report["total_matches_analyzed"] == 3
    assert report["total_turns_analyzed"] == 6
    # Matches with avg compliance >= 0.7 are M1 (95%) and M2 (82.5%) -> both won = 100%
    assert report["winrate_when_followed"] == 100.0
    # Match with avg compliance < 0.7 is M3 (25%) -> lost = 0%
    assert report["winrate_when_diverged"] == 0.0
    assert report["effectiveness_delta"] == 100.0
    # Lethal was flagged in M1 (won) and M3 (lost) -> 1/2 = 50%
    assert report["lethal_conversion_pct"] == 50.0
