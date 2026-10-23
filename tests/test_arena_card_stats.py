"""Tests for real arena win-rate data integration (Firestone public stats)."""

from core.ai_engine import AiEngine
from core.arena_card_stats import ArenaCardStats, PRIOR_STRENGTH
from core.card_db import CardInfo


def _payload(entries):
    return {"lastUpdated": "2026-10-23T00:00:00Z", "stats": [
        {"cardId": cid, "stats": {"drawn": n, "drawnThenWin": w, "played": n, "playedThenWin": w,
                                  "decksWithCard": n, "decksWithCardThenWin": w}}
        for cid, n, w in entries
    ]}


def test_bayesian_shrinkage_and_baseline(offline_arena_stats):
    # baseline = (600 + 400 + 30) / (1000 + 1000 + 60)
    offline_arena_stats.load_payload("global", _payload([
        ("STRONG", 1000, 600), ("WEAK", 1000, 400), ("TINY", 60, 30),
    ]))
    strong = offline_arena_stats.get_card_winrate("STRONG")
    weak = offline_arena_stats.get_card_winrate("WEAK")
    base = 1030 / 2060
    assert abs(strong.baseline_pct - base * 100) < 1e-6
    expected = (600 + PRIOR_STRENGTH * base) / (1000 + PRIOR_STRENGTH) * 100
    assert abs(strong.adjusted_winrate_pct - expected) < 1e-6
    assert strong.adjusted_winrate_pct < strong.drawn_winrate_pct   # shrunk toward baseline
    assert strong.score_delta > 0 > weak.score_delta


def test_unknown_and_low_sample_cards_return_none(offline_arena_stats):
    offline_arena_stats.load_payload("global", _payload([("FEW", 10, 9)]))
    assert offline_arena_stats.get_card_winrate("FEW") is None
    assert offline_arena_stats.get_card_winrate("MISSING") is None


def test_class_context_preferred_over_global(offline_arena_stats):
    offline_arena_stats.load_payload("global", _payload([("X", 1000, 500), ("Y", 1000, 500)]))
    offline_arena_stats.load_payload("mage", _payload([("X", 800, 560), ("Y", 800, 400)]))
    assert offline_arena_stats.get_card_winrate("X", "MAGE").context == "mage"
    assert offline_arena_stats.get_card_winrate("X", "WARRIOR").context == "global"


def test_core_prefix_fallback(offline_arena_stats):
    offline_arena_stats.load_payload("global", _payload([("CS2_029", 1000, 600), ("Z", 1000, 400)]))
    assert offline_arena_stats.get_card_winrate("CORE_CS2_029") is not None


def test_draft_ranking_follows_real_data_over_heuristics(offline_arena_stats):
    """A legendary with a poor real win rate must lose to a common with a strong one."""
    offline_arena_stats.load_payload("global", _payload([
        ("LEG_BAD", 5000, 2300), ("COM_GOOD", 5000, 3300), ("MID", 5000, 2800),
    ]))
    leg = CardInfo(id="LEG_BAD", name="华而不实传说", cost=4, card_type="MINION", attack=5, health=5, rarity="LEGENDARY")
    com = CardInfo(id="COM_GOOD", name="朴实强卡", cost=4, card_type="MINION", attack=3, health=4, rarity="COMMON")
    mid = CardInfo(id="MID", name="普通卡", cost=4, card_type="MINION", attack=4, health=4, rarity="COMMON")
    engine = AiEngine(api_key=None, cache_enabled=False)
    rec = engine.evaluate_draft_pick("MAGE", [leg, com, mid], [], use_llm=False)
    assert rec.best_card_name == "朴实强卡"
    good = next(e for e in rec.cards_evaluations if e.card_name == "朴实强卡")
    assert good.real_winrate_pct is not None and good.real_winrate_samples == 5000
    assert "实战数据" in good.pros[0]


def test_draft_without_data_marks_heuristic(offline_arena_stats):
    c = CardInfo(id="NODATA", name="新卡", cost=3, card_type="MINION", attack=3, health=3)
    engine = AiEngine(api_key=None, cache_enabled=False)
    rec = engine.evaluate_draft_pick("MAGE", [c], [], use_llm=False)
    assert rec.cards_evaluations[0].real_winrate_pct is None
    assert "无实战数据" in rec.cards_evaluations[0].pros[0]
