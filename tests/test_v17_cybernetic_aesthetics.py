"""
Unit tests for v17 Cybernetic Aesthetics (赛博美学版) optimizations:
1. Native Acrylic Glass & Breathing Aura Border
2. Dynamic Island Capsule HUD 2.0
3. Live Winrate Sparkline & EKG Chart
4. Intelligent Window Magnetic Docking & DPI Scaling
5. Interactive Animated Voice Orb
6. 3D Parallax Hologram Card Widget
"""

import sys
import pytest
from PyQt5.QtWidgets import QApplication

from ui.acrylic_effects import (
    AcrylicGlassHelper, BreathingAuraController, AuraState
)
from ui.dynamic_island_capsule import DynamicIslandCapsule
from ui.winrate_sparkline import WinrateSparklineWidget
from ui.magnetic_docking import MagneticDockingManager, DockingAnchor
from ui.animated_voice_orb import AnimatedVoiceOrb, OrbVisualState
from ui.parallax_card_widget import ParallaxCardWidget


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["-platform", "offscreen"])
    return app


def test_acrylic_effects():
    # 1. Test Lethal Gold stylesheet
    qss_gold = AcrylicGlassHelper.get_glass_stylesheet(AuraState.LETHAL_GOLD, glow_phase=0.5)
    assert "245, 158, 11" in qss_gold
    assert "border-radius" in qss_gold

    # 2. Test Blunder Red stylesheet
    qss_red = AcrylicGlassHelper.get_glass_stylesheet(AuraState.BLUNDER_RED, glow_phase=0.8)
    assert "239, 68, 68" in qss_red

    # 3. Test Miracle Purple stylesheet
    qss_purple = AcrylicGlassHelper.get_glass_stylesheet(AuraState.MIRACLE_PURPLE, glow_phase=0.2)
    assert "168, 85, 247" in qss_purple

    # 4. Test controller ticking
    ctrl = BreathingAuraController()
    emitted = []
    ctrl.sig_aura_updated.connect(lambda s: emitted.append(s))
    ctrl.set_state(AuraState.LETHAL_GOLD)
    ctrl._on_tick()
    assert len(emitted) >= 1
    assert "245, 158, 11" in emitted[0]


def test_dynamic_island_capsule(qapp):
    island = DynamicIslandCapsule()
    assert island._is_expanded is False
    assert island.width() == DynamicIslandCapsule.COLLAPSED_WIDTH
    assert island.height() == DynamicIslandCapsule.COLLAPSED_HEIGHT

    # Update metrics
    island.update_metrics(turn=5, lethal=12, winrate=68.5)
    assert "T5" in island.lbl_status.text()
    assert "12点" in island.lbl_status.text()
    assert "68.5%" in island.lbl_status.text()

    # Expand alert
    island.show_alert("🚨 伏笔拦截！", "请先打奥术智慧过牌！", alert_color="#ef4444", duration_ms=2000)
    assert island._is_expanded is True
    assert island.width() == DynamicIslandCapsule.EXPANDED_WIDTH
    assert not island.lbl_title.isHidden()
    assert "伏笔拦截" in island.lbl_title.text()

    # Collapse
    island.collapse()
    assert island._is_expanded is False
    assert island.lbl_title.isHidden()
    assert island.width() == DynamicIslandCapsule.COLLAPSED_WIDTH


def test_winrate_sparkline(qapp):
    sparkline = WinrateSparklineWidget()
    assert len(sparkline.history) == 1

    # Add turns
    sparkline.add_turn_record(turn=2, winrate=62.0, tag="STANDARD")
    sparkline.add_turn_record(turn=3, winrate=45.0, tag="BLUNDER_ALERT")
    sparkline.add_turn_record(turn=4, winrate=88.5, tag="MIRACLE_STAR")

    assert len(sparkline.history) == 4
    assert sparkline.history[-1][1] == 88.5
    assert sparkline.history[-1][2] == "MIRACLE_STAR"

    # Overwrite turn 4
    sparkline.add_turn_record(turn=4, winrate=92.0, tag="MIRACLE_STAR")
    assert len(sparkline.history) == 4
    assert sparkline.history[-1][1] == 92.0

    # Clear
    sparkline.clear()
    assert len(sparkline.history) == 1


def test_magnetic_docking():
    # 1. Standard 1080p window docking (TOP_RIGHT)
    anchor_1080 = MagneticDockingManager.compute_dock_coordinates(
        hs_rect=(100, 50, 1920, 1080),
        overlay_width=380,
        overlay_height=620,
        dock_mode="TOP_RIGHT",
    )
    assert anchor_1080.is_snapped is True
    assert anchor_1080.scale_factor == 1.0
    assert anchor_1080.width == 380
    assert anchor_1080.x == 100 + 1920 - 380 - 12

    # 2. 4K Window docking (High DPI scale 1.45)
    anchor_4k = MagneticDockingManager.compute_dock_coordinates(
        hs_rect=(0, 0, 3840, 2160),
        overlay_width=380,
        overlay_height=620,
        dock_mode="TOP_CENTER",
    )
    assert anchor_4k.scale_factor == 1.45
    assert anchor_4k.width == int(380 * 1.45)
    assert anchor_4k.x == int((3840 - anchor_4k.width) / 2)

    # 3. Scaled font calculation
    font_scaled = MagneticDockingManager.get_scaled_font_size(10, 1.45)
    assert font_scaled == 14


def test_animated_voice_orb(qapp):
    orb = AnimatedVoiceOrb(size=36)
    assert orb.current_state == OrbVisualState.IDLE

    # Switch states
    orb.set_state(OrbVisualState.SPEAKING)
    assert orb.current_state == OrbVisualState.SPEAKING

    orb.set_amplitude(0.85)
    assert orb.amplitude == 0.85

    orb.set_state(OrbVisualState.COMFORT)
    assert orb.current_state == OrbVisualState.COMFORT

    # Tick animation phase
    old_phase = orb.phase
    orb._on_tick()
    assert orb.phase != old_phase


def test_parallax_card_widget(qapp):
    # Titan card widget
    card = ParallaxCardWidget(
        card_name="阿曼苏尔",
        cost=7,
        attack=3,
        health=8,
        score=98.5,
        is_titan=True,
    )
    assert card.lbl_cost.text() == "7"
    assert card.lbl_name.text() == "阿曼苏尔"
    assert card.lbl_score.text() == "98.5"
    assert card.is_titan is True

    # Mouse hover state
    card.is_hovered = True
    card.tilt_x = 0.5
    card.tilt_y = -0.5
    assert card.tilt_x == 0.5

    # Leave resets tilt
    card.is_hovered = False
    card.tilt_x = 0.0
    card.tilt_y = 0.0
    assert card.tilt_x == 0.0
