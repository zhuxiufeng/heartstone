"""
Intelligent Window Magnetic Docking & DPI Scaling (游戏窗口智能磁吸吸附与 DPI 视网膜缩放)
- Automatically locks the AI overlay to the top-right / top-center of the Hearthstone client.
- Follows window movements, minimize, and restore events smoothly.
- Computes optimal Retina DPI scaling factor (0.8x to 1.5x) based on 1080p, 2K, 4K monitor bounds.
"""

from dataclasses import dataclass
from typing import Tuple, Optional


@dataclass
class DockingAnchor:
    x: int
    y: int
    width: int
    height: int
    scale_factor: float
    is_snapped: bool


class MagneticDockingManager:
    """
    Calculates magnetic snapping coordinates and DPI scaling.
    """

    @classmethod
    def compute_dock_coordinates(
        cls,
        hs_rect: Optional[Tuple[int, int, int, int]],  # (x, y, w, h)
        overlay_width: int = 380,
        overlay_height: int = 620,
        dock_mode: str = "TOP_RIGHT",  # "TOP_RIGHT", "TOP_CENTER"
    ) -> DockingAnchor:
        """
        Calculates magnetic snapped position relative to the Hearthstone window.
        """
        if not hs_rect or hs_rect[2] <= 0 or hs_rect[3] <= 0:
            # Fallback to standard top-right screen margin
            return DockingAnchor(
                x=100, y=100, width=overlay_width, height=overlay_height, scale_factor=1.0, is_snapped=False
            )

        hx, hy, hw, hh = hs_rect

        # 1. Calculate DPI scale factor from window height
        if hh >= 2100:  # 4K
            scale = 1.45
        elif hh >= 1400:  # 2K / 1440p
            scale = 1.20
        elif hh <= 900:  # 720p / Small
            scale = 0.85
        else:  # 1080p standard
            scale = 1.0

        scaled_w = int(overlay_width * scale)
        scaled_h = int(overlay_height * scale)

        if dock_mode == "TOP_CENTER":
            # For Dynamic Island capsule
            target_x = hx + int((hw - scaled_w) / 2)
            target_y = hy + 8  # Slight top offset
        else:
            # TOP_RIGHT dock: snap to right margin inside game window
            target_x = hx + hw - scaled_w - 12
            target_y = hy + 38  # Below window title bar

        return DockingAnchor(
            x=target_x,
            y=target_y,
            width=scaled_w,
            height=scaled_h,
            scale_factor=scale,
            is_snapped=True,
        )

    @classmethod
    def get_scaled_font_size(cls, base_pt: int, scale_factor: float) -> int:
        """
        Scales font point size proportionally with DPI factor.
        """
        return max(7, int(base_pt * scale_factor))
