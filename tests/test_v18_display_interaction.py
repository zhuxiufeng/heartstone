"""
Unit and integration tests for v18 Display & Interactive Hologram Suite.
Covers:
- ARBoardProjectionWidget, VectorAttackArrow, GhostPlacementSlot, MinionStatusAura
- RadialProbabilityCompassWidget, ManaSectorData
- HologramCardInspectorWidget, HologramCardData
- PrismaticThemeEngine, ThemePreset
- StreamerHUDController, StreamerTickerWidget, TickerItem
- WebCompanion v18 Endpoints (/api/ui/streamer, /api/ui/prismatic/theme, /api/ui/board/tactics, /obs)
"""

import json
from unittest.mock import MagicMock

import pytest
try:
    from PyQt5.QtWidgets import QApplication
except ImportError:
    try:
        from PyQt6.QtWidgets import QApplication
    except ImportError:
        QApplication = None

from ui.ar_board_overlay import (
    ARBoardProjectionWidget,
    GhostPlacementSlot,
    MinionStatusAura,
    VectorAttackArrow,
)
from ui.radial_probability_compass import ManaSectorData, RadialProbabilityCompassWidget
from ui.hologram_card_inspector import HologramCardData, HologramCardInspectorWidget
from ui.prismatic_theme_engine import PrismaticThemeEngine, ThemePreset
from ui.streamer_hud import StreamerHUDController, StreamerTickerWidget, TickerItem


@pytest.fixture(scope="session")
def qapp():
    if QApplication is None:
        return None
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


def test_ar_board_projection_tactics(qapp):
    arrow = VectorAttackArrow(
        start_x=100.0,
        start_y=200.0,
        end_x=300.0,
        end_y=150.0,
        damage=8,
        is_lethal=True,
        source_name="火元素",
        target_name="吉安娜",
        step_order=1,
        description="直伤走脸过墙斩杀",
    )
    tooltip = arrow.get_tooltip()
    assert "火元素 ➔ 吉安娜" in tooltip
    assert "造成伤害: 8 点" in tooltip
    assert "【直接斩杀】" in tooltip

    slot = GhostPlacementSlot(
        slot_index=2,
        x=250.0,
        y=400.0,
        strategy_type="防陨石",
        ev_delta=0.65,
    )
    rect = slot.get_bounds()
    rx = rect.x() if callable(getattr(rect, "x", None)) else rect.x
    ry = rect.y() if callable(getattr(rect, "y", None)) else rect.y
    assert rx == 250.0 - 36.0
    assert ry == 400.0 - 48.0

    aura = MinionStatusAura(x=200.0, y=200.0, radius=40.0, status_flags=["TAUNT", "DIVINE_SHIELD"])
    assert "TAUNT" in aura.status_flags

    widget = ARBoardProjectionWidget()
    widget.set_tactics([arrow], [slot], [aura])
    assert len(widget.arrows) == 1
    assert len(widget.ghost_slots) == 1
    assert len(widget.status_auras) == 1

    # Hit testing
    hovered_idx = widget.get_hovered_arrow(200.0, 175.0)
    assert hovered_idx == 0

    clicked = widget.get_clicked_slot(250.0, 400.0)
    assert clicked is not None
    assert clicked.slot_index == 2

    widget.advance_pulse(0.1)
    assert widget.pulse_phase > 0.0


def test_radial_probability_compass(qapp):
    data = ManaSectorData(
        mana_cost=4,
        card_count=3,
        total_deck=15,
        card_names=["火球术", "变形术", "水元素"],
    )
    assert data.probability == pytest.approx(3 / 15)

    compass = RadialProbabilityCompassWidget()
    deck_dist = {
        1: ["奥术飞弹", "法力浮龙"],
        2: ["寒冰箭", "远古雕文"],
        4: ["火球术", "变形术"],
        7: ["烈焰风暴"],
    }
    compass.set_data(deck_dist, lethal_pct=45.0, survival_pct=72.0, fatigue_turns=5, fatigue_dmg=1)
    assert compass.total_cards == 7
    assert len(compass.sectors) == 4
    assert compass.topdeck_lethal_pct == 45.0

    # Needle target angle calculation
    compass.update_needle_target()
    assert compass.needle_angle_target == pytest.approx(-120.0 + 0.45 * 240.0)

    # Toggle mode
    new_mode = compass.toggle_mode()
    assert new_mode == "SURVIVAL"
    assert compass.active_mode == "SURVIVAL"
    assert compass.needle_angle_target == pytest.approx(-120.0 + 0.72 * 240.0)

    # Hit testing sector at 12 o'clock area
    sec = compass.get_sector_at(100.0, 50.0, 100.0, 100.0, 80.0)
    # Distance is 50, within radius 80 and outside inner radius
    assert sec is not None
    assert sec.mana_cost in deck_dist


