"""
Overlay: High-performance frameless transparent floating overlay for Hearthstone.
Integrates:
1. PyQt5 Frameless & Translucent window with draggable header
2. Click-through toggle (WS_EX_TRANSPARENT on Windows, Qt.WindowTransparentForInput)
3. Recommendation cards, tactical play panel, and dynamic mana curve
4. System Tray icon with context menu
5. Graceful shutdown dispatching stop signals to worker QThreads
"""

from __future__ import annotations

import logging
import platform
import re
import sys
import time
from pathlib import Path
from typing import List, Optional

from PyQt5.QtCore import QPoint, Qt, QTimer, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QColor, QFont, QIcon, QKeySequence, QPainter, QPixmap
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QShortcut,
    QSizeGrip,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

try:
    from core.ai_engine import (
        AiEngine,
        AssistantMode,
        DraftRecommendation,
        PlayRecommendation,
    )
    from core.action_tree_search import ActionTreeResult, ActionBranch
    from core.card_db import CardDatabase, CardInfo, get_class_cn
    from core.coin_optimizer import CoinOptimizer, CoinStrategy
    from core.config_manager import ConfigManager
    from core.deck_tracker import DeckTracker, DeckStats
    from core.hand_tracker import HandTracker
    from core.lethal_calculator import LethalCalculator, LethalResult
    from core.log_listener import LogListener
    from core.mulligan_advisor import MulliganAdvisor, MulliganAdvice
    from core.ocr_engine import OcrWorker
    from core.secret_tracker import SecretTracker, TriggerType
    from core.synergy_engine import SynergyEngine
    from core.topdeck_math import TopdeckMath, TopdeckAdvice
    from core.window_finder import WindowFinder
    from core.sound_engine import SoundEngine
    from core.synergy_radar import SynergyRadar, SynergyRadarReport
    from core.hsreplay_sync import HsreplaySync
    from core.blunder_detector import BlunderDetector, TurnSnapshot, MatchReviewReport
    from core.updater import UpdateChecker, UpdateInfo, CURRENT_VERSION
    from core.hero_draft_advisor import HeroDraftAdvisor, ARENA_HERO_TIERS
    from core.archetype_classifier import OpponentArchetypeClassifier
    from core.web_companion import WebCompanionServer
    from core.turn_replayer import TurnReplayerEngine, TurnReviewNode, MatchReplaySummary
    from core.draft_quota_tracker import DraftQuotaTracker, DraftQuotaReport
    from core.rng_probability_engine import RngProbabilityEngine, RngProbabilityReport
    from core.personal_weakness_profiler import PersonalWeaknessProfiler, BlunderEntry
    from core.matchup_micro_meta import MatchupMicroMetaEngine
    from core.board_resilience_evaluator import BoardResilienceEvaluator, BoardResilienceReport
    from core.voice_commander import VoiceCommander
    from core.championship_dna_exporter import ChampionshipDnaExporter
    from core.reboot_macro import RebootMacro
    from core.global_hotkeys import GlobalHotkeyManager, HotkeyID
    from core.capsule_hud import CapsuleHUD, CapsuleDisplayData
    from core.i18n_engine import I18nEngine, t
    from core.topdeck_matrix import TopdeckMatrix
    from core.multi_turn_lookahead import MultiTurnLookahead
    from core.game_phase_machine import GamePhaseMachine
    from core.leak_buster import LeakBuster
    from core.secret_deathrattle_simulator import SecretDeathrattleSimulator
    from core.hand_age_intel import HandAgeIntel
    from core.mobile_remote_controller import MobileRemoteController, RemoteCommandType
    from core.esports_caster import EsportsCaster, CasterEventType
    from core.deck_matchup_sandbox import DeckMatchupSandbox
    from core.arena_career_vault import ArenaCareerVault
    from core.master_copilot import MasterCoPilotEngine, CoPilotTurnPlan, CoPilotStep
    from core.pre_cast_blunder_interceptor import PreCastBlunderInterceptor, BlunderInterceptAlert
    from core.conversational_tts_streamer import ConversationalTtsStreamer
    from core.mid_turn_pivot_engine import MidTurnPivotEngine
    from core.neural_hand_silhouette import NeuralHandSilhouette, HandSilhouetteReport
    from core.future_pick_forecaster import FuturePickForecaster
    from core.instant_card_lens import InstantCardLens
    from core.zero_cloud_engine import ZeroCloudEngine
    from core.post_match_talkshow import PostMatchTalkshow
    from core.mental_bluff_engine import MentalBluffEngine, OpponentMentalProfile
    from core.tactical_setup_planner import TacticalSetupPlanner
    from core.miracle_inversion_engine import MiracleInversionEngine
    from core.self_evolving_reinforcement import SelfEvolvingReinforcement
    from core.fatigue_endgame_horizon import FatigueEndgameHorizon
    from core.interactive_voice_brain import InteractiveVoiceBrain
    from core.micro_meta_climate import MicroMetaClimateRadar
    from core.secret_causal_forest import SecretCausalForest
    from core.flow_tilt_guardian import FlowTiltGuardian
    from core.hover_intent_radar import HoverIntentRadar
    from core.auto_highlight_reel import AutoHighlightReel
    from core.battlegrounds_mode_reactor import BattlegroundsModeReactor
    from core.council_of_champions import CouncilOfChampions
    from core.gaze_attention_tracker import GazeAttentionTracker
    from core.persona_voice_matrix import PersonaVoiceMatrix, VoicePersona
    from core.acoustic_emotion_guard import AcousticEmotionGuard
    from core.genetic_deck_architect import GeneticDeckArchitect
    from core.universal_tcg_theory import UniversalTcgTheoryEngine
except (ImportError, ValueError):
    from ..core.ai_engine import (
        AiEngine,
        AssistantMode,
        DraftRecommendation,
        PlayRecommendation,
    )
    from ..core.action_tree_search import ActionTreeResult, ActionBranch
    from ..core.card_db import CardDatabase, CardInfo, get_class_cn
    from ..core.coin_optimizer import CoinOptimizer, CoinStrategy
    from ..core.config_manager import ConfigManager
    from ..core.deck_tracker import DeckTracker, DeckStats
    from ..core.hand_tracker import HandTracker
    from ..core.lethal_calculator import LethalCalculator, LethalResult
    from ..core.log_listener import LogListener
    from ..core.mulligan_advisor import MulliganAdvisor, MulliganAdvice
    from ..core.ocr_engine import OcrWorker
    from ..core.secret_tracker import SecretTracker, TriggerType
    from ..core.synergy_engine import SynergyEngine
    from ..core.topdeck_math import TopdeckMath, TopdeckAdvice
    from ..core.window_finder import WindowFinder
    from ..core.sound_engine import SoundEngine
    from ..core.synergy_radar import SynergyRadar, SynergyRadarReport
    from ..core.hsreplay_sync import HsreplaySync
    from ..core.blunder_detector import BlunderDetector, TurnSnapshot, MatchReviewReport
    from ..core.hero_draft_advisor import HeroDraftAdvisor, ARENA_HERO_TIERS
    from ..core.updater import UpdateChecker, UpdateInfo, CURRENT_VERSION
    from ..core.archetype_classifier import OpponentArchetypeClassifier
    from ..core.web_companion import WebCompanionServer
    from ..core.turn_replayer import TurnReplayerEngine, TurnReviewNode, MatchReplaySummary
    from ..core.draft_quota_tracker import DraftQuotaTracker, DraftQuotaReport
    from ..core.rng_probability_engine import RngProbabilityEngine, RngProbabilityReport
    from ..core.personal_weakness_profiler import PersonalWeaknessProfiler, BlunderEntry
    from ..core.matchup_micro_meta import MatchupMicroMetaEngine
    from ..core.board_resilience_evaluator import BoardResilienceEvaluator, BoardResilienceReport
    from ..core.voice_commander import VoiceCommander
    from ..core.championship_dna_exporter import ChampionshipDnaExporter
    from ..core.reboot_macro import RebootMacro
    from ..core.global_hotkeys import GlobalHotkeyManager, HotkeyID
    from ..core.capsule_hud import CapsuleHUD, CapsuleDisplayData
    from ..core.i18n_engine import I18nEngine, t
    from ..core.topdeck_matrix import TopdeckMatrix
    from ..core.multi_turn_lookahead import MultiTurnLookahead
    from ..core.game_phase_machine import GamePhaseMachine
    from ..core.leak_buster import LeakBuster
    from ..core.secret_deathrattle_simulator import SecretDeathrattleSimulator
    from ..core.hand_age_intel import HandAgeIntel
    from ..core.mobile_remote_controller import MobileRemoteController, RemoteCommandType
    from ..core.esports_caster import EsportsCaster, CasterEventType
    from ..core.deck_matchup_sandbox import DeckMatchupSandbox
    from ..core.arena_career_vault import ArenaCareerVault
    from ..core.master_copilot import MasterCoPilotEngine, CoPilotTurnPlan, CoPilotStep
    from ..core.pre_cast_blunder_interceptor import PreCastBlunderInterceptor, BlunderInterceptAlert
    from ..core.conversational_tts_streamer import ConversationalTtsStreamer
    from ..core.mid_turn_pivot_engine import MidTurnPivotEngine
    from ..core.neural_hand_silhouette import NeuralHandSilhouette, HandSilhouetteReport
    from ..core.future_pick_forecaster import FuturePickForecaster
    from ..core.instant_card_lens import InstantCardLens
    from ..core.zero_cloud_engine import ZeroCloudEngine
    from ..core.post_match_talkshow import PostMatchTalkshow
    from ..core.mental_bluff_engine import MentalBluffEngine, OpponentMentalProfile
    from ..core.tactical_setup_planner import TacticalSetupPlanner
    from ..core.miracle_inversion_engine import MiracleInversionEngine
    from ..core.self_evolving_reinforcement import SelfEvolvingReinforcement
    from ..core.fatigue_endgame_horizon import FatigueEndgameHorizon
    from ..core.interactive_voice_brain import InteractiveVoiceBrain
    from ..core.micro_meta_climate import MicroMetaClimateRadar
    from ..core.secret_causal_forest import SecretCausalForest
    from ..core.flow_tilt_guardian import FlowTiltGuardian
    from ..core.hover_intent_radar import HoverIntentRadar
    from ..core.auto_highlight_reel import AutoHighlightReel
    from ..core.battlegrounds_mode_reactor import BattlegroundsModeReactor
    from ..core.council_of_champions import CouncilOfChampions
    from ..core.gaze_attention_tracker import GazeAttentionTracker
    from ..core.persona_voice_matrix import PersonaVoiceMatrix, VoicePersona
    from ..core.acoustic_emotion_guard import AcousticEmotionGuard
    from ..core.genetic_deck_architect import GeneticDeckArchitect
    from ..core.universal_tcg_theory import UniversalTcgTheoryEngine
from .card_tooltip import CardTooltip
from .inplace_hud import InPlaceHudManager
from .board_overlay import BoardTacticalOverlay
from .mana_curve import ManaCurveWidget
from .recommendation_card import RecommendationCard
from .settings_dialog import SettingsDialog
from .acrylic_effects import AcrylicGlassHelper, BreathingAuraController, AuraState
from .dynamic_island_capsule import DynamicIslandCapsule
from .winrate_sparkline import WinrateSparklineWidget
from .magnetic_docking import MagneticDockingManager, DockingAnchor
from .animated_voice_orb import AnimatedVoiceOrb, OrbVisualState
from .parallax_card_widget import ParallaxCardWidget
from .ar_board_overlay import ARBoardProjectionWidget, VectorAttackArrow, GhostPlacementSlot, MinionStatusAura
from .radial_probability_compass import RadialProbabilityCompassWidget
from .hologram_card_inspector import HologramCardInspectorWidget, HologramCardData
from .prismatic_theme_engine import PrismaticThemeEngine, ThemePreset
from .streamer_hud import StreamerHUDController, StreamerTickerWidget

logger = logging.getLogger("Overlay")


def get_app_icon_path() -> Optional[Path]:
    """Finds app.ico or app.png across frozen, bundle, and local paths."""
    candidates = []
    if hasattr(sys, "_MEIPASS"):
        candidates.append(Path(sys._MEIPASS) / "app.ico")
        candidates.append(Path(sys._MEIPASS) / "app.png")
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        candidates.append(exe_dir / "app.ico")
        candidates.append(exe_dir / "app.png")
        candidates.append(exe_dir / "_internal" / "app.ico")
        candidates.append(exe_dir / "_internal" / "app.png")
    root_dir = Path(__file__).resolve().parent.parent
    candidates.append(root_dir / "app.ico")
    candidates.append(root_dir / "app.png")
    candidates.append(Path("app.ico").resolve())
    candidates.append(Path("app.png").resolve())

    for c in candidates:
        if c.exists():
            return c
    return None


def create_app_icon() -> QIcon:
    """Returns high-res icon from asset file, or falls back to programmatic QIcon."""
    icon_path = get_app_icon_path()
    if icon_path and icon_path.exists():
        icon = QIcon(str(icon_path))
        if not icon.isNull():
            return icon

    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    painter.setBrush(QColor("#78350f"))
    painter.setPen(QColor("#d97706"))
    painter.drawRoundedRect(4, 4, 56, 56, 12, 12)

    painter.setBrush(Qt.NoBrush)
    painter.setPen(QColor("#fbbf24"))
    painter.drawRoundedRect(8, 8, 48, 48, 8, 8)

    painter.setPen(QColor("#ffffff"))
    font = QFont("Arial", 22, QFont.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignCenter, "HS")
    painter.end()

    return QIcon(pixmap)


def format_tactical_text(text: str) -> str:
    """Converts markdown formatting (**bold**, `chips`) into clean Qt rich-text HTML."""
    if not text:
        return ""
    # Convert **bold** to <b>bold</b>
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    # Convert `code` to stylish warm gold highlighted text
    s = re.sub(r"`(.+?)`", r"<span style='color: #fbbf24;'>【\1】</span>", s)
    # Replace newlines with <br/>
    s = s.replace("\n", "<br/>")
    return s


