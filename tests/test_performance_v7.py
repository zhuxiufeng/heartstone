"""
Unit tests for Performance Optimization Suite (v7):
1. Card Database N-gram Inverted Index & High-speed Fuzzy Lookup
2. ActionTreeSearch Transposition Table Memoization & Lethal Short-Circuit
3. OCR 64-bit dHash Perceptual Deduplication Filter
4. WebCompanion ThreadingHTTPServer & Versioned ETag 304 Not Modified
5. AiEngine Decoupled Optimistic Fast-Path
6. BoardTacticalOverlay Repaint Deduplication
"""

import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import time
import urllib.request
from typing import Dict, Any, List

import numpy as np
import pytest
from PyQt5.QtWidgets import QApplication

_qapp = QApplication.instance() or QApplication([])

from core.card_db import CardDatabase, CardInfo
from core.action_tree_search import ActionTreeSearch, ActionTreeResult
from core.ocr_engine import compute_dhash, OcrWorker
from core.web_companion import WebCompanionServer, _STATE_VERSION
from core.ai_engine import AiEngine
from ui.board_overlay import BoardTacticalOverlay


def test_card_db_ngram_index_and_fuzzy_speed():
    db = CardDatabase.get_instance()
    assert len(db.ngram_index) > 0

    # Ensure 2-grams and 3-grams exist
    assert "淡水" in db.ngram_index or "火球" in db.ngram_index or "奥术" in db.ngram_index

    # Benchmark fuzzy lookup speed with N-Gram index
    t0 = time.perf_counter()
    res = db.fuzzy_match_card("淡水鳄")
    t1 = time.perf_counter()
    assert res is not None
    assert res.name == "淡水鳄"
    assert (t1 - t0) < 0.05  # Must complete in < 50ms (typically <0.1ms)


def test_action_tree_memoization_and_lethal_short_circuit():
    ActionTreeSearch.clear_cache()

    friendly = [{"name": "随从A", "atk": 6, "health": 6, "can_attack": True}]
    enemy = []  # No taunt
    hand = [CardInfo(id="CS2_029", name="火球术", cost=4)]

    # 1. Direct lethal face short-circuit (enemy has 5 hp, friendly board has 6 atk)
    res_lethal = ActionTreeSearch.search_optimal_branch(
        friendly_minions=friendly,
        enemy_minions=enemy,
        hand_cards=hand,
        available_mana=4,
        friendly_hp=30,
        enemy_hp=5,
        opponent_class="Mage",
    )
    assert res_lethal.best_branch.ev_score >= 900.0
    assert "斩杀" in res_lethal.best_branch.tactical_intent

    # 2. Memoization cache hit test
    t0 = time.perf_counter()
    res_cached = ActionTreeSearch.search_optimal_branch(
        friendly_minions=friendly,
        enemy_minions=enemy,
        hand_cards=hand,
        available_mana=4,
        friendly_hp=30,
        enemy_hp=5,
        opponent_class="Mage",
    )
    t1 = time.perf_counter()
    assert res_cached is res_lethal  # Must be exact cached object instance!
    assert (t1 - t0) < 0.001  # Sub-millisecond return


def test_ocr_dhash_perceptual_filter():
    # Create two identical visual frames
    frame1 = np.zeros((100, 200, 3), dtype=np.uint8)
    frame1[20:60, 30:80] = 200

    frame2 = frame1.copy()

    h1 = compute_dhash(frame1)
    h2 = compute_dhash(frame2)
    assert isinstance(h1, int)
    assert h1 == h2

    # Frame with tiny noise (1 pixel difference)
    frame3 = frame1.copy()
    frame3[0, 0] = 50
    h3 = compute_dhash(frame3)
    hamming = bin(h1 ^ h3).count("1")
    assert hamming <= 2


def test_web_companion_etag_304_and_threading():
    server = WebCompanionServer(port=8897)
    server.start()
    time.sleep(0.1)

    url = f"http://127.0.0.1:{server.port}/api/state"

    # 1. Initial GET request returns 200 with ETag header
    req1 = urllib.request.Request(url)
    with urllib.request.urlopen(req1, timeout=3) as resp1:
        assert resp1.status == 200
        etag = resp1.headers.get("ETag")
        assert etag is not None

    # 2. Conditional GET with matching If-None-Match returns 304 Not Modified
    req2 = urllib.request.Request(url, headers={"If-None-Match": etag})
    try:
        with urllib.request.urlopen(req2, timeout=3) as resp2:
            assert resp2.status == 304
    except urllib.error.HTTPError as e:
        assert e.code == 304

    server.stop()


def test_ai_engine_optimistic_decoupling():
    ai = AiEngine(api_key="", cache_enabled=False)
    candidates = [
        CardInfo(id="CS2_022", name="变形术", cost=4, card_type="SPELL"),
        CardInfo(id="CS2_120", name="淡水鳄", cost=2, attack=2, health=3, card_type="MINION"),
        CardInfo(id="CS2_182", name="冰风雪人", cost=4, attack=4, health=5, card_type="MINION"),
    ]

    t0 = time.perf_counter()
    rec_draft = ai.evaluate_draft_pick("法师", candidates, [], use_llm=False)
    t1 = time.perf_counter()
    assert rec_draft is not None
    assert len(rec_draft.cards_evaluations) == 3
    assert (t1 - t0) < 0.05  # Instant local evaluation

    t2 = time.perf_counter()
    rec_play = ai.evaluate_play_turn(
        turn_number=3,
        current_mana=3,
        hand_cards=candidates,
        friendly_board=[],
        enemy_board=[],
        opponent_class="法师",
        use_llm=False,
    )
    t3 = time.perf_counter()
    assert rec_play is not None
    assert (t3 - t2) < 0.05


def test_board_overlay_repaint_deduplication():
    overlay = BoardTacticalOverlay()
    minions = [{"name": "淡水鳄", "atk": 2, "health": 3}]

    overlay.update_board_tactics(minions, [], ["走脸"], ["出牌"], 0, 30, False, 0, 0)
    key1 = overlay._last_board_tactics_key
    assert key1 is not None

    # Call with same arguments
    overlay.update_board_tactics(minions, [], ["走脸"], ["出牌"], 0, 30, False, 0, 0)
    assert overlay._last_board_tactics_key == key1
