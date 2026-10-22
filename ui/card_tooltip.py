"""
CardTooltip: Floating preview card providing high-definition metadata and clean card summary
when hovering over cards in the deck tracker or recommendation lists.
"""

from __future__ import annotations

import logging
from typing import Optional

from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

try:
    from core.card_db import CardInfo
except (ImportError, ValueError):
    from ..core.card_db import CardInfo

logger = logging.getLogger("CardTooltip")

RARITY_COLORS = {
    "FREE": "#94a3b8",
    "COMMON": "#ffffff",
    "RARE": "#3b82f6",
    "EPIC": "#a855f7",
    "LEGENDARY": "#f59e0b",
}


class CardTooltip(QWidget):
    """Floating card info card popup."""

    _instance: Optional[CardTooltip] = None

    @classmethod
    def get_instance(cls) -> CardTooltip:
        if cls._instance is None:
            cls._instance = CardTooltip()
        return cls._instance

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.ToolTip |
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedWidth(220)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.card_frame = QFrame(self)
        self.card_frame.setObjectName("tooltipFrame")
        layout = QVBoxLayout(self.card_frame)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # Header: Cost + Name
        header = QHBoxLayout()
        header.setSpacing(6)
        self.mana_lbl = QLabel("💎 0", self)
        self.mana_lbl.setStyleSheet("color: #38bdf8; font-size: 13px; font-weight: bold;")
        self.name_lbl = QLabel("卡牌名称", self)
        self.name_lbl.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: bold;")
        header.addWidget(self.mana_lbl)
        header.addWidget(self.name_lbl)
        header.addStretch()
        layout.addLayout(header)

        # Type, Rarity, Race
        self.meta_lbl = QLabel("随从 • 普通", self)
        self.meta_lbl.setStyleSheet("color: #94a3b8; font-size: 10px;")
        layout.addWidget(self.meta_lbl)

        # Body: Card text
        self.text_lbl = QLabel("", self)
        self.text_lbl.setWordWrap(True)
        self.text_lbl.setStyleSheet("color: #e2e8f0; font-size: 11px; line-height: 1.3;")
        layout.addWidget(self.text_lbl)

        # Mechanics tags
        self.mechanics_lbl = QLabel("", self)
        self.mechanics_lbl.setWordWrap(True)
        self.mechanics_lbl.setStyleSheet("color: #38bdf8; font-size: 10px; font-weight: bold;")
        layout.addWidget(self.mechanics_lbl)

        # Stats banner (Atk / Health)
        self.stats_lbl = QLabel("⚔️ 4 / 🩸 5", self)
        self.stats_lbl.setStyleSheet("color: #34d399; font-size: 12px; font-weight: bold;")
        layout.addWidget(self.stats_lbl)

        # Tokens / Titan Abilities
        self.tokens_lbl = QLabel("", self)
        self.tokens_lbl.setWordWrap(True)
        self.tokens_lbl.setStyleSheet("color: #7dd3fc; font-size: 10px; margin-top: 4px; padding-top: 4px; border-top: 1px dashed rgba(56, 189, 248, 0.3);")
        layout.addWidget(self.tokens_lbl)
        self.tokens_lbl.hide()

        main_layout.addWidget(self.card_frame)

    def show_card(self, card: CardInfo, global_pos: QPoint) -> None:
        """Positions and populates card preview."""
        self.mana_lbl.setText(f"💎 {card.cost}")
        self.name_lbl.setText(card.name)

        rarity_color = RARITY_COLORS.get((card.rarity or "COMMON").upper(), "#ffffff")
        self.name_lbl.setStyleSheet(f"color: {rarity_color}; font-size: 13px; font-weight: bold;")

        race_str = f" • {card.race}" if card.race else ""
        c_class = getattr(card, "card_class", "中立")
        c_type = getattr(card, "card_type", getattr(card, "type", "随从"))
        school = f" ({card.spell_school})" if getattr(card, "spell_school", None) else ""
        self.meta_lbl.setText(f"{c_class} • {c_type}{school}{race_str}")

        clean_desc = card.clean_text or "(无特殊卡牌描述)"
        self.text_lbl.setText(clean_desc)

        # Keyword mechanics tags
        mech_map = {
            "BATTLECRY": "⚡ 战吼",
            "DEATHRATTLE": "💀 亡语",
            "TAUNT": "🛡️ 嘲讽",
            "DIVINE_SHIELD": "✨ 圣盾",
            "RUSH": "🐎 突袭",
            "CHARGE": "⚔️ 冲锋",
            "POISONOUS": "☠️ 剧毒",
            "LIFESTEAL": "🩸 吸血",
            "REBORN": "🕯️ 复生",
            "DISCOVER": "🔮 发现",
            "SECRET": "❓ 奥秘",
            "OVERLOAD": "⚡ 过载",
            "SPELLPOWER": "✨ 法术伤害",
        }
        active_mechs = [mech_map[m] for m in getattr(card, "mechanics", []) if m in mech_map]
        if active_mechs:
            self.mechanics_lbl.setText("  ".join(active_mechs))
            self.mechanics_lbl.show()
        else:
            self.mechanics_lbl.hide()

        if card.attack is not None and card.health is not None:
            self.stats_lbl.setText(f"⚔️ {card.attack} / 🩸 {card.health}")
            self.stats_lbl.show()
        elif card.durability is not None:
            self.stats_lbl.setText(f"⚔️ {card.attack or 0} / 🛡️ {card.durability}")
            self.stats_lbl.show()
        else:
            self.stats_lbl.hide()

        # Check for Tokens or Titan Abilities
        try:
            from core.token_inspector import TokenInspector
            token_summary = TokenInspector.format_token_summary(getattr(card, "id", ""), card.name)
            if token_summary:
                self.tokens_lbl.setText(token_summary)
                self.tokens_lbl.show()
            else:
                self.tokens_lbl.hide()
        except Exception:
            self.tokens_lbl.hide()

        self.card_frame.setStyleSheet(f"""
            QFrame#tooltipFrame {{
                background-color: rgba(24, 24, 27, 250);
                border: 1.5px solid {rarity_color};
                border-radius: 8px;
            }}
        """)

        # Adjust position slightly offset from mouse cursor
        self.move(global_pos.x() + 15, global_pos.y() - 10)
        self.adjustSize()
        self.show()

    def hide_card(self) -> None:
        self.hide()
