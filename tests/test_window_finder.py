"""
Unit tests for WindowFinder and resolution adaptation.
"""

from core.window_finder import WindowFinder, WindowRect


def test_window_rect_conversion():
    rect = WindowRect(left=100, top=200, width=1920, height=1080)
    mss_dict = rect.to_mss_dict()
    assert mss_dict == {"top": 200, "left": 100, "width": 1920, "height": 1080}
    assert rect.right == 2020
    assert rect.bottom == 1280


def test_draft_card_banners_scaling():
    # Test 1080p
    win_1080p = WindowRect(left=0, top=0, width=1920, height=1080)
    banners_1080 = WindowFinder.get_draft_card_name_regions(win_1080p)
    assert len(banners_1080) == 3
    # Check left to right order
    assert banners_1080[0].left < banners_1080[1].left < banners_1080[2].left
    assert banners_1080[0].width > 0 and banners_1080[0].height > 0

    # Test 4K (3840x2160)
    win_4k = WindowRect(left=0, top=0, width=3840, height=2160)
    banners_4k = WindowFinder.get_draft_card_name_regions(win_4k)
    assert len(banners_4k) == 3
    # Width and height should scale proportionally (2x of 1080p)
    assert banners_4k[0].width == banners_1080[0].width * 2
    assert banners_4k[0].height == banners_1080[0].height * 2
