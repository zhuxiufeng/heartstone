"""
PrismaticThemeEngine: Multi-Dimensional Holographic Color Palettes & Dual-End Theming.
Generates comprehensive Qt stylesheets (QSS) and Web companion CSS variables for 5 master themes:
Cyber Neon, Tavern Hearth, Frozen Throne, Void Shadow, and Minimal Monochrome.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


@dataclass
class ThemePreset:
    """Defines complete visual attributes for a theme."""
    name: str
    display_name_zh: str
    primary_color: str
    secondary_color: str
    background_rgba: str
    border_color: str
    aura_glow: str
    text_primary: str
    text_secondary: str
    accent_color: str
    ekg_gradient_start: str
    ekg_gradient_end: str
    card_border_radius: int = 12

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "display_name_zh": self.display_name_zh,
            "primary_color": self.primary_color,
            "secondary_color": self.secondary_color,
            "background_rgba": self.background_rgba,
            "border_color": self.border_color,
            "aura_glow": self.aura_glow,
            "text_primary": self.text_primary,
            "text_secondary": self.text_secondary,
            "accent_color": self.accent_color,
            "ekg_gradient_start": self.ekg_gradient_start,
            "ekg_gradient_end": self.ekg_gradient_end,
            "card_border_radius": self.card_border_radius,
        }


class PrismaticThemeEngine:
    """Manages active UI themes and stylesheet generation for desktop and web."""

    THEMES: Dict[str, ThemePreset] = {
        "CYBER_NEON": ThemePreset(
            name="CYBER_NEON",
            display_name_zh="赛博霓虹",
            primary_color="#38bdf8",
            secondary_color="#a855f7",
            background_rgba="rgba(15, 23, 42, 235)",
            border_color="rgba(56, 189, 248, 0.4)",
            aura_glow="#06b6d4",
            text_primary="#f8fafc",
            text_secondary="#94a3b8",
            accent_color="#f43f5e",
            ekg_gradient_start="#38bdf8",
            ekg_gradient_end="#10b981",
        ),
        "TAVERN_HEARTH": ThemePreset(
            name="TAVERN_HEARTH",
            display_name_zh="酒馆暖木",
            primary_color="#f59e0b",
            secondary_color="#d97706",
            background_rgba="rgba(38, 24, 14, 240)",
            border_color="rgba(245, 158, 11, 0.45)",
            aura_glow="#fbbf24",
            text_primary="#fef3c7",
            text_secondary="#d97706",
            accent_color="#b45309",
            ekg_gradient_start="#fbbf24",
            ekg_gradient_end="#f59e0b",
        ),
        "FROZEN_THRONE": ThemePreset(
            name="FROZEN_THRONE",
            display_name_zh="冰封王座",
            primary_color="#67e8f9",
            secondary_color="#0284c7",
            background_rgba="rgba(12, 28, 48, 240)",
            border_color="rgba(103, 232, 249, 0.4)",
            aura_glow="#38bdf8",
            text_primary="#ecfeff",
            text_secondary="#7dd3fc",
            accent_color="#e0f2fe",
            ekg_gradient_start="#67e8f9",
            ekg_gradient_end="#0369a1",
        ),
        "VOID_SHADOW": ThemePreset(
            name="VOID_SHADOW",
            display_name_zh="暗影虚空",
            primary_color="#c084fc",
            secondary_color="#7e22ce",
            background_rgba="rgba(26, 16, 37, 245)",
            border_color="rgba(192, 132, 252, 0.4)",
            aura_glow="#a855f7",
            text_primary="#f3e8ff",
            text_secondary="#c084fc",
            accent_color="#10b981",
            ekg_gradient_start="#a855f7",
            ekg_gradient_end="#ec4899",
        ),
        "MINIMAL_MONOCHROME": ThemePreset(
            name="MINIMAL_MONOCHROME",
            display_name_zh="极简黑白",
            primary_color="#e2e8f0",
            secondary_color="#94a3b8",
            background_rgba="rgba(18, 18, 20, 250)",
            border_color="rgba(226, 232, 240, 0.3)",
            aura_glow="#ffffff",
            text_primary="#ffffff",
            text_secondary="#94a3b8",
            accent_color="#cbd5e1",
            ekg_gradient_start="#ffffff",
            ekg_gradient_end="#64748b",
        ),
    }

    def __init__(self, default_theme: str = "CYBER_NEON"):
        self.current_theme_name = default_theme if default_theme in self.THEMES else "CYBER_NEON"

    @classmethod
    def list_theme_names(cls) -> List[str]:
        return list(cls.THEMES.keys())

    @classmethod
    def get_theme(cls, name: str) -> ThemePreset:
        return cls.THEMES.get(name, cls.THEMES["CYBER_NEON"])

    def set_theme(self, name: str) -> ThemePreset:
        if name in self.THEMES:
            self.current_theme_name = name
        return self.get_current_theme()

    def get_current_theme(self) -> ThemePreset:
        return self.THEMES[self.current_theme_name]

    def cycle_next_theme(self) -> ThemePreset:
        """Cycles through available themes interactively."""
        names = self.list_theme_names()
        idx = names.index(self.current_theme_name)
        next_idx = (idx + 1) % len(names)
        self.current_theme_name = names[next_idx]
        return self.get_current_theme()

    def generate_qss(self, theme_name: Optional[str] = None) -> str:
        """Generates comprehensive Qt QSS stylesheet for the overlay."""
        t = self.get_theme(theme_name or self.current_theme_name)
        return f"""
        QWidget#mainOverlayWidget {{
            background-color: {t.background_rgba};
            border: 1.8px solid {t.border_color};
            border-radius: {t.card_border_radius}px;
        }}
        QLabel {{
            color: {t.text_primary};
            font-family: 'Microsoft YaHei', sans-serif;
        }}
        QLabel#secondaryText {{
            color: {t.text_secondary};
        }}
        QPushButton {{
            background-color: rgba(30, 41, 59, 200);
            color: {t.text_primary};
            border: 1px solid {t.border_color};
            border-radius: 6px;
            padding: 4px 8px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {t.primary_color};
            color: #ffffff;
            border-color: {t.primary_color};
        }}
        QPushButton:pressed {{
            background-color: {t.secondary_color};
        }}
        """

    def generate_css_variables(self, theme_name: Optional[str] = None) -> Dict[str, str]:
        """Generates CSS variable mappings for web companion and OBS overlay."""
        t = self.get_theme(theme_name or self.current_theme_name)
        return {
            "--theme-primary": t.primary_color,
            "--theme-secondary": t.secondary_color,
            "--theme-bg": t.background_rgba,
            "--theme-border": t.border_color,
            "--theme-aura": t.aura_glow,
            "--theme-text": t.text_primary,
            "--theme-text-sub": t.text_secondary,
            "--theme-accent": t.accent_color,
            "--theme-ekg-start": t.ekg_gradient_start,
            "--theme-ekg-end": t.ekg_gradient_end,
        }
