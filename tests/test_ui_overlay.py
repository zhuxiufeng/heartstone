import os
import pytest

# Ensure headless Qt
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PyQt5.QtWidgets import QApplication

from core.ai_engine import AiEngine
from core.card_db import CardDatabase
from core.config_manager import ConfigManager
from core.log_listener import LogListener
from core.ocr_engine import OcrWorker
from ui.overlay import OverlayWindow, get_app_icon_path, create_app_icon


@pytest.fixture(scope="session", autouse=True)
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def overlay(qapp, tmp_path):
    cfg_file = tmp_path / "config.json"
    cfg = ConfigManager(str(cfg_file))
    cdb = CardDatabase(auto_download=False)
    ai = AiEngine(card_db=cdb)
    ll = LogListener(log_dir=str(tmp_path), card_db=cdb)
    ocr = OcrWorker(card_db=cdb)
    win = OverlayWindow(cfg, cdb, ai, ll, ocr)
    yield win
    try:
        win.close()
    except Exception:
        pass


def test_app_icon(qapp):
    icon = create_app_icon()
    assert icon is not None
    assert not icon.isNull()


def test_compact_mode_toggle(overlay):
    assert overlay.is_compact_mode is False
    assert overlay.compact_widget.isHidden()

    # Toggle to compact
    overlay.toggle_compact_mode()
    assert overlay.is_compact_mode is True
    assert not overlay.compact_widget.isHidden()
    assert overlay.draft_container.isHidden()
    assert overlay.play_container.isHidden()
    assert overlay.height() <= 54

    # Toggle back
    overlay.toggle_compact_mode()
    assert overlay.is_compact_mode is False
    assert overlay.compact_widget.isHidden()
    assert overlay.height() >= 350


def test_theme_cycling(overlay):
    initial_theme = overlay._current_theme
    overlay.cycle_theme()
    assert overlay._current_theme != initial_theme
    assert overlay._current_theme in overlay.THEMES


def test_turn_replayer_ui(overlay):
    assert overlay.turn_replayer_frame.isHidden()
    overlay.simulate_sample_replay()
    assert not overlay.turn_replayer_frame.isHidden()
    assert overlay._current_replay_summary is not None
    assert overlay._current_replay_summary.total_turns == 6
    assert overlay.replayer_turns_layout.count() == 6

    # Step through turns
    overlay._replayer_next_turn()
    assert overlay._current_replay_index >= 0
    overlay._replayer_prev_turn()

    # Hide and verify
    overlay.hide_turn_replayer()
    assert overlay.turn_replayer_frame.isHidden()
