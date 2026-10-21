"""
CapsuleHUD: Minimalist Pill-Bar Floating Heads-Up Display Mode.
Encapsulates critical live battle data (lethal alerts, key action, winrate, miracle out)
into an ultra-compact ~36px status pill that prevents game board occlusion.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger("CapsuleHUD")


@dataclass
class CapsuleDisplayData:
    is_capsule_active: bool
    has_lethal: bool
    lethal_text: str
    primary_action_short: str
    winrate_pct: float
    miracle_topdeck_card: str
    miracle_topdeck_pct: float
    status_summary_line: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_capsule_active": self.is_capsule_active,
            "has_lethal": self.has_lethal,
            "lethal_text": self.lethal_text,
            "primary_action_short": self.primary_action_short,
            "winrate_pct": round(self.winrate_pct, 1),
            "miracle_topdeck_card": self.miracle_topdeck_card,
            "miracle_topdeck_pct": round(self.miracle_topdeck_pct, 1),
            "status_summary_line": self.status_summary_line,
        }


class CapsuleHUD:
    """Manages data packing and formatting for the compact floating pill bar."""

    CAPSULE_WIDTH = 480
    CAPSULE_HEIGHT = 38
    FULL_WIDTH = 480
    FULL_HEIGHT = 720

    @classmethod
    def format_display(
        cls,
        has_lethal: bool = False,
        lethal_desc: str = "",
        primary_action: str = "等待对局启动...",
        winrate_pct: float = 50.0,
        miracle_card: str = "",
        miracle_pct: float = 0.0,
        is_capsule_active: bool = False,
    ) -> CapsuleDisplayData:
        # Shorten primary action if too long
        if len(primary_action) > 20:
            short_action = primary_action[:19] + "…"
        else:
            short_action = primary_action

        parts = []
        if has_lethal:
            parts.append("⚡斩杀!")
        parts.append(short_action)
        parts.append(f"胜率{int(winrate_pct)}%")
        if miracle_card and miracle_pct > 0:
            parts.append(f"神抽:{miracle_card}({int(miracle_pct)}%)")

        line = " | ".join(parts)

        return CapsuleDisplayData(
            is_capsule_active=is_capsule_active,
            has_lethal=has_lethal,
            lethal_text=lethal_desc or ("已达成斩杀!" if has_lethal else ""),
            primary_action_short=short_action,
            winrate_pct=winrate_pct,
            miracle_topdeck_card=miracle_card,
            miracle_topdeck_pct=miracle_pct,
            status_summary_line=line,
        )
