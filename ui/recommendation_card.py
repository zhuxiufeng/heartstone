"""
RecommendationCard: PyQt5 card widget presenting single candidate card evaluation.
Highlights the recommended best pick with distinct borders and tags.
"""

from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

try:
    from core.ai_engine import CardEvaluation
    from core.card_db import CardInfo
except (ImportError, ValueError):
    from ..core.ai_engine import CardEvaluation
    from ..core.card_db import CardInfo


class RecommendationCard(QFrame):
    """Visual card for one of the three arena candidate choices."""

    def __init__(self, index: int, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.index = index
        self._current_card_name = ""
        self._current_card_text = ""
        self._init_ui()

    def _init_ui(self) -> None:
        self.setObjectName("recCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # Top row: [Rank Badge] [Card Name] [Score Pill]
        top_row = QHBoxLayout()
        top_row.setSpacing(6)

        self.rank_badge = QLabel(f"#{self.index + 1}", self)
        self.rank_badge.setStyleSheet("""
            background: rgba(255, 255, 255, 0.08);
            color: #94a3b8;
            font-size: 11px;
            font-weight: bold;
            padding: 2px 7px;
            border-radius: 4px;
        """)

        self.name_lbl = QLabel("等待候选牌...", self)
        self.name_lbl.setStyleSheet("color: #f8fafc; font-size: 12.5px; font-weight: 700;")

        self.cost_lbl = QLabel("", self)
        self.cost_lbl.setStyleSheet("""
            background: rgba(56, 189, 248, 0.15);
            color: #38bdf8;
            border: 1px solid rgba(56, 189, 248, 0.3);
            font-size: 10.5px;
            font-weight: bold;
            padding: 1px 5px;
            border-radius: 4px;
        """)
        self.cost_lbl.hide()

        self.score_pill = QLabel("--分", self)
        self.score_pill.setAlignment(Qt.AlignCenter)
        self.score_pill.setFixedWidth(52)
        self.score_pill.setStyleSheet("""
            background: rgba(255, 255, 255, 0.05);
            color: #64748b;
            font-size: 11px;
            font-weight: bold;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 2px 4px;
        """)

        top_row.addWidget(self.rank_badge)
        top_row.addWidget(self.cost_lbl)
        top_row.addWidget(self.name_lbl, stretch=1)
        top_row.addWidget(self.score_pill)
        layout.addLayout(top_row)

        # Summary line
        self.summary_lbl = QLabel("", self)
        self.summary_lbl.setWordWrap(True)
        self.summary_lbl.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        layout.addWidget(self.summary_lbl)

        self.set_unselected_style()

    def update_evaluation(self, eval_data: CardEvaluation, card_info: Optional[CardInfo] = None) -> None:
        """Populate widget with card metadata and evaluation metrics."""
        self.name_lbl.setText(eval_data.card_name)
        self.score_pill.setText(f"{eval_data.score}分")
        self._current_card_name = eval_data.card_name
        self._current_card_text = getattr(card_info, "text", "") or getattr(card_info, "clean_text", "") or ""

        if card_info:
            stats = ""
            if card_info.card_type == "MINION" and card_info.attack is not None:
                stats = f" {card_info.attack}/{card_info.health}"
            self.cost_lbl.setText(f"{card_info.cost}费{stats}")
            self.cost_lbl.show()
        else:
            self.cost_lbl.hide()

        summary_parts = [eval_data.summary]
        if eval_data.pros:
            summary_parts.append(f"🟢 优: {', '.join(eval_data.pros)}")
        if eval_data.cons:
            summary_parts.append(f"🔻 劣: {', '.join(eval_data.cons)}")

        self.summary_lbl.setText("\n".join([p for p in summary_parts if p]))

        if eval_data.is_best_pick:
            self.set_best_pick_style()
        else:
            self.set_unselected_style()

    def update_hero_evaluation(self, hero_info: Any, is_best_pick: bool = False) -> None:
        """Populate widget with hero tier evaluation metrics."""
        self.name_lbl.setText(f"{hero_info.class_cn}")
        self.score_pill.setText(f"{hero_info.winrate:.1f}%")
        self.cost_lbl.setText(f"{hero_info.tier}")
        self.cost_lbl.show()

        summary_parts = [
            f"技能: {hero_info.hero_power_rating}",
            f"推荐体系: {hero_info.recommended_archetype}",
            f"💡 抓牌建议: {hero_info.draft_priority_advice}",
        ]
        self.summary_lbl.setText("\n".join(summary_parts))

        if is_best_pick:
            self.set_best_pick_style()
        else:
            self.set_unselected_style()

    def set_best_pick_style(self) -> None:
        self.rank_badge.setText("★ 首选")
        self.rank_badge.setStyleSheet("""
            background: #0284c7;
            color: #ffffff;
            font-size: 10.5px;
            font-weight: 800;
            padding: 2px 7px;
            border-radius: 4px;
        """)
        self.score_pill.setStyleSheet("""
            background: rgba(16, 185, 129, 0.15);
            color: #34d399;
            font-size: 12px;
            font-weight: 800;
            border: 1px solid rgba(16, 185, 129, 0.35);
            border-radius: 10px;
            padding: 2px 6px;
        """)
        self.setStyleSheet("""
            QFrame#recCard {
                background: rgba(14, 165, 233, 0.08);
                border: 1.5px solid #38bdf8;
                border-radius: 8px;
            }
            QFrame#recCard:hover {
                border-color: #7dd3fc;
                background: rgba(14, 165, 233, 0.14);
            }
        """)

    def set_unselected_style(self) -> None:
        self.rank_badge.setText(f"#{self.index + 1}")
        self.rank_badge.setStyleSheet("""
            background: rgba(255, 255, 255, 0.06);
            color: #94a3b8;
            font-size: 10.5px;
            font-weight: bold;
            padding: 2px 6px;
            border-radius: 4px;
        """)
        self.score_pill.setStyleSheet("""
            background: rgba(255, 255, 255, 0.04);
            color: #64748b;
            font-size: 11px;
            font-weight: bold;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 10px;
            padding: 2px 4px;
        """)
        self.setStyleSheet("""
            QFrame#recCard {
                background-color: rgba(255, 255, 255, 0.025);
                border: 1px solid rgba(255, 255, 255, 0.07);
                border-radius: 8px;
            }
            QFrame#recCard:hover {
                background-color: rgba(255, 255, 255, 0.05);
                border-color: rgba(255, 255, 255, 0.15);
            }
        """)

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        parent_overlay = self.window()
        if hasattr(parent_overlay, "board_overlay") and parent_overlay.board_overlay:
            parent_overlay.board_overlay.set_hovered_card(self._current_card_name, self._current_card_text)

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        parent_overlay = self.window()
        if hasattr(parent_overlay, "board_overlay") and parent_overlay.board_overlay:
            parent_overlay.board_overlay.set_hovered_card("")
