"""
InPlaceHud: Floating transparent badges placed directly on top of the 3 arena candidate cards in-game.
Click-through and frameless so player can directly click Hearthstone cards underneath.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont, QPainter
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

try:
    from core.ai_engine import CardEvaluation, DraftRecommendation
    from core.card_db import CardInfo
    from core.window_finder import WindowFinder, WindowRect
except (ImportError, ValueError):
    from ..core.ai_engine import CardEvaluation, DraftRecommendation
    from ..core.card_db import CardInfo
    from ..core.window_finder import WindowFinder, WindowRect

logger = logging.getLogger("InPlaceHud")


class InPlaceBadge(QWidget):
    """Single floating badge pinned right above one draft choice card."""

    def __init__(self, index: int, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.index = index
        self._score = 70
        self._is_best = False
        self._synergy_text = ""

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.SubWindow |
            Qt.WindowTransparentForInput  # Click-through so card clicks work!
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFixedSize(140, 60)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(1)

        self.frame = QFrame(self)
        self.frame.setObjectName("badgeFrame")
        frame_layout = QVBoxLayout(self.frame)
        frame_layout.setContentsMargins(4, 3, 4, 3)
        frame_layout.setSpacing(1)

        self.title_lbl = QLabel("候选", self)
        self.title_lbl.setAlignment(Qt.AlignCenter)
        self.title_lbl.setStyleSheet("color: #cbd5e1; font-size: 10px; font-weight: bold;")
        frame_layout.addWidget(self.title_lbl)

        self.score_lbl = QLabel("70分", self)
        self.score_lbl.setAlignment(Qt.AlignCenter)
        self.score_lbl.setStyleSheet("color: #fbbf24; font-size: 14px; font-weight: bold;")
        frame_layout.addWidget(self.score_lbl)

        self.syn_lbl = QLabel("", self)
        self.syn_lbl.setAlignment(Qt.AlignCenter)
        self.syn_lbl.setStyleSheet("color: #fbbf24; font-size: 9px;")
        frame_layout.addWidget(self.syn_lbl)

        layout.addWidget(self.frame)
        self._apply_style()

    def update_evaluation(self, eval_item: CardEvaluation, card: CardInfo) -> None:
        self._score = eval_item.score
        self._is_best = eval_item.is_best_pick

        # Look for synergy keyword in pros
        syn_tag = ""
        for p in eval_item.pros:
            if p.startswith("【") and "】" in p:
                syn_tag = p.split("】")[0] + "】"
                break
        self._synergy_text = syn_tag

        if self._is_best:
            self.title_lbl.setText("★ 首选推荐")
            self.title_lbl.setStyleSheet("color: #fef08a; font-size: 10px; font-weight: bold;")
        else:
            self.title_lbl.setText(f"候选 #{self.index + 1}")
            self.title_lbl.setStyleSheet("color: #a8a29e; font-size: 10px;")

        self.score_lbl.setText(f"{self._score}分")
        self.syn_lbl.setText(self._synergy_text)
        self._apply_style()

    def _apply_style(self) -> None:
        if self._is_best:
            self.frame.setStyleSheet("""
                QFrame#badgeFrame {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(180, 83, 9, 235), stop:1 rgba(120, 53, 15, 235));
                    border: 2px solid #fbbf24;
                    border-radius: 8px;
                }
            """)
            self.score_lbl.setStyleSheet("color: #fef08a; font-size: 14px; font-weight: bold;")
        elif self._score >= 70:
            self.frame.setStyleSheet("""
                QFrame#badgeFrame {
                    background: rgba(41, 37, 36, 230);
                    border: 1.5px solid rgba(245, 158, 11, 0.65);
                    border-radius: 8px;
                }
            """)
            self.score_lbl.setStyleSheet("color: #fbbf24; font-size: 14px; font-weight: bold;")
        else:
            self.frame.setStyleSheet("""
                QFrame#badgeFrame {
                    background: rgba(28, 25, 23, 210);
                    border: 1px solid rgba(120, 113, 108, 0.4);
                    border-radius: 8px;
                }
            """)
            self.score_lbl.setStyleSheet("color: #a8a29e; font-size: 14px; font-weight: bold;")


class InPlaceHudManager:
    """Controls the 3 screen-pinned in-place badges."""

    def __init__(self, window_finder: Optional[WindowFinder] = None) -> None:
        self.window_finder = window_finder or WindowFinder()
        self.badges: List[InPlaceBadge] = [InPlaceBadge(i) for i in range(3)]
        self._enabled = True

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        if not enabled:
            self.hide()

    def update_recommendations(self, rec: DraftRecommendation, candidates: List[CardInfo]) -> None:
        if not self._enabled:
            return

        win_rect = self.window_finder.find_window()
        if not win_rect:
            self.hide()
            return

        banner_rects = WindowFinder.get_draft_card_name_regions(win_rect)
        if len(banner_rects) != 3 or len(rec.cards_evaluations) != 3:
            return

        for idx in range(3):
            badge = self.badges[idx]
            r = banner_rects[idx]
            eval_item = rec.cards_evaluations[idx]
            c_info = candidates[idx]
            badge.update_evaluation(eval_item, c_info)

            # Center badge right above the card banner
            bx = r.left + (r.width - badge.width()) // 2
            by = max(0, r.top - badge.height() - 6)
            badge.move(bx, by)
            badge.show()

    def hide(self) -> None:
        for b in self.badges:
            b.hide()
