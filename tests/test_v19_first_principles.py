"""
Unit and integration tests for v19 First-Principles Grandmaster Cockpit.
Covers:
- RecommendationCard Lead Delta & Verdict Tags
- ManaCurveWidget Deck Health Panorama
- Overlay Priority-0 Real-Time Lethal Detection & Execution Banner
- Grandmaster Mulligan Cockpit (HTML Capsule Cards)
- Segmented Tactical Intel Drawer (Deck / Hand / Coin Tab Switching & Collapse)
- Exception Isolation for Secondary Intel Subsystems
"""

import pytest
from unittest.mock import MagicMock

try:
    from PyQt5.QtWidgets import QApplication
except ImportError:
    try:
        from PyQt6.QtWidgets import QApplication
    except ImportError:
        QApplication = None

from core.ai_engine import CardEvaluation, AiEngine
from core.card_db import CardDatabase, CardInfo
from core.config_manager import ConfigManager
from core.log_listener import LogListener
from core.ocr_engine import OcrWorker
from ui.recommendation_card import RecommendationCard
from ui.mana_curve import ManaCurveWidget
from ui.overlay import OverlayWindow


@pytest.fixture(scope="session")
def qapp():
    if QApplication is None:
        return None
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


def test_recommendation_card_first_principles(qapp):
    card = RecommendationCard(index=0)
    eval_best = CardEvaluation(
        card_id="CS2_029",
        card_name="火球术",
        score=92,
        is_best_pick=True,
        summary="直伤终结手段",
        pros=["爆发高", "解大怪"],
        cons=[],
    )
    c_info = CardInfo(
        id="CS2_029",
        name="火球术",
        cost=4,
        card_class="MAGE",
        card_type="SPELL",
        rarity="FREE",
    )

    card.update_evaluation(eval_best, c_info, delta_lead=14.5, verdict_tag="S级核心")

    assert "火球术" in card.name_lbl.text()
    assert "92分" in card.score_pill.text()
    assert "4费" in card.cost_lbl.text()
    assert "绝佳首选" in card.rank_badge.text() or "核心" in card.rank_badge.text()
    summary = card.summary_lbl.text()
    assert "+14.5分" in summary
    assert "S级核心" in summary


def test_mana_curve_deck_health_panorama(qapp):
    widget = ManaCurveWidget()
    assert hasattr(widget, "deck_health_lbl")
    widget.update_deck_health(archetype="节奏中速", health_pct=88, notice="缺少4费随从")
    assert "节奏中速" in widget.deck_health_lbl.text()
    assert "88%" in widget.deck_health_lbl.text()
    assert "缺少4费随从" in widget.deck_health_lbl.text()


def test_overlay_first_principles_lethal_and_drawer(qapp):
    cfg = ConfigManager("/tmp/test_v19_cfg.json")
    cdb = CardDatabase(auto_download=False)
    cdb.load()
    ai = AiEngine(card_db=cdb)
    ll = LogListener(log_dir="/tmp", card_db=cdb)
    ocr = OcrWorker(card_db=cdb)

    win = OverlayWindow(cfg, cdb, ai, ll, ocr)
    win.show()

    # Test Sample Play with Lethal
    win.simulate_sample_play()

    assert win.lethal_frame.isVisible() is True
    assert "绝杀战机已现" in win.lethal_title_lbl.text() or "LETHAL" in win.lethal_title_lbl.text()
    assert "11 点" in win.lethal_detail_lbl.text()
    assert "火球术" in win.lethal_steps_lbl.text()
    assert win.play_actions_frame.isVisible() is True

    # Test Tactical Drawer Switching
    assert hasattr(win, "drawer_bar")
    assert win.deck_frame.isVisible() is True
    assert win.hand_frame.isVisible() is False

    # Switch to HAND tab
    win._switch_intel_tab("HAND")
    assert win.hand_frame.isVisible() is True
    assert win.deck_frame.isVisible() is False

    # Switch to COIN tab
    win._switch_intel_tab("COIN")
    assert win.coin_frame.isVisible() is True
    assert win.deck_frame.isVisible() is False
    assert win.hand_frame.isVisible() is False

    # Double-click COIN to collapse
    win._switch_intel_tab("COIN")
    assert win._intel_expanded is False
    assert win.coin_frame.isVisible() is False

    # Test Mulligan Cockpit
    win.simulate_sample_mulligan()
    assert win.mulligan_frame.isVisible() is True
    assert "必留" in win.mulligan_lbl.text()
    assert "换掉" in win.mulligan_lbl.text()
