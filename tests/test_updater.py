from core.updater import UpdateChecker, CURRENT_VERSION


def test_update_checker():
    results = []

    def cb(info):
        results.append(info)

    UpdateChecker.check_for_updates(cb)
    import time
    time.sleep(0.05)
    assert len(results) == 1
    assert results[0].current_version == CURRENT_VERSION
