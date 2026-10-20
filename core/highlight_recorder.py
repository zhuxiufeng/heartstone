"""
HighlightClipRecorder: Circular Frame Buffer & Milestone Highlight Exporter.
Maintains in-memory circular buffer of recent match frames and exports
highlight GIFs / image clips upon game-winning lethals or critical misplays.
"""

from __future__ import annotations

import collections
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Deque, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("HighlightClipRecorder")


@dataclass
class HighlightFrame:
    timestamp: float
    image: np.ndarray
    turn: int
    note: str


class HighlightClipRecorder:
    """Manages lightweight in-memory circular buffer (<25MB) of match screen frames."""

    _instance: Optional[HighlightClipRecorder] = None

    @classmethod
    def get_instance(cls) -> HighlightClipRecorder:
        if cls._instance is None:
            cls._instance = HighlightClipRecorder()
        return cls._instance

    def __init__(self, max_frames: int = 12) -> None:
        self.buffer: Deque[HighlightFrame] = collections.deque(maxlen=max_frames)
        self.last_capture_time: float = 0.0

    def clear(self) -> None:
        self.buffer.clear()

    def push_frame(self, image: np.ndarray, turn: int = 1, note: str = "") -> None:
        """Pushes a frame to the circular buffer with automatic throttling (max 1 frame per 1.2s)."""
        if image is None or image.size == 0:
            return
        now = time.time()
        if now - self.last_capture_time < 1.0 and len(self.buffer) > 0:
            return
        self.last_capture_time = now
        # Store a scaled down copy to maintain zero memory footprint (<15MB total)
        try:
            import cv2
            h, w = image.shape[:2]
            target_w = 640
            target_h = int(h * (target_w / w))
            small = cv2.resize(image, (target_w, target_h), interpolation=cv2.INTER_AREA)
        except Exception:
            small = image

        self.buffer.append(HighlightFrame(
            timestamp=now,
            image=small,
            turn=turn,
            note=note,
        ))

    def export_highlight(
        self,
        output_path: str,
        event_type: str = "LETHAL_WIN",
        title: str = "🏆 竞技场高光名场面",
        subtitle: str = "极限逆转绝杀",
    ) -> bool:
        """Compiles circular buffer into an animated GIF or composite summary image."""
        if not self.buffer:
            logger.warning("Highlight buffer empty; cannot export.")
            return False

        try:
            from PIL import Image, ImageDraw, ImageFont

            frames_pil = []
            for hf in list(self.buffer):
                arr = hf.image
                if len(arr.shape) == 3 and arr.shape[2] == 3:
                    # BGR to RGB
                    arr_rgb = arr[:, :, ::-1]
                else:
                    arr_rgb = arr
                img = Image.fromarray(arr_rgb)
                draw = ImageDraw.Draw(img)

                # Watermark banner
                w, h = img.size
                draw.rectangle([(0, h - 36), (w, h)], fill=(15, 23, 42, 220))
                tag_text = f"{title} | 第{hf.turn}回合: {hf.note or subtitle}"
                draw.text((12, h - 28), tag_text, fill=(56, 189, 248))

                frames_pil.append(img)

            out_p = Path(output_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)

            if str(output_path).lower().endswith(".gif") and len(frames_pil) > 1:
                frames_pil[0].save(
                    output_path,
                    save_all=True,
                    append_images=frames_pil[1:],
                    duration=600,
                    loop=0,
                )
            else:
                # Save latest frame as high-res PNG snapshot
                frames_pil[-1].save(output_path)

            logger.info(f"Saved highlight to {output_path} ({len(frames_pil)} frames)")
            return True
        except Exception as e:
            logger.error(f"Failed to export highlight clip: {e}", exc_info=True)
            return False