def test_hologram_card_inspector(qapp):
    card = HologramCardData(
        card_id="CORE_CS2_032",
        card_name="烈焰风暴",
        mana_cost=7,
        attack=None,
        health=None,
        card_type="SPELL",
        rarity="EPIC",
        text="对所有敌方随从造成 5 点伤害。",
        flavor_text="当你想给对方全场洗个热水澡时。",
        winrate_pct=61.2,
        inclusion_rate_pct=54.8,
        best_turn=7,
        synergy_tags=["AOE 清场", "反攻节奏"],
    )
    assert card.card_name == "烈焰风暴"
    assert card.mana_cost == 7
    assert "AOE 清场" in card.synergy_tags

    inspector = HologramCardInspectorWidget()
    inspector.inspect_card(card)
    assert inspector.card_data == card

    # Ripple micro interaction
    inspector.trigger_ripple(50.0, 50.0)
    assert inspector.ripple_pos == (50.0, 50.0)
    assert inspector.ripple_radius == 5.0
    inspector._step_ripple()
    assert inspector.ripple_radius > 5.0


def test_prismatic_theme_engine():
    engine = PrismaticThemeEngine("CYBER_NEON")
    names = engine.list_theme_names()
    assert "CYBER_NEON" in names
    assert "TAVERN_HEARTH" in names
    assert "FROZEN_THRONE" in names
    assert "VOID_SHADOW" in names
    assert "MINIMAL_MONOCHROME" in names

    cur = engine.get_current_theme()
    assert cur.name == "CYBER_NEON"
    assert cur.display_name_zh == "赛博霓虹"

    qss = engine.generate_qss()
    assert "mainOverlayWidget" in qss
    assert cur.primary_color in qss

    css_vars = engine.generate_css_variables()
    assert "--theme-primary" in css_vars
    assert css_vars["--theme-primary"] == cur.primary_color

    next_theme = engine.cycle_next_theme()
    assert next_theme.name != "CYBER_NEON"
    assert engine.current_theme_name == next_theme.name


def test_streamer_hud_controller(qapp):
    controller = StreamerHUDController()
    assert controller.is_streamer_mode_active is False

    active = controller.toggle_streamer_mode()
    assert active is True
    assert controller.is_streamer_mode_active is True

    controller.add_ticker_message("💥 斩杀线已锁定！", "LETHAL")
    item = controller.get_current_ticker()
    assert item is not None

    advanced = controller.advance_ticker()
    assert advanced is not None

    # Filter confidential state
    raw_state = {
        "tilt_status": "⚠️ 心态极危: 连败红温中",
        "personal_habit_reminder": "防贪防伏笔",
        "winrate_pct": 52.0,
    }
    filtered = controller.filter_confidential_state(raw_state)
    assert filtered["tilt_status"] == ""
    assert filtered["personal_habit_reminder"] == ""
    assert filtered["winrate_pct"] == 52.0
    assert filtered["is_streamer_mode"] is True

    # OBS browser config
    obs_cfg = controller.get_obs_browser_config()
    assert "http://127.0.0.1:8899/obs" in obs_cfg["url"]
    assert obs_cfg["recommended_width"] == 460

    ticker_widget = StreamerTickerWidget(controller)
    assert ticker_widget.controller == controller


def test_web_companion_v18_endpoints():
    from core.web_companion import WebCompanionHandler

    class DummyHandler(WebCompanionHandler):
        def __init__(self):
            self.headers = {"Content-Length": "0"}
            self.rfile = MagicMock()
            self.wfile = MagicMock()
            self._response_code = 0
            self._headers = {}

        def send_response(self, code, message=None):
            self._response_code = code

        def send_header(self, keyword, value):
            self._headers[keyword] = value

        def end_headers(self):
            pass

    # 1. Test POST /api/ui/streamer
    handler = DummyHandler()
    handler.path = "/api/ui/streamer"
    handler.rfile.read.return_value = json.dumps({"active": True}).encode("utf-8")
    handler.headers = {"Content-Length": str(len(handler.rfile.read.return_value))}
    handler.do_POST()
    assert handler._response_code == 200

    # 2. Test POST /api/ui/prismatic/theme
    handler = DummyHandler()
    handler.path = "/api/ui/prismatic/theme"
    payload = json.dumps({"theme": "FROZEN_THRONE"}).encode("utf-8")
    handler.rfile.read.return_value = payload
    handler.headers = {"Content-Length": str(len(payload))}
    handler.do_POST()
    assert handler._response_code == 200

    # 3. Test POST /api/ui/board/tactics
    handler = DummyHandler()
    handler.path = "/api/ui/board/tactics"
    payload = json.dumps({
        "arrows": [{"source": "随从A", "target": "敌方脸", "damage": 6}],
        "ghost_slots": [{"slot": 1, "strategy": "防陨石"}],
    }).encode("utf-8")
    handler.rfile.read.return_value = payload
    handler.headers = {"Content-Length": str(len(payload))}
    handler.do_POST()
    assert handler._response_code == 200

    # 4. Test GET /obs
    handler = DummyHandler()
    handler.path = "/obs"
    handler.do_GET()
    assert handler._response_code == 200
    assert "text/html" in handler._headers.get("Content-Type", "")
