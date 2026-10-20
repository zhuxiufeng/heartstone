"""
Unit tests for DiscoveryPoolRadar.
"""

from core.discovery_pool_radar import DiscoveryPoolRadar, DiscoveryProbabilityReport


def test_mage_discovery_odds():
    report: DiscoveryProbabilityReport = DiscoveryPoolRadar.calculate_discover_odds(
        opponent_class="法师",
        discover_source_card="发现法术",
    )
    assert report.opponent_class == "MAGE"
    assert len(report.key_odds) >= 2

    # Check that Flamestrike / Blizzard probability is positive and realistic (~15-20%)
    flamestrike_odd = next(o for o in report.key_odds if "烈焰风暴" in o.threat_name)
    assert 10.0 <= flamestrike_odd.probability_pct <= 30.0
    assert "雷达" in report.tactical_warning


def test_shaman_bloodlust_odds():
    report: DiscoveryProbabilityReport = DiscoveryPoolRadar.calculate_discover_odds(
        opponent_class="萨满祭司",
        discover_source_card="发现法术",
    )
    assert report.opponent_class == "SHAMAN"
    bloodlust_odd = next(o for o in report.key_odds if "嗜血" in o.threat_name)
    assert 5.0 <= bloodlust_odd.probability_pct <= 20.0
