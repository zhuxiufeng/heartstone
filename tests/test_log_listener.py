"""
Unit tests for LogListener parsing Hearthstone Arena.log and Power.log.
"""

from pathlib import Path
from core.card_db import CardDatabase, FALLBACK_CARDS_SAMPLE
from core.log_listener import LogListener


def test_log_listener_arena_pick(tmp_path: Path):
    db = CardDatabase(auto_download=False)
    db._build_indexes(FALLBACK_CARDS_SAMPLE)

    log_dir = tmp_path / "Logs"
    log_dir.mkdir()
    arena_log = log_dir / "Arena.log"

    listener = LogListener(str(log_dir), card_db=db)

    picked_events = []
    listener.card_picked.connect(lambda e: picked_events.append(e))

    # Simulate line from Arena.log
    arena_line = "D 14:00:00.0000000 Arena.MakePick - Chosen Card: CORE_CS2_039 Slot: 1\n"
    listener._parse_arena_line(arena_line)

    assert len(picked_events) == 1
    assert picked_events[0]["card_id"] == "CORE_CS2_039"
    assert picked_events[0]["slot"] == 1
    assert picked_events[0]["card"].name == "风暴战斧"
    assert len(listener.current_deck) == 1


def test_log_listener_hero_detection(tmp_path: Path):
    db = CardDatabase(auto_download=False)
    db._build_indexes(FALLBACK_CARDS_SAMPLE)

    listener = LogListener(str(tmp_path), card_db=db)
    heroes = []
    listener.draft_hero_selected.connect(lambda h: heroes.append(h))

    listener._parse_arena_line("Arena - Hero: HERO_08")
    assert len(heroes) == 1
    assert listener.current_hero in ("HERO_08", "法师", "MAGE")
