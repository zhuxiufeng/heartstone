"""
Unit tests for v9 Master Edition optimizations:
1. PositioningGeometry (ASCII board map & Defile health ladder warning)
2. MonteCarloVarEngine (RNG missiles & variable damage simulation, VaR percentiles)
3. OpponentArchetypeClassifier (Bayesian posterior probability updating & threat weights)
4. WebCompanionServer (/obs, /review, /api/meta/sync endpoints)
5. HsreplaySync (Cloud Arena meta analytics & hot patching)
6. MatchReviewDashboardGenerator (Interactive SVG timeline & blunder heatmap HTML)
"""

import json
import unittest
from unittest.mock import MagicMock, patch

from core.positioning_geometry import PositioningGeometry, PositioningAdvice
from core.monte_carlo_var import MonteCarloVarEngine, MonteCarloVarReport
from core.archetype_classifier import OpponentArchetypeClassifier, ArchetypeMatchReport
from core.hsreplay_sync import HsreplaySync, CardMetaAnalytics
from core.match_review_dashboard import MatchReviewDashboardGenerator
from core.turn_replayer import MatchReplaySummary, TurnReviewNode


class TestPositioningGeometryV9(unittest.TestCase):
    def test_ascii_board_map_and_defile_ladder(self):
        board = [
            {"name": "小鬼", "atk": 1, "health": 1, "divine_shield": False, "deathrattle": False, "is_mech": False},
            {"name": "虚空行者", "atk": 1, "health": 3, "divine_shield": False, "deathrattle": False, "is_mech": False},
        ]
        # Incoming minion has 2 health -> against Warlock, this creates 1, 2, 3 ladder!
        new_minion = {"name": "恐狼先锋", "atk": 2, "health": 2, "divine_shield": False, "deathrattle": False}
        advice = PositioningGeometry.calculate_optimal_placement(board, new_minion, opponent_class="WARLOCK")

        self.assertIsNotNone(advice)
        self.assertIn("恐狼先锋", advice.ascii_board_map)
        self.assertIsNotNone(advice.defile_ladder_warning)
        self.assertIn("亵渎", advice.defile_ladder_warning)
        self.assertIn("1~3", advice.defile_ladder_warning)

    def test_magnetic_ascii_fusion(self):
        board = [
            {"name": "微型战斗机甲", "atk": 1, "health": 2, "is_mech": True, "divine_shield": False},
        ]
        new_minion = {"name": "奇利亚斯", "atk": 3, "health": 2, "is_magnetic": True, "divine_shield": True}
        advice = PositioningGeometry.calculate_optimal_placement(board, new_minion, opponent_class="MAGE")

        self.assertTrue(advice.is_magnetic_fuse)
        self.assertEqual(advice.recommended_slot, 0)
        self.assertIn("磁力合体", advice.ascii_board_map)


class TestMonteCarloVarEngineV9(unittest.TestCase):
    def test_simulate_random_missiles(self):
        # 3 missiles, 1 dmg each. Enemy has 1 minion with 1 HP. Hero has 10 HP.
        report = MonteCarloVarEngine.simulate_random_missiles(
            action_name="奥术飞弹",
            missile_count=3,
            damage_per_missile=1,
            enemy_minions=[{"name": "测试小怪", "hp": 1, "divine_shield": False}],
            enemy_hero_hp=10,
            iterations=1000,
        )
        self.assertEqual(report.action_name, "奥术飞弹")
        self.assertGreater(report.clear_probability_pct, 50.0)
        self.assertGreaterEqual(report.p90_kills, 1)
        self.assertIn("杀", report.ascii_histogram)
        self.assertIn(report.risk_profile, ["LOW_RISK_CERTAINTY", "CALCULATED_GAMBLE", "HIGH_RISK_DESPERATION"])

    def test_simulate_aoe_damage_roll(self):
        # Lightning Storm 2-3 damage vs 2 HP minion
        report = MonteCarloVarEngine.simulate_aoe_damage_roll(
            spell_name="闪电风暴",
            min_dmg=2,
            max_dmg=3,
            enemy_minions=[{"hp": 2, "divine_shield": False}],
            iterations=1000,
        )
        self.assertEqual(report.action_name, "闪电风暴")
        self.assertEqual(report.clear_probability_pct, 100.0)
        self.assertEqual(report.p50_kills, 1)


