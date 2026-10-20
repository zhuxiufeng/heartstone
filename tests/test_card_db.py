"""
Unit tests for CardDatabase and CardInfo metadata.
"""

from pathlib import Path
from core.card_db import CardDatabase, CardInfo, FALLBACK_CARDS_SAMPLE


def test_card_info_formatting():
    card = CardInfo(
        id="CS2_222",
        name="暴风城勇士",
        cost=7,
        attack=6,
        health=6,
        card_class="NEUTRAL",
        card_type="MINION",
        rarity="COMMON",
        text="<b>你的其他随从</b>获得+1/+1。",
    )
    assert card.clean_text == "你的其他随从获得+1/+1。"
    prompt_str = card.format_for_ai_prompt()
    assert "暴风城勇士" in prompt_str
    assert "7 费" in prompt_str
    assert "6 攻击力 / 6 生命值" in prompt_str


def test_card_db_indexing_and_fuzzy_match():
    # Force use of fallback sample cards without downloading
    db = CardDatabase(auto_download=False)
    db._build_indexes(FALLBACK_CARDS_SAMPLE)
    
    # ID lookup
    axe = db.get_by_id("CORE_CS2_039")
    assert axe is not None
    assert axe.name == "风暴战斧"
    assert axe.cost == 2
    
    # Name lookup
    dwarf = db.get_by_name("叫嚣的矮人")
    assert dwarf is not None
    assert dwarf.id == "CS2_188"
    
    # Fuzzy match with OCR typos
    # e.g. OCR recognized "暴风成勇士" instead of "暴风城勇士"
    fuzzy_match = db.fuzzy_match_card("暴风成勇士")
    assert fuzzy_match is not None
    assert fuzzy_match.name == "暴风城勇士"

    # Fuzzy match with extra noise/punctuation "【火球术】."
    fireball = db.fuzzy_match_card("【火球术】.")
    assert fireball is not None
    assert fireball.name == "火球术"
