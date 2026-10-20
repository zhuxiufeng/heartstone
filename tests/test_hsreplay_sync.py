from core.hsreplay_sync import HsreplaySync


def test_hsreplay_sync():
    sync = HsreplaySync.get_instance()
    # Test Tier S Titan bonus
    delta = sync.get_card_winrate_delta("TTN_903", "阿曼苏尔")
    assert delta >= 15.0

    # Test unknown card default
    delta_unknown = sync.get_card_winrate_delta("UNKNOWN_ID", "普通随从")
    assert delta_unknown == 0.0