class OverlayWindow(QMainWindow):
    """Transparent always-on-top overlay."""

    sig_status_update = pyqtSignal(str)

    THEMES = {
        "WARM_OBSIDIAN_GOLD": {
            "name": "典雅黑金酒馆 (默认)",
            "frame": "background-color: rgba(11, 15, 25, 0.96); border: 1px solid rgba(245, 158, 11, 0.35); border-radius: 12px;",
        },
        "MINIMAL_GRAPHITE": {
            "name": "极简石墨暗灰",
            "frame": "background-color: rgba(15, 17, 24, 0.96); border: 1px solid rgba(148, 163, 184, 0.22); border-radius: 12px;",
        },
        "ROYAL_ARCANE": {
            "name": "达拉然奥术秘紫",
            "frame": "background-color: rgba(18, 14, 30, 0.96); border: 1px solid rgba(168, 85, 247, 0.35); border-radius: 12px;",
        },
        "NEON_EMERALD": {
            "name": "恶魔邪能翡翠",
            "frame": "background-color: rgba(9, 21, 17, 0.96); border: 1px solid rgba(16, 185, 129, 0.35); border-radius: 12px;",
        },
        "CYBER_NEON": {
            "name": "赛博霓虹",
            "frame": "background-color: rgba(11, 15, 25, 0.96); border: 1px solid rgba(56, 189, 248, 0.38); border-radius: 12px;",
        },
        "TAVERN_HEARTH": {
            "name": "酒馆暖木",
            "frame": "background-color: rgba(24, 18, 15, 0.96); border: 1px solid rgba(245, 158, 11, 0.35); border-radius: 12px;",
        },
        "FROZEN_THRONE": {
            "name": "冰封王座",
            "frame": "background-color: rgba(10, 20, 36, 0.96); border: 1px solid rgba(103, 232, 249, 0.35); border-radius: 12px;",
        },
        "VOID_SHADOW": {
            "name": "暗影虚空",
            "frame": "background-color: rgba(20, 13, 30, 0.96); border: 1px solid rgba(192, 132, 252, 0.35); border-radius: 12px;",
        },
        "MINIMAL_MONOCHROME": {
            "name": "极简黑白",
            "frame": "background-color: rgba(14, 15, 18, 0.97); border: 1px solid rgba(226, 232, 240, 0.25); border-radius: 12px;",
        },
    }

    def __init__(
        self,
        config_manager: ConfigManager,
        card_db: CardDatabase,
        ai_engine: AiEngine,
        log_listener: LogListener,
        ocr_worker: OcrWorker,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.config_manager = config_manager
        self.card_db = card_db
        self.ai_engine = ai_engine
        self.log_listener = log_listener
        self.ocr_worker = ocr_worker

        self.lethal_calculator = LethalCalculator(self.card_db)
        self.secret_tracker = SecretTracker(self.card_db)
        self.deck_tracker = DeckTracker(self.card_db)
        self.mulligan_advisor = MulliganAdvisor(self.card_db)
        self.hand_tracker = HandTracker(self.card_db)
        self.synergy_engine = SynergyEngine(self.card_db)
        self.window_finder = WindowFinder()
        self.inplace_hud = InPlaceHudManager(self.window_finder)

        self._current_theme = self.config_manager.get("theme", "WARM_OBSIDIAN_GOLD")
        if self._current_theme not in self.THEMES:
            self._current_theme = "WARM_OBSIDIAN_GOLD"
        self._drag_pos = QPoint()
        self._is_dragging = False
        self._resize_mode: Optional[str] = None
        self._resize_start_pos: Optional[QPoint] = None
        self._resize_start_geo = None
        self._click_through_enabled = False
        self.is_compact_mode = False
        self.is_rope_mode = False
        self._full_height = self.config_manager.get("overlay_height", 720)
        self.auto_dock_enabled = self.config_manager.get("auto_dock_enabled", False)
        self._dock_timer = QTimer(self)
        self._dock_timer.timeout.connect(self._auto_dock_tick)

        # In-game Board Tactical Projection & Archetype Classifier
        self.board_overlay = BoardTacticalOverlay()
        self.archetype_classifier = OpponentArchetypeClassifier()
        self._turn_start_time = 0.0
        self._is_player_turn = False
        self._auto_rope_active = False
        self._auto_rope_enabled = True
        self._rope_timer = QTimer(self)
        self._rope_timer.setInterval(1000)
        self._rope_timer.timeout.connect(self._check_auto_rope)

        # Mobile LAN Second-Screen Web Companion
        self.web_companion = WebCompanionServer(port=8899)
        self.web_companion.start()

        # Virtual Desktop & Cloak Guard (防多虚拟桌面穿透)
        self._hidden_by_desktop_guard = False
        self._desktop_guard_timer = QTimer(self)
        self._desktop_guard_timer.setInterval(300)
        self._desktop_guard_timer.timeout.connect(self._on_desktop_guard_tick)
        self._desktop_guard_timer.start()

        # Audio & TTS alerts
        self.sound_engine = SoundEngine.get_instance()
        self.sound_engine.update_settings(
            sound_enabled=self.config_manager.get("sound_enabled", True),
            tts_enabled=self.config_manager.get("tts_enabled", False),
            volume=self.config_manager.get("sound_volume", 80),
        )
        self._turn_history: List[TurnSnapshot] = []
        self._last_match_review: Optional[MatchReviewReport] = None
        self._replay_nodes: List[TurnReviewNode] = []
        self._current_replay_summary: Optional[MatchReplaySummary] = None
        self._current_replay_index: int = 0
        self._current_turn_plays: List[str] = []
        self._current_rec: Optional[PlayRecommendation] = None
        self._current_selected_plan: str = "A"
        self._announced_draw_directive: bool = False
        self._announced_face_pivot: bool = False

        # Hands-Free Voice Commander
        self.voice_commander = VoiceCommander.get_instance()
        self.voice_commander.register_callback(self._on_voice_command)
        self.voice_commander.start_listening()

        # v10 Apex: Initialize i18n & Global OS-Level Hotkeys
        initial_locale = self.config_manager.get("locale", "zh-CN")
        I18nEngine.get_instance().set_locale(initial_locale)

        self.global_hotkey_manager = GlobalHotkeyManager.get_instance()
        self.global_hotkey_manager.register_callback(HotkeyID.TOGGLE_OVERLAY, self._on_hotkey_toggle_overlay)
        self.global_hotkey_manager.register_callback(HotkeyID.TOGGLE_TREE, self._on_hotkey_toggle_tree)
        self.global_hotkey_manager.register_callback(HotkeyID.SNAPSHOT_ANALYSIS, self._on_hotkey_snapshot)
        if self.config_manager.get("global_hotkeys_enabled", True):
            self.global_hotkey_manager.start()

        # v11 Legendary: Hand Age Intel & Mobile Remote Controller
        self.hand_age_intel = HandAgeIntel()
        self.remote_controller = MobileRemoteController.get_instance()
        self.remote_controller.register_handler(RemoteCommandType.TOGGLE_OVERLAY, lambda p: {"visible": self._toggle_visibility_remote()})
        self.remote_controller.register_handler(RemoteCommandType.TOGGLE_CAPSULE, lambda p: {"capsule": self._toggle_capsule_remote()})
        self.remote_controller.register_handler(RemoteCommandType.REEVALUATE, lambda p: {"reevaluated": self._trigger_reevaluate_remote()})

        # Background update check
        UpdateChecker.check_for_updates(self._on_update_checked)

        self._init_window_flags()
        self._init_ui()
        self._init_tray()
        self._init_shortcuts()
        self._connect_signals()

        self.setMouseTracking(True)
        if hasattr(self, "central_card"):
            self.central_card.setMouseTracking(True)

        if self.auto_dock_enabled:
            self._dock_timer.start(2500)

        # Apply initial geometry & opacity
        self.setWindowOpacity(self.config_manager.get("overlay_opacity", 0.92))
        w = self.config_manager.get("overlay_width", 480)
        if w < 440:
            w = 480
        h = self.config_manager.get("overlay_height", 720)
        if h < 600:
            h = 720

        screen = QApplication.primaryScreen()
        screen_geo = screen.availableGeometry() if screen else None

        # Safe default coordinates on the right margin of the visible screen
        default_x = (screen_geo.right() - w - 16) if screen_geo else 1200
        default_y = (screen_geo.top() + 40) if screen_geo else 40

        x = self.config_manager.get("overlay_x", default_x)
        y = self.config_manager.get("overlay_y", default_y)

        # Smart placement & strict boundary clamping:
        if screen_geo:
            # 1. If x or y is off-screen (e.g. from DPI scaling, different monitor, or old config):
            if (x + w > screen_geo.right()) or (x < screen_geo.left()):
                x = max(screen_geo.left() + 10, screen_geo.right() - w - 16)
            if (y + 60 > screen_geo.bottom()) or (y < screen_geo.top()):
                y = screen_geo.top() + 40

            # 2. Avoid dead center where cards/heroes appear
            center_min_x = screen_geo.left() + int(screen_geo.width() * 0.22)
            center_max_x = screen_geo.left() + int(screen_geo.width() * 0.68)
            if center_min_x < x < center_max_x:
                x = max(screen_geo.left() + 10, screen_geo.right() - w - 16)
                y = screen_geo.top() + 40

        self.setGeometry(x, y, w, h)
        QTimer.singleShot(600, self._initial_dock_check)

    def _init_window_flags(self) -> None:
        """Sets frameless, translucent, and topmost flags."""
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.SubWindow
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)

    def _on_update_checked(self, info: UpdateInfo) -> None:
        if info.has_update:
            self.sig_status_update.emit(f"📢 发现新版本 {info.latest_version}！可在托盘菜单升级")

    def _init_ui(self) -> None:
        # Central container widget
        self.central_card = QFrame(self)
        self.central_card.setObjectName("mainFrame")
        self.central_card.setStyleSheet("""
            QFrame#mainFrame {
                background-color: rgba(11, 15, 25, 0.96);
                border: 1px solid rgba(255, 255, 255, 0.09);
                border-radius: 12px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Microsoft YaHei", sans-serif;
            }
            QLabel {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Microsoft YaHei", sans-serif;
            }
        """)
        self.setCentralWidget(self.central_card)

        # 3D Acrylic Breathing Aura Controller & Dynamic Island
        self.aura_controller = BreathingAuraController(self)
        self.aura_controller.sig_aura_updated.connect(self._on_aura_stylesheet_updated)
        self.dynamic_island = DynamicIslandCapsule(self)
        self.dynamic_island.setVisible(False)
        self.winrate_sparkline = WinrateSparklineWidget(self)
        self.winrate_sparkline.setVisible(False)

        # v18 Display & Interactive Hologram Engine
        self.theme_engine = PrismaticThemeEngine()
        self.streamer_controller = StreamerHUDController()
        self.streamer_ticker = StreamerTickerWidget(self.streamer_controller, self)
        self.streamer_ticker.setVisible(False)
        self.radial_compass = RadialProbabilityCompassWidget(self)
        self.radial_compass.setVisible(False)
        self.ar_projection = ARBoardProjectionWidget(self)
        self.ar_projection.setVisible(False)
        self.card_inspector = HologramCardInspectorWidget(self)
        self.card_inspector.setVisible(False)

        main_layout = QVBoxLayout(self.central_card)
        main_layout.setContentsMargins(10, 8, 10, 8)
        main_layout.setSpacing(8)

        # 1. Draggable Header Bar
        self.header_widget = QWidget(self)
        self.header_widget.setObjectName("headerWidget")
        self.header_widget.setStyleSheet("background: transparent;")
        header = QHBoxLayout(self.header_widget)
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(4)

        title_lbl = QLabel("HEARTHSTONE AI", self)
        title_lbl.setStyleSheet("color: #f8fafc; font-size: 11px; font-weight: 800; letter-spacing: 1.2px;")
        header.addWidget(title_lbl)

        self.mode_badge = QPushButton("选牌模式", self)
        self.mode_badge.setCursor(Qt.PointingHandCursor)
        self.mode_badge.setStyleSheet("""
            QPushButton {
                background: rgba(14, 165, 233, 0.12);
                color: #38bdf8;
                font-size: 10px;
                font-weight: 700;
                padding: 2px 8px;
                border-radius: 10px;
                border: 1px solid rgba(56, 189, 248, 0.3);
            }
            QPushButton:hover {
                background: rgba(14, 165, 233, 0.22);
                color: #ffffff;
                border-color: #38bdf8;
            }
        """)
        self.mode_badge.clicked.connect(self.toggle_mode)
        header.addWidget(self.mode_badge)

        self.hero_badge = QLabel("我方: 待选", self)
        self.hero_badge.setStyleSheet("color: #64748b; font-size: 10px; font-weight: 500;")
        header.addWidget(self.hero_badge)

        header.addStretch()

        def _style_hdr_btn(btn: QPushButton, hover_color: str = "#38bdf8", hover_bg: str = "rgba(56, 189, 248, 0.15)") -> None:
            btn.setFixedSize(22, 22)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: rgba(255, 255, 255, 0.05);
                    color: #94a3b8;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 4px;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Microsoft YaHei", sans-serif;
                    font-size: 11px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    color: {hover_color};
                    background: {hover_bg};
                    border-color: {hover_color};
                }}
            """)

        # Animated Interactive Voice Orb
        self.voice_orb = AnimatedVoiceOrb(self, size=22)
        self.voice_orb.setToolTip("AI 大师语音智脑光球 (点击切换声优人格)")
        header.addWidget(self.voice_orb)

        # Header action buttons: Dock, Hero Picker, Theme, Wide, Rope, Board HUD, Compact, Settings, Close
        self.dock_btn = QPushButton("⊕", self)
        self.dock_btn.setToolTip("吸附固定至炉石游戏窗口 (Ctrl+F5)")
        _style_hdr_btn(self.dock_btn, "#38bdf8")
        self.dock_btn.clicked.connect(self.dock_to_game_window)
        header.addWidget(self.dock_btn)

        self.hero_btn = QPushButton("★", self)
        self.hero_btn.setToolTip("开局英雄选择推荐 / 梯队胜率排行 (Ctrl+H)")
        _style_hdr_btn(self.hero_btn, "#facc15", "rgba(250, 204, 21, 0.15)")
        self.hero_btn.clicked.connect(self.show_hero_advisor_dialog)
        header.addWidget(self.hero_btn)

        self.theme_btn = QPushButton("✦", self)
        self.theme_btn.setToolTip("切换视觉主题 (Ctrl+F6)")
        _style_hdr_btn(self.theme_btn, "#a855f7", "rgba(168, 85, 247, 0.15)")
        self.theme_btn.clicked.connect(self.cycle_theme)
        header.addWidget(self.theme_btn)

        self.streamer_btn = QPushButton("◎", self)
        self.streamer_btn.setToolTip("切换主播极简隐私模式 / OBS 直播跑马灯 (Alt+S)")
        _style_hdr_btn(self.streamer_btn, "#38bdf8")
        self.streamer_btn.clicked.connect(self.toggle_streamer_mode)
        header.addWidget(self.streamer_btn)

        self.compass_btn = QPushButton("◈", self)
        self.compass_btn.setToolTip("切换 360° 极坐标概率罗盘与神抽斩杀刻度 (Alt+C)")
        _style_hdr_btn(self.compass_btn, "#10b981", "rgba(16, 185, 129, 0.15)")
        self.compass_btn.clicked.connect(self.toggle_radial_compass)
        header.addWidget(self.compass_btn)

        self.wide_btn = QPushButton("⊞", self)
        self.wide_btn.setToolTip("切换战术全景大屏 / 常规窗口 (Alt+W)")
        _style_hdr_btn(self.wide_btn, "#38bdf8")
        self.wide_btn.clicked.connect(self.toggle_wide_mode)
        header.addWidget(self.wide_btn)

        self.rope_btn = QPushButton("⚡", self)
        self.rope_btn.setToolTip("切换烧绳急救极速决策模式 (Alt+R)")
        _style_hdr_btn(self.rope_btn, "#f59e0b", "rgba(245, 158, 11, 0.15)")
        self.rope_btn.clicked.connect(self.toggle_rope_mode)
        header.addWidget(self.rope_btn)

        self.reboot_macro_btn = QPushButton("⟳", self)
        self.reboot_macro_btn.setToolTip("烧绳急救: 秒级极速重启炉石跳过超长动画 (Alt+F12)")
        _style_hdr_btn(self.reboot_macro_btn, "#ef4444", "rgba(239, 68, 68, 0.15)")
        self.reboot_macro_btn.clicked.connect(self.trigger_rope_emergency_reboot)
        header.addWidget(self.reboot_macro_btn)

        self.board_hud_btn = QPushButton("⊛", self)
        self.board_hud_btn.setToolTip("切换棋盘战术投影与动态箭头 (Alt+V)")
        _style_hdr_btn(self.board_hud_btn, "#38bdf8")
        self.board_hud_btn.clicked.connect(self.toggle_board_hud)
        header.addWidget(self.board_hud_btn)

        self.compact_btn = QPushButton("−", self)
        self.compact_btn.setToolTip("切换迷你极简胶囊模式 (Alt+M / F9)")
        _style_hdr_btn(self.compact_btn, "#94a3b8")
        self.compact_btn.clicked.connect(self.toggle_compact_mode)
        header.addWidget(self.compact_btn)

        self.settings_btn = QPushButton("⚙", self)
        self.settings_btn.setToolTip("系统参数设置")
        _style_hdr_btn(self.settings_btn, "#ffffff")
        self.settings_btn.clicked.connect(self.open_settings)
        header.addWidget(self.settings_btn)

        self.close_btn = QPushButton("✕", self)
        self.close_btn.setToolTip("退出助手")
        _style_hdr_btn(self.close_btn, "#ef4444", "rgba(239, 68, 68, 0.25)")
        self.close_btn.clicked.connect(self.close)
        header.addWidget(self.close_btn)

        main_layout.addWidget(self.header_widget)

        # 2. Draft Mode Container
        self.draft_container = QWidget(self)
        draft_layout = QVBoxLayout(self.draft_container)
        draft_layout.setContentsMargins(0, 0, 0, 0)
        draft_layout.setSpacing(6)

        # Quick-entry Hero Draft Advisor Button
        self.hero_picker_btn = QPushButton("★ 开局英雄三选一评级推荐 (Alt+H)", self)
        self.hero_picker_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(14, 165, 233, 0.18), stop:1 rgba(56, 189, 248, 0.08));
                color: #38bdf8;
                font-weight: 700;
                font-size: 11.5px;
                border: 1px solid rgba(56, 189, 248, 0.35);
                border-radius: 8px;
                padding: 6px 10px;
                min-height: 28px;
            }
            QPushButton:hover {
                background: rgba(14, 165, 233, 0.28);
                color: #ffffff;
                border-color: #38bdf8;
            }
        """)
        self.hero_picker_btn.clicked.connect(self.show_hero_advisor_dialog)
        draft_layout.addWidget(self.hero_picker_btn)

        self.manual_draft_btn = QPushButton("本轮卡牌三选一对比评估 (Alt+C)", self)
        self.manual_draft_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.03);
                color: #94a3b8;
                font-weight: 600;
                font-size: 11px;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                padding: 4px 8px;
                min-height: 24px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.07);
                color: #f8fafc;
                border-color: rgba(255, 255, 255, 0.18);
            }
        """)
        self.manual_draft_btn.clicked.connect(self.show_manual_draft_dialog)
        draft_layout.addWidget(self.manual_draft_btn)

        self.cards_layout = QVBoxLayout()
        self.cards_layout.setSpacing(6)
        self.rec_cards: List[RecommendationCard] = []
        for i in range(3):
            card_widget = RecommendationCard(index=i, parent=self)
            self.rec_cards.append(card_widget)
            self.cards_layout.addWidget(card_widget)
        draft_layout.addLayout(self.cards_layout)

        # Strategy / Advice Box for Draft
        self.advice_box = QFrame(self)
        self.advice_box.setObjectName("adviceBox")
        self.advice_box.setStyleSheet("""
            QFrame#adviceBox {
                background: rgba(255, 255, 255, 0.025);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
            }
            QLabel { background: transparent; border: none; padding: 0px; }
        """)
        adv_layout = QVBoxLayout(self.advice_box)
        adv_layout.setContentsMargins(8, 6, 8, 6)
        adv_layout.setSpacing(2)
        self.advice_lbl = QLabel("等待游戏或OCR检测候选卡牌...", self)
        self.advice_lbl.setWordWrap(True)
        self.advice_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        adv_layout.addWidget(self.advice_lbl)
        draft_layout.addWidget(self.advice_box)

        # 12-Win Deck Role Quota Radar Box
        self.quota_radar_box = QFrame(self)
        self.quota_radar_box.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
                padding: 2px;
            }
            QLabel { background: transparent; border: none; font-size: 11px; }
        """)
        qr_layout = QVBoxLayout(self.quota_radar_box)
        qr_layout.setContentsMargins(8, 5, 8, 5)
        qr_layout.setSpacing(2)
        self.quota_radar_lbl = QLabel("12胜套牌定额: 1-2费 0/8 | 3-4费 0/10 | 大解 0/3 | 突袭 0/5", self)
        self.quota_radar_lbl.setStyleSheet("color: #cbd5e1;")
        self.quota_radar_lbl.setWordWrap(True)
        qr_layout.addWidget(self.quota_radar_lbl)
        draft_layout.addWidget(self.quota_radar_box)

        # Export 12-Win Infographic Button
        self.export_dna_btn = QPushButton("⤓ 导出 12 胜战报海报 (Alt+P)", self)
        self.export_dna_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.04);
                color: #cbd5e1;
                font-size: 11px;
                font-weight: 600;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 5px;
                min-height: 28px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.08);
                color: #ffffff;
                border-color: rgba(255, 255, 255, 0.2);
            }
        """)
        self.export_dna_btn.clicked.connect(self.export_12_win_infographic)
        draft_layout.addWidget(self.export_dna_btn)

        # Mana Curve Widget
        self.mana_curve_widget = ManaCurveWidget(self)
        draft_layout.addWidget(self.mana_curve_widget)

        main_layout.addWidget(self.draft_container)

        # 3. Play Mode Container (Real-time Tactical Suggestions)
        self.play_container = QWidget(self)
        play_layout = QVBoxLayout(self.play_container)
        play_layout.setContentsMargins(0, 0, 0, 0)
        play_layout.setSpacing(6)

        # 3.1 Integrated Tactical Header Ribbon (Turn, Mana, Opponent, Posture, Clock) - Pinned at Top
        self.play_status_banner = QFrame(self)
        self.play_status_banner.setObjectName("playStatusBanner")
        self.play_status_banner.setStyleSheet("""
            QFrame#playStatusBanner {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
            }
            QLabel { background: transparent; border: none; padding: 0px; }
        """)
        ps_layout = QVBoxLayout(self.play_status_banner)
        ps_layout.setContentsMargins(10, 6, 10, 6)
        ps_layout.setSpacing(4)

        ps_top_row = QHBoxLayout()
        self.play_turn_lbl = QLabel("回合 1 · 法力水晶 1/1", self)
        self.play_turn_lbl.setStyleSheet("color: #38bdf8; font-size: 12.5px; font-weight: 800; letter-spacing: 0.5px;")
        self.play_opp_lbl = QLabel("对手: 等待检测", self)
        self.play_opp_lbl.setStyleSheet("""
            color: #cbd5e1;
            font-size: 10.5px;
            font-weight: 600;
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 6px;
            padding: 2px 8px;
        """)
        ps_top_row.addWidget(self.play_turn_lbl)
        ps_top_row.addStretch()
        ps_top_row.addWidget(self.play_opp_lbl)
        ps_layout.addLayout(ps_top_row)

        # Seamless Posture & Beatdown Clock Row inside status banner
        self.posture_frame = QFrame(self.play_status_banner)
        self.posture_frame.setObjectName("postureFrame")
        self.posture_frame.setStyleSheet("""
            QFrame#postureFrame {
                background: transparent;
                border: none;
                border-top: 1px solid rgba(255, 255, 255, 0.06);
                padding-top: 3px;
            }
            QLabel { background: transparent; border: none; padding: 0px; }
        """)
        pf_layout = QHBoxLayout(self.posture_frame)
        pf_layout.setContentsMargins(0, 3, 0, 0)
        self.posture_badge_lbl = QLabel("姿态: 均势博弈", self)
        self.posture_badge_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 600;")
        self.clock_lbl = QLabel("斩杀时钟: --", self)
        self.clock_lbl.setStyleSheet("color: #64748b; font-size: 10.5px;")
        pf_layout.addWidget(self.posture_badge_lbl)
        pf_layout.addStretch()
        pf_layout.addWidget(self.clock_lbl)
        ps_layout.addWidget(self.posture_frame)

        play_layout.addWidget(self.play_status_banner)

        # 3.2 Smooth Scroll Area for Tactical Content (Prevents awkward stretching and void gaps)
        self.play_scroll = QScrollArea(self.play_container)
        self.play_scroll.setWidgetResizable(True)
        self.play_scroll.setFrameShape(QFrame.NoFrame)
        self.play_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.play_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.play_scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: rgba(28, 25, 23, 0.4);
                width: 5px;
                border-radius: 2px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(245, 158, 11, 0.35);
                min-height: 20px;
                border-radius: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(245, 158, 11, 0.75);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

        self.play_scroll_widget = QWidget()
        self.play_scroll_widget.setStyleSheet("background: transparent;")
        play_content_layout = QVBoxLayout(self.play_scroll_widget)
        play_content_layout.setContentsMargins(0, 0, 4, 0)
        play_content_layout.setSpacing(6)

        # Dedicated Game Over / Match Settlement Frame (shown when game ends)
        self.game_over_frame = QFrame(self)
        self.game_over_frame.setObjectName("gameOverFrame")
        self.game_over_frame.setStyleSheet("""
            QFrame#gameOverFrame {
                background: rgba(24, 24, 27, 245);
                border: 2px solid #f59e0b;
                border-radius: 8px;
            }
            QLabel { background: transparent; border: none; padding: 0px; }
        """)
        gof_layout = QVBoxLayout(self.game_over_frame)
        gof_layout.setContentsMargins(10, 8, 10, 8)
        gof_layout.setSpacing(5)

        self.game_over_title = QLabel("🏁 对局结算完成", self)
        self.game_over_title.setStyleSheet("color: #fbbf24; font-size: 13px; font-weight: bold;")
        gof_layout.addWidget(self.game_over_title)

        self.game_over_grade_lbl = QLabel("⭐ 战局综合评级: 【S】", self)
        self.game_over_grade_lbl.setStyleSheet("color: #fbbf24; font-size: 12px; font-weight: bold;")
        gof_layout.addWidget(self.game_over_grade_lbl)

        self.game_over_turning_lbl = QLabel("🔄 关键转折点: --", self)
        self.game_over_turning_lbl.setWordWrap(True)
        self.game_over_turning_lbl.setStyleSheet("color: #e2e8f0; font-size: 11px;")
        gof_layout.addWidget(self.game_over_turning_lbl)

        self.game_over_blunder_lbl = QLabel("💡 伏笔与优化点: 全程无明显伏笔，决策极佳！", self)
        self.game_over_blunder_lbl.setWordWrap(True)
        self.game_over_blunder_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        gof_layout.addWidget(self.game_over_blunder_lbl)

        gof_btn_row = QHBoxLayout()
        self.return_draft_btn = QPushButton("🃏 返回选牌模式", self)
        self.return_draft_btn.setStyleSheet("""
            QPushButton {
                background: rgba(180, 83, 9, 0.35);
                color: #fde68a;
                font-size: 11px;
                font-weight: bold;
                padding: 4px 10px;
                border-radius: 4px;
                border: 1px solid rgba(245, 158, 11, 0.6);
            }
            QPushButton:hover {
                background: #92400e;
                color: #ffffff;
            }
        """)
        self.return_draft_btn.clicked.connect(self.toggle_mode)
        gof_btn_row.addWidget(self.return_draft_btn)

        self.new_game_btn = QPushButton("🔄 准备下局对战", self)
        self.new_game_btn.setStyleSheet("""
            QPushButton {
                background: #064e3b;
                color: #6ee7b7;
                font-size: 11px;
                font-weight: bold;
                padding: 4px 10px;
                border-radius: 4px;
                border: 1px solid #10b981;
            }
            QPushButton:hover {
                background: #047857;
                color: #ffffff;
            }
        """)
        self.new_game_btn.clicked.connect(self._reset_to_waiting_play_state)
        gof_btn_row.addWidget(self.new_game_btn)

        self.open_replayer_btn = QPushButton("🔍 步步复盘分析 (Ctrl+R)", self)
        self.open_replayer_btn.setStyleSheet("""
            QPushButton {
                background: #5b21b6;
                color: #ddd6fe;
                font-size: 11px;
                font-weight: bold;
                padding: 4px 10px;
                border-radius: 4px;
                border: 1px solid #7c3aed;
            }
            QPushButton:hover {
                background: #6d28d9;
                color: #ffffff;
            }
        """)
        self.open_replayer_btn.clicked.connect(self.show_turn_replayer)
        gof_btn_row.addWidget(self.open_replayer_btn)

        gof_layout.addLayout(gof_btn_row)
        play_content_layout.addWidget(self.game_over_frame)
        self.game_over_frame.hide()

        # =========================================================================
        # Turn-by-Turn Chess-Style Replayer Frame (Accuracy% Analyzer)
        # =========================================================================
        self.turn_replayer_frame = QFrame(self)
        self.turn_replayer_frame.setObjectName("turnReplayerFrame")
        self.turn_replayer_frame.setStyleSheet("""
            QFrame#turnReplayerFrame {
                background: rgba(15, 23, 42, 245);
                border: 2px solid #8b5cf6;
                border-radius: 8px;
            }
            QLabel { background: transparent; border: none; padding: 0px; }
        """)
        replayer_layout = QVBoxLayout(self.turn_replayer_frame)
        replayer_layout.setContentsMargins(10, 8, 10, 8)
        replayer_layout.setSpacing(5)

        replayer_hdr_layout = QHBoxLayout()
        self.replayer_title_lbl = QLabel("🔍 步步对局复盘 · 决策精度分析", self)
        self.replayer_title_lbl.setStyleSheet("color: #a78bfa; font-size: 13px; font-weight: bold;")
        replayer_hdr_layout.addWidget(self.replayer_title_lbl)

        self.replayer_accuracy_lbl = QLabel("精度: --%", self)
        self.replayer_accuracy_lbl.setStyleSheet("color: #34d399; font-size: 13px; font-weight: bold;")
        replayer_hdr_layout.addWidget(self.replayer_accuracy_lbl, alignment=Qt.AlignRight)
        replayer_layout.addLayout(replayer_hdr_layout)

        self.replayer_badges_lbl = QLabel("★ 妙手: 0 | ✅ 最佳: 0 | ⚖️ 良好: 0 | ⚠️ 疑问: 0 | ❌ 伏笔: 0", self)
        self.replayer_badges_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
        replayer_layout.addWidget(self.replayer_badges_lbl)

        # Quick Turn Jump Pills
        self.replayer_turns_widget = QWidget(self)
        self.replayer_turns_layout = QHBoxLayout(self.replayer_turns_widget)
        self.replayer_turns_layout.setContentsMargins(0, 2, 0, 2)
        self.replayer_turns_layout.setSpacing(4)
        replayer_layout.addWidget(self.replayer_turns_widget)

        # Turn Stepper Bar
        turn_nav_layout = QHBoxLayout()
        self.replayer_prev_btn = QPushButton("◀ 上一回合", self)
        self.replayer_prev_btn.setStyleSheet("""
            QPushButton {
                background: #334155;
                color: #f1f5f9;
                font-size: 11px;
                font-weight: bold;
                padding: 3px 8px;
                border-radius: 4px;
                border: 1px solid #475569;
            }
            QPushButton:hover { background: #475569; }
        """)
        self.replayer_prev_btn.clicked.connect(self._replayer_prev_turn)
        turn_nav_layout.addWidget(self.replayer_prev_btn)

        self.replayer_turn_lbl = QLabel("第 1 / 1 回合", self)
        self.replayer_turn_lbl.setAlignment(Qt.AlignCenter)
        self.replayer_turn_lbl.setStyleSheet("color: #fbbf24; font-size: 12px; font-weight: bold;")
        turn_nav_layout.addWidget(self.replayer_turn_lbl)

        self.replayer_next_btn = QPushButton("下一回合 ▶", self)
        self.replayer_next_btn.setStyleSheet("""
            QPushButton {
                background: rgba(41, 37, 36, 0.85);
                color: #f5f5f4;
                font-size: 11px;
                font-weight: bold;
                padding: 3px 8px;
                border-radius: 4px;
                border: 1px solid rgba(120, 113, 108, 0.5);
            }
            QPushButton:hover { background: rgba(68, 64, 60, 0.95); border-color: #fbbf24; }
        """)
        self.replayer_next_btn.clicked.connect(self._replayer_next_turn)
        turn_nav_layout.addWidget(self.replayer_next_btn)
        replayer_layout.addLayout(turn_nav_layout)

        # Granular Turn Review Card
        self.replayer_details_box = QFrame(self)
        self.replayer_details_box.setStyleSheet("""
            QFrame {
                background: rgba(28, 25, 23, 0.9);
                border: 1px solid rgba(245, 158, 11, 0.35);
                border-radius: 6px;
                padding: 6px;
            }
        """)
        det_box_layout = QVBoxLayout(self.replayer_details_box)
        det_box_layout.setContentsMargins(6, 6, 6, 6)
        det_box_layout.setSpacing(4)

        grade_row = QHBoxLayout()
        self.replayer_grade_badge = QLabel("✅ 最佳 (Best)", self)
        self.replayer_grade_badge.setStyleSheet("color: #10b981; font-size: 12px; font-weight: bold;")
        grade_row.addWidget(self.replayer_grade_badge)

        self.replayer_score_lbl = QLabel("得分: 100", self)
        self.replayer_score_lbl.setStyleSheet("color: #d6d3d1; font-size: 11px;")
        grade_row.addWidget(self.replayer_score_lbl, alignment=Qt.AlignRight)
        det_box_layout.addLayout(grade_row)

        self.replayer_state_lbl = QLabel("💎 水晶: 1/1 | ❤️ 己方: 30 vs 敌方: 30", self)
        self.replayer_state_lbl.setStyleSheet("color: #a8a29e; font-size: 11px;")
        det_box_layout.addWidget(self.replayer_state_lbl)

        self.replayer_diag_lbl = QLabel("出牌思路清晰，最大化法力水晶与场面收益。", self)
        self.replayer_diag_lbl.setWordWrap(True)
        self.replayer_diag_lbl.setStyleSheet("color: #fafaf9; font-size: 11px;")
        det_box_layout.addWidget(self.replayer_diag_lbl)

        self.replayer_ai_line_lbl = QLabel("🤖 AI最优线: --", self)
        self.replayer_ai_line_lbl.setWordWrap(True)
        self.replayer_ai_line_lbl.setStyleSheet("color: #fbbf24; font-size: 11px;")
        det_box_layout.addWidget(self.replayer_ai_line_lbl)

        self.replayer_player_line_lbl = QLabel("👤 玩家实战: --", self)
        self.replayer_player_line_lbl.setWordWrap(True)
        self.replayer_player_line_lbl.setStyleSheet("color: #a7f3d0; font-size: 11px;")
        det_box_layout.addWidget(self.replayer_player_line_lbl)

        replayer_layout.addWidget(self.replayer_details_box)

        replayer_ctrl_row = QHBoxLayout()
        self.replayer_back_btn = QPushButton("🏁 返回战果结算", self)
        self.replayer_back_btn.setStyleSheet("""
            QPushButton {
                background: rgba(41, 37, 36, 0.85);
                color: #d6d3d1;
                font-size: 11px;
                padding: 4px 8px;
                border-radius: 4px;
                border: 1px solid rgba(120, 113, 108, 0.45);
            }
            QPushButton:hover { background: rgba(68, 64, 60, 0.95); color: #fbbf24; border-color: #fbbf24; }
        """)
        self.replayer_back_btn.clicked.connect(self.hide_turn_replayer)
        replayer_ctrl_row.addWidget(self.replayer_back_btn)

        self.replayer_key_btn = QPushButton("🎯 跳转关键转折点", self)
        self.replayer_key_btn.setStyleSheet("""
            QPushButton {
                background: rgba(41, 37, 36, 0.85);
                color: #fbbf24;
                font-size: 11px;
                padding: 4px 8px;
                border-radius: 4px;
                border: 1px solid rgba(245, 158, 11, 0.4);
            }
            QPushButton:hover { background: rgba(68, 64, 60, 0.95); color: #fef08a; border-color: #fbbf24; }
        """)
        self.replayer_key_btn.clicked.connect(self._replayer_jump_key_turn)
        replayer_ctrl_row.addWidget(self.replayer_key_btn)
        replayer_layout.addLayout(replayer_ctrl_row)

        play_content_layout.addWidget(self.turn_replayer_frame)
        self.turn_replayer_frame.hide()

        # Dynamic Alert Layer: Lethal Warning Banner (Prominent banner shown only when lethal exists)
        self.lethal_frame = QFrame(self)
        self.lethal_frame.setObjectName("lethalFrame")
        self.lethal_frame.setStyleSheet("""
            QFrame#lethalFrame {
                background: rgba(14, 165, 233, 0.14);
                border: 1.5px solid #38bdf8;
                border-radius: 8px;
            }
            QLabel { background: transparent; border: none; padding: 0px; }
        """)
        lf_layout = QVBoxLayout(self.lethal_frame)
        lf_layout.setContentsMargins(10, 8, 10, 8)
        lf_layout.setSpacing(3)
        self.lethal_title_lbl = QLabel("⚡ 绝杀战机已现 (LETHAL DETECTED)!", self)
        self.lethal_title_lbl.setStyleSheet("color: #38bdf8; font-size: 13px; font-weight: 800; letter-spacing: 0.5px;")
        self.lethal_detail_lbl = QLabel("可造成 0 点伤害", self)
        self.lethal_detail_lbl.setStyleSheet("color: #ffffff; font-size: 11.5px; font-weight: bold;")
        self.lethal_steps_lbl = QLabel("", self)
        self.lethal_steps_lbl.setWordWrap(True)
        self.lethal_steps_lbl.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        lf_layout.addWidget(self.lethal_title_lbl)
        lf_layout.addWidget(self.lethal_detail_lbl)
        lf_layout.addWidget(self.lethal_steps_lbl)
        play_content_layout.addWidget(self.lethal_frame)
        self.lethal_frame.hide()

        # Mulligan Guidance Frame - Grandmaster Mulligan Cockpit
        self.mulligan_frame = QFrame(self)
        self.mulligan_frame.setObjectName("mulliganFrame")
        self.mulligan_frame.setStyleSheet("""
            QFrame#mulliganFrame {
                background: rgba(13, 148, 136, 0.14);
                border: 1px solid rgba(20, 184, 166, 0.45);
                border-radius: 8px;
            }
            QLabel { background: transparent; border: none; padding: 0px; }
        """)
        mf_layout = QVBoxLayout(self.mulligan_frame)
        mf_layout.setContentsMargins(10, 8, 10, 8)
        mf_layout.setSpacing(4)
        mf_head = QHBoxLayout()
        mf_title = QLabel("🃏 起手留牌决胜座舱 (Mulligan Guide)", self)
        mf_title.setStyleSheet("color: #2dd4bf; font-size: 11.5px; font-weight: 800; letter-spacing: 0.5px;")
        mf_head.addWidget(mf_title)
        mf_head.addStretch()
        self.mulligan_coin_badge = QLabel("先手", self)
        self.mulligan_coin_badge.setStyleSheet("color: #38bdf8; font-size: 10px; font-weight: 700; background: rgba(56, 189, 248, 0.15); border-radius: 4px; padding: 1px 6px;")
        mf_head.addWidget(self.mulligan_coin_badge)
        mf_layout.addLayout(mf_head)

        self.mulligan_lbl = QLabel("等待起手发牌...", self)
        self.mulligan_lbl.setWordWrap(True)
        self.mulligan_lbl.setStyleSheet("color: #f0fdfa; font-size: 11px;")
        mf_layout.addWidget(self.mulligan_lbl)

        # Quick enter match button
        self.mulligan_enter_btn = QPushButton("▶ 确认留牌 · 开启实战出牌", self)
        self.mulligan_enter_btn.setCursor(Qt.PointingHandCursor)
        self.mulligan_enter_btn.setStyleSheet("""
            QPushButton {
                background: rgba(20, 184, 166, 0.22);
                color: #2dd4bf;
                border: 1px solid #14b8a6;
                padding: 3px 8px;
                border-radius: 4px;
                font-size: 10.5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(20, 184, 166, 0.45);
                color: #ffffff;
            }
        """)
        self.mulligan_enter_btn.clicked.connect(lambda: self.mulligan_frame.hide())
        mf_layout.addWidget(self.mulligan_enter_btn)

        play_content_layout.addWidget(self.mulligan_frame)
        self.mulligan_frame.hide()

        # Coin Optimizer Frame
        self.coin_frame = QFrame(self)
        self.coin_frame.setObjectName("coinFrame")
        self.coin_frame.setStyleSheet("""
            QFrame#coinFrame {
                background: rgba(234, 179, 8, 0.10);
                border: 1px solid rgba(234, 179, 8, 0.35);
                border-radius: 6px;
            }
            QLabel { background: transparent; border: none; padding: 0px; }
        """)
        coin_layout = QVBoxLayout(self.coin_frame)
        coin_layout.setContentsMargins(10, 6, 10, 6)
        coin_layout.setSpacing(3)
        self.coin_title_lbl = QLabel("🪙 幸运币节奏曲线 (Coin Optimizer)", self)
        self.coin_title_lbl.setStyleSheet("color: #facc15; font-size: 11px; font-weight: bold;")
        self.coin_desc_lbl = QLabel("", self)
        self.coin_desc_lbl.setWordWrap(True)
        self.coin_desc_lbl.setStyleSheet("color: #fef08a; font-size: 11px;")
        coin_layout.addWidget(self.coin_title_lbl)
        coin_layout.addWidget(self.coin_desc_lbl)
        play_content_layout.addWidget(self.coin_frame)
        self.coin_frame.hide()

        # 3.15 Live Blunder Shield Alert Banner
        self.blunder_frame = QFrame(self)
        self.blunder_frame.setObjectName("blunderFrame")
        self.blunder_frame.setStyleSheet("""
            QFrame#blunderFrame {
                background: rgba(239, 68, 68, 0.12);
                border: 1px solid #ef4444;
                border-radius: 6px;
            }
            QLabel { background: transparent; border: none; padding: 0px; }
        """)
        blunder_layout = QVBoxLayout(self.blunder_frame)
        blunder_layout.setContentsMargins(10, 7, 10, 7)
        blunder_layout.setSpacing(3)
        self.blunder_title_lbl = QLabel("⚠️【伏笔拦截·操作次序警报】", self)
        self.blunder_title_lbl.setStyleSheet("color: #fee2e2; font-size: 12px; font-weight: bold;")
        self.blunder_desc_lbl = QLabel("", self)
        self.blunder_desc_lbl.setWordWrap(True)
        self.blunder_desc_lbl.setStyleSheet("color: #ffffff; font-size: 11px;")
        blunder_layout.addWidget(self.blunder_title_lbl)
        blunder_layout.addWidget(self.blunder_desc_lbl)
        play_content_layout.addWidget(self.blunder_frame)
        self.blunder_frame.hide()

        # 3.1b Draw & RNG First Directive Banner
        self.draw_directive_frame = QFrame(self)
        self.draw_directive_frame.setObjectName("drawDirectiveFrame")
        self.draw_directive_frame.setStyleSheet("""
            QFrame#drawDirectiveFrame {
                background: rgba(14, 165, 233, 0.12);
                border: 1px solid #0284c7;
                border-radius: 6px;
            }
            QLabel { background: transparent; border: none; padding: 0px; }
        """)
        dd_layout = QHBoxLayout(self.draw_directive_frame)
        dd_layout.setContentsMargins(8, 4, 8, 4)
        dd_layout.setSpacing(6)
        self.draw_directive_icon = QLabel("🎲", self)
        self.draw_directive_icon.setStyleSheet("font-size: 13px;")
        self.draw_directive_lbl = QLabel("【不确定性先行】优先打出抽牌/发现，获取信息后再行动！", self)
        self.draw_directive_lbl.setWordWrap(True)
        self.draw_directive_lbl.setStyleSheet("color: #38bdf8; font-size: 10.5px; font-weight: bold;")
        dd_layout.addWidget(self.draw_directive_icon)
        dd_layout.addWidget(self.draw_directive_lbl, 1)
        play_content_layout.addWidget(self.draw_directive_frame)
        self.draw_directive_frame.hide()

        # 3.2 Core Tactical Sequence - Interactive Action Checklist & Dual Plan Toggle
        self.play_actions_frame = QFrame(self)
        self.play_actions_frame.setObjectName("playActionsFrame")
        self.play_actions_frame.setStyleSheet("""
            QFrame#playActionsFrame {
                background: rgba(255, 255, 255, 0.025);
                border: 1px solid rgba(56, 189, 248, 0.22);
                border-radius: 8px;
            }
            QLabel { background: transparent; border: none; padding: 0px; }
        """)
        pa_layout = QVBoxLayout(self.play_actions_frame)
        pa_layout.setContentsMargins(10, 6, 10, 6)
        pa_layout.setSpacing(4)

        # Plan toggle header row
        plan_btn_row = QHBoxLayout()
        plan_btn_row.setSpacing(6)

        pa_title = QLabel("战术规划", self)
        pa_title.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 700;")
        plan_btn_row.addWidget(pa_title)

        self.plan_a_btn = QPushButton("方案A · 最优线", self)
        self.plan_a_btn.setCursor(Qt.PointingHandCursor)
        self.plan_a_btn.setStyleSheet("background: rgba(14, 165, 233, 0.22); color: #38bdf8; border: 1px solid #0284c7; padding: 2px 8px; border-radius: 9px; font-weight: bold; font-size: 10px;")
        self.plan_a_btn.clicked.connect(lambda: self._switch_plan_view("A"))
        plan_btn_row.addWidget(self.plan_a_btn)

        self.plan_b_btn = QPushButton("方案B · 备选线", self)
        self.plan_b_btn.setCursor(Qt.PointingHandCursor)
        self.plan_b_btn.setStyleSheet("background: rgba(255, 255, 255, 0.04); color: #64748b; border: 1px solid rgba(255, 255, 255, 0.08); padding: 2px 8px; border-radius: 9px; font-size: 10px;")
        self.plan_b_btn.clicked.connect(lambda: self._switch_plan_view("B"))
        plan_btn_row.addWidget(self.plan_b_btn)
        plan_btn_row.addStretch()

        self.lethal_cushion_tag = QLabel("", self)
        self.lethal_cushion_tag.setStyleSheet("color: #34d399; font-size: 10px; font-weight: bold;")
        plan_btn_row.addWidget(self.lethal_cushion_tag)
        pa_layout.addLayout(plan_btn_row)

        self.plan_outcome_lbl = QLabel("", self)
        self.plan_outcome_lbl.setWordWrap(True)
        self.plan_outcome_lbl.setStyleSheet("color: #cbd5e1; font-size: 10px;")
        pa_layout.addWidget(self.plan_outcome_lbl)

        self.play_actions_lbl = QLabel("等待当回合出牌规划...", self)
        self.play_actions_lbl.setWordWrap(True)
        self.play_actions_lbl.setStyleSheet("color: #f5f5f4; font-size: 11px;")
        pa_layout.addWidget(self.play_actions_lbl)
        play_content_layout.addWidget(self.play_actions_frame)

        # 3.2b Next-Turn Threat Radar Chips
        self.threat_radar_frame = QFrame(self)
        self.threat_radar_frame.setObjectName("threatRadarFrame")
        self.threat_radar_frame.setStyleSheet("""
            QFrame#threatRadarFrame {
                background: rgba(30, 27, 75, 0.45);
                border: 1px solid rgba(99, 102, 241, 0.35);
                border-radius: 6px;
            }
            QLabel { background: transparent; border: none; padding: 0px; }
        """)
        tr_layout = QVBoxLayout(self.threat_radar_frame)
        tr_layout.setContentsMargins(8, 4, 8, 4)
        tr_layout.setSpacing(2)

        self.threat_radar_title = QLabel("对手下回合高危单卡预警", self)
        self.threat_radar_title.setStyleSheet("color: #a5b4fc; font-size: 10px; font-weight: bold;")
        self.threat_radar_chips_lbl = QLabel("", self)
        self.threat_radar_chips_lbl.setWordWrap(True)
        self.threat_radar_chips_lbl.setStyleSheet("color: #e2e8f0; font-size: 10px;")
        tr_layout.addWidget(self.threat_radar_title)
        tr_layout.addWidget(self.threat_radar_chips_lbl)
        play_content_layout.addWidget(self.threat_radar_frame)
        self.threat_radar_frame.hide()

        # 3.3 Minion Trading & Mana Planning
        self.play_trade_frame = QFrame(self)
        self.play_trade_frame.setObjectName("playTradeFrame")
        self.play_trade_frame.setStyleSheet("""
            QFrame#playTradeFrame {
                background: rgba(255, 255, 255, 0.025);
                border: 1px solid rgba(255, 255, 255, 0.07);
                border-radius: 8px;
            }
            QLabel { background: transparent; border: none; padding: 0px; }
        """)
        pt_layout = QVBoxLayout(self.play_trade_frame)
        pt_layout.setContentsMargins(10, 6, 10, 6)
        pt_layout.setSpacing(3)

        pt_title = QLabel("随从交换与场面", self)
        pt_title.setStyleSheet("color: #fb923c; font-size: 11px; font-weight: 700;")
        self.play_trade_lbl = QLabel("优先以小换大，保全核心战力", self)
        self.play_trade_lbl.setWordWrap(True)
        self.play_trade_lbl.setStyleSheet("color: #e7e5e4; font-size: 11px;")
        pt_layout.addWidget(pt_title)
        pt_layout.addWidget(self.play_trade_lbl)
        play_content_layout.addWidget(self.play_trade_frame)

        # 3.4 Risk & AOE Warning
        self.play_risk_frame = QFrame(self)
        self.play_risk_frame.setObjectName("playRiskFrame")
        self.play_risk_frame.setStyleSheet("""
            QFrame#playRiskFrame {
                background: rgba(239, 68, 68, 0.08);
                border: 1px solid rgba(239, 68, 68, 0.22);
                border-radius: 8px;
            }
            QLabel { background: transparent; border: none; padding: 0px; }
        """)
        pr_layout = QVBoxLayout(self.play_risk_frame)
        pr_layout.setContentsMargins(10, 5, 10, 5)
        pr_layout.setSpacing(2)

        self.play_risk_lbl = QLabel("防范对手当回合关键解牌与AOE", self)
        self.play_risk_lbl.setWordWrap(True)
        self.play_risk_lbl.setStyleSheet("color: #fca5a5; font-size: 11px;")
        pr_layout.addWidget(self.play_risk_lbl)
        play_content_layout.addWidget(self.play_risk_frame)

        # 3.5 Secret Tracker Frame - Soft Purple Accent
        self.secret_frame = QFrame(self)
        self.secret_frame.setObjectName("secretFrame")
        self.secret_frame.setStyleSheet("""
            QFrame#secretFrame {
                background: rgba(88, 28, 135, 0.22);
                border: none;
                border-left: 3.5px solid #a855f7;
                border-radius: 6px;
            }
            QLabel { background: transparent; border: none; padding: 0px; }
        """)
        sf_layout = QVBoxLayout(self.secret_frame)
        sf_layout.setContentsMargins(10, 6, 10, 6)
        sf_layout.setSpacing(4)
        sf_head = QHBoxLayout()
        sf_title = QLabel("🔮 敌方奥秘推演 (Secret Tracker)", self)
        sf_title.setStyleSheet("color: #c084fc; font-size: 11px; font-weight: bold;")
        sf_head.addWidget(sf_title)
        sf_head.addStretch()
        self.secret_count_badge = QLabel("无奥秘", self)
        self.secret_count_badge.setStyleSheet("color: #94a3b8; font-size: 10px;")
        sf_head.addWidget(self.secret_count_badge)
        sf_layout.addLayout(sf_head)

        self.secret_desc_lbl = QLabel("当前无活跃奥秘", self)
        self.secret_desc_lbl.setWordWrap(True)
        self.secret_desc_lbl.setStyleSheet("color: #e2e8f0; font-size: 11px;")
        sf_layout.addWidget(self.secret_desc_lbl)

        sf_actions = QHBoxLayout()
        sf_actions.setSpacing(4)
        for label, trig in [("测随从", TriggerType.PLAY_MINION), ("测法术", TriggerType.CAST_SPELL), ("测打脸", TriggerType.ATTACK_HERO)]:
            btn = QPushButton(label, self)
            btn.setStyleSheet("""
                QPushButton {
                    background: #334155;
                    color: #cbd5e1;
                    font-size: 10px;
                    padding: 2px 6px;
                    border-radius: 3px;
                    border: none;
                }
                QPushButton:hover {
                    background: #475569;
                    color: #ffffff;
                }
            """)
            btn.clicked.connect(lambda checked, t=trig: self._on_secret_action_tested(t))
            sf_actions.addWidget(btn)
        sf_layout.addLayout(sf_actions)
        play_content_layout.addWidget(self.secret_frame)
        self.secret_frame.hide()

        # 3.6 Segmented Tactical Intel Drawer (First Principles: Progressive Disclosure)
        self.drawer_bar = QWidget(self)
        db_layout = QHBoxLayout(self.drawer_bar)
        db_layout.setContentsMargins(0, 2, 0, 2)
        db_layout.setSpacing(4)

        self.tab_deck_btn = QPushButton("🗃️ 剩余牌库", self)
        self.tab_hand_btn = QPushButton("👁️ 敌方手牌", self)
        self.tab_coin_btn = QPushButton("🪙 幸运币/罗盘", self)

        for btn in (self.tab_deck_btn, self.tab_hand_btn, self.tab_coin_btn):
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.04);
                    color: #94a3b8;
                    font-size: 10px;
                    font-weight: 600;
                    padding: 3px 8px;
                    border-radius: 4px;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                }
                QPushButton:hover {
                    background: rgba(255, 255, 255, 0.08);
                    color: #f8fafc;
                }
            """)
        db_layout.addWidget(self.tab_deck_btn)
        db_layout.addWidget(self.tab_hand_btn)
        db_layout.addWidget(self.tab_coin_btn)
        play_content_layout.addWidget(self.drawer_bar)

        self.tab_deck_btn.clicked.connect(lambda: self._switch_intel_tab("DECK"))
        self.tab_hand_btn.clicked.connect(lambda: self._switch_intel_tab("HAND"))
        self.tab_coin_btn.clicked.connect(lambda: self._switch_intel_tab("COIN"))

        self.intel_container = QWidget(self)
        intel_layout = QVBoxLayout(self.intel_container)
        intel_layout.setContentsMargins(0, 0, 0, 0)
        intel_layout.setSpacing(6)

        # Opponent Hand Tracker Frame
        self.hand_frame = QFrame(self.intel_container)
        self.hand_frame.setObjectName("handFrame")
        self.hand_frame.setStyleSheet("""
            QFrame#handFrame {
                background: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
            }
            QLabel { background: transparent; border: none; padding: 0px; }
        """)
        hf_layout = QVBoxLayout(self.hand_frame)
        hf_layout.setContentsMargins(8, 6, 8, 6)
        hf_layout.setSpacing(3)
        hf_head = QHBoxLayout()
        hf_title = QLabel("敌方手牌逆向推演", self)
        hf_title.setStyleSheet("color: #f59e0b; font-size: 11px; font-weight: 700;")
        hf_head.addWidget(hf_title)
        hf_head.addStretch()
        self.hand_count_badge = QLabel("对战中", self)
        self.hand_count_badge.setStyleSheet("color: #64748b; font-size: 10px;")
        hf_head.addWidget(self.hand_count_badge)
        hf_layout.addLayout(hf_head)

        self.hand_status_lbl = QLabel("实时手牌追踪中", self)
        self.hand_status_lbl.setWordWrap(True)
        self.hand_status_lbl.setStyleSheet("color: #94a3b8; font-size: 10px;")
        hf_layout.addWidget(self.hand_status_lbl)
        intel_layout.addWidget(self.hand_frame)
        self.hand_frame.hide()

        # Deck Tracker Frame
        self.deck_frame = QFrame(self.intel_container)
        self.deck_frame.setObjectName("deckFrame")
        self.deck_frame.setStyleSheet("""
            QFrame#deckFrame {
                background: rgba(255, 255, 255, 0.02);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
            }
            QLabel { background: transparent; border: none; padding: 0px; }
        """)
        df_layout = QVBoxLayout(self.deck_frame)
        df_layout.setContentsMargins(8, 6, 8, 6)
        df_layout.setSpacing(3)
        df_head = QHBoxLayout()
        df_title = QLabel("己方剩余牌库", self)
        df_title.setStyleSheet("color: #34d399; font-size: 11px; font-weight: 700;")
        df_head.addWidget(df_title)
        df_head.addStretch()
        self.deck_count_badge = QLabel("30/30", self)
        self.deck_count_badge.setStyleSheet("color: #64748b; font-size: 10px;")
        df_head.addWidget(self.deck_count_badge)
        df_layout.addLayout(df_head)

        self.deck_stats_lbl = QLabel("剩余 30 张 · 随从 --% · 法术 --%", self)
        self.deck_stats_lbl.setWordWrap(True)
        self.deck_stats_lbl.setStyleSheet("color: #d6d3d1; font-size: 10px;")
        df_layout.addWidget(self.deck_stats_lbl)

        self.topdeck_lbl = QLabel("", self)
        self.topdeck_lbl.setWordWrap(True)
        self.topdeck_lbl.setStyleSheet("color: #fbcfe8; font-size: 10px; margin-top: 2px;")
        df_layout.addWidget(self.topdeck_lbl)
        self.topdeck_lbl.hide()
        intel_layout.addWidget(self.deck_frame)

        play_content_layout.addWidget(self.intel_container)
        self._active_intel_tab = "DECK"
        self._intel_expanded = True
        self.tab_deck_btn.setStyleSheet("background: rgba(14, 165, 233, 0.18); color: #38bdf8; font-size: 10px; font-weight: bold; padding: 3px 8px; border-radius: 4px; border: 1px solid #0284c7;")

        # Absorb vertical space so cards stack naturally without stretching
        play_content_layout.addStretch(1)

        self.play_scroll.setWidget(self.play_scroll_widget)
        play_layout.addWidget(self.play_scroll, 1)

        main_layout.addWidget(self.play_container, 1)
        self.play_container.hide()  # Default in Draft mode

        # 4.5 Compact Capsule Container (Mini HUD Mode)
        self.compact_widget = QWidget(self)
        self.compact_widget.setObjectName("compactWidget")
        self.compact_widget.setStyleSheet("background: transparent;")
        compact_layout = QHBoxLayout(self.compact_widget)
        compact_layout.setContentsMargins(2, 0, 2, 0)
        compact_layout.setSpacing(6)

        self.compact_brand_lbl = QLabel("⚔️ 炉石AI", self)
        self.compact_brand_lbl.setStyleSheet("color: #fbbf24; font-size: 11px; font-weight: bold;")
        compact_layout.addWidget(self.compact_brand_lbl)

        self.compact_mode_pill = QPushButton("选牌", self)
        self.compact_mode_pill.setCursor(Qt.PointingHandCursor)
        self.compact_mode_pill.setToolTip("点击切换选牌/实战模式")
        self.compact_mode_pill.setStyleSheet("""
            QPushButton {
                background: rgba(180, 83, 9, 0.35);
                color: #fde68a;
                font-size: 10px;
                font-weight: bold;
                padding: 1px 6px;
                border-radius: 3px;
                border: 1px solid rgba(245, 158, 11, 0.55);
            }
            QPushButton:hover {
                background: rgba(217, 119, 6, 0.55);
                color: #ffffff;
                border-color: #fbbf24;
            }
        """)
        self.compact_mode_pill.clicked.connect(self.toggle_mode)
        compact_layout.addWidget(self.compact_mode_pill)

        self.compact_status_lbl = QLabel("⚔️ 胶囊模式 | 等待对局...", self)
        self.compact_status_lbl.setStyleSheet("color: #f5f5f4; font-size: 11px;")
        compact_layout.addWidget(self.compact_status_lbl, 1)

        # Right action buttons for compact capsule
        self.compact_expand_btn = QPushButton("🗖", self)
        self.compact_expand_btn.setToolTip("还原完整窗口模式 (Alt+M / F9)")
        self.compact_expand_btn.setCursor(Qt.PointingHandCursor)
        _style_hdr_btn(self.compact_expand_btn, "#fbbf24")
        self.compact_expand_btn.clicked.connect(self.toggle_compact_mode)
        compact_layout.addWidget(self.compact_expand_btn)

        self.compact_settings_btn = QPushButton("⚙️", self)
        self.compact_settings_btn.setToolTip("系统参数设置")
        _style_hdr_btn(self.compact_settings_btn, "#ffffff")
        self.compact_settings_btn.clicked.connect(self.open_settings)
        compact_layout.addWidget(self.compact_settings_btn)

        self.compact_close_btn = QPushButton("✕", self)
        self.compact_close_btn.setToolTip("退出助手")
        _style_hdr_btn(self.compact_close_btn, "#ef4444", "rgba(239, 68, 68, 0.25)")
        self.compact_close_btn.clicked.connect(self.close)
        compact_layout.addWidget(self.compact_close_btn)

        main_layout.addWidget(self.compact_widget)
        self.compact_widget.hide()

        # 5. Bottom Status Strip with Resizing QSizeGrip
        self.status_bar_widget = QWidget(self)
        status_bar = QHBoxLayout(self.status_bar_widget)
        status_bar.setContentsMargins(0, 0, 0, 0)
        self.status_lbl = QLabel("● 系统就绪", self)
        self.status_lbl.setStyleSheet("color: #10b981; font-size: 10.5px; font-weight: 600;")
        self.lock_lbl = QLabel("", self)
        self.lock_lbl.setStyleSheet("color: #f59e0b; font-size: 11px; font-weight: bold;")

        status_bar.addWidget(self.status_lbl)
        status_bar.addStretch()
        status_bar.addWidget(self.lock_lbl)

        self.size_grip = QSizeGrip(self)
        self.size_grip.setToolTip("拖拽调整窗口大小 (自由缩放)")
        self.size_grip.setStyleSheet("QSizeGrip { width: 14px; height: 14px; }")
        status_bar.addWidget(self.size_grip, 0, Qt.AlignBottom | Qt.AlignRight)

        main_layout.addWidget(self.status_bar_widget)

    def _init_tray(self) -> None:
        """Sets up system tray icon and menu."""
        self.tray_icon = QSystemTrayIcon(self)
        app_icon = create_app_icon()
        self.setWindowIcon(app_icon)
        self.tray_icon.setIcon(app_icon)

        tray_menu = QMenu()
        tray_menu.setStyleSheet("""
            QMenu {
                background-color: #1c1917;
                color: #f5f5f4;
                border: 1px solid rgba(245, 158, 11, 0.45);
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item:selected {
                background-color: #b45309;
                color: #fef3c7;
            }
        """)

        toggle_action = QAction("显示/隐藏 悬浮窗", self)
        toggle_action.triggered.connect(self._toggle_visibility)
        tray_menu.addAction(toggle_action)

        self.click_through_action = QAction("启用鼠标穿透 (Ctrl+F2)", self, checkable=True)
        self.click_through_action.triggered.connect(self.toggle_click_through)
        tray_menu.addAction(self.click_through_action)

        dock_action = QAction("🧲 吸附至游戏窗口 (Ctrl+F5)", self)
        dock_action.triggered.connect(self.dock_to_game_window)
        tray_menu.addAction(dock_action)

        compact_action = QAction("🗕 切换迷你极简胶囊模式 (Alt+M / F9)", self)
        compact_action.triggered.connect(self.toggle_compact_mode)
        tray_menu.addAction(compact_action)

        wide_action = QAction("🗖 切换战术全景大屏 (Alt+W)", self)
        wide_action.triggered.connect(self.toggle_wide_mode)
        tray_menu.addAction(wide_action)

        rope_action = QAction("⏱️ 切换烧绳急救极速模式 (Alt+R)", self)
        rope_action.triggered.connect(self.toggle_rope_mode)
        tray_menu.addAction(rope_action)

        board_action = QAction("🎯 切换棋盘动态战术投影 (Alt+V)", self)
        board_action.triggered.connect(self.toggle_board_hud)
        tray_menu.addAction(board_action)

        self.follow_desktop_action = QAction("🖥️ 仅在炉石所在桌面显示 (防多桌面穿透)", self, checkable=True)
        self.follow_desktop_action.setChecked(self.config_manager.get("follow_game_desktop", True))
        self.follow_desktop_action.triggered.connect(self._toggle_follow_desktop)
        tray_menu.addAction(self.follow_desktop_action)

        hero_action = QAction("👑 竞技场开局英雄三选一推荐 (Ctrl+H)", self)
        hero_action.triggered.connect(self.show_hero_advisor_dialog)
        tray_menu.addAction(hero_action)

        tray_menu.addSeparator()

        test_hero_action = QAction("🧪 模拟英雄三选一测试 (死骑/法师/战士)", self)
        test_hero_action.triggered.connect(lambda: self._on_heroes_detected(["死亡骑士", "法师", "战士"]))
        tray_menu.addAction(test_hero_action)

        test_draft_action = QAction("🧪 模拟三选一选牌测试", self)
        test_draft_action.triggered.connect(self.simulate_sample_draft)
        tray_menu.addAction(test_draft_action)

        test_play_action = QAction("🎮 模拟实战出牌建议测试 (Ctrl+F4)", self)
        test_play_action.triggered.connect(self.simulate_sample_play)
        tray_menu.addAction(test_play_action)

        test_mulligan_action = QAction("🃏 模拟起手留牌测试 (Ctrl+F7)", self)
        test_mulligan_action.triggered.connect(self.simulate_sample_mulligan)
        tray_menu.addAction(test_mulligan_action)

        theme_action = QAction("🎨 切换视觉主题 (Ctrl+F6)", self)
        theme_action.triggered.connect(self.cycle_theme)
        tray_menu.addAction(theme_action)

        reset_deck_action = QAction("🔄 重置当前套牌", self)
        reset_deck_action.triggered.connect(self.reset_current_deck)
        tray_menu.addAction(reset_deck_action)

        settings_action = QAction("⚙️ 参数设置...", self)
        settings_action.triggered.connect(self.open_settings)
        tray_menu.addAction(settings_action)

        review_action = QAction("📝 查看上局复盘战报与伏笔检测", self)
        review_action.triggered.connect(self.show_last_match_review)
        tray_menu.addAction(review_action)

        replayer_action = QAction("🔍 步步复盘分析器 (Ctrl+R)", self)
        replayer_action.triggered.connect(self.show_turn_replayer)
        tray_menu.addAction(replayer_action)

        test_replay_action = QAction("🧪 模拟步步复盘分析测试", self)
        test_replay_action.triggered.connect(self.simulate_sample_replay)
        tray_menu.addAction(test_replay_action)

        hsreplay_action = QAction("📊 同步 HSReplay 大数据竞技场胜率", self)
        hsreplay_action.triggered.connect(self.sync_hsreplay_data)
        tray_menu.addAction(hsreplay_action)

        update_cards_action = QAction("🌐 在线同步最新卡牌库 (HearthstoneJSON)", self)
        update_cards_action.triggered.connect(self.update_card_database)
        tray_menu.addAction(update_cards_action)

        updater_action = QAction("🔄 检查软件版本与卡牌补丁更新", self)
        updater_action.triggered.connect(self.check_app_updates)
        tray_menu.addAction(updater_action)

        tray_menu.addSeparator()

        exit_action = QAction("退出程序", self)
        exit_action.triggered.connect(self.shutdown)
        tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _connect_signals(self) -> None:
        """Binds signals across LogListener, OcrWorker, and AiEngine."""
        self.sig_status_update.connect(self._on_status_updated)

        # Log Listener bindings
        self.log_listener.draft_hero_selected.connect(self._on_hero_selected)
        self.log_listener.draft_choices_updated.connect(self._on_draft_candidates_received)
        self.log_listener.card_previewed.connect(self._on_card_previewed)
        self.log_listener.card_picked.connect(self._on_card_picked)
        self.log_listener.draft_finished.connect(self._on_draft_finished)
        self.log_listener.log_status.connect(self._on_status_updated)

        # Game Play bindings
        self.log_listener.game_started.connect(self._on_game_started)
        self.log_listener.turn_active.connect(self._on_turn_active)
        self.log_listener.play_state_updated.connect(self._on_play_state_updated)
        self.log_listener.card_played.connect(self._on_card_played_in_match)
        self.log_listener.game_over.connect(self._on_game_over)

        # OCR Worker bindings
        self.ocr_worker.cards_detected.connect(self._on_draft_candidates_received)
        self.ocr_worker.heroes_detected.connect(self._on_heroes_detected)
        self.ocr_worker.deck_detected.connect(self._on_ocr_deck_detected)
        self.ocr_worker.state_lock_changed.connect(self._on_state_lock_changed)
        self.ocr_worker.ocr_status.connect(self._on_status_updated)

    # ==========================
    # Mouse Dragging & Resizing Support
    # ==========================
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            pos = event.pos()
            rect = self.rect()
            dist_r = rect.width() - pos.x()
            dist_b = rect.height() - pos.y()
            dist_l = pos.x()

            if dist_r <= 10 and dist_b <= 10:
                self._resize_mode = "BR"
                self._resize_start_pos = event.globalPos()
                self._resize_start_geo = self.geometry()
                event.accept()
                return
            elif dist_r <= 10:
                self._resize_mode = "R"
                self._resize_start_pos = event.globalPos()
                self._resize_start_geo = self.geometry()
                event.accept()
                return
            elif dist_b <= 10:
                self._resize_mode = "B"
                self._resize_start_pos = event.globalPos()
                self._resize_start_geo = self.geometry()
                event.accept()
                return
            elif dist_l <= 10:
                self._resize_mode = "L"
                self._resize_start_pos = event.globalPos()
                self._resize_start_geo = self.geometry()
                event.accept()
                return

            self._resize_mode = None
            self._is_dragging = True
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._resize_mode and (event.buttons() & Qt.LeftButton) and self._resize_start_geo and self._resize_start_pos:
            diff = event.globalPos() - self._resize_start_pos
            geo = self._resize_start_geo
            new_x = geo.x()
            new_y = geo.y()
            new_w = geo.width()
            new_h = geo.height()

            if "R" in self._resize_mode:
                new_w = max(380, geo.width() + diff.x())
            if "B" in self._resize_mode:
                new_h = max(240, geo.height() + diff.y())
            if "L" in self._resize_mode:
                proposed_w = geo.width() - diff.x()
                if proposed_w >= 380:
                    new_w = proposed_w
                    new_x = geo.x() + diff.x()

            self.setGeometry(new_x, new_y, new_w, new_h)
            event.accept()
            return
        elif self._is_dragging and (event.buttons() & Qt.LeftButton):
            self.move(event.globalPos() - self._drag_pos)
            event.accept()
            return
        else:
            pos = event.pos()
            rect = self.rect()
            dist_r = rect.width() - pos.x()
            dist_b = rect.height() - pos.y()
            dist_l = pos.x()
            if dist_r <= 10 and dist_b <= 10:
                self.setCursor(Qt.SizeFDiagCursor)
            elif dist_r <= 10 or dist_l <= 10:
                self.setCursor(Qt.SizeHorCursor)
            elif dist_b <= 10:
                self.setCursor(Qt.SizeVerCursor)
            else:
                self.setCursor(Qt.ArrowCursor)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            if self._resize_mode:
                self._resize_mode = None
                self.setCursor(Qt.ArrowCursor)
                self.config_manager.set("overlay_width", self.width(), auto_save=False)
                self.config_manager.set("overlay_height", self.height(), auto_save=True)
                event.accept()
                return
            elif self._is_dragging:
                self._is_dragging = False
                self.config_manager.set("overlay_x", self.x(), auto_save=False)
                self.config_manager.set("overlay_y", self.y(), auto_save=True)
                event.accept()

    # ==========================
    # Click-Through Management
    # ==========================
    def toggle_click_through(self, enabled: bool) -> None:
        """Toggles click-through / transparent for input."""
        self._click_through_enabled = enabled
        self.setAttribute(Qt.WA_TransparentForMouseEvents, enabled)

        if platform.system() == "Windows":
            try:
                import win32con
                import win32gui
                hwnd = int(self.winId())
                ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                if enabled:
                    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style | win32con.WS_EX_TRANSPARENT | win32con.WS_EX_LAYERED)
                else:
                    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style & ~win32con.WS_EX_TRANSPARENT)
            except Exception as e:
                logger.warning(f"Windows click-through toggle failed: {e}")

        status_text = "已启用鼠标穿透 (可在托盘取消)" if enabled else "已关闭鼠标穿透"
        self._on_status_updated(status_text)

    # ==========================
    # Event Handlers & AI Link
    # ==========================
    @pyqtSlot(str)
    def _on_hero_selected(self, hero: str) -> None:
        hero_cn_map = {
            "DEATHKNIGHT": "死亡骑士", "DEMONHUNTER": "恶魔猎手", "DRUID": "德鲁伊",
            "HUNTER": "猎人", "MAGE": "法师", "PALADIN": "圣骑士",
            "PRIEST": "牧师", "ROGUE": "潜行者", "SHAMAN": "萨满祭司",
            "WARLOCK": "术士", "WARRIOR": "战士",
            "HERO_01": "战士", "HERO_02": "萨满祭司", "HERO_03": "潜行者",
            "HERO_04": "圣骑士", "HERO_05": "猎人", "HERO_06": "德鲁伊",
            "HERO_07": "术士", "HERO_08": "法师", "HERO_09": "牧师",
            "HERO_10": "恶魔猎手", "HERO_11": "死亡骑士"
        }
        hero_display = hero_cn_map.get(str(hero).upper(), str(hero))
        self._hero_has_been_selected = True
        if hasattr(self, "ocr_worker"):
            self.ocr_worker.set_hero_mode(False)
        self.hero_badge.setText(f"我方: {hero_display}")
        self.mode_badge.setText("选牌模式")
        self.hero_picker_btn.setText(f"👑 已选定: {hero_display} (点击可重选英雄评级)")
        self.hero_picker_btn.setStyleSheet("""
            QPushButton {
                background: #1e293b;
                color: #94a3b8;
                font-size: 11px;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 3px 6px;
                min-height: 24px;
            }
            QPushButton:hover {
                background: #334155;
                color: #f1f5f9;
            }
        """)
        self.draft_container.show()
        self.play_container.hide()
        # Reset cards from hero selection to card draft mode
        for idx in range(3):
            self.rec_cards[idx].name_lbl.setText("等待候选牌...")
            self.rec_cards[idx].score_pill.setText("0分")
            self.rec_cards[idx].cost_lbl.hide()
            self.rec_cards[idx].rank_badge.setText(f"#{idx+1}")
            self.rec_cards[idx].summary_lbl.setText("在游戏内悬停卡牌，AI 将实时给出打分与体系建议...")
            self.rec_cards[idx].set_unselected_style()
        self.advice_lbl.setText(f"⚔️ 已选定职业: 【{hero_display}】！进入 30 抓选牌阶段。\n可在游戏内悬停卡牌实时获取单卡评级，或点击下方【本轮卡牌三选一对比评估】。")
        self._on_status_updated(f"选牌模式: {hero_display}")

    @pyqtSlot(object)
    def _on_card_previewed(self, card_info: CardInfo) -> None:
        """Triggered when player hovers over a candidate card in draft."""
        if not card_info or not hasattr(card_info, "name"):
            return
        try:
            if not hasattr(self, "_current_round_candidates"):
                self._current_round_candidates = []

            # Check if card is already known in current round candidates
            found_idx = -1
            for i, c in enumerate(self._current_round_candidates):
                if c.id == card_info.id or c.name == card_info.name:
                    found_idx = i
                    break

            if found_idx == -1:
                if len(self._current_round_candidates) < 3:
                    found_idx = len(self._current_round_candidates)
                    self._current_round_candidates.append(card_info)
                else:
                    # New round detected! Reset candidate list with this new card
                    self._current_round_candidates = [card_info]
                    found_idx = 0

            hero = self.log_listener.current_hero or "DEATHKNIGHT"
            deck = self.log_listener.current_deck

            # If all 3 cards in the round have been hovered, trigger full comparison
            if len(self._current_round_candidates) == 3:
                self._on_draft_candidates_received(list(self._current_round_candidates))
                return

            # Otherwise, evaluate and display this single candidate in its slot
            eval_item = self.ai_engine.evaluate_single_card(hero, card_info, deck)
            target_idx = min(max(found_idx, 0), 2)
            self.rec_cards[target_idx].update_evaluation(eval_item, card_info)

            stats = f" ({card_info.attack}/{card_info.health})" if card_info.card_type == "MINION" and card_info.attack is not None else ""
            self.advice_lbl.setText(
                f"🔍 悬停识别卡牌: 【{card_info.name}】 ({card_info.cost}费{stats})\n"
                f"⭐ 竞技场单卡评分: {eval_item.score:.1f}分\n"
                f"💡 战术建议: {eval_item.summary}"
            )
            self._on_status_updated(f"已评估卡牌: {card_info.name} ({eval_item.score:.1f}分)")
        except Exception as e:
            logger.error(f"Error previewing card: {e}", exc_info=True)

    @pyqtSlot(list)
    def _on_heroes_detected(self, hero_names: List[str], force: bool = False) -> None:
        """Triggered when 3 candidate hero portraits are detected from screen OCR or user selection."""
        try:
            if getattr(self, "_hero_has_been_selected", False) and not force:
                return
            if not hero_names or len(hero_names) < 2:
                return

            self._last_detected_heroes = list(hero_names)
            self.draft_container.show()
            self.play_container.hide()
            self.mode_badge.setText("👑 英雄选择")
            self.hero_badge.setText("我方: 3选1")

            evals = HeroDraftAdvisor.evaluate_hero_choices(hero_names)
            if not evals:
                return

            # Display up to 3 hero candidate cards
            for idx in range(min(3, len(evals))):
                h_info = evals[idx]
                self.rec_cards[idx].update_hero_evaluation(h_info, is_best_pick=(idx == 0))
                self.rec_cards[idx].show()

            best = evals[0]
            strat_text = (
                f"👑 竞技场开局英雄首选推荐: 【{best.class_cn}】\n"
                f"📊 天梯评级: {best.tier} (平均胜率 {best.winrate:.1f}% / 战力 {best.power_rating}分)\n"
                f"🎯 推荐抓牌风格: {best.recommended_archetype}\n"
                f"⚔️ 抓牌指导: {best.draft_priority_advice}"
            )
            self.advice_lbl.setText(strat_text)
            try:
                self.sound_engine.play_chime()
            except Exception as se:
                logger.debug(f"Audio playback skipped: {se}")
            self._on_status_updated(f"已评估英雄: 首选 {best.class_cn} ({best.tier})")
        except Exception as e:
            logger.error(f"Error in _on_heroes_detected: {e}", exc_info=True)
            self._on_status_updated(f"英雄评估异常: {e}")

    @pyqtSlot(list)
    def _on_draft_candidates_received(self, candidates: List[CardInfo]) -> None:
        """Triggered when 3 candidate cards are detected from log or OCR."""
        if not candidates:
            if hasattr(self, "_current_round_candidates"):
                self._current_round_candidates.clear()
            for idx in range(3):
                self.rec_cards[idx].name_lbl.setText("等待候选牌...")
                self.rec_cards[idx].score_pill.setText("0分")
                self.rec_cards[idx].cost_lbl.hide()
                self.rec_cards[idx].rank_badge.setText(f"#{idx+1}")
                self.rec_cards[idx].summary_lbl.setText("视觉引擎自动识别中，或鼠标悬停任意候选牌...")
                self.rec_cards[idx].set_unselected_style()
            return

        if len(candidates) != 3:
            return

        hero = self.log_listener.current_hero or "NEUTRAL"
        deck = self.log_listener.current_deck

        # Handle partial detection (e.g. 2 cards visible while 1 is covered by a hover tooltip)
        if any(c is None for c in candidates):
            self._current_round_candidates = [c for c in candidates if c is not None]
            best_partial_name = ""
            best_partial_score = -1.0
            for idx in range(3):
                c_info = candidates[idx]
                if c_info is not None:
                    eval_item = self.ai_engine.evaluate_single_card(hero, c_info, deck)
                    self.rec_cards[idx].update_evaluation(eval_item, c_info)
                    if eval_item.score > best_partial_score:
                        best_partial_score = eval_item.score
                        best_partial_name = c_info.name
                else:
                    self.rec_cards[idx].name_lbl.setText("移开游戏内悬停提示以识别...")
                    self.rec_cards[idx].score_pill.setText("--")
                    self.rec_cards[idx].cost_lbl.hide()
                    self.rec_cards[idx].rank_badge.setText(f"#{idx+1}")
                    self.rec_cards[idx].summary_lbl.setText("当前位置被游戏内词条弹窗遮挡，移开鼠标即可自动补全三选一对比。")
                    self.rec_cards[idx].set_unselected_style()
            if best_partial_name:
                self.advice_lbl.setText(
                    f"⚡ 已识别可见候选牌，当前最高分: 【{best_partial_name}】 ({best_partial_score:.0f}分)\n"
                    f"💡 移开游戏内遮挡卡牌标题的鼠标悬停框，即可自动完成 3 张完整对比。"
                )
            return

        self._current_round_candidates = list(candidates)

        self.advice_lbl.setText("🧠 AI 正在极速评估候选卡牌...")

        try:
            # 1. Optimistic Fast-Path: instant heuristic evaluation (<3ms) without blocking UI thread
            rec: DraftRecommendation = self.ai_engine.evaluate_draft_pick(
                hero_class=hero,
                candidates=candidates,
                deck_so_far=deck,
                use_llm=False,
            )

            # Compute lead delta and best pick tag
            scores = [e.score for e in rec.cards_evaluations]
            sorted_scores = sorted(scores, reverse=True)
            lead_delta = sorted_scores[0] - sorted_scores[1] if len(sorted_scores) > 1 else 0.0

            # Update 3 UI cards with First-Principles advantage tags
            for idx in range(3):
                eval_item = rec.cards_evaluations[idx]
                c_info = candidates[idx]
                delta = lead_delta if eval_item.is_best_pick else 0.0
                tag = ""
                if eval_item.is_best_pick:
                    if eval_item.score >= 90:
                        tag = "S级核心"
                    elif "曲线" in eval_item.summary or (hasattr(rec, "curve_advice") and "曲线" in str(rec.curve_advice)):
                        tag = "曲线急缺"
                    else:
                        tag = "综合最优"
                self.rec_cards[idx].update_evaluation(eval_item, c_info, delta_lead=delta, verdict_tag=tag)

            # Update in-place screen HUD badges directly pinned on top of Hearthstone cards
            try:
                self.inplace_hud.update_recommendations(rec, candidates)
            except Exception as he:
                logger.warning(f"InPlaceHud update suppressed: {he}")

            # Strategy tip with SynergyRadar analysis
            radar_rep = SynergyRadar.analyze_deck(deck)
            cache_tag = " [⚡本地秒回]" if rec.is_cached else ""
            strat_text = f"{rec.overall_strategy}{cache_tag}\n💡 {rec.curve_advice}"
            if getattr(rec, "archetype_advice", ""):
                strat_text += f"\n🎯 风格特化: {rec.archetype_advice}"
            strat_text += f"\n📊 套牌雷达: 【{radar_rep.archetype_title}】 (平衡度: {radar_rep.overall_balance_score:.0f}分)"
            self.advice_lbl.setText(strat_text)

            # Update mana curve deck health panorama
            if hasattr(self, "mana_curve_widget") and hasattr(self.mana_curve_widget, "update_deck_health"):
                self.mana_curve_widget.update_deck_health(
                    archetype=radar_rep.archetype_title,
                    health_pct=int(radar_rep.overall_balance_score),
                    notice="核心战术成型" if len(deck) >= 15 else "早期框架搭建",
                )

            # 2. Asynchronous LLM Enhancement: if Gemini is configured, compute in background
            if self.ai_engine.has_llm_client():
                def _bg_draft_eval():
                    try:
                        llm_rec = self.ai_engine.evaluate_draft_pick(
                            hero_class=hero,
                            candidates=candidates,
                            deck_so_far=deck,
                            use_llm=True,
                        )
                        QTimer.singleShot(0, lambda: self._enhance_draft_with_llm(llm_rec, candidates))
                    except Exception as ex:
                        logger.debug(f"Background LLM draft eval skipped: {ex}")

                import threading
                threading.Thread(target=_bg_draft_eval, daemon=True).start()

            # Update 12-win quota radar display & Championship DNA
            dna_rep = ChampionshipDnaExporter.evaluate_deck_dna(deck, hero)
            if getattr(rec, "quota_report", None):
                q_rep = rec.quota_report
                self.quota_radar_lbl.setText(f"🎯 12胜套牌定额: {q_rep.short_status_strip} | {dna_rep.dna_title}\n{q_rep.most_urgent_need}")
                WebCompanionServer.update_state({
                    "mode": "DRAFT",
                    "quota_strip": q_rep.short_status_strip,
                    "championship_dna": f"<b>{dna_rep.dna_title}</b>: {dna_rep.tactical_verdict}"
                })

            # Update compact capsule mode display
            best_eval = max(rec.cards_evaluations, key=lambda e: e.score)
            self.compact_status_lbl.setText(f"🃏 推荐: 【{best_eval.card_name}】 ({best_eval.score:.1f}分)")

        except Exception as e:
            logger.error(f"Error evaluating draft pick: {e}", exc_info=True)
            self.advice_lbl.setText(f"评估异常: {e}")

    def _enhance_draft_with_llm(self, llm_rec: DraftRecommendation, candidates: List[CardInfo]) -> None:
        """Asynchronously enhances draft card evaluations and strategy with deep LLM insights."""
        if not llm_rec:
            return
        try:
            for idx in range(min(3, len(llm_rec.cards_evaluations))):
                eval_item = llm_rec.cards_evaluations[idx]
                c_info = candidates[idx]
                self.rec_cards[idx].update_evaluation(eval_item, c_info)
            if hasattr(self, "inplace_hud"):
                self.inplace_hud.update_recommendations(llm_rec, candidates)
            strat = f"{llm_rec.overall_strategy} [🧠 大模型深度推演]\n💡 {llm_rec.curve_advice}"
            self.advice_lbl.setText(strat)
        except Exception as e:
            logger.debug(f"Error applying LLM draft enhancement: {e}")

    def _enhance_play_with_llm(self, llm_rec: PlayRecommendation) -> None:
        """Asynchronously enhances live play recommendation with deep LLM tactical commentary."""
        if not llm_rec:
            return
        try:
            if hasattr(self, "compass_lbl") and getattr(llm_rec, "compass_directive", ""):
                self.compass_lbl.setText(f"{llm_rec.compass_directive} [🧠 LLM协同]")
        except Exception as e:
            logger.debug(f"Error applying LLM play enhancement: {e}")

    @pyqtSlot(dict)
    def _on_card_picked(self, pick_data: dict) -> None:
        """Triggered when card pick action completes."""
        # 0. Trigger audio chime
        c_name = ""
        if isinstance(pick_data, dict):
            c_name = pick_data.get("card_name", "")
            if not c_name and "card" in pick_data and hasattr(pick_data["card"], "name"):
                c_name = pick_data["card"].name
        self.sound_engine.notify_card_picked(c_name)

        # 1. Trigger OCR debouncing animation lock & clear round candidates
        if hasattr(self, "_current_round_candidates"):
            self._current_round_candidates.clear()
        if hasattr(self, "ocr_worker"):
            self.ocr_worker.trigger_animation_lock(self.config_manager.get("animation_lock_duration_sec", 2.0))
        self.inplace_hud.hide()

        # Visual indicator that round is transitioning
        for idx in range(3):
            self.rec_cards[idx].name_lbl.setText("进入下一轮...")
            self.rec_cards[idx].score_pill.setText("--")
            self.rec_cards[idx].cost_lbl.hide()
            self.rec_cards[idx].summary_lbl.setText("等待新一轮候选卡牌出现...")
            self.rec_cards[idx].set_unselected_style()
        if c_name:
            self.advice_lbl.setText(f"✅ 已选择: 【{c_name}】\n正在洗入牌库，等待下一轮候选牌...")

        # 2. Update mana curve
        deck = self.log_listener.current_deck
        curve = self.ai_engine.calculate_mana_curve(deck)
        self.mana_curve_widget.update_curve(curve, total_cards=len(deck))

        # 3. Add to deck tracker
        card = pick_data.get("card")
        if card:
            self.deck_tracker.add_draft_card(card)

    @pyqtSlot(dict)
    def _on_ocr_deck_detected(self, data: dict) -> None:
        """Triggered when OcrWorker recognizes the already-drafted deck list on the right sidebar."""
        try:
            cards: List[CardInfo] = data.get("cards", [])
            total_picked: int = int(data.get("total_picked", len(cards)))
            if not cards and total_picked <= 0:
                return

            # Sync with log_listener.current_deck so AI evaluations use the real drafted deck
            if len(cards) >= len(self.log_listener.current_deck):
                self.log_listener.current_deck = list(cards)

            deck = self.log_listener.current_deck
            display_total = max(total_picked, len(deck))
            curve = self.ai_engine.calculate_mana_curve(deck)
            self.mana_curve_widget.update_curve(curve, total_cards=display_total)
            if deck:
                self.deck_tracker.set_draft_deck(deck)

            # Re-evaluate current 3 candidate cards if already on screen so scores reflect the drafted deck
            if hasattr(self, "_current_round_candidates") and len(self._current_round_candidates) == 3:
                self._on_draft_candidates_received(list(self._current_round_candidates))
        except Exception as e:
            logger.error(f"Error in _on_ocr_deck_detected: {e}", exc_info=True)

    @pyqtSlot(list)
    def _on_draft_finished(self, final_deck: List[CardInfo]) -> None:
        self.inplace_hud.hide()
        self.advice_lbl.setText("🎉 竞技场选牌完成 (30/30)！已构建完整套牌。")
        self.deck_tracker.set_draft_deck(final_deck)
        self._on_status_updated("选牌完成，已同步牌库追踪")

    @pyqtSlot(bool)
    def _on_state_lock_changed(self, is_locked: bool) -> None:
        if is_locked:
            self.lock_lbl.setText("🔒 动画防抖中")
        else:
            self.lock_lbl.setText("")

    @pyqtSlot(str)
    def _on_status_updated(self, text: str) -> None:
        self.status_lbl.setText(f"● {text}")

    @pyqtSlot(dict)
    def _on_game_started(self, info: dict) -> None:
        self._switch_to_play_view()
        self.deck_tracker.reset_game()
        self.secret_tracker.reset()
        self._reset_to_waiting_play_state()
        if getattr(self.log_listener, "current_hero", None):
            friendly_name = get_class_cn(self.log_listener.current_hero)
            self.hero_badge.setText(f"我方: {friendly_name}")
        # Suspend OCR polling during active match for zero CPU overhead
        self.ocr_worker.pause()
        self._on_status_updated("进入对局实战模式 (已挂起OCR截屏，纯日志极速驱动)")

    @pyqtSlot(dict)
    def _on_turn_active(self, turn_info: dict) -> None:
        turn = turn_info.get("turn", 1)
        self._is_player_turn = turn_info.get("is_player_turn", True)
        self._turn_start_time = time.time()
        self._current_turn_plays = []
        self._announced_draw_directive = False
        self._announced_face_pivot = False
        if turn == 1:
            self._replay_nodes = []
            self._current_replay_summary = None
        if hasattr(self, "_rope_timer"):
            self._rope_timer.start()

        if getattr(self, "_auto_rope_active", False) and getattr(self, "is_rope_mode", False):
            self.toggle_rope_mode()
            self._auto_rope_active = False

        self._on_status_updated(f"进入第 {turn} 回合")

    @pyqtSlot(dict)
    def _on_play_state_updated(self, payload: dict) -> None:
        """Triggered in Play Mode: calculates real-time tactical advice and card plays."""
        turn = payload.get("turn", 1)
        mana = payload.get("mana", 1)
        max_mana = payload.get("max_mana", 1)
        hand = payload.get("hand", [])
        friendly = payload.get("friendly_board", [])
        enemy = payload.get("enemy_board", [])
        opp_raw = payload.get("opponent_hero", "法师")
        opp = get_class_cn(opp_raw)

        # Performance: Fast state fingerprint to eliminate redundant re-rendering and calculations
        hand_ids = tuple(c.id if hasattr(c, "id") else str(c) for c in hand)
        state_fingerprint = (turn, mana, max_mana, tuple(friendly), tuple(enemy), hand_ids, opp, getattr(self, "is_rope_mode", False))
        if state_fingerprint == getattr(self, "_last_play_state_key", None):
            return
        self._last_play_state_key = state_fingerprint
        self._last_play_payload = payload

        # Hide Game Over frame if an active match update arrives
        if hasattr(self, "game_over_frame") and self.game_over_frame.isVisible():
            self.game_over_frame.hide()
            self.play_actions_frame.show()
            self.play_trade_frame.show()
            self.play_risk_frame.show()
            self.posture_frame.show()
            if hasattr(self, "intel_container"):
                self.intel_container.show()

        # 1. Switch to play container with adaptive height
        self._switch_to_play_view()

        # Update friendly hero badge if known
        friendly_hero_raw = payload.get("friendly_hero", getattr(self.log_listener, "current_hero", None))
        if friendly_hero_raw:
            friendly_name = get_class_cn(friendly_hero_raw)
            self.hero_badge.setText(f"我方: {friendly_name}")

        # 2. Update status banner
        self.play_turn_lbl.setText(f"⚡ 回合 {turn} | 可用法力: {mana}/{max_mana} 💎")
        self.play_turn_lbl.setStyleSheet("color: #6ee7b7; font-size: 13px; font-weight: bold;")
        self.play_opp_lbl.setText(f"对手: {opp}")

        # 3. Call AI Engine for real-time play recommendations
        try:
            self.hand_tracker.set_opponent_class(opp_raw)
            hand_warnings = self.hand_tracker.get_threat_warnings()
            has_long_held = self.hand_tracker.has_long_held_cards(min_turns=4)

            friendly_hp = payload.get("friendly_hp", 30)
            enemy_hp = payload.get("enemy_hp", 30)
            secrets_count = len(self.secret_tracker.active_secrets) if hasattr(self, "secret_tracker") else 0

            # 1. Optimistic Fast-Path: evaluate 15 heuristic engines locally (<2ms) without UI freezing
            rec: PlayRecommendation = self.ai_engine.evaluate_play_turn(
                turn_number=turn,
                current_mana=mana,
                hand_cards=hand,
                friendly_board=friendly,
                enemy_board=enemy,
                opponent_class=opp,
                opponent_hand_warnings=hand_warnings,
                has_long_held_card=has_long_held,
                friendly_hp=friendly_hp,
                enemy_hp=enemy_hp,
                enemy_secrets_count=secrets_count,
                use_llm=False,
            )

            # 2. Asynchronous LLM Deep Evaluation: non-blocking thread for online reasoning
            if self.ai_engine.has_llm_client():
                def _bg_play_eval():
                    try:
                        llm_rec = self.ai_engine.evaluate_play_turn(
                            turn_number=turn,
                            current_mana=mana,
                            hand_cards=hand,
                            friendly_board=friendly,
                            enemy_board=enemy,
                            opponent_class=opp,
                            opponent_hand_warnings=hand_warnings,
                            has_long_held_card=has_long_held,
                            friendly_hp=friendly_hp,
                            enemy_hp=enemy_hp,
                            enemy_secrets_count=secrets_count,
                            use_llm=True,
                        )
                        QTimer.singleShot(0, lambda: self._enhance_play_with_llm(llm_rec))
                    except Exception as ex:
                        logger.debug(f"Background LLM play eval skipped: {ex}")

                import threading
                threading.Thread(target=_bg_play_eval, daemon=True).start()

            # 3.2. Priority 0: Real-Time Lethal & Survival Calculation (First Principles)
            friendly_board_objs = payload.get("friendly_board_objs", [])
            if not friendly_board_objs and friendly:
                for item in friendly:
                    atk_val = 2
                    if "(" in str(item) and "/" in str(item):
                        try:
                            atk_val = int(str(item).split("(")[1].split("/")[0])
                        except Exception:
                            atk_val = 2
                    friendly_board_objs.append({"name": str(item), "atk": atk_val, "can_attack": True, "windfury": False})

            enemy_taunts = payload.get("enemy_taunt_objs", [])
            enemy_hp_val = payload.get("enemy_hp", 30)
            enemy_armor_val = payload.get("enemy_armor", 0)

            lethal_res: LethalResult = self.lethal_calculator.calculate_lethal(
                friendly_minions=friendly_board_objs,
                enemy_taunts=enemy_taunts,
                hand_cards=hand,
                available_mana=mana,
                enemy_hp=enemy_hp_val,
                enemy_armor=enemy_armor_val,
                hero_class=payload.get("friendly_hero", "MAGE"),
                hero_power_available=payload.get("hero_power_available", True),
            )

            if lethal_res.is_lethal:
                self.lethal_frame.show()
                self.lethal_title_lbl.setText("⚡ 绝杀战机已现 (LETHAL DETECTED)!")
                self.lethal_title_lbl.setStyleSheet("color: #38bdf8; font-size: 13px; font-weight: 800; letter-spacing: 0.5px;")
                self.lethal_frame.setStyleSheet("""
                    QFrame#lethalFrame {
                        background: rgba(14, 165, 233, 0.15);
                        border: 1.5px solid #38bdf8;
                        border-radius: 8px;
                    }
                    QLabel { background: transparent; border: none; padding: 0px; }
                """)
                self.lethal_detail_lbl.setText(
                    f"可造成 {lethal_res.total_damage} 点斩杀伤害 (敌方血量 {lethal_res.target_hp}，溢出 {lethal_res.overkill} 点)！"
                )
                self.lethal_steps_lbl.setText("<b>斩杀执行路径:</b><br>" + "<br>".join(f"• {s}" for s in lethal_res.action_steps))
                self.sound_engine.notify_lethal(damage=lethal_res.total_damage)
            elif getattr(rec, "two_turn_lethal_advice", ""):
                self.lethal_frame.show()
                self.lethal_title_lbl.setText("⚔️ 两回合将死推演 · TWO-TURN LETHAL")
                self.lethal_title_lbl.setStyleSheet("color: #fbbf24; font-size: 13px; font-weight: 800;")
                self.lethal_frame.setStyleSheet("""
                    QFrame#lethalFrame {
                        background: rgba(245, 158, 11, 0.12);
                        border: 1.5px solid #f59e0b;
                        border-radius: 8px;
                    }
                    QLabel { background: transparent; border: none; padding: 0px; }
                """)
                self.lethal_detail_lbl.setText(rec.two_turn_lethal_advice)
                self.lethal_steps_lbl.setText("💡 战术导向: 全员走脸控血，敌方下回合无解场必崩盘！")
                self.sound_engine.notify_two_turn_lethal()
            elif rec.opponent_burst_danger and rec.opponent_burst_danger.threat_tier == "CRITICAL_LETHAL":
                self.lethal_frame.show()
                self.lethal_title_lbl.setText("🚨 敌方绝杀警报！下回合面临死亡威胁！")
                self.lethal_title_lbl.setStyleSheet("color: #f87171; font-size: 13px; font-weight: 800;")
                self.lethal_frame.setStyleSheet("""
                    QFrame#lethalFrame {
                        background: rgba(239, 68, 68, 0.15);
                        border: 1.5px solid #ef4444;
                        border-radius: 8px;
                    }
                    QLabel { background: transparent; border: none; padding: 0px; }
                """)
                self.lethal_detail_lbl.setText(rec.opponent_burst_danger.survival_directive)
                self.lethal_steps_lbl.setText(
                    f"敌方场攻: {rec.opponent_burst_danger.opponent_field_atk} | 空场直伤: ~{rec.opponent_burst_danger.empty_board_burst} | 总斩杀: {rec.opponent_burst_danger.total_projected_damage} 点<br>"
                    f"👉 生存法则: 必须优先解掉敌方高攻随从，或打出嘲讽/叠甲抬血！"
                )
                self.sound_engine.notify_opponent_lethal_threat(rec.opponent_burst_danger.lethal_deficit)
            else:
                self.lethal_frame.hide()

            # 3.3. Update Live Blunder Shield Interceptor Banner
            if rec.blunder_alerts:
                self.blunder_frame.show()
                alert_text = "\n".join(rec.blunder_alerts)
                self.blunder_desc_lbl.setText(format_tactical_text(alert_text))
                self.sound_engine.notify_blunder_alert(rec.blunder_alerts[0])
            else:
                self.blunder_frame.hide()

            # 3.5. Update Matchup Blueprint & Opponent Archetype in status banner
            arch_report = self.archetype_classifier.get_current_report() if hasattr(self, "archetype_classifier") else None
            arch_tag = f" | 🏷️ {arch_report.archetype_name} ({arch_report.confidence_pct}%)" if (arch_report and arch_report.confidence_pct >= 40) else ""

            if getattr(rec, "matchup_blueprint", ""):
                self.play_opp_lbl.setText(f"对手: {opp} | 🧭 {rec.matchup_blueprint}{arch_tag}")
            else:
                self.play_opp_lbl.setText(f"对手职业: {opp}{arch_tag}")

            # 4. Render Posture & Beatdown Clock
            mode_colors = {
                "AGGRESSIVE": ("🔥 姿态: 突击抢脸 (Beatdown)", "#ef4444"),
                "CONTROL": ("🛡️ 姿态: 控场防守 (Control)", "#38bdf8"),
                "ALL_IN": ("⚡ 姿态: 孤注一掷 (All-in)", "#f59e0b"),
                "BALANCED": ("⚖️ 姿态: 稳健均势 (Balanced)", "#10b981"),
            }
            badge_text, badge_color = mode_colors.get(rec.posture_mode, ("⚖️ 姿态: 稳健均势", "#10b981"))
            self.posture_badge_lbl.setText(badge_text)
            self.posture_badge_lbl.setStyleSheet(f"color: {badge_color}; font-size: 11px; font-weight: bold;")
            self.clock_lbl.setText(rec.beatdown_clock or "")

            # 4.5. Coin Optimizer Analysis
            has_coin = payload.get("has_coin", False)
            if not has_coin:
                for c in hand:
                    c_name = getattr(c, "name", str(c))
                    c_id = getattr(c, "id", "")
                    if "幸运币" in c_name or c_id == "GAME_005":
                        has_coin = True
                        break

            if has_coin:
                coin_strat: Optional[CoinStrategy] = CoinOptimizer.calculate_strategy(
                    hand_cards=hand,
                    current_turn=turn,
                    has_coin=True,
                )
                if coin_strat:
                    self.coin_frame.show()
                    if coin_strat.should_coin_now:
                        self.sound_engine.notify_coin_opportunity()
                        self.coin_title_lbl.setText("🪙 幸运币规划 👉【本回合跳币最佳时刻】")
                        self.coin_frame.setStyleSheet("""
                            QFrame#coinFrame {
                                background: rgba(16, 185, 129, 0.15);
                                border: 1px solid #10b981;
                                border-radius: 6px;
                            }
                            QLabel { background: transparent; border: none; padding: 0px; }
                        """)
                    elif coin_strat.waste_warning:
                        self.coin_title_lbl.setText("🪙 幸运币规划 ⚠️【切勿乱交！保留节奏】")
                        self.coin_frame.setStyleSheet("""
                            QFrame#coinFrame {
                                background: rgba(239, 68, 68, 0.15);
                                border: 1px solid #ef4444;
                                border-radius: 6px;
                            }
                            QLabel { background: transparent; border: none; padding: 0px; }
                        """)
                    else:
                        self.coin_title_lbl.setText("🪙 幸运币节奏曲线 (Coin Optimizer)")
                        self.coin_frame.setStyleSheet("""
                            QFrame#coinFrame {
                                background: rgba(234, 179, 8, 0.10);
                                border: 1px solid rgba(234, 179, 8, 0.35);
                                border-radius: 6px;
                            }
                            QLabel { background: transparent; border: none; padding: 0px; }
                        """)
                    self.coin_desc_lbl.setText(format_tactical_text(f"**节奏预演**: {coin_strat.curve_pattern}\n{coin_strat.advice}"))
                else:
                    self.coin_frame.hide()
            else:
                self.coin_frame.hide()

            # 5. Render Interactive Action Checklist & Dual Plan Toggle
            self._current_rec = rec
            self._render_tactical_plan_checklist()

            # 5.2 Tactical Voice Callouts via TTS
            if getattr(rec, "draw_first_directive", "") and not getattr(self, "_announced_draw_directive", False):
                self._announced_draw_directive = True
                self.sound_engine.notify_tactical_callout("先过牌再出牌")
            elif getattr(rec, "face_pivot_warning", "") and "走脸转折点" in rec.face_pivot_warning and not getattr(self, "_announced_face_pivot", False):
                self._announced_face_pivot = True
                self.sound_engine.notify_tactical_callout("全员走脸压血")

            # 5.3 Secondary Intelligence & Web Companion (Protected Non-Blocking Sandbox)
            try:
                if hasattr(self, "web_companion"):
                    b1 = rec.best_branch
                    b2 = rec.alt_branch
                    from core.tactical_tree_visualizer import TacticalDecisionTree
                    from core.tilt_guard import TiltGuard
                    from core.highlight_recorder import HighlightClipRecorder

                    TiltGuard.get_instance().record_turn_action(duration_sec=3.5, blunders=len(rec.blunder_alerts))
                    mind_dossier = " | ".join([f"#{c['slot']} {c['provenance']}: {c['deduction']}" for c in self.hand_tracker.get_mind_reading_report()[:3]]) if hasattr(self, "hand_tracker") else ""

                    tree_ascii = ""
                    if b1:
                        alts = [b2] if b2 else []
                        tree_root = TacticalDecisionTree.build_tree(ActionTreeResult(b1, alts), mana, friendly_hp, enemy_hp, opp)
                        tree_ascii = TacticalDecisionTree.to_ascii_tree(tree_root)

                    # Coach directive & Lethal flag evaluation
                    is_lth = bool(b1 and b1.damage_to_face >= enemy_hp and enemy_hp > 0)
                    if is_lth:
                        c_dir = "绝杀战机已现！全部战力全力走脸斩杀！"
                    elif "孤注一掷" in getattr(rec, "hypergeometric_summary", ""):
                        c_dir = "局势落后，唯有搏命神抽直伤/关键解牌，拼脸放手一搏！"
                    elif rec.aoe_threats and any("烈焰" in t or "乱斗" in t for t in rec.aoe_threats):
                        c_dir = "进入敌方核心清场回合，注意克制下怪，防止一波清空！"
                    elif getattr(rec, "draw_first_directive", ""):
                        c_dir = getattr(rec, "draw_first_directive", "")
                    else:
                        c_dir = getattr(rec, "compass_directive", "") or "按费平滑出牌，稳固随从交换优势。"

                    # v10 Apex: Topdeck Matrix, Multi-Turn Lookahead, Game Phase, Capsule HUD
                    rem_deck = self.deck_tracker.get_stats().remaining_cards if hasattr(self, "deck_tracker") else []
                    topdeck_rep = TopdeckMatrix.evaluate(
                        remaining_cards=rem_deck,
                        friendly_hp=friendly_hp,
                        enemy_hp=enemy_hp,
                        friendly_field_atk=b1.damage_to_face if b1 else 0,
                        enemy_field_atk=getattr(rec, "enemy_board_attack", 0),
                        available_mana=mana,
                    )

                    friendly_minions_list = [{"attack": getattr(m, "attack", 0), "health": getattr(m, "health", 0)} for m in getattr(rec, "friendly_minions", [])]
                    enemy_minions_list = [{"attack": getattr(m, "attack", 0), "health": getattr(m, "health", 0)} for m in getattr(rec, "enemy_minions", [])]
                    lookahead_rep = MultiTurnLookahead.evaluate_horizon(
                        friendly_minions=friendly_minions_list,
                        enemy_minions=enemy_minions_list,
                        friendly_hp=friendly_hp,
                        enemy_hp=enemy_hp,
                        opponent_class=opp,
                        current_turn=turn,
                    )

                    phase_state = GamePhaseMachine.evaluate(
                        current_turn=turn,
                        available_mana=mana,
                        remaining_deck_count=self.deck_tracker.get_stats().total_remaining if hasattr(self, "deck_tracker") else 20,
                        friendly_hp=friendly_hp,
                        enemy_hp=enemy_hp,
                    )

                    miracle_top = topdeck_rep.miracle_outs[0].card_name if topdeck_rep.miracle_outs else ""
                    miracle_prob = topdeck_rep.miracle_outs[0].draw_probability_pct if topdeck_rep.miracle_outs else 0.0
                    capsule_data = CapsuleHUD.format_display(
                        has_lethal=is_lth,
                        lethal_desc=c_dir if is_lth else "",
                        primary_action=b1.action_sequence[0] if (b1 and b1.action_sequence) else "稳健控场",
                        winrate_pct=b1.projected_winrate if b1 else 50.0,
                        miracle_card=miracle_top,
                        miracle_pct=miracle_prob,
                        is_capsule_active=getattr(self, "is_compact_mode", False),
                    )

                    # v11 Legendary: Secret Probing, Hand Age Intel, Deck Matchup Sandbox
                    active_sec_names = []
                    if hasattr(self, "secret_tracker"):
                        for sec in getattr(self.secret_tracker, "active_secrets", []):
                            if hasattr(self.secret_tracker, "get_possible_secrets"):
                                possible = self.secret_tracker.get_possible_secrets(sec.secret_id)
                                active_sec_names.extend([p.name for p in possible])
                            elif hasattr(sec, "hero_class"):
                                active_sec_names.append(sec.hero_class)
                    secret_rep = SecretDeathrattleSimulator.evaluate_probing_order(
                        active_secrets=active_sec_names,
                        friendly_minions=friendly_minions_list,
                        friendly_hand=[],
                        friendly_hp=friendly_hp,
                    )

                    hand_age_rep = self.hand_age_intel.update_turn(turn) if hasattr(self, "hand_age_intel") else None
                    matchup_rep = DeckMatchupSandbox.evaluate_deck(rem_deck)

                    # v13 Supreme Omniscience: Neural Hand Silhouette
                    hand_raw = [
                        {"slot": c.slot, "hold_turns": c.hold_turns, "origin": c.origin.value}
                        for c in getattr(hand_age_rep, "cards", [])
                    ] if hand_age_rep else []
                    silhouette_rep = NeuralHandSilhouette.evaluate_hand_silhouette(
                        opponent_class=opp,
                        hand_cards_info=hand_raw,
                        current_turn=turn,
                    )

                    # v12 Grandmaster Co-Pilot Step Plan & Conversational Voice Streaming
                    copilot_plan = MasterCoPilotEngine.build_step_plan(
                        action_sequence=b1.action_sequence if b1 else (rec.checklist_steps or rec.suggested_plays),
                        trading_plan=rec.trading_plan,
                        had_lethal=is_lth,
                        friendly_hp=friendly_hp,
                        enemy_hp=enemy_hp,
                        mana=mana,
                        turn=turn,
                    )
                    MasterCoPilotEngine.get_instance().load_turn_plan(copilot_plan)

                    tts_streamer = ConversationalTtsStreamer.get_instance()
                    if hasattr(self, "sound_engine"):
                        tts_streamer.set_speaker_func(lambda msg: self.sound_engine.speak(msg) if getattr(self.sound_engine, "tts_enabled", False) else None)
                    tts_streamer.speak_macro_overview(copilot_plan.macro_voice_overview)
                    active_st = copilot_plan.get_active_step()
                    if active_st:
                        tts_streamer.speak_step_guidance(active_st.conversational_voice)

                    self.web_companion.update_state({
                        "mode": "PLAY",
                        "turn": turn,
                        "mana": mana,
                        "max_mana": max_mana,
                        "opponent_hero": opp,
                        "archetype": getattr(arch_report, "archetype_name", "--") if arch_report else "--",
                        "winrate_pct": b1.projected_winrate if b1 else 50.0,
                        "plan_a_title": b1.plan_name if b1 else "最优方案",
                        "plan_a_steps": b1.action_sequence if b1 else (rec.checklist_steps or rec.suggested_plays),
                        "plan_a_ev": b1.ev_score if b1 else 0.0,
                        "plan_b_title": b2.plan_name if b2 else "",
                        "plan_b_steps": b2.action_sequence if b2 else getattr(rec, "plan_b_steps", []),
                        "plan_b_ev": b2.ev_score if b2 else 0.0,
                        "blunder_alert": rec.blunder_alerts[0] if rec.blunder_alerts else "",
                        "compass_directive": getattr(rec, "compass_directive", ""),
                        "burst_danger": rec.opponent_burst_danger.danger_badge if (rec.opponent_burst_danger and rec.opponent_burst_danger.threat_tier in {"CRITICAL_LETHAL", "HIGH_DANGER"}) else "",
                        "discover_guidance": f"{rec.discover_guidance.priority_badge}: {rec.discover_guidance.guidance_text}" if rec.discover_guidance else "",
                        "variance_policy": getattr(b1, "variance_policy", "") if b1 else "",
                        "curve_foresight": getattr(b1, "curve_foresight_text", "") if b1 else "",
                        "positioning_advice": getattr(b1, "positioning_slot_advice", "") if b1 else "",
                        "draw_first_directive": getattr(rec, "draw_first_directive", ""),
                        "next_turn_threat_cards": getattr(rec, "next_turn_threat_cards", []),
                        "lethal_cushion": getattr(rec, "lethal_cushion", ""),
                        "rng_badge": rec.rng_report.summary_badge if (getattr(rec, "rng_report", None) and rec.rng_report.summary_badge) else "",
                        "personal_habit_reminder": getattr(rec, "personal_weakness_reminder", ""),
                        "ghost_board_summary": self.board_tactical_overlay.get_ghost_board_summary() if hasattr(self, "board_tactical_overlay") else "",
                        "negative_deductions": self.hand_tracker.get_negative_deductions() if hasattr(self, "hand_tracker") else [],
                        "resilience_badge": getattr(b1, "resilience_badge", "") if b1 else "",
                        "resilience_verdict": getattr(rec, "resilience_verdict", ""),
                        "hypergeometric_gamble": getattr(rec, "hypergeometric_summary", ""),
                        "tilt_status": getattr(rec, "tilt_summary", ""),
                        "mind_reading_summary": mind_dossier,
                        "decision_tree_ascii": tree_ascii,
                        "coach_directive": c_dir,
                        "is_lethal": is_lth,
                        "topdeck_summary": topdeck_rep.summary_markdown,
                        "topdeck_matrix": topdeck_rep.to_dict(),
                        "lookahead_summary": lookahead_rep.summary_markdown,
                        "lookahead_table": lookahead_rep.forecast_table_ascii,
                        "game_phase": phase_state.phase.value,
                        "game_phase_zh": phase_state.phase_name_zh,
                        "game_phase_weights": {
                            "tempo": phase_state.tempo_weight,
                            "card_advantage": phase_state.card_advantage_weight,
                            "face_pressure": phase_state.face_pressure_weight,
                            "survival": phase_state.survival_weight,
                        },
                        "capsule_summary": capsule_data.status_summary_line,
                        "secrets_summary": secret_rep.summary_markdown,
                        "hand_age_summary": hand_age_rep.summary_markdown if hand_age_rep else "",
                        "matchup_sandbox": matchup_rep.to_dict(),
                        "copilot_plan": copilot_plan.to_dict(),
                        "hand_silhouette": silhouette_rep.to_dict(),
                    })

                    # Coach voice commentary trigger
                    if hasattr(self, "sound_engine"):
                        if is_lth:
                            self.sound_engine.notify_coach_directive("LETHAL")
                        elif "孤注一掷" in getattr(rec, "hypergeometric_summary", ""):
                            self.sound_engine.notify_coach_directive("GAMBLE")
                        elif rec.aoe_threats and any("烈焰" in t or "乱斗" in t for t in rec.aoe_threats):
                            self.sound_engine.notify_coach_directive("AOE")
            except Exception as sec_ex:
                logger.debug(f"Secondary intelligence update suppressed: {sec_ex}")

            # 6. Render trading & mana planning with optimal trades, face pivot & positioning
            trade_text_parts = []
            if getattr(rec, "face_pivot_warning", ""):
                trade_text_parts.append(f"🔥 **{rec.face_pivot_warning}**\n")
            trade_text_parts.append(f"⚔️ {rec.trading_plan}")
            if rec.optimal_trades:
                trade_text_parts.append("\n**随从去向推演:**")
                for ot in rec.optimal_trades[:3]:
                    trade_text_parts.append(f"• {ot}")
            if getattr(rec, "positioning_advice", ""):
                trade_text_parts.append(f"\n♟️ **{rec.positioning_advice}**")
            trade_text_parts.append(f"\n💡 {rec.mana_plan}")
            self.play_trade_lbl.setText(format_tactical_text("\n".join(trade_text_parts)))

            # 7. Render risk warnings, burst danger, Discovery Radar & AOE Radar
            risk_lines = []
            if rec.opponent_burst_danger and rec.opponent_burst_danger.threat_tier in {"CRITICAL_LETHAL", "HIGH_DANGER"}:
                risk_lines.append(f"🚨 **【敌方斩杀防御】** {rec.opponent_burst_danger.survival_directive}")
            elif getattr(rec, "burst_safety_warning", ""):
                risk_lines.append(rec.burst_safety_warning)

            if rec.discover_guidance:
                risk_lines.append(f"🔮 **【实战发现抓取导向】** {rec.discover_guidance.priority_badge}: {rec.discover_guidance.guidance_text}")

            if getattr(rec, "personal_weakness_reminder", ""):
                risk_lines.append(f"💡 **【个人短板警示】** {rec.personal_weakness_reminder}")

            if getattr(rec, "resilience_verdict", ""):
                risk_lines.append(f"🛡️ **【局势抗灭韧性】** {rec.resilience_verdict}")

            if getattr(rec, "rng_report", None) and rec.rng_report.summary_badge:
                risk_lines.append(f"🎲 **【概率透视】** {rec.rng_report.summary_badge}")

            if hasattr(self, "hand_tracker"):
                neg_deductions = self.hand_tracker.get_negative_deductions()
                if neg_deductions:
                    neg_notes = [f"• 槽位#{d['slot']}: {d['deduction']}" for d in neg_deductions[:2]]
                    risk_lines.append("🚫 **【对手未出牌负向排查】**\n" + "\n".join(neg_notes))

            if hasattr(self, "hand_tracker"):
                hand_matrix = self.hand_tracker.get_hand_reading_matrix()
                if hand_matrix:
                    risk_lines.append("🎯 **【对手留牌深度逆向读牌】**\n" + self.hand_tracker.get_reading_matrix_text())

            if getattr(rec, "discovery_radar_warning", ""):
                risk_lines.append(rec.discovery_radar_warning)
            risk_lines.append(rec.risk_warning)
            if rec.aoe_threats:
                for at in rec.aoe_threats[:2]:
                    if at not in rec.risk_warning:
                        risk_lines.append(f"• {at}")
            self.play_risk_lbl.setText(format_tactical_text("\n".join(risk_lines)))

            # 8. Update compact capsule mode display
            top_action = rec.suggested_plays[0] if rec.suggested_plays else "观察局势"
            b1_ev = f"EV:+{rec.best_branch.ev_score:.1f}" if rec.best_branch else ""
            if lethal_res.is_lethal:
                self.compact_status_lbl.setText(f"🔥 斩杀已成! ({lethal_res.total_damage}伤) | 💡 {top_action[:18]}")
            else:
                ev_str = f" | {b1_ev}" if b1_ev else ""
                self.compact_status_lbl.setText(f"⚡ T{turn} 💎{mana}{ev_str} | 💡 {top_action[:20]}")

            # 9. Update In-game Board Tactical Projection (Arrows, Badges & Placement)
            if hasattr(self, "board_overlay") and self.board_overlay._enabled:
                win_rect = self.window_finder.find_window()
                self.board_overlay.sync_to_window(win_rect)
                active_steps = rec.best_branch.action_sequence if rec.best_branch else rec.play_sequence
                active_slot = 0
                if rec.best_branch and getattr(rec.best_branch, "positioning_slot_advice", ""):
                    import re
                    match = re.search(r"Slot\s+(\d+)", rec.best_branch.positioning_slot_advice)
                    if match:
                        active_slot = int(match.group(1))

                top_aoe_dmg = 0
                for a_str in (rec.aoe_threats or []):
                    import re
                    m = re.search(r"[打造成]\s*(\d+)", a_str)
                    if m:
                        top_aoe_dmg = int(m.group(1))
                        break
                if top_aoe_dmg == 0 and any("烈焰风暴" in a for a in rec.aoe_threats):
                    top_aoe_dmg = 5
                elif top_aoe_dmg == 0 and any("奉献" in a or "横扫" in a or "暴风雪" in a for a in rec.aoe_threats):
                    top_aoe_dmg = 2

                self.board_overlay.update_board_tactics(
                    friendly_minions=friendly,
                    enemy_minions=enemy,
                    optimal_trades=rec.optimal_trades,
                    play_actions=active_steps,
                    recommended_slot=active_slot,
                    enemy_hp=enemy_hp,
                    is_lethal=lethal_res.is_lethal,
                    lethal_damage=lethal_res.total_damage,
                    aoe_threat_damage=top_aoe_dmg,
                )

            if any("🚨" in t for t in rec.aoe_threats):
                top_aoe = rec.aoe_threats[0].replace("•", "").replace("🚨", "").strip()
                self.sound_engine.notify_aoe_threat(top_aoe)

            # Record turn snapshot for BlunderDetector
            self._turn_history.append(
                TurnSnapshot(
                    turn_number=turn,
                    mana_available=mana,
                    friendly_hp=friendly_hp,
                    enemy_hp=enemy_hp,
                    had_lethal=lethal_res.is_lethal,
                    lethal_damage=lethal_res.total_damage,
                    aoe_threat_warning=rec.aoe_threats[0] if rec.aoe_threats else "",
                    suggested_play=rec.suggested_plays[0] if rec.suggested_plays else "",
                    played_card_count=len(friendly),
                    posture_mode=rec.posture_mode,
                )
            )

            # Record turn review node for Step-by-Step Replayer
            friendly_names = [getattr(c, "name", str(c)) for c in friendly]
            enemy_names = [getattr(c, "name", str(c)) for c in enemy]
            hand_names = [getattr(c, "name", str(c)) for c in hand]
            ai_plan = rec.best_branch.action_sequence if rec.best_branch else rec.suggested_plays
            ai_ev = rec.best_branch.ev_score if rec.best_branch else 0.0
            ai_wr = rec.best_branch.projected_winrate if rec.best_branch else 50.0
            floating_m = rec.best_branch.floating_mana if rec.best_branch else max(0, mana - len(hand))

            existing_node = next((n for n in self._replay_nodes if n.turn_number == turn), None)
            if existing_node:
                existing_node.mana = mana
                existing_node.max_mana = max_mana
                existing_node.friendly_hp = friendly_hp
                existing_node.enemy_hp = enemy_hp
                existing_node.friendly_board = friendly_names
                existing_node.enemy_board = enemy_names
                existing_node.hand_cards = hand_names
                existing_node.ai_best_plan = ai_plan
                existing_node.ai_ev = ai_ev
                existing_node.ai_winrate = ai_wr
                existing_node.had_lethal = lethal_res.is_lethal
                existing_node.lethal_damage = lethal_res.total_damage
                existing_node.blunder_alerts = rec.blunder_alerts
                existing_node.aoe_threat = rec.aoe_threats[0] if rec.aoe_threats else ""
                existing_node.floating_mana = floating_m
            else:
                new_node = TurnReviewNode(
                    turn_number=turn,
                    mana=mana,
                    max_mana=max_mana,
                    friendly_hp=friendly_hp,
                    enemy_hp=enemy_hp,
                    friendly_board=friendly_names,
                    enemy_board=enemy_names,
                    hand_cards=hand_names,
                    ai_best_plan=ai_plan,
                    ai_ev=ai_ev,
                    ai_winrate=ai_wr,
                    player_actual_plays=list(self._current_turn_plays),
                    had_lethal=lethal_res.is_lethal,
                    lethal_damage=lethal_res.total_damage,
                    blunder_alerts=rec.blunder_alerts,
                    aoe_threat=rec.aoe_threats[0] if rec.aoe_threats else "",
                    floating_mana=floating_m,
                )
                self._replay_nodes.append(new_node)

            # 8. Update Secret Tracker & Deck Tracker views
            if len(self.secret_tracker.active_secrets) > 0:
                self.secret_frame.show()
                self.secret_count_badge.setText(f"{len(self.secret_tracker.active_secrets)} 个活跃奥秘")
                self.secret_desc_lbl.setText(format_tactical_text(self.secret_tracker.get_summary_text()))
            else:
                self.secret_frame.hide()

            deck_stats = self.deck_tracker.get_stats()
            self.deck_count_badge.setText(f"剩余 {deck_stats.total_remaining} 张")
            if deck_stats.total_remaining > 0:
                card_previews = [f"{c[0].name}x{c[1]}" for c in deck_stats.remaining_cards[:3]]
                self.deck_stats_lbl.setText(
                    f"随从率: {deck_stats.draw_odds_minion}% · 法术率: {deck_stats.draw_odds_spell}%\n"
                    f"牌库卡牌: {', '.join(card_previews)}"
                )

                # 8.5. Calculate Topdeck Odds & Clutch Advice
                friendly_field_atk = 0
                for item in friendly_board_objs:
                    if isinstance(item, dict):
                        friendly_field_atk += item.get("atk", 0)
                    elif hasattr(item, "atk"):
                        friendly_field_atk += getattr(item, "atk", 0)

                enemy_field_atk = 0
                for item in enemy:
                    if isinstance(item, dict):
                        enemy_field_atk += item.get("atk", 0)
                    elif "(" in str(item) and "/" in str(item):
                        try:
                            enemy_field_atk += int(str(item).split("(")[1].split("/")[0])
                        except Exception:
                            enemy_field_atk += 2

                topdeck_advice: Optional[TopdeckAdvice] = TopdeckMath.calculate_endgame_odds(
                    deck_tracker=self.deck_tracker,
                    friendly_hp=friendly_hp,
                    enemy_hp=enemy_hp,
                    friendly_field_atk=friendly_field_atk,
                    enemy_field_atk=enemy_field_atk,
                    current_turn=turn,
                )
                if topdeck_advice:
                    self.topdeck_lbl.show()
                    self.topdeck_lbl.setText(topdeck_advice.advice_text)
                    if topdeck_advice.recommended_line == "ALL_IN_FACE":
                        self.posture_badge_lbl.setText("🎲 姿态: 绝境神抽打脸 (Topdeck Win)")
                        self.posture_badge_lbl.setStyleSheet("color: #ec4899; font-size: 11px; font-weight: bold;")
                else:
                    self.topdeck_lbl.hide()
            else:
                self.topdeck_lbl.hide()

            # 9. Update Hand Tracker views
            self.hand_tracker.set_turn(turn)
            if self.hand_tracker.cards:
                self.hand_status_lbl.setText(format_tactical_text(self.hand_tracker.get_display_text()))
                self.hand_count_badge.setText(f"{len(self.hand_tracker.cards)}张")
            else:
                self.hand_status_lbl.setText("实时手牌追踪中（敌方出牌/抽牌时自动感知）")
                self.hand_count_badge.setText("对战中")

            self._on_status_updated(f"回合 {turn} 战术建议与斩杀推演完成")

        except Exception as e:
            logger.error(f"Error evaluating play turn: {e}", exc_info=True)
            self.play_actions_lbl.setText(f"出牌推演异常: {e}")

    def _switch_intel_tab(self, tab: str) -> None:
        """Toggles between Deck Tracker, Hand Reading, and Coin/Compass in the tactical drawer."""
        current_tab = getattr(self, "_active_intel_tab", "DECK")
        if current_tab == tab and getattr(self, "_intel_expanded", True):
            self.deck_frame.hide()
            self.hand_frame.hide()
            self.coin_frame.hide()
            self._intel_expanded = False
            for btn in (self.tab_deck_btn, self.tab_hand_btn, self.tab_coin_btn):
                btn.setStyleSheet("background: rgba(255, 255, 255, 0.04); color: #94a3b8; font-size: 10px; font-weight: 600; padding: 3px 8px; border-radius: 4px; border: 1px solid rgba(255, 255, 255, 0.08);")
            return

        self._intel_expanded = True
        self._active_intel_tab = tab

        active_btn_qss = "background: rgba(14, 165, 233, 0.18); color: #38bdf8; font-size: 10px; font-weight: bold; padding: 3px 8px; border-radius: 4px; border: 1px solid #0284c7;"
        inactive_btn_qss = "background: rgba(255, 255, 255, 0.04); color: #94a3b8; font-size: 10px; font-weight: 600; padding: 3px 8px; border-radius: 4px; border: 1px solid rgba(255, 255, 255, 0.08);"

        self.tab_deck_btn.setStyleSheet(active_btn_qss if tab == "DECK" else inactive_btn_qss)
        self.tab_hand_btn.setStyleSheet(active_btn_qss if tab == "HAND" else inactive_btn_qss)
        self.tab_coin_btn.setStyleSheet(active_btn_qss if tab == "COIN" else inactive_btn_qss)

        self.deck_frame.setVisible(tab == "DECK")
        self.hand_frame.setVisible(tab == "HAND")
        self.coin_frame.setVisible(tab == "COIN")

    def _switch_plan_view(self, plan: str) -> None:
        self._current_selected_plan = plan
        self._render_tactical_plan_checklist()

    @staticmethod
    def _get_completed_step_indices(steps: List[str], played_names: List[str]) -> set:
        completed = set()
        unmatched_played = list(played_names)
        for idx, step in enumerate(steps):
            for p in unmatched_played:
                if not p:
                    continue
                if f"【{p}】" in step or p in step:
                    completed.add(idx)
                    unmatched_played.remove(p)
                    break
        return completed

    def _render_tactical_plan_checklist(self) -> None:
        if not hasattr(self, "_current_rec") or not self._current_rec:
            return

        rec = self._current_rec
        is_rope = getattr(self, "is_rope_mode", False)

        # Draw First Directive Warning Banner
        if getattr(rec, "draw_first_directive", ""):
            self.draw_directive_lbl.setText(rec.draw_first_directive)
            self.draw_directive_frame.show()
        else:
            self.draw_directive_frame.hide()

        # Next-Turn Threat Radar Chips
        threat_cards = getattr(rec, "next_turn_threat_cards", [])
        if threat_cards:
            self.threat_radar_frame.show()
            chips = [f"<b>【{c['name']}】</b> ({c['cost']}费: {c['effect']})" for c in threat_cards[:3]]
            self.threat_radar_chips_lbl.setText(" • ".join(chips))
        else:
            self.threat_radar_frame.hide()

        # Lethal Cushion Tag
        if getattr(rec, "lethal_cushion", ""):
            self.lethal_cushion_tag.setText(rec.lethal_cushion)
            self.lethal_cushion_tag.show()
        else:
            self.lethal_cushion_tag.hide()

        # Select branch
        selected_plan = getattr(self, "_current_selected_plan", "A")
        branch = rec.best_branch if selected_plan == "A" else (rec.alt_branch or rec.best_branch)

        # Style toggle buttons
        if rec.alt_branch:
            self.plan_b_btn.show()
            if selected_plan == "A":
                self.plan_a_btn.setStyleSheet("background: #0284c7; color: #ffffff; border: 1px solid #38bdf8; padding: 2px 10px; border-radius: 9px; font-weight: bold; font-size: 10px;")
                self.plan_b_btn.setStyleSheet("background: rgba(255, 255, 255, 0.05); color: #94a3b8; border: 1px solid rgba(255, 255, 255, 0.1); padding: 2px 10px; border-radius: 9px; font-size: 10px;")
            else:
                self.plan_a_btn.setStyleSheet("background: rgba(255, 255, 255, 0.05); color: #94a3b8; border: 1px solid rgba(255, 255, 255, 0.1); padding: 2px 10px; border-radius: 9px; font-size: 10px;")
                self.plan_b_btn.setStyleSheet("background: #0284c7; color: #ffffff; border: 1px solid #38bdf8; padding: 2px 10px; border-radius: 9px; font-weight: bold; font-size: 10px;")
        else:
            self.plan_b_btn.hide()
            self.plan_a_btn.setStyleSheet("background: #0284c7; color: #ffffff; border: 1px solid #38bdf8; padding: 2px 10px; border-radius: 9px; font-weight: bold; font-size: 10px;")

        # Render Outcome line
        if branch:
            res_str = f" | {branch.resilience_badge}" if getattr(branch, "resilience_badge", "") else ""
            self.plan_outcome_lbl.setText(
                f"胜率: <b style='color: #38bdf8;'>{branch.projected_winrate}%</b> | "
                f"EV: <b style='color: #34d399;'>+{branch.ev_score:.1f}</b>{res_str} | "
                f"消耗 <b>{branch.mana_spent}</b> 费 | 抢脸 <b>{branch.damage_to_face}</b> 伤 | 场攻 <b>{branch.projected_board_attack}</b>"
            )
            self.plan_outcome_lbl.show()
            steps = list(branch.action_sequence) if branch.action_sequence else ["稳固场面"]
        else:
            self.plan_outcome_lbl.hide()
            steps = list(rec.checklist_steps or rec.play_sequence or rec.suggested_plays or ["稳固场面"])

        # If Draw First directive exists and not yet in steps, prepend it
        if getattr(rec, "draw_first_directive", "") and not any("抽牌" in s or "过牌" in s for s in steps):
            steps.insert(0, f"先过牌: {rec.draw_first_directive}")

        # If Rope Emergency Mode, render compressed punchlist
        if is_rope:
            lines = ["⏱️ <b>【烧绳急救·极速出牌】</b>"]
            for i, st in enumerate(steps[:3], 1):
                lines.append(f"⚡ <b>第{i}步:</b> {st}")
            self.play_actions_lbl.setText("<br>".join(lines))
            return

        # Render Interactive Checklist
        completed_indices = self._get_completed_step_indices(steps, self._current_turn_plays)
        checklist_lines = []
        found_next = False

        for idx, step in enumerate(steps):
            if idx in completed_indices:
                checklist_lines.append(f"<span style='color: #475569; text-decoration: line-through;'>☑️ <s>第{idx+1}步: {step}</s></span>")
            elif not found_next:
                found_next = True
                checklist_lines.append(f"<div style='background: rgba(14, 165, 233, 0.12); border-left: 2.5px solid #38bdf8; padding: 3px 6px; border-radius: 4px;'><b style='color: #38bdf8;'>👉 第{idx+1}步:</b> <b style='color: #f8fafc;'>{step}</b></div>")
            else:
                checklist_lines.append(f"&nbsp;&nbsp;&nbsp;&nbsp;<span style='color: #cbd5e1;'>[ ] 第{idx+1}步: {step}</span>")

        # Extra tactical tips from branch
        extra_tips = []
        if branch:
            if getattr(branch, "tactical_intent", ""):
                extra_tips.append(f"💡 <b>总纲:</b> {branch.tactical_intent}")
            if getattr(branch, "positioning_slot_advice", ""):
                extra_tips.append(f"📐 <b>站位:</b> {branch.positioning_slot_advice}")
            if getattr(branch, "curve_foresight_text", ""):
                extra_tips.append(f"⚡ <b>平滑:</b> {branch.curve_foresight_text}")
            if getattr(branch, "variance_policy", ""):
                extra_tips.append(f"🎲 <b>方差:</b> {branch.variance_policy}")
        if extra_tips:
            checklist_lines.append("<div style='margin-top: 3px; font-size: 10px; color: #94a3b8;'>" + " | ".join(extra_tips) + "</div>")

        self.play_actions_lbl.setText("<br>".join(checklist_lines))

    def _on_secret_action_tested(self, trigger: TriggerType) -> None:
        """User or automatic action eliminates candidate secrets that didn't trigger."""
        self.secret_tracker.on_game_action(trigger)
        self.secret_desc_lbl.setText(format_tactical_text(self.secret_tracker.get_summary_text()))
        self._on_status_updated(f"已执行奥秘动作测试: {trigger.value}")

    @pyqtSlot(dict)
    def _on_card_played_in_match(self, payload: dict) -> None:
        """Triggered when player plays a card in combat, updating real-time remaining deck."""
        cid = payload.get("card_id", "")
        if cid:
            c_name = cid
            if hasattr(self, "card_db"):
                c_obj = self.card_db.get_by_id(cid)
                if c_obj:
                    c_name = c_obj.name
            self._current_turn_plays.append(c_name)
            if self._replay_nodes:
                self._replay_nodes[-1].player_actual_plays = list(self._current_turn_plays)
            if hasattr(self, "_render_tactical_plan_checklist"):
                self._render_tactical_plan_checklist()

        if cid and hasattr(self, "deck_tracker"):
            self.deck_tracker.record_card_played(cid)
            deck_stats = self.deck_tracker.get_stats()
            self.deck_count_badge.setText(f"剩余 {deck_stats.total_remaining} 张")
            if deck_stats.total_remaining > 0:
                card_previews = [f"{c[0].name}x{c[1]}" for c in deck_stats.remaining_cards[:3]]
                self.deck_stats_lbl.setText(
                    f"随从率: {deck_stats.draw_odds_minion}% · 法术率: {deck_stats.draw_odds_spell}%\n"
                    f"牌库卡牌: {', '.join(card_previews)}"
                )

    def _reset_to_waiting_play_state(self) -> None:
        """Resets the play view to waiting for next match/turn."""
        if hasattr(self, "turn_replayer_frame"):
            self.turn_replayer_frame.hide()
        if hasattr(self, "game_over_frame"):
            self.game_over_frame.hide()
        if hasattr(self, "draw_directive_frame"):
            self.draw_directive_frame.hide()
        if hasattr(self, "threat_radar_frame"):
            self.threat_radar_frame.hide()
        self._replay_nodes = []
        self._current_replay_summary = None
        self._current_turn_plays = []
        self._current_rec = None
        self._current_selected_plan = "A"
        self._announced_draw_directive = False
        self._announced_face_pivot = False
        if hasattr(self, "plan_outcome_lbl"):
            self.plan_outcome_lbl.setText("")
        if hasattr(self, "lethal_cushion_tag"):
            self.lethal_cushion_tag.setText("")
        self.play_actions_frame.show()
        self.play_trade_frame.show()
        self.play_risk_frame.show()
        self.posture_frame.show()
        if hasattr(self, "intel_container"):
            self.intel_container.show()
        self.play_turn_lbl.setText("⚡ 等待新对战回合开始...")
        self.play_turn_lbl.setStyleSheet("color: #fbbf24; font-size: 13px; font-weight: bold;")
        self.play_opp_lbl.setText("对手: 等待检测")
        self.play_actions_lbl.setText("等待游戏内打出卡牌或进入新回合...")
        self.play_trade_lbl.setText("等待随从场面...")
        self.play_risk_lbl.setText("⚠️ 防范对手当回合关键解牌与AOE")
        self.posture_badge_lbl.setText("🛡️ 姿态: 均势博弈")
        self.clock_lbl.setText("斩杀时钟: --")
        self.deck_count_badge.setText("30/30")
        self.deck_stats_lbl.setText("剩余 30 张 · 随从 --% · 法术 --%")
        self.hand_count_badge.setText("对战中")
        self.hand_status_lbl.setText("实时手牌追踪中")
        self.secret_frame.hide()
        self.lethal_frame.hide()
        self.coin_frame.hide()
        self.mulligan_frame.hide()
        if hasattr(self, "blunder_frame"):
            self.blunder_frame.hide()
        if hasattr(self, "board_overlay"):
            self.board_overlay.hide()
        if hasattr(self, "_rope_timer"):
            self._rope_timer.stop()
        if hasattr(self, "archetype_classifier"):
            self.archetype_classifier.reset()

    @pyqtSlot(dict)
    def _on_game_over(self, result: dict) -> None:
        won = result.get("won", True)
        res_str = "WIN" if won else "LOSS"
        opp_name = get_class_cn(getattr(self.log_listener, "opponent_hero", "敌方"))
        friendly_name = get_class_cn(self.log_listener.current_hero or "我方")
        self._last_match_review = BlunderDetector.evaluate_match(
            result=res_str,
            friendly_hero=friendly_name,
            opponent_hero=opp_name,
            turn_history=self._turn_history,
        )

        # Voice Debrief Summary
        self.sound_engine.voice_debrief_match(self._last_match_review, won)

        # Update TiltGuard and Export Highlight
        from core.tilt_guard import TiltGuard
        from core.highlight_recorder import HighlightClipRecorder
        TiltGuard.get_instance().record_match_finished(won=won, total_turns=len(self._turn_history))
        if won:
            try:
                out_clip = os.path.expanduser("~/Pictures/Screenshots/arena_victory_highlight.png")
                HighlightClipRecorder.get_instance().export_highlight(
                    output_path=out_clip,
                    event_type="LETHAL_WIN",
                    title="🏆 竞技场胜场高光时刻",
                    subtitle=f"对战【{opp_name}】大获全胜",
                )
            except Exception as ex:
                logger.debug(f"Highlight export suppressed: {ex}")

        if hasattr(self, "board_overlay"):
            self.board_overlay.hide()
        if hasattr(self, "_rope_timer"):
            self._rope_timer.stop()
        if hasattr(self, "archetype_classifier"):
            self.archetype_classifier.reset()

        # Hide combat recommendation frames
        self.mulligan_frame.hide()
        self.coin_frame.hide()
        self.lethal_frame.hide()
        self.secret_frame.hide()
        if hasattr(self, "blunder_frame"):
            self.blunder_frame.hide()
        self.play_actions_frame.hide()
        self.play_trade_frame.hide()
        self.play_risk_frame.hide()
        self.posture_frame.hide()
        if hasattr(self, "intel_container"):
            self.intel_container.hide()

        # Update Play Status Banner for game end
        res_tag = "🏆 胜利 (Victory!)" if won else "💔 惜败 (Defeat)"
        banner_color = "#34d399" if won else "#f87171"
        self.play_turn_lbl.setText(f"🏁 对局结算 - {res_tag}")
        self.play_turn_lbl.setStyleSheet(f"color: {banner_color}; font-size: 13px; font-weight: bold;")
        self.play_opp_lbl.setText(f"对手: {opp_name} | 战局评级: 【{self._last_match_review.match_grade}】")

        # Generate Turn-by-Turn Chess-Style Match Replay
        self._current_replay_summary = TurnReplayerEngine.analyze_replay(
            result=res_str,
            turn_snapshots=self._replay_nodes,
        )
        if hasattr(self, "web_companion"):
            self.web_companion.update_replay(self._current_replay_summary)

        # Generate standalone interactive review dashboard
        try:
            from core.match_review_dashboard import MatchReviewDashboardGenerator
            review_dir = os.path.expanduser("~/Pictures/Screenshots/match_reviews")
            MatchReviewDashboardGenerator.generate_dashboard_html(
                summary=self._current_replay_summary,
                friendly_class=friendly_name,
                opponent_class=opp_name,
                output_dir=review_dir,
            )
        except Exception as e_dash:
            logger.debug(f"Match review dashboard error: {e_dash}")

        # Update and show dedicated Game Over Frame
        self.game_over_title.setText(f"{'🏆 本局大获全胜！' if won else '💔 本局遗憾告负'}")
        self.game_over_title.setStyleSheet(f"color: {banner_color}; font-size: 14px; font-weight: bold;")
        acc_str = f" | 决策精度: {self._current_replay_summary.overall_accuracy_pct}%" if self._current_replay_summary and self._current_replay_summary.total_turns > 0 else ""
        self.game_over_grade_lbl.setText(f"⭐ 战局综合评级: 【{self._last_match_review.match_grade}】{acc_str}")
        self.game_over_turning_lbl.setText(f"🔄 关键转折点: {self._last_match_review.key_turning_point}")
        if self._last_match_review.blunders:
            blunder_summary = "、".join(b.description for b in self._last_match_review.blunders[:2])
            self.game_over_blunder_lbl.setText(f"💡 伏笔提醒: {blunder_summary}")
        else:
            self.game_over_blunder_lbl.setText("💡 伏笔检测: 全程无明显伏笔，决策极佳！")

        # Record persistent match analysis into PersonalWeaknessProfiler
        try:
            import time
            profiler_blunders = []
            if self._last_match_review and self._last_match_review.blunders:
                for b in self._last_match_review.blunders:
                    desc = getattr(b, "description", "")
                    b_type = "MANA_WASTE" if ("费用" in desc or "法力" in desc) else (
                        "MISSED_LETHAL" if "斩杀" in desc else (
                            "AOE_OVEREXTEND" if ("AOE" in desc or "清场" in desc) else "SUBOPTIMAL_ORDER"
                        )
                    )
                    profiler_blunders.append(BlunderEntry(
                        turn=getattr(b, "turn", 1),
                        blunder_type=b_type,
                        description=desc,
                        impact_score=getattr(b, "impact_score", 5),
                    ))
            PersonalWeaknessProfiler.get_instance().record_match_blunders(
                match_id=f"M_{int(time.time())}",
                hero_class=friendly_name,
                opponent_class=opp_name,
                result=res_str,
                total_turns=max(1, len(self._turn_history)),
                blunders=profiler_blunders,
            )
            weakness_diag = PersonalWeaknessProfiler.get_instance().diagnose_weaknesses()
            if weakness_diag.top_blind_spots:
                self.game_over_blunder_lbl.setText(f"{self.game_over_blunder_lbl.text()}\n🧠 个人短板画像: {weakness_diag.top_blind_spots[0]}")
        except Exception as pe:
            logger.warning(f"Failed to record weakness profile: {pe}")

        self.game_over_frame.show()
        self._on_status_updated(f"对局结算: {'胜利' if won else '惜败'} | 战局评级: {self._last_match_review.match_grade}")
        self._turn_history = []
        self.ocr_worker.resume()
        self._last_play_state_key = None
        # Performance: Clean up match memory buffers via GC
        try:
            import gc
            gc.collect()
        except Exception:
            pass

    # ==========================
    # Actions & Dialogs
    # ==========================
    def open_settings(self) -> None:
        dialog = SettingsDialog(self.config_manager, self)
        dialog.settings_saved.connect(self._on_settings_applied)
        dialog.exec_()

    def _on_settings_applied(self, new_cfg: dict) -> None:
        self.setWindowOpacity(new_cfg.get("overlay_opacity", 0.92))
        self.toggle_click_through(new_cfg.get("click_through", False))
        self.ai_engine.update_config(new_cfg.get("gemini_api_key", ""), new_cfg.get("gemini_model", "gemini-1.5-flash"))
        self.log_listener.update_log_dir(new_cfg.get("hearthstone_log_dir", ""))
        self.sound_engine.update_settings(
            sound_enabled=new_cfg.get("sound_enabled", True),
            tts_enabled=new_cfg.get("tts_enabled", False),
            volume=new_cfg.get("sound_volume", 80),
        )
        self._on_status_updated("配置与音效设置已即时更新")

    def show_last_match_review(self) -> None:
        """Displays dialog with detailed match analysis and blunder detection."""
        if not self._last_match_review:
            # Generate sample review if none recorded yet
            sample_snap = [
                TurnSnapshot(turn_number=1, mana_available=1, friendly_hp=30, enemy_hp=30),
                TurnSnapshot(turn_number=2, mana_available=2, friendly_hp=30, enemy_hp=28),
                TurnSnapshot(turn_number=3, mana_available=3, friendly_hp=30, enemy_hp=24),
            ]
            self._last_match_review = BlunderDetector.evaluate_match(
                result="WIN",
                friendly_hero="法师",
                opponent_hero="猎人",
                turn_history=sample_snap,
            )

        clean_report = self._last_match_review.markdown_summary.replace("### ", "").replace("#### ", "")
        QMessageBox.information(
            self,
            "📝 战局复盘战报与伏笔检测",
            clean_report,
        )

    def toggle_turn_replayer(self) -> None:
        """Toggles visibility of the Step-by-Step Chess-Style Replayer."""
        if hasattr(self, "turn_replayer_frame") and self.turn_replayer_frame.isVisible():
            self.hide_turn_replayer()
        else:
            self.show_turn_replayer()

    def show_turn_replayer(self) -> None:
        """Opens the Turn-by-Turn Replayer & Decision Accuracy Analyzer."""
        if not self._current_replay_summary or not self._current_replay_summary.turn_nodes:
            if self._replay_nodes:
                self._current_replay_summary = TurnReplayerEngine.analyze_replay(
                    result="WIN",
                    turn_snapshots=self._replay_nodes,
                )
            else:
                self._current_replay_summary = TurnReplayerEngine.generate_sample_replay()
                self._on_status_updated("🔍 演示模式：已加载示例步步复盘分析 (按 Ctrl+R 切换)")

        if hasattr(self, "game_over_frame"):
            self.game_over_frame.hide()
        if hasattr(self, "mulligan_frame"):
            self.mulligan_frame.hide()
        if hasattr(self, "coin_frame"):
            self.coin_frame.hide()
        if hasattr(self, "lethal_frame"):
            self.lethal_frame.hide()
        if hasattr(self, "secret_frame"):
            self.secret_frame.hide()
        if hasattr(self, "blunder_frame"):
            self.blunder_frame.hide()
        self.play_actions_frame.hide()
        self.play_trade_frame.hide()
        self.play_risk_frame.hide()
        self.posture_frame.hide()
        if hasattr(self, "intel_container"):
            self.intel_container.hide()

        self.draft_container.hide()
        self.play_container.show()
        self.turn_replayer_frame.show()

        # Jump to key turning point or first turn
        key_idx = 0
        if self._current_replay_summary and self._current_replay_summary.key_turning_turn > 1:
            for i, n in enumerate(self._current_replay_summary.turn_nodes):
                if n.turn_number == self._current_replay_summary.key_turning_turn:
                    key_idx = i
                    break
        self._current_replay_index = key_idx
        self._rebuild_replayer_turn_buttons()
        self._render_current_replay_turn()
        self._on_status_updated("🔍 已开启步步复盘分析器")

    def hide_turn_replayer(self) -> None:
        """Hides the Replayer and returns to Game Over or combat state."""
        if hasattr(self, "turn_replayer_frame"):
            self.turn_replayer_frame.hide()
        if hasattr(self, "game_over_frame") and getattr(self, "_last_match_review", None):
            self.game_over_frame.show()
        else:
            self.play_actions_frame.show()
            self.play_trade_frame.show()
            self.play_risk_frame.show()
            self.posture_frame.show()
            if hasattr(self, "intel_container"):
                self.intel_container.show()

    def _rebuild_replayer_turn_buttons(self) -> None:
        """Populates the turn jump button strip matching Chess move tabs."""
        if not hasattr(self, "replayer_turns_layout"):
            return
        while self.replayer_turns_layout.count() > 0:
            child = self.replayer_turns_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not self._current_replay_summary or not self._current_replay_summary.turn_nodes:
            return

        for idx, node in enumerate(self._current_replay_summary.turn_nodes):
            t_btn = QPushButton(f"T{node.turn_number}", self)
            is_cur = (idx == self._current_replay_index)
            border_style = "2px solid #facc15" if is_cur else f"1px solid {node.grade_color}"
            t_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {node.grade_color}22;
                    color: {node.grade_color};
                    font-size: 10px;
                    font-weight: bold;
                    padding: 2px 4px;
                    border-radius: 4px;
                    border: {border_style};
                    min-width: 26px;
                }}
                QPushButton:hover {{
                    background: {node.grade_color}55;
                }}
            """)
            t_btn.clicked.connect(lambda checked, i=idx: self._replayer_jump_to_turn(i))
            self.replayer_turns_layout.addWidget(t_btn)

    def _render_current_replay_turn(self) -> None:
        """Renders the snapshot of the selected turn."""
        summary = self._current_replay_summary
        if not summary or not summary.turn_nodes:
            return

        idx = max(0, min(len(summary.turn_nodes) - 1, self._current_replay_index))
        node = summary.turn_nodes[idx]

        self.replayer_accuracy_lbl.setText(f"精度: {summary.overall_accuracy_pct}% 【{summary.grade_tier}】")
        self.replayer_badges_lbl.setText(
            f"★ 妙手: {summary.brilliant_count} | ✅ 最佳: {summary.best_count} | ⚖️ 良好: {summary.good_count} | ⚠️ 疑问: {summary.inaccuracy_count} | ❌ 伏笔: {summary.blunder_count}"
        )

        self.replayer_turn_lbl.setText(f"第 {node.turn_number} / {summary.total_turns} 回合")
        self.replayer_grade_badge.setText(node.action_grade)
        self.replayer_grade_badge.setStyleSheet(f"color: {node.grade_color}; font-size: 12px; font-weight: bold;")
        self.replayer_score_lbl.setText(f"决策评分: {node.score}分")

        self.replayer_state_lbl.setText(
            f"💎 可用法力: {node.mana}/{node.max_mana} | ❤️ 我方: {node.friendly_hp} vs 敌方: {node.enemy_hp} | 胜率: {node.ai_winrate}%"
        )
        self.replayer_diag_lbl.setText(f"💡 决策诊断: {node.analysis_comment}")

        ai_seq = " ➔ ".join(node.ai_best_plan) if node.ai_best_plan else "空过/维持场面"
        self.replayer_ai_line_lbl.setText(f"🤖 AI最优线: {ai_seq}")

        player_seq = "、".join(node.player_actual_plays) if node.player_actual_plays else "无实战记录/空过"
        self.replayer_player_line_lbl.setText(f"👤 玩家实战: {player_seq}")

        # Update button highlight borders
        for i in range(self.replayer_turns_layout.count()):
            item = self.replayer_turns_layout.itemAt(i)
            if item and item.widget():
                w = item.widget()
                n = summary.turn_nodes[i]
                is_cur = (i == idx)
                border_style = "2px solid #facc15" if is_cur else f"1px solid {n.grade_color}"
                w.setStyleSheet(f"""
                    QPushButton {{
                        background: {n.grade_color}22;
                        color: {n.grade_color};
                        font-size: 10px;
                        font-weight: bold;
                        padding: 2px 4px;
                        border-radius: 4px;
                        border: {border_style};
                        min-width: 26px;
                    }}
                    QPushButton:hover {{
                        background: {n.grade_color}55;
                    }}
                """)

    def _replayer_prev_turn(self) -> None:
        if not self._current_replay_summary or not self._current_replay_summary.turn_nodes:
            return
        if self._current_replay_index > 0:
            self._current_replay_index -= 1
            self._render_current_replay_turn()

    def _replayer_next_turn(self) -> None:
        if not self._current_replay_summary or not self._current_replay_summary.turn_nodes:
            return
        if self._current_replay_index < len(self._current_replay_summary.turn_nodes) - 1:
            self._current_replay_index += 1
            self._render_current_replay_turn()

    def _replayer_jump_to_turn(self, idx: int) -> None:
        self._current_replay_index = idx
        self._render_current_replay_turn()

    def _replayer_jump_key_turn(self) -> None:
        if not self._current_replay_summary or not self._current_replay_summary.turn_nodes:
            return
        kt = self._current_replay_summary.key_turning_turn
        for i, n in enumerate(self._current_replay_summary.turn_nodes):
            if n.turn_number == kt:
                self._current_replay_index = i
                self._render_current_replay_turn()
                break

    def simulate_sample_replay(self) -> None:
        """Simulates and opens the Chess-Style Turn Replayer with sample match data."""
        self._current_replay_summary = TurnReplayerEngine.generate_sample_replay()
        if hasattr(self, "web_companion"):
            self.web_companion.update_replay(self._current_replay_summary)
        self.show_turn_replayer()
        self._on_status_updated("🧪 模拟步步复盘分析已加载，展示全部5级操作精度评级")

    def sync_hsreplay_data(self) -> None:
        """Triggers cloud HSReplay arena win-rate data synchronization."""
        self._on_status_updated("🌐 正在同步 HSReplay 竞技场大数据胜率...")
        def _cb(success: bool, msg: str):
            if success:
                self.sig_status_update.emit(f"✅ {msg}")
            else:
                self.sig_status_update.emit(f"⚠️ HSReplay 同步超时: {msg}")

        HsreplaySync.get_instance().trigger_async_sync(_cb)

    def check_app_updates(self) -> None:
        """Manually checks for application and card database updates."""
        self._on_status_updated("🔄 正在检查最新版本与补丁数据...")
        def _cb(info: UpdateInfo):
            if info.has_update:
                self.sig_status_update.emit(f"📢 发现新版本 {info.latest_version}！")
                QMessageBox.information(self, "版本更新", f"发现新版本: {info.latest_version}\n更新日志:\n{info.changelog}")
            else:
                self.sig_status_update.emit(f"✅ 当前已是最新版本 ({info.current_version})")
                QMessageBox.information(self, "版本检查", f"当前已是最新版本: {info.current_version}\n已适配最新炉石卡牌补丁！")

        UpdateChecker.check_for_updates(_cb)

    def update_card_database(self) -> None:
        """Triggers online card update in background without blocking UI."""
        self._on_status_updated("🌐 正在从官方源同步最新版本卡牌数据...")
        import threading
        def _worker():
            try:
                raw = self.card_db._download_cards()
                if raw:
                    self.card_db._build_indexes(raw)
                    self.card_db._save_binary_cache()
                    self.sig_status_update.emit(f"✅ 卡牌库已同步至最新补丁 (共 {len(self.card_db.cards_by_id)} 张卡牌)")
                else:
                    self.sig_status_update.emit("⚠️ 卡牌下载超时，继续使用本地离线完整卡库 (36,390张)")
            except Exception as e:
                self.sig_status_update.emit(f"卡牌更新异常: {e}")

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def _switch_to_draft_view(self) -> None:
        """Transitions UI display into Draft Mode with adaptive height adjustment."""
        self.play_container.hide()
        if not self.is_compact_mode:
            self.draft_container.show()
            if self.height() < 660:
                self.resize(self.width(), 700)
        self.ocr_worker.resume()
        self.mode_badge.setText("选牌模式")
        if hasattr(self, "compact_mode_pill"):
            self.compact_mode_pill.setText("选牌")
        self.mode_badge.setStyleSheet("""
            QPushButton {
                background: rgba(180, 83, 9, 0.35);
                color: #fde68a;
                font-size: 11px;
                font-weight: bold;
                padding: 2px 7px;
                border-radius: 4px;
                border: 1px solid rgba(245, 158, 11, 0.55);
            }
            QPushButton:hover {
                background: rgba(217, 119, 6, 0.55);
                color: #ffffff;
                border-color: #fbbf24;
            }
        """)

    def _switch_to_play_view(self) -> None:
        """Transitions UI display into Play Mode with adaptive height adjustment."""
        self.draft_container.hide()
        if not self.is_compact_mode:
            self.play_container.show()
            if self.height() >= 660:
                self.resize(self.width(), 520)
        self.ocr_worker.pause()
        self.mode_badge.setText("实战模式")
        if hasattr(self, "compact_mode_pill"):
            self.compact_mode_pill.setText("实战")
        self.mode_badge.setStyleSheet("""
            QPushButton {
                background: #047857;
                color: #a7f3d0;
                font-size: 11px;
                font-weight: bold;
                padding: 2px 6px;
                border-radius: 4px;
                border: 1px solid #10b981;
            }
            QPushButton:hover {
                background: #059669;
                color: #ffffff;
            }
        """)

    def toggle_mode(self) -> None:
        """Toggles active UI view between Draft Mode and Play Mode."""
        is_in_play = self.play_container.isVisible() or "实战" in self.mode_badge.text() or "起手" in self.mode_badge.text()
        if is_in_play:
            self._switch_to_draft_view()
            self._on_status_updated("已切换到选牌模式")
        else:
            self._switch_to_play_view()
            self._on_status_updated("已切换到实战模式")

    def show_hero_advisor_dialog(self) -> None:
        """Modal dialog displaying Arena Hero Meta Tier List and 1-out-of-3 picker."""
        dialog = QDialog(self)
        dialog.setWindowTitle("👑 竞技场开局英雄三选一评级推荐")
        dialog.resize(540, 620)
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #141416;
                color: #f5f5f4;
                font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
            }
            QLabel {
                color: #e7e5e4;
            }
            QComboBox {
                background-color: #1c1917;
                border: 1px solid rgba(245, 158, 11, 0.4);
                border-radius: 6px;
                color: #fef3c7;
                padding: 4px 8px;
                min-height: 28px;
                font-size: 12px;
            }
            QPushButton {
                background-color: #b45309;
                color: #fef3c7;
                font-weight: bold;
                border: 1px solid #f59e0b;
                border-radius: 6px;
                padding: 6px 12px;
                min-height: 32px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #d97706;
                color: #ffffff;
            }
        """)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(10)
        layout.setContentsMargins(14, 14, 14, 14)

        title = QLabel("👑 竞技场开局英雄三选一评估", dialog)
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #fbbf24;")
        layout.addWidget(title)

        detected = getattr(self, "_last_detected_heroes", [])
        if len(detected) < 2:
            try:
                rect = self.window_finder.find_window()
                if rect:
                    frame = self.window_finder.grab_window_image(rect)
                    if frame is not None and frame.size > 0:
                        from core.ocr_engine import classify_hero_banner
                        fh, fw = frame.shape[:2]
                        hero_boxes = [
                            (int(fw * 0.18), int(fh * 0.405), int(fw * 0.10), int(fh * 0.05)),
                            (int(fw * 0.355), int(fh * 0.405), int(fw * 0.10), int(fh * 0.05)),
                            (int(fw * 0.53), int(fh * 0.405), int(fw * 0.10), int(fh * 0.05)),
                        ]
                        scanned = [classify_hero_banner(frame[y:y+rh, x:x+rw]) for x, y, rw, rh in hero_boxes]
                        valid = [h for h in scanned if h]
                        if len(valid) >= 2:
                            self._last_detected_heroes = valid
                            detected = valid
            except Exception as e:
                logger.debug(f"Direct scan on hero dialog open: {e}")

        if len(detected) >= 2:
            tip_text = f"✨ AI 已自动识别到候选英雄: {' / '.join(detected)} (可直接评估或手动微调)："
            tip_style = "color: #fbbf24; font-size: 11px; font-weight: bold;"
        else:
            tip_text = "请确认您当前开局出现的 3 位候选英雄，AI 将立即计算天梯胜率梯队与抓牌策略："
            tip_style = "color: #a8a29e; font-size: 11px;"

        tip = QLabel(tip_text, dialog)
        tip.setStyleSheet(tip_style)
        tip.setWordWrap(True)
        layout.addWidget(tip)

        hero_options = [
            "死亡骑士",
            "恶魔猎手",
            "法师",
            "德鲁伊",
            "猎人",
            "圣骑士",
            "潜行者",
            "萨满祭司",
            "术士",
            "牧师",
            "战士",
        ]

        row = QHBoxLayout()
        combos = []
        for i in range(3):
            col = QVBoxLayout()
            lbl = QLabel(f"候选英雄 {i+1}:", dialog)
            lbl.setStyleSheet("font-weight: bold; color: #fbbf24; font-size: 11px;")
            cb = QComboBox(dialog)
            cb.addItems(hero_options)
            # Pre-select detected hero if available
            if len(detected) > i and detected[i] in hero_options:
                cb.setCurrentText(detected[i])
            else:
                cb.setCurrentIndex(i)
            combos.append(cb)
            col.addWidget(lbl)
            col.addWidget(cb)
            row.addLayout(col)
        layout.addLayout(row)

        btn_row = QHBoxLayout()
        eval_btn = QPushButton("🎯 立即在主界面展示评估结果", dialog)
        def on_eval():
            try:
                selected = [c.currentText() for c in combos]
                dialog.accept()
                QTimer.singleShot(50, lambda s=selected: self._on_heroes_detected(s, force=True))
            except Exception as e:
                logger.error(f"Error evaluating heroes: {e}", exc_info=True)
                dialog.accept()
        eval_btn.clicked.connect(on_eval)
        btn_row.addWidget(eval_btn)

        close_btn = QPushButton("✖ 关闭", dialog)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(41, 37, 36, 0.85);
                color: #d6d3d1;
                border: 1px solid rgba(120, 113, 108, 0.45);
                font-weight: normal;
            }
            QPushButton:hover {
                background-color: rgba(68, 64, 60, 0.95);
                color: #fbbf24;
                border-color: #fbbf24;
            }
        """)
        close_btn.clicked.connect(dialog.reject)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        # Meta Tier List summary
        tier_title = QLabel("📊 当前版本竞技场全职业天梯榜单 (Tier List)", dialog)
        tier_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #fbbf24; margin-top: 8px;")
        layout.addWidget(tier_title)

        scroll = QScrollArea(dialog)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 8px;")

        tier_widget = QWidget()
        tier_layout = QVBoxLayout(tier_widget)
        tier_layout.setSpacing(6)

        sorted_heroes = sorted(ARENA_HERO_TIERS.values(), key=lambda d: d["power_rating"], reverse=True)
        for h in sorted_heroes:
            card = QFrame()
            card.setStyleSheet("background: #1e293b; border-radius: 6px; padding: 6px;")
            c_lay = QVBoxLayout(card)
            c_lay.setContentsMargins(6, 4, 6, 4)
            c_lay.setSpacing(2)

            top_line = QHBoxLayout()
            h_lbl = QLabel(f"【{h['class_cn']}】  {h['tier']}  胜率: {h['winrate']}%")
            h_lbl.setStyleSheet("font-weight: bold; color: #f8fafc; font-size: 12px;")
            top_line.addWidget(h_lbl)
            top_line.addStretch()
            c_lay.addLayout(top_line)

            p_lbl = QLabel(f"技能: {h['hero_power_rating']}")
            p_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
            c_lay.addWidget(p_lbl)

            a_lbl = QLabel(f"建议: {h['draft_priority_advice']}")
            a_lbl.setStyleSheet("color: #cbd5e1; font-size: 11px;")
            a_lbl.setWordWrap(True)
            c_lay.addWidget(a_lbl)

            tier_layout.addWidget(card)

        scroll.setWidget(tier_widget)
        layout.addWidget(scroll)

        dialog.exec_()

    def show_manual_draft_dialog(self) -> None:
        """Allows manual input of 3 candidate cards for comprehensive tier comparison."""
        dialog = QDialog(self)
        dialog.setWindowTitle("🃏 竞技场候选卡牌三选一评估")
        dialog.setFixedWidth(360)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #141416;
                border: 1px solid rgba(245, 158, 11, 0.45);
                border-radius: 8px;
            }
            QLabel { color: #f5f5f4; font-size: 12px; }
            QLineEdit {
                background-color: #1c1917;
                color: #fef3c7;
                border: 1px solid rgba(245, 158, 11, 0.4);
                border-radius: 4px;
                padding: 6px;
                font-size: 12px;
            }
            QLineEdit:focus { border: 1px solid #fbbf24; }
            QPushButton {
                background-color: #b45309;
                color: #fef3c7;
                font-weight: bold;
                border: 1px solid #f59e0b;
                border-radius: 4px;
                padding: 6px 14px;
            }
            QPushButton:hover { background-color: #d97706; color: #ffffff; }
        """)
        layout = QVBoxLayout(dialog)
        layout.setSpacing(10)
        layout.setContentsMargins(14, 14, 14, 14)

        title = QLabel("🃏 竞技场卡牌三选一评估", dialog)
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #fbbf24;")
        layout.addWidget(title)

        deck_now = self.log_listener.current_deck
        deck_preview = "、".join(c.name for c in deck_now[:6]) + ("..." if len(deck_now) > 6 else "")
        deck_info_text = (
            f"📦 已关联当前套牌 ({len(deck_now)}/30 张): {deck_preview}"
            if deck_now
            else "📦 当前套牌: 0/30 张 (自动扫描右侧套牌列表中)"
        )
        deck_lbl = QLabel(deck_info_text, dialog)
        deck_lbl.setStyleSheet("color: #34d399; font-size: 11px; font-weight: bold;")
        deck_lbl.setWordWrap(True)
        layout.addWidget(deck_lbl)

        tip = QLabel("请输入或确认当前轮次的 3 张候选卡牌名称（支持拼音/模糊匹配）：", dialog)
        tip.setStyleSheet("color: #a8a29e; font-size: 11px;")
        tip.setWordWrap(True)
        layout.addWidget(tip)

        default_names = ["", "", ""]
        slot_mem = getattr(self.ocr_worker, "_slot_memory", [None, None, None])
        if isinstance(slot_mem, list) and any(c is not None for c in slot_mem):
            for i in range(min(3, len(slot_mem))):
                if slot_mem[i] is not None:
                    default_names[i] = slot_mem[i].name
        elif hasattr(self, "_current_round_candidates") and self._current_round_candidates:
            for i in range(min(3, len(self._current_round_candidates))):
                if self._current_round_candidates[i] is not None:
                    default_names[i] = self._current_round_candidates[i].name
        if not any(default_names):
            default_names = ["食人魔帮骑手", "邪恶荒裔怪", "白骨堆"]

        inputs = []
        for i in range(3):
            col = QVBoxLayout()
            lbl = QLabel(f"候选卡牌 {i+1}:", dialog)
            lbl.setStyleSheet("font-weight: bold; color: #fbbf24; font-size: 11px;")
            line_edit = QLineEdit(dialog)
            line_edit.setText(default_names[i])
            line_edit.setPlaceholderText("输入或确认卡牌名称")
            inputs.append(line_edit)
            col.addWidget(lbl)
            col.addWidget(line_edit)
            layout.addLayout(col)

        btn_row = QHBoxLayout()
        eval_btn = QPushButton("🎯 立即对比打分", dialog)
        def on_eval():
            try:
                candidates = []
                for edit in inputs:
                    txt = edit.text().strip()
                    if txt:
                        c = self.card_db.fuzzy_match_card(txt)
                        if c:
                            candidates.append(c)
                dialog.accept()
                if len(candidates) == 3:
                    QTimer.singleShot(50, lambda c=candidates: self._on_draft_candidates_received(c))
                elif len(candidates) > 0:
                    first_c = candidates[0]
                    while len(candidates) < 3:
                        candidates.append(first_c)
                    QTimer.singleShot(50, lambda c=candidates: self._on_draft_candidates_received(c))
            except Exception as e:
                logger.error(f"Error evaluating manual draft cards: {e}", exc_info=True)
                dialog.accept()

        eval_btn.clicked.connect(on_eval)
        btn_row.addWidget(eval_btn)

        close_btn = QPushButton("✖ 关闭", dialog)
        close_btn.setStyleSheet("background-color: rgba(41, 37, 36, 0.85); color: #d6d3d1; border: 1px solid rgba(120, 113, 108, 0.45);")
        close_btn.clicked.connect(dialog.reject)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        dialog.exec_()

    def simulate_sample_draft(self) -> None:
        """Injects 3 sample arena cards for visual verification and testing."""
        self._switch_to_draft_view()
        sample_ids = ["CS2_188", "CORE_CS2_039", "CS2_222"]  # 叫嚣的矮人, 风暴战斧, 暴风城勇士
        cards = [self.card_db.get_by_id(cid) for cid in sample_ids]
        valid_cards = [c for c in cards if c]
        if len(valid_cards) == 3:
            self._on_draft_candidates_received(valid_cards)

    def _init_shortcuts(self) -> None:
        """Configures global in-app keyboard shortcuts."""
        self.sc_toggle_vis = QShortcut(QKeySequence("Ctrl+F1"), self)
        self.sc_toggle_vis.activated.connect(self._toggle_visibility)

        self.sc_click_through = QShortcut(QKeySequence("Ctrl+F2"), self)
        self.sc_click_through.activated.connect(self.toggle_click_through)

        self.sc_sim_draft = QShortcut(QKeySequence("Ctrl+F3"), self)
        self.sc_sim_draft.activated.connect(self.simulate_sample_draft)

        self.sc_sim_play = QShortcut(QKeySequence("Ctrl+F4"), self)
        self.sc_sim_play.activated.connect(self.simulate_sample_play)

        self.sc_dock = QShortcut(QKeySequence("Ctrl+F5"), self)
        self.sc_dock.activated.connect(self.dock_to_game_window)

        self.sc_theme = QShortcut(QKeySequence("Ctrl+F6"), self)
        self.sc_theme.activated.connect(self.cycle_theme)

        self.sc_mulligan = QShortcut(QKeySequence("Ctrl+F7"), self)
        self.sc_mulligan.activated.connect(self.simulate_sample_mulligan)

        self.sc_hero = QShortcut(QKeySequence("Ctrl+H"), self)
        self.sc_hero.activated.connect(self.show_hero_advisor_dialog)

        # Convenient Alt shortcuts for single-hand triggers
        self.sc_alt_d = QShortcut(QKeySequence("Alt+D"), self)
        self.sc_alt_d.activated.connect(self._toggle_visibility)

        self.sc_alt_h = QShortcut(QKeySequence("Alt+H"), self)
        self.sc_alt_h.activated.connect(self.show_hero_advisor_dialog)

        self.sc_alt_c = QShortcut(QKeySequence("Alt+C"), self)
        self.sc_alt_c.activated.connect(self.show_manual_draft_dialog)

        self.sc_alt_q = QShortcut(QKeySequence("Alt+Q"), self)
        self.sc_alt_q.activated.connect(self.hide)

        self.sc_alt_s = QShortcut(QKeySequence("Alt+S"), self)
        self.sc_alt_s.activated.connect(self.trigger_reevaluate)

        self.sc_alt_a = QShortcut(QKeySequence("Alt+A"), self)
        self.sc_alt_a.activated.connect(self.toggle_auto_dock)

        self.sc_compact = QShortcut(QKeySequence("Alt+M"), self)
        self.sc_compact.activated.connect(self.toggle_compact_mode)

        self.sc_compact_f9 = QShortcut(QKeySequence("F9"), self)
        self.sc_compact_f9.activated.connect(self.toggle_compact_mode)

        self.sc_wide = QShortcut(QKeySequence("Alt+W"), self)
        self.sc_wide.activated.connect(self.toggle_wide_mode)

        self.sc_rope = QShortcut(QKeySequence("Alt+R"), self)
        self.sc_rope.activated.connect(self.toggle_rope_mode)

    def _on_hotkey_toggle_overlay(self) -> None:
        """Windows global hotkey: Ctrl+Shift+H."""
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()

    def _on_hotkey_toggle_tree(self) -> None:
        """Windows global hotkey: Ctrl+Shift+T."""
        if hasattr(self, "show_tactical_tree_dialog"):
            self.show_tactical_tree_dialog()

    def _on_hotkey_snapshot(self) -> None:
        """Windows global hotkey: Ctrl+Shift+S."""
        self._on_status_updated("已捕获对局战况分析快照")

    def _toggle_visibility_remote(self) -> bool:
        """Remote command handler: toggle overlay visibility safely via Qt event loop."""
        QTimer.singleShot(0, self._toggle_visibility)
        return True

    def _toggle_capsule_remote(self) -> bool:
        """Remote command handler: toggle capsule/full mode safely via Qt event loop."""
        QTimer.singleShot(0, self.toggle_compact_mode)
        return True

    def _trigger_reevaluate_remote(self) -> bool:
        """Remote command handler: trigger AI re-evaluation safely via Qt event loop."""
        QTimer.singleShot(0, self.trigger_reevaluate)
        return True

        self.sc_board = QShortcut(QKeySequence("Alt+V"), self)
        self.sc_board.activated.connect(self.toggle_board_hud)

        self.sc_replay = QShortcut(QKeySequence("Ctrl+R"), self)
        self.sc_replay.activated.connect(self.toggle_turn_replayer)

        self.sc_infographic = QShortcut(QKeySequence("Alt+P"), self)
        self.sc_infographic.activated.connect(self.export_12_win_infographic)

        self.sc_emergency_reboot = QShortcut(QKeySequence("Alt+F12"), self)
        self.sc_emergency_reboot.activated.connect(self.trigger_rope_emergency_reboot)

        self.sc_lens = QShortcut(QKeySequence("Alt+Z"), self)
        self.sc_lens.activated.connect(self._trigger_instant_lens)

    def _trigger_instant_lens(self) -> None:
        """Alt+Z: triggers instant card lens inquiry."""
        lens = InstantCardLens.inspect("烈焰风暴")
        self._on_status_updated(f"AI透镜: {lens.card_name} ({lens.danger_tier}威胁)")

    def _on_voice_command(self, cmd_key: str, raw_text: str) -> None:
        """Handles hands-free voice commands."""
        logger.info(f"Voice Command recognized: {cmd_key} ('{raw_text}')")
        if cmd_key == "PLAN_A":
            self._switch_plan_view("A")
            self.sound_engine.notify_tactical_callout("已切换方案A")
        elif cmd_key == "PLAN_B":
            self._switch_plan_view("B")
            self.sound_engine.notify_tactical_callout("已切换方案B")
        elif cmd_key == "CHECK_STEP":
            self._toggle_next_checklist_step()
        elif cmd_key == "CHECK_LETHAL":
            if getattr(self, "_last_lethal_res", None) and self._last_lethal_res.has_lethal:
                self.sound_engine.notify_tactical_callout(f"当回合可斩杀，伤害{self._last_lethal_res.max_damage}点")
            else:
                self.sound_engine.notify_tactical_callout("当前暂无当回合斩杀线")
        elif cmd_key == "CHECK_AOE":
            if hasattr(self, "_current_rec") and getattr(self._current_rec, "next_turn_threat_cards", []):
                t_names = "、".join(c["name"] for c in self._current_rec.next_turn_threat_cards[:2])
                self.sound_engine.notify_tactical_callout(f"注意防范{t_names}")
            else:
                self.sound_engine.notify_tactical_callout("暂无致命全清威胁")
        elif cmd_key == "RESET":
            self._completed_step_indices.clear()
            self._render_tactical_plan_checklist()

    def _toggle_next_checklist_step(self) -> None:
        """Toggles the first unchecked step in active plan."""
        steps = getattr(self, "_current_active_steps", [])
        if not steps:
            return
        for i in range(len(steps)):
            if i not in self._completed_step_indices:
                self._completed_step_indices.add(i)
                self.sound_engine.notify_action_step_completed(steps[i])
                self._render_tactical_plan_checklist()
                WebCompanionServer.update_state({"checked_steps": sorted(list(self._completed_step_indices))})
                break

    def export_12_win_infographic(self) -> bool:
        """Exports high-resolution 12-win infographic poster."""
        hero = self.log_listener.current_hero or "法师"
        deck = self.log_listener.current_deck
        out_path = r"C:\Users\sageb\Pictures\Screenshots\12_win_championship_infographic.png"
        ok = ChampionshipDnaExporter.export_victory_infographic(
            output_path=out_path,
            deck=deck,
            hero_class=hero,
            wins=12,
            losses=1,
        )
        if ok:
            self._on_status_updated("👑 12胜战报海报已成功保存至截图目录！")
            self.sound_engine.notify_tactical_callout("战报海报导出成功")
        else:
            self._on_status_updated("⚠️ 战报导出失败，请检查卡组与绘图环境")
        return ok

    def trigger_rope_emergency_reboot(self) -> bool:
        """Triggers emergency client reboot to skip long animation queues."""
        ok = RebootMacro.execute_rope_emergency_reboot()
        if ok:
            self._on_status_updated("🚀 烧绳急救: 已秒级重启客户端跳过长动画！")
            self.sound_engine.notify_tactical_callout("烧绳急救重启中")
        return ok

    def toggle_auto_dock(self) -> None:
        """Toggles continuous tracking and docking to Hearthstone window."""
        self.auto_dock_enabled = not getattr(self, "auto_dock_enabled", False)
        if self.auto_dock_enabled:
            self._dock_timer.start(2000)
            self.dock_to_game_window()
            self._on_status_updated("🧲 自动吸附跟随已开启 (Alt+A)")
        else:
            self._dock_timer.stop()
            self._on_status_updated("🧲 自动吸附已关闭")

    def _calculate_dock_position(self, win_rect) -> tuple:
        screen = QApplication.primaryScreen()
        screen_geo = screen.availableGeometry() if screen else None
        dpr = screen.devicePixelRatio() if screen else 1.0

        screen_left = screen_geo.left() if screen_geo else 0
        screen_right = screen_geo.right() if screen_geo else 1920
        screen_top = screen_geo.top() if screen_geo else 0
        screen_bottom = screen_geo.bottom() if screen_geo else 1080

        overlay_w = self.width()
        overlay_h = self.height()

        # Convert win_rect physical pixels to Qt logical coordinates
        game_left = int(win_rect.left / dpr)
        game_top = int(win_rect.top / dpr)
        game_width = int(win_rect.width / dpr)
        game_height = int(win_rect.height / dpr)
        game_right = game_left + game_width

        # If there is ample space outside the right border of Hearthstone on the screen:
        if screen_geo and (game_right + overlay_w + 10 <= screen_right):
            target_x = game_right + 4
        else:
            # Hearthstone is fullscreen or occupies full width:
            # Dock inside the far-right border of Hearthstone (side margin, completely clear of central cards)
            target_x = max(screen_left + 10, min(screen_right - overlay_w - 12, game_right - overlay_w - 12))

        target_y = max(screen_top + 10, min(game_top + 40, screen_bottom - overlay_h - 10))

        # Absolute safety clamp: NEVER allow target_x or target_y to go outside visible screen
        target_x = max(screen_left + 10, min(target_x, screen_right - overlay_w - 10))
        target_y = max(screen_top + 10, min(target_y, screen_bottom - overlay_h - 10))

        return target_x, target_y

    def _initial_dock_check(self) -> None:
        """Silently dock to game window on startup if game is running and overlay is covering board."""
        try:
            win_rect = self.window_finder.find_window()
            if win_rect and win_rect.width > 0:
                screen = QApplication.primaryScreen()
                dpr = screen.devicePixelRatio() if screen else 1.0
                game_center = int((win_rect.left + win_rect.width // 2) / dpr)
                overlay_center = self.x() + self.width() // 2
                game_width_logical = int(win_rect.width / dpr)
                if self.auto_dock_enabled or abs(overlay_center - game_center) < (game_width_logical * 0.35):
                    target_x, target_y = self._calculate_dock_position(win_rect)
                    self.move(target_x, target_y)
        except Exception as e:
            logger.debug(f"Initial dock check skipped: {e}")

    def _auto_dock_tick(self) -> None:
        if not getattr(self, "auto_dock_enabled", False) or not self.isVisible():
            return
        win_rect = self.window_finder.find_window()
        if win_rect and win_rect.width > 0:
            target_x, target_y = self._calculate_dock_position(win_rect)
            if abs(self.x() - target_x) > 10 or abs(self.y() - target_y) > 10:
                self.move(target_x, target_y)

    def _on_desktop_guard_tick(self) -> None:
        """
        Monitors active virtual desktop and minimizes/restores overlay accordingly.
        Prevents overlay from bleeding into unrelated virtual desktops (e.g. work/code/browser).
        """
        if not getattr(self, "config_manager", None) or not self.config_manager.get("follow_game_desktop", True):
            return
        game_on_active = self.window_finder.is_game_on_active_desktop()
        if not game_on_active:
            # Game is minimized or on another virtual desktop -> hide overlay
            if self.isVisible() and not self._hidden_by_desktop_guard:
                self._hidden_by_desktop_guard = True
                self.hide()
                if hasattr(self, "board_overlay") and self.board_overlay.isVisible():
                    self.board_overlay.hide()
        else:
            # Game is visible on current active desktop -> restore overlay if we hid it
            if self._hidden_by_desktop_guard:
                self._hidden_by_desktop_guard = False
                self.show()
                if getattr(self, "auto_dock_enabled", False):
                    win_rect = self.window_finder.find_window()
                    if win_rect and win_rect.width > 0:
                        tx, ty = self._calculate_dock_position(win_rect)
                        self.move(tx, ty)

    def _toggle_follow_desktop(self) -> None:
        val = self.follow_desktop_action.isChecked()
        self.config_manager.set("follow_game_desktop", val)
        if not val and self._hidden_by_desktop_guard:
            self._hidden_by_desktop_guard = False
            self.show()
        tip = "已开启：仅在炉石所在虚拟桌面显示（切到其他桌面或最小化自动隐藏）" if val else "已关闭：在所有虚拟桌面穿透显示"
        self._on_status_updated(tip)

    def trigger_reevaluate(self) -> None:
        """Forces re-evaluation of current game state."""
        if self.ai_engine.mode == AssistantMode.DRAFT:
            self.simulate_sample_draft()
        else:
            self.simulate_sample_play()

    def dock_to_game_window(self) -> None:
        """Finds the Hearthstone window and docks the overlay cleanly to its right edge."""
        win_rect = self.window_finder.find_window()
        if not win_rect or win_rect.width <= 0:
            self._on_status_updated("未检测到炉石游戏窗口 (请先启动游戏)")
            return

        target_x, target_y = self._calculate_dock_position(win_rect)
        self.move(target_x, target_y)
        self.config_manager.set("overlay_x", target_x, auto_save=False)
        self.config_manager.set("overlay_y", target_y, auto_save=True)
        self._on_status_updated(f"🧲 已智能吸附至炉石右侧边栏 ({target_x}, {target_y})")

    def simulate_sample_play(self) -> None:
        """
        Simulates an active in-game turn scenario demonstrating:
        1. Tactical card plays & minion trading
        2. Lethal calculator burst damage detection
        3. Opponent secret tracking & Bayesian elimination
        4. Deck remaining cards and draw probability calculation
        """
        # Hand with Fireball, Frostbolt, Dire Wolf, Abusive Sergeant, The Coin
        hand_ids = ["CS2_029", "CS2_024", "CS2_065", "CS2_188", "GAME_005"]
        hand = [self.card_db.get_by_id(cid) for cid in hand_ids]
        valid_hand = [c for c in hand if c]

        # Populate sample draft deck into deck tracker
        sample_deck_ids = ["CS2_029", "CS2_024", "CS2_065", "CS2_188", "CS2_222", "CS2_120"]
        sample_cards = [self.card_db.get_by_id(cid) for cid in sample_deck_ids]
        self.deck_tracker.set_draft_deck([c for c in sample_cards if c] * 3)

        # Add an active secret for opponent Mage
        self.secret_tracker.reset()
        self.secret_tracker.add_opponent_secret("MAGE", turn=4)

        # Initialize opponent hand tracker simulation
        self.hand_tracker.reset()
        self.hand_tracker.init_opening_hand(card_count=4, has_coin=True)
        self.hand_tracker.set_turn(6)
        self.hand_tracker.record_card_drawn(creator="暗影视界")

        # Initialize opponent archetype classifier simulation
        if hasattr(self, "archetype_classifier"):
            self.archetype_classifier.reset("MAGE")
            self.archetype_classifier.record_card_played("奥术飞弹", "造成3点伤害")
            self.archetype_classifier.record_card_played("制造余震", "对所有随从造成1点伤害，施放三次")

        sample_play_state = {
            "turn": 6,
            "mana": 6,
            "max_mana": 6,
            "hand": valid_hand,
            "has_coin": True,
            "friendly_board": ["淡水鳄 (3/3)"],
            "friendly_board_objs": [{"name": "淡水鳄", "atk": 3, "can_attack": True, "windfury": False}],
            "enemy_board": ["石牙野猪 (1/1 嘲讽)"],
            "enemy_taunt_objs": [{"name": "石牙野猪", "health": 1}],
            "enemy_hp": 10,
            "enemy_armor": 0,
            "friendly_hero": "MAGE",
            "opponent_hero": "法师",
            "hero_power_available": False,
        }
        self._on_play_state_updated(sample_play_state)

    def simulate_sample_mulligan(self) -> None:
        """Simulates an opening hand mulligan scenario with keep/replace advice."""
        card_ids = ["CS2_188", "CS2_065", "CS2_029", "CS2_222"]  # 叫嚣(1), 恐狼(2), 火球(4), 暴风城(7)
        hand = [self.card_db.get_by_id(cid) for cid in card_ids]
        valid_hand = [c for c in hand if c]

        advice: MulliganAdvice = self.mulligan_advisor.evaluate_mulligan(
            hand_cards=valid_hand,
            hero_class="MAGE",
            opponent_class="HUNTER",
            has_coin=True,
        )

        lines = [f"<div style='margin-bottom: 6px;'><b>对战战略:</b> <span style='color: #38bdf8;'>{advice.game_plan}</span></div>"]
        for c in advice.choices:
            if c.action == "KEEP":
                lines.append(
                    f"<div style='background: rgba(16, 185, 129, 0.12); border-left: 3px solid #10b981; padding: 4px 8px; border-radius: 4px; margin-bottom: 4px;'>"
                    f"<b style='color: #34d399;'>🟢 【必留】</b> <b style='color: #f8fafc;'>{c.card.name}</b> ({c.card.cost}费) · "
                    f"<span style='color: #cbd5e1;'>{c.reason}</span></div>"
                )
            else:
                lines.append(
                    f"<div style='background: rgba(239, 68, 68, 0.10); border-left: 3px solid #ef4444; padding: 4px 8px; border-radius: 4px; margin-bottom: 4px;'>"
                    f"<b style='color: #f87171;'>🔴 【换掉】</b> <b style='color: #f8fafc;'>{c.card.name}</b> ({c.card.cost}费) · "
                    f"<span style='color: #94a3b8;'>{c.reason}</span></div>"
                )

        self.mulligan_lbl.setText("".join(lines))
        self.mulligan_coin_badge.setText("后手 (握幸运币)")
        self.mulligan_frame.show()

        # Switch to play container
        self._switch_to_play_view()
        self.mode_badge.setText("起手留牌")
        self._on_status_updated("已生成起手留牌决胜座舱指南")

    def cycle_theme(self) -> None:
        """Cycles between themes in THEMES and syncs with PrismaticThemeEngine."""
        themes = list(self.THEMES.keys())
        curr_idx = themes.index(self._current_theme) if self._current_theme in themes else 0
        next_theme = themes[(curr_idx + 1) % len(themes)]
        self.apply_theme(next_theme)
        if hasattr(self, "theme_engine") and next_theme in self.theme_engine.THEMES:
            self.theme_engine.set_theme(next_theme)

    def toggle_streamer_mode(self) -> bool:
        """Toggles Streamer Minimal Privacy Mode with broadcast ticker."""
        if not hasattr(self, "streamer_controller"):
            return False
        active = self.streamer_controller.toggle_streamer_mode()
        if hasattr(self, "streamer_ticker"):
            self.streamer_ticker.setVisible(active)
        if hasattr(self, "streamer_btn"):
            if active:
                self.streamer_btn.setStyleSheet("background: rgba(16, 185, 129, 0.4); color: #10b981; border: 1px solid #10b981;")
            else:
                self.streamer_btn.setStyleSheet("background: rgba(30, 41, 59, 200); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.4);")
        self._on_status_updated("主播极简隐私模式: 已开启 (防泄密)" if active else "主播模式: 已关闭 (还原全维视窗)")
        return active

    def toggle_radial_compass(self) -> bool:
        """Toggles 360-degree polar probability compass."""
        if not hasattr(self, "radial_compass"):
            return False
        is_vis = not self.radial_compass.isVisible()
        self.radial_compass.setVisible(is_vis)
        self._on_status_updated("极坐标概率罗盘: 已开启" if is_vis else "极坐标概率罗盘: 已收起")
        return is_vis

    def inspect_card_hologram(self, card_data: HologramCardData) -> None:
        """Pops up the high-definition holographic card inspector."""
        if hasattr(self, "card_inspector"):
            self.card_inspector.inspect_card(card_data)
            self.card_inspector.show()
            self.card_inspector.raise_()

    def apply_theme(self, theme_key: str) -> None:
        self._current_theme = theme_key
        cfg = self.THEMES.get(theme_key, self.THEMES["WARM_OBSIDIAN_GOLD"])
        self.central_card.setStyleSheet(f"QFrame#mainFrame {{ {cfg['frame']} }}")
        self.config_manager.set("theme", theme_key, auto_save=True)
        self._on_status_updated(f"已应用视觉主题: {cfg['name']}")

    def _on_aura_stylesheet_updated(self, qss: str) -> None:
        self.central_card.setStyleSheet(f"QFrame#mainFrame {{ {qss} }}")

    def set_aura_state(self, state: AuraState) -> None:
        """Dynamically triggers pulsing aura glow border (Lethal, Blunder, Miracle, Zen)."""
        if hasattr(self, "aura_controller"):
            self.aura_controller.set_state(state)

    def toggle_compact_mode(self) -> None:
        """Toggles between full overlay and compact mini capsule overlay."""
        self.is_compact_mode = not self.is_compact_mode
        if self.is_compact_mode:
            self._full_height = self.height()
            self.header_widget.hide()
            self.draft_container.hide()
            self.play_container.hide()
            self.status_bar_widget.hide()
            self.central_card.layout().setContentsMargins(8, 4, 8, 4)
            self.central_card.layout().setSpacing(0)
            self.compact_widget.show()
            self.compact_btn.setText("🗖")
            self.compact_btn.setToolTip("还原完整窗口模式 (Alt+M / F9)")
            self.setMinimumHeight(32)
            self.setMaximumHeight(42)
            self.resize(self.width(), 36)
            is_draft = "选牌" in self.mode_badge.text() or "英雄" in self.mode_badge.text()
            if hasattr(self, "compact_mode_pill"):
                self.compact_mode_pill.setText("选牌" if is_draft else "实战")
            self._on_status_updated("已切换至迷你极简胶囊模式")
        else:
            self.compact_widget.hide()
            self.header_widget.show()
            self.central_card.layout().setContentsMargins(10, 8, 10, 8)
            self.central_card.layout().setSpacing(8)
            self.compact_btn.setText("🗕")
            self.compact_btn.setToolTip("切换迷你极简胶囊模式 (Alt+M / F9)")
            is_draft = "选牌" in self.mode_badge.text() or "英雄" in self.mode_badge.text()
            if is_draft:
                self.draft_container.show()
                self.play_container.hide()
                target_h = self._full_height if self._full_height >= 600 else 700
            else:
                self.draft_container.hide()
                self.play_container.show()
                target_h = self._full_height if (350 <= self._full_height <= 600) else 520
            self.status_bar_widget.show()
            self.setMinimumHeight(350)
            self.setMaximumHeight(16777215)
            self.resize(self.width(), target_h)
            self._on_status_updated("已还原完整模式")

    def toggle_wide_mode(self) -> None:
        """Toggles between standard width and wide tactical briefing canvas."""
        if getattr(self, "is_compact_mode", False):
            self.toggle_compact_mode()

        current_w = self.width()
        if current_w < 540:
            target_w = self.config_manager.get("wide_overlay_width", 640)
            target_h = max(self.height(), 740)
            self.resize(target_w, target_h)
            if hasattr(self, "wide_btn"):
                self.wide_btn.setText("🗗")
                self.wide_btn.setToolTip("还原常规窗口模式 (Alt+W)")
            self.config_manager.set("overlay_width", target_w, auto_save=False)
            self.config_manager.set("overlay_height", target_h, auto_save=True)
            self._on_status_updated(f"已切换至战术大屏看板模式 ({target_w}px)")
        else:
            target_w = 480
            self.resize(target_w, self.height())
            if hasattr(self, "wide_btn"):
                self.wide_btn.setText("🗖")
                self.wide_btn.setToolTip("切换战术全景大屏 (Alt+W)")
            self.config_manager.set("overlay_width", target_w, auto_save=True)
            self._on_status_updated(f"已还原常规窗口模式 ({target_w}px)")

    def toggle_rope_mode(self) -> None:
        """Toggles rope emergency mode (collapses extra panels, inflates core 3 actions)."""
        self.is_rope_mode = not getattr(self, "is_rope_mode", False)
        if self.is_rope_mode:
            if hasattr(self, "rope_btn"):
                self.rope_btn.setStyleSheet("""
                    QPushButton {
                        background: #dc2626;
                        color: #ffffff;
                        border: 1px solid #ef4444;
                        font-size: 13px;
                        border-radius: 4px;
                    }
                """)
            if hasattr(self, "play_trade_frame"):
                self.play_trade_frame.hide()
            if hasattr(self, "play_risk_frame"):
                self.play_risk_frame.hide()
            if hasattr(self, "posture_frame"):
                self.posture_frame.hide()
            if hasattr(self, "intel_container"):
                self.intel_container.hide()
            self._on_status_updated("⏱️ 烧绳急救模式已开启 (Alt+R)")
        else:
            if hasattr(self, "rope_btn"):
                self.rope_btn.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        color: #94a3b8;
                        border: none;
                        font-size: 13px;
                    }
                    QPushButton:hover {
                        color: #f59e0b;
                        background: #334155;
                        border-radius: 4px;
                    }
                """)
            if hasattr(self, "play_trade_frame"):
                self.play_trade_frame.show()
            if hasattr(self, "play_risk_frame"):
                self.play_risk_frame.show()
            if hasattr(self, "posture_frame"):
                self.posture_frame.show()
            if hasattr(self, "intel_container"):
                self.intel_container.show()
            self._on_status_updated("⏱️ 已退出烧绳急救模式")

        # Invalidate fingerprint and re-render if payload exists
        if hasattr(self, "_last_play_payload") and self._last_play_payload:
            self._last_play_state_key = None
            self._on_play_state_updated(self._last_play_payload)

    def toggle_board_hud(self) -> None:
        """Toggles in-game transparent board tactical canvas projection."""
        if hasattr(self, "board_overlay"):
            is_enabled = not self.board_overlay._enabled
            self.board_overlay.set_enabled(is_enabled)
            if is_enabled:
                if hasattr(self, "board_hud_btn"):
                    self.board_hud_btn.setStyleSheet("""
                        QPushButton {
                            background: rgba(180, 83, 9, 0.45);
                            color: #fef08a;
                            border: 1px solid #fbbf24;
                            font-size: 13px;
                            border-radius: 4px;
                        }
                    """)
                win_rect = self.window_finder.find_window()
                self.board_overlay.sync_to_window(win_rect)
                self._on_status_updated("🎯 棋盘战术投影与动态箭头已开启 (Alt+V)")
            else:
                if hasattr(self, "board_hud_btn"):
                    self.board_hud_btn.setStyleSheet("""
                        QPushButton {
                            background: transparent;
                            color: #a8a29e;
                            border: none;
                            font-size: 13px;
                        }
                        QPushButton:hover {
                            color: #fbbf24;
                            background: rgba(245, 158, 11, 0.2);
                            border-radius: 4px;
                        }
                    """)
                self.board_overlay.hide()
                self._on_status_updated("🎯 棋盘战术投影已关闭")

    def _check_auto_rope(self) -> None:
        """Checks turn duration and auto-triggers rope emergency mode when running low on time."""
        if not getattr(self, "_auto_rope_enabled", True) or not getattr(self, "_is_player_turn", False):
            return
        if getattr(self, "is_rope_mode", False):
            return
        if getattr(self, "_turn_start_time", 0.0) <= 0:
            return

        elapsed = time.time() - self._turn_start_time
        if elapsed >= 50.0:  # Hearthstone rope burns for ~20s starting at 55s
            self._auto_rope_active = True
            self.toggle_rope_mode()
            self.sound_engine.notify_rope_emergency()
            self._on_status_updated("⏱️ 绳子开始燃烧！已自动启动急救模式！")

    def reset_current_deck(self) -> None:
        self.log_listener.reset_draft()
        self.mana_curve_widget.update_curve([0] * 8, 0)
        self.advice_lbl.setText("套牌已重置，等待新对局/选牌。")
        self._on_status_updated("套牌已重置")

    def _toggle_visibility(self) -> None:
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.activateWindow()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.Trigger:
            self._toggle_visibility()

    def shutdown(self) -> None:
        """Graceful shutdown: terminate worker threads, flush cache, close application."""
        logger.info("Initiating graceful shutdown...")
        self._on_status_updated("正在安全退出...")

        # 1. Stop background threads cleanly
        try:
            self.log_listener.stop()
            self.log_listener.wait(1000)
        except Exception as e:
            logger.warning(f"Error stopping LogListener: {e}")

        try:
            self.ocr_worker.stop()
            self.ocr_worker.wait(1000)
        except Exception as e:
            logger.warning(f"Error stopping OcrWorker: {e}")

        try:
            if hasattr(self, "web_companion"):
                self.web_companion.stop()
        except Exception as e:
            logger.warning(f"Error stopping WebCompanion: {e}")

        try:
            if hasattr(self, "global_hotkey_manager"):
                self.global_hotkey_manager.stop()
        except Exception as e:
            logger.warning(f"Error stopping GlobalHotkeyManager: {e}")

        # 2. Save cache & configs
        self.ai_engine.cache.save()
        self.config_manager.save()

        # 3. Hide tray and close
        self.tray_icon.hide()
        QApplication.quit()

    def closeEvent(self, event) -> None:
        """Intercept window close to execute graceful shutdown."""
        self.shutdown()
        event.accept()