class TestOpponentArchetypeClassifierV9(unittest.TestCase):
    def test_bayesian_posterior_updating(self):
        classifier = OpponentArchetypeClassifier(opponent_class="MAGE")
        # Record spell burn cards
        classifier.record_card_played("火球术")
        classifier.record_card_played("制造余震")
        report = classifier.get_current_report()

        self.assertIn("法强直伤法", report.archetype_name)
        self.assertGreaterEqual(report.confidence_pct, 60)
        self.assertIn("法强直伤法 (Spell Burn)", report.posterior_probabilities)
        self.assertGreater(report.burn_threat_probability_pct, 50)
        self.assertIn("贝叶斯流派后验分布", report.bayesian_dossier_text)
        self.assertIn("AOE清场概率", report.bayesian_dossier_text)


class TestHsreplaySyncV9(unittest.TestCase):
    def test_meta_analytics_and_patch(self):
        sync = HsreplaySync.get_instance()
        meta = sync.get_card_meta_analytics("TTN_903")
        self.assertEqual(meta.card_name, "阿曼苏尔")
        self.assertEqual(meta.tier, "S+")
        self.assertGreater(meta.deck_winrate_pct, 60.0)

        # Hot-patching
        patched = sync.apply_meta_patch({
            "modifiers": {"MOCK_BOMB_999": 20.0},
            "analytics": {
                "MOCK_BOMB_999": {"name": "灭世巨龙", "tier": "S+", "deck_wr": 72.0, "played_wr": 75.0, "inclusion": 50.0}
            }
        })
        self.assertGreaterEqual(patched, 2)
        self.assertEqual(sync.get_card_winrate_delta("MOCK_BOMB_999"), 20.0)
        mock_meta = sync.get_card_meta_analytics("MOCK_BOMB_999")
        self.assertEqual(mock_meta.card_name, "灭世巨龙")
        self.assertEqual(mock_meta.tier, "S+")


class TestMatchReviewDashboardV9(unittest.TestCase):
    def test_generate_interactive_html(self):
        nodes = [
            TurnReviewNode(
                turn_number=1,
                mana=1,
                max_mana=1,
                friendly_hp=30,
                enemy_hp=30,
                ai_winrate=52.0,
                action_grade="✅ 最佳 (Best)",
                grade_color="#10b981",
                ai_best_plan=["打出: 齿轮大师 (1费 1/2)"],
                player_actual_plays=["打出: 齿轮大师"],
            ),
            TurnReviewNode(
                turn_number=2,
                mana=2,
                max_mana=2,
                friendly_hp=30,
                enemy_hp=28,
                ai_winrate=58.0,
                action_grade="★ 妙手 (Brilliant)",
                grade_color="#a855f7",
                ai_best_plan=["使用英雄技能"],
                player_actual_plays=["使用英雄技能"],
            ),
        ]
        summary = MatchReplaySummary(
            result="WIN",
            total_turns=2,
            overall_accuracy_pct=96.5,
            grade_tier="S (大师级)",
            brilliant_count=1,
            best_count=1,
            turn_nodes=nodes,
        )

        html_out = MatchReviewDashboardGenerator.generate_dashboard_html(
            summary=summary,
            friendly_class="PALADIN",
            opponent_class="MAGE",
        )

        self.assertIn("<!DOCTYPE html>", html_out)
        self.assertIn("胜率波动走势图", html_out)
        self.assertIn("回合失误热力带", html_out)
        self.assertIn("PALADIN vs MAGE", html_out)
        self.assertIn("96.5%", html_out)
        self.assertEqual(MatchReviewDashboardGenerator.get_latest_html(), html_out)


class TestWebCompanionEndpointsV9(unittest.TestCase):
    def test_obs_template_exists(self):
        from core.web_companion import OBS_HTML_TEMPLATE
        self.assertIn("ARENA PRO HUD", OBS_HTML_TEMPLATE)
        self.assertIn("obs-container", OBS_HTML_TEMPLATE)
        self.assertIn("lethal-banner", OBS_HTML_TEMPLATE)
        self.assertIn("coach-box", OBS_HTML_TEMPLATE)


if __name__ == "__main__":
    unittest.main()
