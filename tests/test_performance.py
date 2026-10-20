"""
Unit tests for performance optimizations.
"""

from core.card_db import CardDatabase, FALLBACK_CARDS_SAMPLE
from core.log_listener import LogListener
from core.ocr_engine import OcrWorker


def test_card_db_length_buckets_and_cache():
    db = CardDatabase(auto_download=False)
    db._build_indexes(FALLBACK_CARDS_SAMPLE)

    # Length buckets should be initialized
    assert len(db.length_buckets) > 0
    # Clear cache
    db._fuzzy_cache.clear()

    # Search with typo/fuzzy: "暴风成勇士" for "暴风城勇士"
    card = db.fuzzy_match_card("暴风成勇士")
    assert card is not None
    assert card.name == "暴风城勇士"
    # Cache should be populated
    assert len(db._fuzzy_cache) > 0

    # Second lookup should hit cache in 0ms
    card_cached = db.fuzzy_match_card("暴风成勇士")
    assert card_cached == card


def test_ocr_worker_pause_resume():
    worker = OcrWorker()
    assert worker.is_paused() is False
    worker.pause()
    assert worker.is_paused() is True
    worker.resume()
    assert worker.is_paused() is False


def test_log_listener_fast_path():
    listener = LogListener(log_dir="/tmp")
    # Unrelated log lines (e.g. sound/animation/debug) should be filtered out immediately
    unrelated_line = "D 15:45:00.123456 SoundManager: Playing sound UI_Minion_Summon.wav"
    initial_turn = listener.turn_count
    listener._parse_power_line(unrelated_line)
    # No state change
    assert listener.turn_count == initial_turn
