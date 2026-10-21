"""
Core modules for Hearthstone Arena AI Assistant.
"""

from .config_manager import ConfigManager
from .card_db import CardDatabase, CardInfo
from .window_finder import WindowFinder, WindowRect
from .log_listener import LogListener
from .ocr_engine import OcrWorker
from .ai_engine import AiEngine, AssistantMode, DraftRecommendation, PlayRecommendation
from .lethal_calculator import LethalCalculator, LethalResult
from .secret_tracker import SecretTracker, TriggerType
from .deck_tracker import DeckTracker, DeckStats
from .mulligan_advisor import MulliganAdvisor, MulliganAdvice, MulliganChoice
from .hand_tracker import HandTracker, OpponentHandCard
from .synergy_engine import SynergyEngine, SynergyEvaluation
from .coin_optimizer import CoinOptimizer, CoinStrategy
from .topdeck_math import TopdeckMath, TopdeckAdvice
from .matchup_blueprint import MatchupBlueprintEngine, MatchupStrategy
from .ping_protector import PingProtector, PingProtectionAdvice
from .mana_efficiency import ManaEfficiencyOptimizer, ManaEfficiencyPlan
from .archetype_specializer import ArchetypeSpecializer, ArchetypeProfile, ArchetypeType
from .punish_simulator import PunishSimulator, PunishAssessment
from .card_advantage_engine import CardAdvantageEngine, ResourceAdvantagePlan, ResourceState
from .blunder_shield import BlunderShield, BlunderAlert
from .two_turn_lethal import TwoTurnLethalEngine, TwoTurnLethalPlan
from .positioning_geometry import PositioningGeometry, PositioningAdvice
from .mulligan_hand_reader import MulliganHandReader, MulliganHandAnalysis, SlotDeduction, CardOrigin
from .draft_cap_enforcer import DraftCapEnforcer, DraftCapModifier
from .hero_draft_advisor import HeroDraftAdvisor, HeroTierInfo
from .action_tree_search import ActionTreeSearch, ActionTreeResult, ActionBranch
from .match_history_learner import MatchHistoryLearner, MatchRecord
from .discovery_pool_radar import DiscoveryPoolRadar, DiscoveryProbabilityReport, ThreatOdd
from .sound_engine import SoundEngine
from .token_inspector import TokenInspector, TokenInfo
from .synergy_radar import SynergyRadar, SynergyRadarReport
from .hsreplay_sync import HsreplaySync
from .blunder_detector import BlunderDetector, TurnSnapshot, BlunderItem, MatchReviewReport
from .updater import UpdateChecker, UpdateInfo, CURRENT_VERSION
from .hypergeometric_odds import HypergeometricOddsEngine, HypergeometricOddsReport
from .tilt_guard import TiltGuard, TiltReport
from .highlight_recorder import HighlightClipRecorder
from .tactical_tree_visualizer import TacticalDecisionTree, DecisionNode
from .monte_carlo_var import MonteCarloVarEngine, MonteCarloVarReport
from .match_review_dashboard import MatchReviewDashboardGenerator
from .archetype_classifier import OpponentArchetypeClassifier, ArchetypeMatchReport
from .web_companion import WebCompanionServer
from .topdeck_matrix import TopdeckMatrix, TopdeckMatrixReport, CardTopdeckProfile
from .multi_turn_lookahead import MultiTurnLookahead, LookaheadForecastReport, CandidatePlayOutcome
from .game_phase_machine import GamePhaseMachine, GamePhase, GamePhaseState
from .leak_buster import LeakBuster, LeakItem, LeakType, LeakAuditSummary
from .capsule_hud import CapsuleHUD, CapsuleDisplayData
from .global_hotkeys import GlobalHotkeyManager, HotkeyID
from .i18n_engine import I18nEngine, t
from .secret_deathrattle_simulator import SecretDeathrattleSimulator, SecretCascadeReport, DeathrattleCascadeResult
from .hand_age_intel import HandAgeIntel, HandAgeIntelReport, TrackedHandCard, CardOriginType
from .mobile_remote_controller import MobileRemoteController, RemoteCommandType, RemoteCommandResult
from .esports_caster import EsportsCaster, VoiceAnswer, CasterCommentary, CasterEventType
from .deck_matchup_sandbox import DeckMatchupSandbox, DeckMatchupReport, ClassMatchupStats
from .arena_career_vault import ArenaCareerVault, ArenaRunRecord, CareerSummary
from .master_copilot import MasterCoPilotEngine, CoPilotTurnPlan, CoPilotStep, CoPilotStepType
from .pre_cast_blunder_interceptor import PreCastBlunderInterceptor, BlunderInterceptAlert, InterceptType
from .conversational_tts_streamer import ConversationalTtsStreamer
from .mid_turn_pivot_engine import MidTurnPivotEngine
from .neural_hand_silhouette import NeuralHandSilhouette, GhostCardSilhouette, HandSilhouetteReport
from .future_pick_forecaster import FuturePickForecaster, DraftArchetype, FutureForecastReport
from .what_if_sandbox import WhatIfSandbox, WhatIfSimulationReport
from .instant_card_lens import InstantCardLens, CardLensBreakdown
from .zero_cloud_engine import ZeroCloudEngine, ZeroCloudDecision
from .post_match_talkshow import PostMatchTalkshow, TalkshowScriptReport
from .mental_bluff_engine import MentalBluffEngine, OpponentMentalProfile, OpponentStyle, BluffOpportunity
from .tactical_setup_planner import TacticalSetupPlanner, TacticalSetupPlan, SetupCategory, SetupStep
from .miracle_inversion_engine import MiracleInversionEngine, MiracleGamblePath, RiskAttitude
from .self_evolving_reinforcement import SelfEvolvingReinforcement, CardEvolvingWeight, PersonalBlindspot
from .fatigue_endgame_horizon import FatigueEndgameHorizon, FatigueEndgameReport, EndgameVerdict, ResourcePool
from .interactive_voice_brain import InteractiveVoiceBrain, VoiceBrainResponse, VoiceIntent

