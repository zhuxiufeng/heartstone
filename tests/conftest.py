"""Shared test fixtures."""

import pytest

from core.arena_card_stats import ArenaCardStats


@pytest.fixture(autouse=True)
def offline_arena_stats(tmp_path_factory):
    """Keep tests hermetic: arena win-rate stats start empty and never touch the network.

    Individual tests may load a payload via ArenaCardStats.get_instance().load_payload(...).
    """
    ArenaCardStats.reset_instance()
    inst = ArenaCardStats(cache_dir=tmp_path_factory.mktemp("arena_stats"), auto_refresh=False)
    ArenaCardStats._instance = inst
    yield inst
    ArenaCardStats.reset_instance()
