"""
UI components for Hearthstone Arena AI Assistant.
"""

from .mana_curve import ManaCurveWidget
from .recommendation_card import RecommendationCard
from .settings_dialog import SettingsDialog
from .overlay import OverlayWindow
from .inplace_hud import InPlaceHudManager
from .card_tooltip import CardTooltip
from .acrylic_effects import AcrylicGlassHelper, BreathingAuraController, AuraState
from .dynamic_island_capsule import DynamicIslandCapsule
from .winrate_sparkline import WinrateSparklineWidget
from .magnetic_docking import MagneticDockingManager, DockingAnchor
from .animated_voice_orb import AnimatedVoiceOrb, OrbVisualState
from .parallax_card_widget import ParallaxCardWidget

__all__ = [
    "ManaCurveWidget",
    "RecommendationCard",
    "SettingsDialog",
    "OverlayWindow",
    "InPlaceHudManager",
    "CardTooltip",
    "AcrylicGlassHelper",
    "BreathingAuraController",
    "AuraState",
    "DynamicIslandCapsule",
    "WinrateSparklineWidget",
    "MagneticDockingManager",
    "DockingAnchor",
    "AnimatedVoiceOrb",
    "OrbVisualState",
    "ParallaxCardWidget",
]