__all__ = [
    "ConfigManager",
    "CardDatabase",
    "CardInfo",
    "WindowFinder",
    "WindowRect",
    "LogListener",
    "OcrWorker",
    "AiEngine",
    "AssistantMode",
    "DraftRecommendation",
    "PlayRecommendation",
    "LethalCalculator",
    "LethalResult",
    "SecretTracker",
    "TriggerType",
    "DeckTracker",
    "DeckStats",
    "MulliganAdvisor",
    "MulliganAdvice",
    "MulliganChoice",
    "HandTracker",
    "OpponentHandCard",
    "SynergyEngine",
    "SynergyEvaluation",
    "CoinOptimizer",
    "CoinStrategy",
    "TopdeckMath",
    "TopdeckAdvice",
    "MatchupBlueprintEngine",
    "MatchupStrategy",
    "PingProtector",
    "PingProtectionAdvice",
    "ManaEfficiencyOptimizer",
    "ManaEfficiencyPlan",
    "ArchetypeSpecializer",
    "ArchetypeProfile",
    "ArchetypeType",
    "PunishSimulator",
    "PunishAssessment",
    "CardAdvantageEngine",
    "ResourceAdvantagePlan",
    "ResourceState",
    "BlunderShield",
    "BlunderAlert",
    "TwoTurnLethalEngine",
    "TwoTurnLethalPlan",
    "PositioningGeometry",
    "PositioningAdvice",
    "MulliganHandReader",
    "MulliganHandAnalysis",
    "SlotDeduction",
    "CardOrigin",
    "DraftCapEnforcer",
    "DraftCapModifier",
    "HeroDraftAdvisor",
    "HeroTierInfo",
    "ActionTreeSearch",
    "ActionTreeResult",
    "ActionBranch",
    "MatchHistoryLearner",
    "MatchRecord",
    "DiscoveryPoolRadar",
    "DiscoveryProbabilityReport",
    "ThreatOdd",
    "SoundEngine",
    "TokenInspector",
    "TokenInfo",
    "SynergyRadar",
    "SynergyRadarReport",
    "HsreplaySync",
    "BlunderDetector",
    "TurnSnapshot",
    "BlunderItem",
    "MatchReviewReport",
    "UpdateChecker",
    "UpdateInfo",
    "CURRENT_VERSION",
    "HypergeometricOddsEngine",
    "HypergeometricOddsReport",
    "TiltGuard",
    "TiltReport",
    "HighlightClipRecorder",
    "TacticalDecisionTree",
    "DecisionNode",
    "MonteCarloVarEngine",
    "MonteCarloVarReport",
    "MatchReviewDashboardGenerator",
    "OpponentArchetypeClassifier",
    "ArchetypeMatchReport",
    "WebCompanionServer",
    "TopdeckMatrix",
    "TopdeckMatrixReport",
    "CardTopdeckProfile",
    "MultiTurnLookahead",
    "LookaheadForecastReport",
    "CandidatePlayOutcome",
    "GamePhaseMachine",
    "GamePhase",
    "GamePhaseState",
    "LeakBuster",
    "LeakItem",
    "LeakType",
    "LeakAuditSummary",
    "CapsuleHUD",
    "CapsuleDisplayData",
    "GlobalHotkeyManager",
    "HotkeyID",
    "I18nEngine",
    "t",
    "SecretDeathrattleSimulator",
    "SecretCascadeReport",
    "DeathrattleCascadeResult",
    "HandAgeIntel",
    "HandAgeIntelReport",
    "TrackedHandCard",
    "CardOriginType",
    "MobileRemoteController",
    "RemoteCommandType",
    "RemoteCommandResult",
    "EsportsCaster",
    "VoiceAnswer",
    "CasterCommentary",
    "CasterEventType",
    "DeckMatchupSandbox",
    "DeckMatchupReport",
    "ClassMatchupStats",
    "ArenaCareerVault",
    "ArenaRunRecord",
    "CareerSummary",
    "MasterCoPilotEngine",
    "CoPilotTurnPlan",
    "CoPilotStep",
    "CoPilotStepType",
    "PreCastBlunderInterceptor",
    "BlunderInterceptAlert",
    "InterceptType",
    "ConversationalTtsStreamer",
    "MidTurnPivotEngine",
    "NeuralHandSilhouette",
    "GhostCardSilhouette",
    "HandSilhouetteReport",
    "FuturePickForecaster",
    "DraftArchetype",
    "FutureForecastReport",
    "WhatIfSandbox",
    "WhatIfSimulationReport",
    "InstantCardLens",
    "CardLensBreakdown",
    "ZeroCloudEngine",
    "ZeroCloudDecision",
    "PostMatchTalkshow",
    "TalkshowScriptReport",
    "MentalBluffEngine",
    "OpponentMentalProfile",
    "OpponentStyle",
    "BluffOpportunity",
    "TacticalSetupPlanner",
    "TacticalSetupPlan",
    "SetupCategory",
    "SetupStep",
    "MiracleInversionEngine",
    "MiracleGamblePath",
    "RiskAttitude",
    "SelfEvolvingReinforcement",
    "CardEvolvingWeight",
    "PersonalBlindspot",
    "FatigueEndgameHorizon",
    "FatigueEndgameReport",
    "EndgameVerdict",
    "ResourcePool",
    "InteractiveVoiceBrain",
    "VoiceBrainResponse",
    "VoiceIntent",
]
