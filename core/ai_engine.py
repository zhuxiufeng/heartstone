"""
AiEngine: Core strategic brain powered by Google Gemini API with fallback heuristics.
Implements:
1. Metadata injection to completely eliminate LLM hallucination
2. Draft Mode (选牌模式): 3-pick evaluation considering hero, deck curve, and synergies
3. Play Mode (实战模式): Tactical turn recommendations, minion trading, AOE prevention
4. Evaluation Cache: Hash-based memory and disk caching (0 latency, 0 token cost)
5. State Machine for dual-mode transitions
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

_genai_cached = None


def _get_genai():
    """Lazily import google.generativeai only when Gemini API is actually invoked."""
    global _genai_cached
    if _genai_cached is None:
        try:
            import google.generativeai as genai
            _genai_cached = genai
        except Exception as e:
            logger.debug(f"google.generativeai import unavailable: {e}")
            _genai_cached = False
    return _genai_cached if _genai_cached is not False else None

from .card_db import CardDatabase, CardInfo, get_class_cn
from .synergy_engine import SynergyEngine
from .trade_optimizer import TradeOptimizer
from .aoe_radar import AoeRadar
from .posture_engine import PostureEngine, BeatdownPivotAlert, DynamicPivotTracker
from .sequence_optimizer import SequenceOptimizer
from .matchup_blueprint import MatchupBlueprintEngine, MatchupStrategy
from .archetype_specializer import ArchetypeSpecializer, ArchetypeProfile, ArchetypeType
from .punish_simulator import PunishSimulator, PunishAssessment
from .card_advantage_engine import CardAdvantageEngine, ResourceAdvantagePlan, ResourceState
from .blunder_shield import BlunderShield, BlunderAlert
from .mana_efficiency import ManaEfficiencyOptimizer, ManaEfficiencyPlan
from .ping_protector import PingProtector
from .hsreplay_sync import HsreplaySync
from .arena_card_stats import ArenaCardStats, CardWinrate
from .two_turn_lethal import TwoTurnLethalEngine, TwoTurnLethalPlan
from .positioning_geometry import PositioningGeometry, PositioningAdvice
from .mulligan_hand_reader import MulliganHandReader, MulliganHandAnalysis
from .draft_cap_enforcer import DraftCapEnforcer, DraftCapModifier
from .action_tree_search import ActionTreeSearch, ActionTreeResult, ActionBranch
from .discovery_pool_radar import DiscoveryPoolRadar, DiscoveryProbabilityReport
from .match_history_learner import MatchHistoryLearner
from .hero_draft_advisor import HeroDraftAdvisor, HeroTierInfo
from .burst_damage_guard import BurstDamageGuard, BurstThreatReport
from .live_discover_advisor import LiveDiscoverAdvisor, DiscoverGuidance, DiscoverTriPickResult, DiscoverCardEvaluation
from .secret_tracker import SecretTracker, SecretProbingPlan, SecretProbingStep
from .variance_evaluator import VarianceEvaluator, VariancePolicyReport
from .draft_quota_tracker import DraftQuotaTracker, DraftQuotaReport
from .rng_probability_engine import RngProbabilityEngine, RngProbabilityReport
from .personal_weakness_profiler import PersonalWeaknessProfiler
from .matchup_micro_meta import MatchupMicroMetaEngine, MatchupDeltaResult
from .board_resilience_evaluator import BoardResilienceEvaluator, BoardResilienceReport
from .winrate_estimator import WinRateEstimator, WinRateReport
from .aoe_radar import AoeRadar, AOEOverextensionGuard, OverextensionAssessment
from .fatigue_endgame_horizon import FatigueEndgameHorizon, FatigueEndgameReport, EndgameVerdict
from .hand_age_intel import HandAgeIntel, HandAgeIntelReport
from .tactical_ghost_board import TacticalGhostBoardSimulator, GhostBoardSnapshot
from .opponent_punish_envelope import OpponentPunishEnvelopeCalculator, OpponentPunishEnvelope
from .zero_leak_mana_auditor import ZeroLeakManaAuditor, ManaLeakAuditResult
from .miracle_out_filter import MiracleOutFilter, MiracleOutReport
from .temporal_bottleneck_guard import TemporalBottleneckGuard, SaturationAssessment

logger = logging.getLogger("AiEngine")

# Bump whenever draft scoring logic changes so persisted evaluation caches are invalidated.
DRAFT_SCORING_VERSION = "v23-realdata"

def get_default_eval_cache_file() -> Path:
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).resolve().parent
    else:
        base_dir = Path(__file__).resolve().parent.parent
    return base_dir / "cache" / "eval_cache.json"


EVAL_CACHE_FILE = get_default_eval_cache_file()


class AssistantMode(Enum):
    DRAFT = "DRAFT"
    PLAY = "PLAY"


@dataclass
class CardEvaluation:
    card_id: str
    card_name: str
    score: int  # 0 to 100
    is_best_pick: bool
    summary: str
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)
    marginal_delta: float = 0.0
    archetype_fit_tag: str = ""
    saturation_assessment: Optional[SaturationAssessment] = None
    real_winrate_pct: Optional[float] = None      # Bayesian-adjusted drawn win rate, None = no data
    real_winrate_samples: int = 0


@dataclass
class DraftRecommendation:
    best_card_index: int  # 0, 1, 2
    best_card_name: str
    cards_evaluations: List[CardEvaluation]
    curve_advice: str
    overall_strategy: str
    is_cached: bool = False
    raw_reasoning: str = ""
    archetype_name: str = ""
    archetype_advice: str = ""
    quota_report: Optional[DraftQuotaReport] = None
    quota_strip: str = ""


@dataclass
class PlayRecommendation:
    suggested_plays: List[str]
    mana_plan: str
    trading_plan: str
    risk_warning: str
    raw_reasoning: str = ""
    posture_mode: str = "CONTROL"
    beatdown_clock: str = ""
    optimal_trades: List[str] = field(default_factory=list)
    aoe_threats: List[str] = field(default_factory=list)
    play_sequence: List[str] = field(default_factory=list)
    positioning_advice: str = ""
    face_pivot_warning: str = ""
    burst_safety_warning: str = ""
    matchup_blueprint: str = ""
    mana_efficiency_advice: str = ""
    punish_assessment: str = ""
    card_advantage_directive: str = ""
    blunder_alerts: List[str] = field(default_factory=list)
    two_turn_lethal_advice: str = ""
    mulligan_hand_reading: str = ""
    action_tree_summary: str = ""
    discovery_radar_warning: str = ""
    best_branch: Optional[ActionBranch] = None
    alt_branch: Optional[ActionBranch] = None
    compass_directive: str = ""
    opponent_burst_danger: Optional[BurstThreatReport] = None
    discover_guidance: Optional[DiscoverGuidance] = None
    variance_policy: str = ""
    checklist_steps: List[str] = field(default_factory=list)
    draw_first_directive: str = ""
    next_turn_threat_cards: List[Dict[str, str]] = field(default_factory=list)
    lethal_cushion: str = ""
    plan_b_steps: List[str] = field(default_factory=list)
    rng_report: Optional[RngProbabilityReport] = None
    personal_weakness_reminder: str = ""
    resilience_report: Optional[BoardResilienceReport] = None
    resilience_verdict: str = ""
    hypergeometric_report: Optional[Any] = None
    hypergeometric_summary: str = ""
    tilt_summary: str = ""
    mind_reading_summary: str = ""
    decision_tree_dict: Dict[str, Any] = field(default_factory=dict)
    var_report: Optional[Any] = None
    var_summary: str = ""
    # v20 First-Principles Apex Engine Attributes
    two_turn_lockout: bool = False
    two_turn_lockout_directive: str = ""
    two_turn_lockout_badge: str = ""
    mana_flow_plan: Optional[ManaEfficiencyPlan] = None
    mana_flow_tag: str = ""
    mana_flow_preview: str = ""
    beatdown_pivot_alert: Optional[BeatdownPivotAlert] = None
    beatdown_pivot_text: str = ""
    discover_tri_pick: Optional[DiscoverTriPickResult] = None
    secret_probing_plan: Optional[SecretProbingPlan] = None
    secret_probing_directive: str = ""
    # v21 First-Principles Omniscience Attributes & Live Win Rate
    live_winrate_report: Optional[WinRateReport] = None
    live_winrate_pct: float = 50.0
    live_winrate_delta: float = 0.0
    live_winrate_tier: str = ""
    live_winrate_driver: str = ""
    overextension_assessment: Optional[OverextensionAssessment] = None
    fatigue_endgame_report: Optional[FatigueEndgameReport] = None
    bayesian_hand_report: Optional[HandAgeIntelReport] = None
    # v22 First-Principles Ultimate Attributes
    ghost_board_snapshot: Optional[GhostBoardSnapshot] = None
    opponent_punish_envelope: Optional[OpponentPunishEnvelope] = None
    mana_leak_audit: Optional[ManaLeakAuditResult] = None
    miracle_out_report: Optional[MiracleOutReport] = None
    # Data integrity flags
    data_complete: bool = True
    data_warnings: List[str] = field(default_factory=list)


class EvaluationCache:
    """Hash-based evaluation cache storing identical scenario evaluations."""

    def __init__(self, cache_file: Path = EVAL_CACHE_FILE) -> None:
        self.cache_file = cache_file
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.memory_cache = data
                        logger.info(f"Loaded {len(self.memory_cache)} cached evaluations.")
            except Exception as e:
                logger.warning(f"Failed to load evaluation cache: {e}")

    def save(self) -> None:
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.memory_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save evaluation cache: {e}")

    @staticmethod
    def compute_draft_hash(hero: str, picked_curve: List[int], candidate_ids: List[str]) -> str:
        """
        Generates deterministic hash based on:
        hero class + 0-7+ mana distribution bucket + candidate card IDs
        """
        curve_str = ",".join(str(c) for c in picked_curve)
        cands_str = ",".join(candidate_ids)
        key_source = f"{hero}|{curve_str}|{cands_str}"
        return hashlib.sha256(key_source.encode("utf-8")).hexdigest()[:24]

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        return self.memory_cache.get(key)

    def set(self, key: str, val: Dict[str, Any]) -> None:
        self.memory_cache[key] = val
        self.save()


class AiEngine:
    """Manages Gemini LLM prompts, state machine, metadata injection, and evaluation cache."""

    def __init__(
        self,
        api_key: str = "",
        model_name: str = "gemini-1.5-flash",
        temperature: float = 0.3,
        card_db: Optional[CardDatabase] = None,
        cache_enabled: bool = True,
    ) -> None:
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.model_name = model_name
        self.temperature = temperature
        self.card_db = card_db or CardDatabase.get_instance()
        self.cache_enabled = cache_enabled

        self.cache = EvaluationCache()
        self.mode = AssistantMode.DRAFT
        self.synergy_engine = SynergyEngine(self.card_db)
        self.trade_optimizer = TradeOptimizer()
        self.aoe_radar = AoeRadar()
        self.posture_engine = PostureEngine()
        self.sequence_optimizer = SequenceOptimizer()
        self.secret_tracker = SecretTracker(self.card_db)
        self.match_learner = MatchHistoryLearner()
        self.hand_age_intel = HandAgeIntel()
        self._last_winrate_pct = 50.0
        self._gemini_model = None

    @property
    def _gemini_client(self):
        """Lazy accessor for Gemini GenerativeModel client."""
        if self._gemini_model is None and self.api_key:
            self._init_gemini()
        return self._gemini_model

    @_gemini_client.setter
    def _gemini_client(self, value):
        self._gemini_model = value

    def has_llm_client(self) -> bool:
        """Checks if online LLM client is configured and available."""
        return bool(self.api_key and _get_genai() is not None)

    def update_config(self, api_key: str, model_name: str) -> None:
        """Update API configuration dynamically from Settings UI."""
        self.api_key = api_key
        self.model_name = model_name
        self._gemini_model = None

    def _init_gemini(self) -> None:
        genai = _get_genai()
        if not genai or not self.api_key:
            self._gemini_model = None
            return
        try:
            genai.configure(api_key=self.api_key)
            clean_name = self.model_name.strip()
            if clean_name.startswith("models/"):
                clean_name = clean_name[7:]
            self._gemini_model = genai.GenerativeModel(
                model_name=clean_name,
                generation_config={"temperature": self.temperature},
            )
            logger.info(f"Gemini client initialized with model: {clean_name}")
        except Exception as e:
            logger.error(f"Failed to configure Gemini: {e}")
            self._gemini_model = None

    @staticmethod
    def fetch_available_models(api_key: str) -> List[str]:
        """Queries Google Gemini API to return all supported generateContent models for this key."""
        genai = _get_genai()
        if not genai or not api_key:
            return []
        try:
            genai.configure(api_key=api_key)
            models = []
            for m in genai.list_models():
                methods = getattr(m, "supported_generation_methods", [])
                if "generateContent" in methods:
                    name = m.name.replace("models/", "")
                    models.append(name)
            return sorted(models, reverse=True)
        except Exception as e:
            logger.warning(f"Failed to fetch available Gemini models: {e}")
            return []

    def set_mode(self, mode: AssistantMode) -> None:
        self.mode = mode
        logger.info(f"AI Engine mode set to: {self.mode.value}")

    # =========================================================================
    # Phase 3: Draft Mode (选牌模式)
    # =========================================================================
    def evaluate_draft_pick(
        self,
        hero_class: str,
        candidates: List[CardInfo],
        deck_so_far: List[CardInfo],
        use_llm: bool = True,
    ) -> DraftRecommendation:
        """
        Evaluates 3 draft cards in context of current hero and mana curve.
        1. Injects complete card metadata from CardDB (costs, stats, effects)
        2. Checks local EvaluationCache for instant return
        3. Calls Gemini API if online, or falls back to heuristic engine
        """
        candidate_ids = [c.id for c in candidates]
        deck_ids = [c.id for c in deck_so_far]
        curve = self.calculate_mana_curve(deck_so_far)
        quota_rep = DraftQuotaTracker.evaluate_deck_quotas(deck_so_far, len(deck_so_far) + 1)

        # Check Cache (keyed by hero, curve, candidate IDs, and drafted deck IDs)
        if self.cache_enabled:
            # Salt with scoring version + stats snapshot date so new data/logic invalidates old entries
            stats_ver = ArenaCardStats.get_instance().last_updated()[:10]
            cache_key = self.cache.compute_draft_hash(
                hero_class, curve, candidate_ids + ["|"] + deck_ids + ["|", DRAFT_SCORING_VERSION, stats_ver]
            )
            cached_val = self.cache.get(cache_key)
            if cached_val:
                logger.info(f"Draft recommendation cache HIT: {cache_key}")
                rec = self._deserialize_draft_recommendation(cached_val)
                rec.is_cached = True
                rec.quota_report = quota_rep
                rec.quota_strip = quota_rep.short_status_strip
                return rec

        # If Gemini is configured and enabled, use LLM
        if use_llm and self._gemini_client:
            try:
                rec = self._evaluate_draft_with_llm(hero_class, candidates, deck_so_far, curve)
                rec.quota_report = quota_rep
                rec.quota_strip = quota_rep.short_status_strip
                if self.cache_enabled:
                    self.cache.set(cache_key, asdict(rec))
                return rec
            except Exception as e:
                logger.warning(f"LLM API draft call failed: {e}. Falling back to heuristic analysis.")

        # Heuristic rule-based fallback
        rec = self._heuristic_draft_evaluation(hero_class, candidates, deck_so_far, curve)
        rec.quota_report = quota_rep
        rec.quota_strip = quota_rep.short_status_strip
        if self.cache_enabled:
            self.cache.set(cache_key, asdict(rec))
        return rec

    def evaluate_single_card(
        self,
        hero_class: str,
        card: CardInfo,
        deck: List[CardInfo],
    ) -> CardEvaluation:
        """Evaluates a single card in the context of the current draft/deck."""
        rec = self.evaluate_draft_pick(hero_class, [card], deck)
        if rec and rec.cards_evaluations:
            return rec.cards_evaluations[0]
        return CardEvaluation(
            card_id=card.id,
            card_name=card.name,
            score=70,
            is_best_pick=True,
            summary=f"{card.cost}费 {card.card_type}",
            pros=[],
            cons=[],
        )

    def _evaluate_draft_with_llm(
        self,
        hero_class: str,
        candidates: List[CardInfo],
        deck_so_far: List[CardInfo],
        curve: List[int],
    ) -> DraftRecommendation:
        """Assembles prompt with metadata injection and queries Gemini."""
        prompt = self._build_draft_prompt(hero_class, candidates, deck_so_far, curve)
        logger.debug(f"Draft prompt:\n{prompt}")

        response = self._gemini_client.generate_content(prompt)
        text = response.text.strip()
        logger.debug(f"Draft response:\n{text}")

        # Parse JSON from markdown block
        parsed = self._extract_json(text)
        if not parsed:
            raise ValueError(f"Could not extract JSON from response: {text[:200]}")

        best_idx = int(parsed.get("best_card_index", 0))
        evals: List[CardEvaluation] = []
        for idx, item in enumerate(parsed.get("cards", [])):
            cid = candidates[idx].id if idx < len(candidates) else f"CARD_{idx}"
            cname = candidates[idx].name if idx < len(candidates) else item.get("name", "")
            evals.append(
                CardEvaluation(
                    card_id=cid,
                    card_name=cname,
                    score=int(item.get("score", 70)),
                    is_best_pick=(idx == best_idx),
                    summary=item.get("summary", ""),
                    pros=item.get("pros", []),
                    cons=item.get("cons", []),
                )
            )

        best_name = evals[best_idx].card_name if 0 <= best_idx < len(evals) else candidates[0].name
        return DraftRecommendation(
            best_card_index=best_idx,
            best_card_name=best_name,
            cards_evaluations=evals,
            curve_advice=parsed.get("curve_advice", ""),
            overall_strategy=parsed.get("overall_strategy", ""),
            raw_reasoning=text,
        )

    def _build_draft_prompt(
        self,
        hero_class: str,
        candidates: List[CardInfo],
        deck: List[CardInfo],
        curve: List[int],
    ) -> str:
        """Constructs prompt injecting verified card metadata."""
        meta_blocks = [c.format_for_ai_prompt_compact() for c in candidates]
        meta_str = "\n".join(meta_blocks)

        deck_summary = [f"- {c.name} ({c.cost}费 {c.card_type})" for c in deck]
        deck_str = "\n".join(deck_summary) if deck_summary else "(当前牌库为空，第1抓)"

        curve_str = f"0费:{curve[0]}张, 1费:{curve[1]}张, 2费:{curve[2]}张, 3费:{curve[3]}张, 4费:{curve[4]}张, 5费:{curve[5]}张, 6费:{curve[6]}张, 7+费:{curve[7]}张"

        prompt = f"""你是《炉石传说》全球顶尖竞技场大师。请根据当前对局状态与候选卡牌元数据，给出最专业的三选一抓牌指导。

【当前职业】: {hero_class}
【已选卡牌数量】: {len(deck)} / 30
【当前法力曲线】: {curve_str}

【候选三张卡牌的权威元数据 (已由系统验证，请严格基于此数据分析，杜绝幻觉)】:
{meta_str}

【已选套牌列表】:
{deck_str}

【评估维度】:
1. 单卡质量与身材模型 (Vanilla / Tier 价值)
2. 与当前职业技能和法力曲线的拟合度 (补齐断档费用、强化节奏)
3. 竞技场核心需求 (解场、优质2费随从、终结手段、资源补充)

【输出要求】:
必须仅输出合法的 JSON 格式（包含在 ```json 代码块中），结构如下：
{{
  "best_card_index": 0, // 推荐抓取的索引 (0 代表第1张, 1 代表第2张, 2 代表第3张)
  "overall_strategy": "套牌当前思路总结 (1-2句话)",
  "curve_advice": "法力曲线调整建议 (例如: 缺少2费节奏随从，急需补强)",
  "cards": [
    {{
      "name": "卡名1",
      "score": 85, // 0-100分
      "summary": "简明评价 (30字以内)",
      "pros": ["优势1", "优势2"],
      "cons": ["劣势1"]
    }},
    {{
      "name": "卡名2",
      "score": 70,
      "summary": "简明评价",
      "pros": ["优势"],
      "cons": ["劣势"]
    }},
    {{
      "name": "卡名3",
      "score": 60,
      "summary": "简明评价",
      "pros": ["优势"],
      "cons": ["劣势"]
    }}
  ]
}}
"""
        return prompt

    # =========================================================================
    # Fallback Heuristics
    # =========================================================================
    def _heuristic_draft_evaluation(
        self,
        hero_class: str,
        candidates: List[CardInfo],
        deck: List[CardInfo],
        curve: List[int],
    ) -> DraftRecommendation:
        """
        Rule-based expert heuristic algorithm to guarantee instant recommendations
        even without internet connection or Gemini API Key.
        """
        evals: List[CardEvaluation] = []
        best_idx = 0
        max_score = -1

        pick_num = len(deck) + 1
        archetype_prof = ArchetypeSpecializer.detect_archetype(deck)

        if pick_num <= 10:
            phase_name = "第1阶段·单卡质量与曲线奠基"
            phase_desc = "优先抓取身材超标、填补空缺曲线的顶级单卡。"
        elif pick_num <= 20:
            phase_name = f"第2阶段·曲线修补 ({archetype_prof.name_cn})"
            phase_desc = f"{archetype_prof.description} 严格平衡 2-4 费前期节奏，稳固展开。"
        else:
            phase_name = f"第3阶段·战术协力 ({archetype_prof.name_cn})"
            phase_desc = f"{archetype_prof.advice} 补充过牌、补刀解牌与终结爆发手段。"

        for idx, card in enumerate(candidates):
            score = 65  # Base score
            curve_fill_note = ""

            # 0. Real arena win-rate data (Firestone public stats). When present it REPLACES the
            #    intrinsic-quality heuristics below (rarity / stat ratio / keywords / static table),
            #    which would otherwise double-count card strength.
            real_wr = ArenaCardStats.get_instance().get_card_winrate(card.id, hero_class)
            if real_wr is not None:
                score += int(round(real_wr.score_delta))
            else:
                # 1. Rarity bonus (Phase 1 amplifies raw quality)
                rarity_mult = 1.3 if pick_num <= 10 else 1.0
                if card.rarity == "LEGENDARY":
                    score += int(16 * rarity_mult)
                elif card.rarity == "EPIC":
                    score += int(9 * rarity_mult)
                elif card.rarity == "RARE":
                    score += int(5 * rarity_mult)

                # 2. Stats to cost ratio
                if card.attack is not None and card.health is not None:
                    expected_stats = card.cost * 2 + 1
                    actual_stats = card.attack + card.health
                    if actual_stats >= expected_stats:
                        score += 10
                    elif actual_stats < expected_stats - 2:
                        score -= 6

            # 3. Curve balance logic - Phase & Drafted-Deck Aware
            cost_bucket = min(card.cost, 7)
            if len(deck) >= 2 and cost_bucket in (2, 3, 4) and curve[cost_bucket] == 0:
                score += 6
                curve_fill_note = f"补齐当前{cost_bucket}费空缺(+6分)"

            if pick_num <= 10:
                if cost_bucket == 2 and curve[2] < 2:
                    score += 6
                elif cost_bucket >= 7 and curve[7] >= 3:
                    score -= 10
            elif 11 <= pick_num <= 20:
                if cost_bucket == 2:
                    if curve[2] < 4:
                        score += 18
                    elif curve[2] < 6:
                        score += 10
                elif cost_bucket == 3 and curve[3] < 5:
                    score += 10
                elif cost_bucket >= 7 and curve[7] >= 3:
                    score -= 18
            else:
                if cost_bucket == 2 and curve[2] < 4:
                    score += 22
                elif cost_bucket >= 7 and curve[7] >= 3:
                    score -= 20

            # 4. Key mechanics (heuristic quality proxy; skipped when real data exists)
            if real_wr is None:
                if "DEATHRATTLE" in card.mechanics or "BATTLECRY" in card.mechanics:
                    score += 6
                if "TAUNT" in card.mechanics or "RUSH" in card.mechanics:
                    score += 8

            # 5. Dynamic Synergy Engine bonus (Phase 3 amplified)
            syn_eval = self.synergy_engine.evaluate_synergies(card, deck)
            syn_mult = 1.4 if pick_num > 20 else 1.0
            score += int(syn_eval.bonus_score * syn_mult)

            # 6. Dynamic Archetype Weighting (Aggro / Control / Tempo Midrange / Tribal)
            arch_delta, arch_desc = ArchetypeSpecializer.evaluate_card_archetype_delta(card, archetype_prof)
            score += arch_delta

            # 7. Draft Cap Enforcer (Heavy Bomb Hard Cap & Spell Overload Limits)
            cap_mod = DraftCapEnforcer.evaluate_card_caps(card, deck)
            score += int(cap_mod.score_delta)

            # 8. Adaptive Local Win-Rate Learning (强化学习本地校准)
            hist_delta = self.match_learner.get_card_winrate_adjustment(card.id)
            if hist_delta != 0:
                score += int(hist_delta)

            # 9. HSReplay Cloud Meta Win-Rate (天梯大数据校准)
            hsreplay_delta = 0.0 if real_wr is not None else HsreplaySync.get_instance().get_card_winrate_delta(card.id, card.name)
            if hsreplay_delta != 0:
                score += int(hsreplay_delta)

            # 10. Arena 12-Win Deck Role & Functional Component Quota Compensation
            quota_bonus = DraftQuotaTracker.calculate_quota_score_bonus(card, deck, pick_num)
            if quota_bonus != 0:
                score += quota_bonus

            # 11. Matchup Specific Micro-Meta Synergy & Arena Rotation Bias
            meta_bias = MatchupMicroMetaEngine.evaluate_draft_meta_bias(hero_class, card)
            if meta_bias.score_delta != 0:
                score += meta_bias.score_delta

            # 12. Dynamic Archetype Convergence & Marginal Synergy Delta (选牌动力学原型收敛罗盘)
            marginal_delta = 0.0
            archetype_fit_tag = ""
            cost_count = sum(1 for c in deck if c.cost == card.cost)
            arch_name = archetype_prof.archetype.name

            if cost_count >= 5 and pick_num >= 10:
                marginal_delta -= 14.0
                archetype_fit_tag = f"⚠️【{card.cost}费曲线严重拥堵 · 边际 -14分】"
            elif card.cost == 2 and cost_count <= 2 and pick_num >= 12:
                marginal_delta += 18.0
                archetype_fit_tag = "🎯【2费曲线急缺补强 · 边际 +18分】"
            elif arch_name == "AGGRO" and (getattr(card, "attack", 0) or 0) >= card.cost:
                marginal_delta += 15.0
                archetype_fit_tag = "🔥【12胜快攻核心收敛 · 边际 +15分】"
            elif arch_name == "CONTROL" and (getattr(card, "card_type", "") == "SPELL" or (getattr(card, "health", 0) or 0) >= 5):
                marginal_delta += 14.0
                archetype_fit_tag = "🛡️【12胜控制核心收敛 · 边际 +14分】"
            elif syn_eval.bonus_score >= 8:
                marginal_delta += float(syn_eval.bonus_score)
                archetype_fit_tag = f"💎【强力套牌协同收敛 · 边际 +{syn_eval.bonus_score:.0f}分】"

            if marginal_delta != 0:
                score += int(marginal_delta)

            # 13. Temporal Action Bottleneck & Saturation Guard (武器与频次瓶颈饱和熔断器)
            sat_res = TemporalBottleneckGuard.evaluate_card_saturation(card, deck)
            if sat_res.is_saturated:
                score += int(sat_res.score_delta)

            score = max(35, min(98, score))

            if score > max_score:
                max_score = score
                best_idx = idx

            card_pros = [real_wr.label] if real_wr is not None else ["⚙️ 无实战数据，按规则估分"]
            if sat_res.is_saturated:
                card_pros.append(f"{sat_res.saturation_tag}: {sat_res.advice}")
            if archetype_fit_tag:
                card_pros.append(archetype_fit_tag)
            if curve_fill_note:
                card_pros.append(f"📈 曲线联动: {curve_fill_note}")
            if hist_delta != 0:
                card_pros.append(f"📊 本地胜率反馈: {'+' if hist_delta > 0 else ''}{hist_delta:.0f}分")
            if hsreplay_delta != 0:
                card_pros.append(f"📚 内置参考表: {'+' if hsreplay_delta > 0 else ''}{hsreplay_delta:.0f}分")
            if syn_eval.bonus_score != 0:
                sign = "+" if syn_eval.bonus_score > 0 else ""
                card_pros.append(f"【{syn_eval.synergy_type}】{sign}{syn_eval.bonus_score:.0f}分: {syn_eval.explanation}")
            if quota_bonus > 0:
                card_pros.append(f"🎯 12胜组件定额急需: +{quota_bonus}分")
            elif quota_bonus < 0:
                card_pros.append(f"⚠️ 组件定额溢出惩罚: {quota_bonus}分")
            if meta_bias.score_delta > 0:
                card_pros.append(f"{meta_bias.meta_tag}: +{meta_bias.score_delta}分 ({meta_bias.explanation})")
            if arch_desc:
                card_pros.append(arch_desc)
            if cap_mod.reasons:
                for r in cap_mod.reasons:
                    card_pros.append(r)

            summary_parts = [f"{card.cost}费"]
            if curve_fill_note:
                summary_parts.append(curve_fill_note)
            if syn_eval.bonus_score > 0:
                summary_parts.append(f"【{syn_eval.synergy_type}】{syn_eval.explanation}")
            elif syn_eval.bonus_score < 0:
                summary_parts.append(f"⚠️{syn_eval.explanation}")
            elif not curve_fill_note:
                summary_parts.append("契合当前套牌曲线与站场节奏")

            evals.append(
                CardEvaluation(
                    card_id=card.id,
                    card_name=card.name,
                    score=score,
                    is_best_pick=False,
                    summary=" | ".join(summary_parts),
                    pros=card_pros,
                    cons=["后期略显乏力" if card.cost <= 2 else "需要配合"],
                    marginal_delta=marginal_delta,
                    archetype_fit_tag=archetype_fit_tag,
                    saturation_assessment=sat_res,
                    real_winrate_pct=round(real_wr.adjusted_winrate_pct, 1) if real_wr else None,
                    real_winrate_samples=real_wr.drawn_games if real_wr else 0,
                )
            )

        evals[best_idx].is_best_pick = True

        # Summarize already-drafted cards and curve gaps
        if deck:
            deck_names = "、".join(c.name for c in deck[:8])
            if len(deck) > 8:
                deck_names += f" 等{len(deck)}张"
            empty_slots = [f"{cost}费" for cost in (2, 3, 4) if curve[cost] == 0]
            if empty_slots:
                curve_adv = f"基于已抓 ({deck_names})：当前 {'/'.join(empty_slots)} 为 0 张，优先补齐断档曲线！"
            elif curve[2] < 4 and len(deck) >= 10:
                curve_adv = f"基于已抓 ({deck_names})：2费随从偏少({curve[2]}张)，建议优先补充前期节奏！"
            else:
                curve_adv = f"基于已抓 ({deck_names})：{phase_desc}"
        else:
            curve_adv = f"【{phase_name}】{phase_desc}"

        overall_strat = f"围绕 {hero_class} 构筑 (已抓 {len(deck)}/30 张): {phase_name}"
        if archetype_prof.archetype != ArchetypeType.UNDETERMINED:
            overall_strat += f" | 流派: {archetype_prof.name_cn}"

        return DraftRecommendation(
            best_card_index=best_idx,
            best_card_name=candidates[best_idx].name if candidates else "",
            cards_evaluations=evals,
            curve_advice=curve_adv,
            overall_strategy=overall_strat,
            raw_reasoning="[内置启发式三阶段动态策略与流派特化引擎推荐]",
            archetype_name=archetype_prof.name_cn,
            archetype_advice=archetype_prof.advice,
        )

    def _parse_board_minions(self, board_items: List[Any]) -> List[Dict[str, Any]]:
        """Parses board representations (strings like '淡水鳄 (2/3)' or dicts) into structured dicts."""
        minions = []
        import re
        for idx, item in enumerate(board_items):
            if isinstance(item, dict):
                minions.append(item)
                continue
            name = str(item)
            atk = 2
            hp = 2
            taunt = "嘲讽" in name or "Taunt" in name
            shield = "圣盾" in name or "Divine" in name
            poison = "剧毒" in name or "Poison" in name
            m = re.search(r"\((\d+)/(\d+)\)", name)
            stats_known = bool(m)
            if m:
                atk = int(m.group(1))
                hp = int(m.group(2))
            minions.append({
                "stats_known": stats_known,
                "name": name,
                "attack": atk,
                "health": hp,
                "taunt": taunt,
                "divine_shield": shield,
                "poisonous": poison,
                "can_attack": True,
            })
        return minions

    def evaluate_play_turn(
        self,
        turn_number: int,
        current_mana: int,
        hand_cards: List[CardInfo],
        friendly_board: List[str],
        enemy_board: List[str],
        opponent_class: str = "UNKNOWN",
        opponent_hand_warnings: Optional[List[str]] = None,
        has_long_held_card: bool = False,
        friendly_hp: int = 30,
        enemy_hp: int = 30,
        enemy_secrets_count: int = 0,
        use_llm: bool = True,
        remaining_deck: Optional[List[CardInfo]] = None,
    ) -> PlayRecommendation:
        """Provides real-time tactical suggestions during play turns with Hand Reading.

        remaining_deck: cards still in the player's deck (from DeckTracker). When None, deck-dependent
        probability features (topdeck odds, miracle outs) report "no deck data" instead of guessing.
        """
        deck_cards: List[CardInfo] = list(remaining_deck or [])
        f_minions = self._parse_board_minions(friendly_board)
        e_minions = self._parse_board_minions(enemy_board)

        # 0. Data integrity: never present guessed stats as facts
        data_warnings: List[str] = []
        unknown_f = [m.get("name", "?") for m in f_minions if m.get("stats_known") is False]
        unknown_e = [m.get("name", "?") for m in e_minions if m.get("stats_known") is False]
        if unknown_f or unknown_e:
            data_warnings.append(f"⚠️ {len(unknown_f) + len(unknown_e)} 个随从身材未识别，斩杀/交换结果仅供参考")
        if remaining_deck is None:
            data_warnings.append("ℹ️ 未提供剩余牌库，抽牌概率功能已停用")
        data_complete = not (unknown_f or unknown_e)

        # 1. Posture & Clock
        f_atk = sum(m.get("attack", 0) for m in f_minions)
        e_atk = sum(m.get("attack", 0) for m in e_minions)
        enemy_hand_count = len(opponent_hand_warnings) if opponent_hand_warnings else 4

        posture_res = self.posture_engine.assess_posture(
            friendly_hp=friendly_hp,
            enemy_hp=enemy_hp,
            friendly_board_attack=f_atk,
            enemy_board_attack=e_atk,
            friendly_hand_count=len(hand_cards),
            enemy_hand_count=enemy_hand_count,
            enemy_has_taunts=any(m.get("taunt", False) for m in e_minions),
            current_turn=turn_number,
        )

        # 1.5. Matchup Blueprint Engine (All 11 Classes)
        matchup_strat: MatchupStrategy = MatchupBlueprintEngine.get_matchup_strategy(
            opponent_class=opponent_class,
            current_turn=turn_number,
            friendly_board=friendly_board,
            enemy_board=enemy_board,
            friendly_hp=friendly_hp,
            enemy_hp=enemy_hp,
        )

        # 1.6. Card Advantage & Hand Starvation Engine
        res_plan: ResourceAdvantagePlan = CardAdvantageEngine.evaluate_resource_dynamics(
            friendly_hand_count=len(hand_cards),
            enemy_hand_count=enemy_hand_count,
            friendly_board_count=len(f_minions),
            enemy_hp=enemy_hp,
            turn_number=turn_number,
        )

        # 1.7. Next-Turn Worst-Case Punish Simulation
        punish_res: PunishAssessment = PunishSimulator.evaluate_board_punish(
            friendly_minions=f_minions,
            opponent_class=opponent_class,
            current_turn=turn_number,
        )

        # 1.8. Real-time Blunder Shield (Live Operational Interceptor)
        blunders: List[BlunderAlert] = BlunderShield.scan_for_blunders(
            hand_cards=hand_cards,
            friendly_minions=f_minions,
            enemy_secrets_count=enemy_secrets_count,
            available_mana=current_mana,
            hero_power_available=current_mana >= 2,
            enemy_minions=e_minions,
        )
        blunder_directives = [b.action_directive for b in blunders]

        # 2. Optimal Minion Trades with Ping Resistance
        trade_res = self.trade_optimizer.calculate_trades(
            friendly_minions=f_minions,
            enemy_minions=e_minions,
            enemy_hero_health=enemy_hp,
            face_aggression=1.8 if (posture_res.posture_mode == "AGGRESSIVE" or res_plan.choke_pressure_active) else 0.8,
            opponent_class=opponent_class,
        )
        trade_steps = [a.description for a in trade_res.actions]

        # 2.5. 2-Turn Continuous Mana Efficiency Optimization
        mana_eff_plan: Optional[ManaEfficiencyPlan] = ManaEfficiencyOptimizer.calculate_2turn_efficiency(
            hand_cards=hand_cards,
            current_mana=current_mana,
        )

        # 3. Dynamic AOE Threat Radar & Punish Simulator Alerts
        aoe_threats = self.aoe_radar.evaluate_threats(
            opponent_class=opponent_class,
            current_turn=turn_number,
            friendly_minions=f_minions,
            has_long_held_card=has_long_held_card,
        )
        aoe_alerts = [t.warning_advice for t in aoe_threats[:3]]
        if punish_res.punish_risk_level in {"HIGH", "CRITICAL"}:
            aoe_alerts.insert(0, punish_res.tactical_advice)
        if matchup_strat.turn_danger_alert and matchup_strat.turn_danger_alert not in aoe_alerts:
            aoe_alerts.insert(0, matchup_strat.turn_danger_alert)
        if opponent_hand_warnings:
            aoe_alerts = opponent_hand_warnings[:2] + aoe_alerts

        # 4. Sequence Optimizer with Blunder Interceptions & Secret Probing
        secret_probing_plan: SecretProbingPlan = self.secret_tracker.generate_probing_sequence(
            friendly_minions=f_minions,
            hand_cards=hand_cards,
            available_mana=current_mana,
            hero_power_available=current_mana >= 2,
        )
        seq_res = self.sequence_optimizer.evaluate_sequence(
            planned_cards=[c.as_dict() if hasattr(c, "as_dict") else {"name": getattr(c, "name", str(c))} for c in hand_cards],
            friendly_minions_can_attack=any(m.get("can_attack", True) for m in f_minions),
            hero_power_available=current_mana >= 2,
            friendly_hero_class=opponent_class,
        )
        rec_seq = seq_res.recommended_sequence
        if secret_probing_plan.has_active_secrets:
            rec_seq = [f"🛡️【探奥秘】{s.instruction}" for s in secret_probing_plan.steps] + rec_seq
        if blunder_directives:
            rec_seq = blunder_directives + rec_seq

        # 4.5. Anticipatory 2-Turn Lethal / Checkmate Engine
        two_turn_plan: TwoTurnLethalPlan = TwoTurnLethalEngine.evaluate_two_turn_lethal(
            friendly_minions=f_minions,
            enemy_taunts=[m for m in e_minions if m.get("taunt", False)],
            hand_cards=hand_cards,
            available_mana=current_mana,
            enemy_hp=enemy_hp,
            enemy_armor=0,
            enemy_hand_count=enemy_hand_count,
            enemy_class=opponent_class,
            hero_power_damage=1 if opponent_class.upper() in {"MAGE", "HUNTER"} else 0,
            friendly_hp=friendly_hp,
            enemy_board_attack=sum(m.get("atk", 0) for m in e_minions),
        )
        is_two_turn_lockout = getattr(two_turn_plan, "is_guaranteed_lockout", False)
        lockout_directive = getattr(two_turn_plan, "lockout_directive", "")
        lockout_badge = getattr(two_turn_plan, "lockout_badge", "")

        # 5. Face Pivot Point & Choke Pressure
        face_pivot = ""
        pivot_alert: Optional[BeatdownPivotAlert] = getattr(posture_res, "pivot_alert", None)
        if is_two_turn_lockout and lockout_directive:
            face_pivot = lockout_directive
        elif two_turn_plan.is_two_turn_lethal and two_turn_plan.confidence >= 0.65:
            face_pivot = two_turn_plan.recommendation
        elif pivot_alert and pivot_alert.has_pivoted:
            face_pivot = f"{pivot_alert.banner_badge} {pivot_alert.action_directive}"
        elif res_plan.choke_pressure_active:
            face_pivot = res_plan.strategic_directive
        elif f_atk >= enemy_hp * 0.45 or posture_res.posture_mode == "AGGRESSIVE":
            face_pivot = f"【走脸转折点】我方场攻达 {f_atk} 点，敌方仅剩 {enemy_hp} 血！停止被动交换，除嘲讽外全员走脸压制！"

        # 6. Minion Positioning Advice (几何站位防御系统)
        positioning = "站位指南：大怪置于两翼，低血杂毛居中（防背叛/流星/冰锥）；亡语随从放最右侧。"
        playable_minions = [c for c in hand_cards if (getattr(c, "card_type", "") or "").upper() == "MINION" and c.cost <= current_mana]
        if playable_minions and f_minions:
            p_cand = playable_minions[0]
            geom = PositioningGeometry.calculate_optimal_placement(
                board=f_minions,
                new_minion={
                    "name": p_cand.name,
                    "atk": p_cand.attack or 2,
                    "health": p_cand.health or 2,
                    "divine_shield": "DIVINE_SHIELD" in (p_cand.mechanics or []),
                    "deathrattle": "DEATHRATTLE" in (p_cand.mechanics or []),
                    "taunt": "TAUNT" in (p_cand.mechanics or []),
                    "is_magnetic": "MAGNETIC" in (p_cand.mechanics or []),
                    "is_mech": (p_cand.race or "").upper() == "MECHANICAL",
                },
                opponent_class=opponent_class,
            )
            positioning = f"📐 几何站位：打出【{p_cand.name}】{geom.slot_description}（{geom.strategic_rationale}）"

        # 6.5. Hand Reading Summary
        hand_read_str = " | ".join(opponent_hand_warnings[:2]) if opponent_hand_warnings else ""

        # 6.6. 1-Ply Multi-Branch Action Tree Search (动作树前瞻博弈搜索)
        action_tree_res: ActionTreeResult = ActionTreeSearch.search_optimal_branch(
            friendly_minions=f_minions,
            enemy_minions=e_minions,
            hand_cards=hand_cards,
            available_mana=current_mana,
            friendly_hp=friendly_hp,
            enemy_hp=enemy_hp,
            opponent_class=opponent_class,
        )

        # 6.7. Discovery Pool Radar (发现池概率雷达)
        disc_radar_res: DiscoveryProbabilityReport = DiscoveryPoolRadar.calculate_discover_odds(
            opponent_class=opponent_class,
            discover_source_card="发现牌",
        )

        # 7. Opponent Burst Damage Threshold Guard (全职业动态斩杀线防御预警)
        f_taunt_hp = sum(m.get("health", 0) for m in f_minions if m.get("taunt", False))
        burst_report: BurstThreatReport = BurstDamageGuard.evaluate_threat(
            opponent_class=opponent_class,
            current_turn=turn_number,
            opponent_board_atk=e_atk,
            friendly_hp=friendly_hp,
            friendly_armor=0,
            friendly_taunt_hp=f_taunt_hp,
            opponent_has_coin=False,
        )
        burst_safety = burst_report.survival_directive if burst_report.threat_tier in {"CRITICAL_LETHAL", "HIGH_DANGER"} else ""
        if not burst_safety and "🚨" in matchup_strat.burst_danger_warning:
            burst_safety = matchup_strat.burst_danger_warning

        # 7.2. Live Discover & Adapt Dynamic Priority Guidance
        is_lethal_peril = (burst_report.lethal_deficit >= 0)
        disc_guidance: DiscoverGuidance = LiveDiscoverAdvisor.evaluate_discover_need(
            friendly_hp=friendly_hp,
            enemy_hp=enemy_hp,
            friendly_board_atk=f_atk,
            enemy_board_atk=e_atk,
            hand_size=len(hand_cards),
            is_facing_lethal=is_lethal_peril,
        )

        # 7.2.1 In-Match Discover Tri-Pick Lens
        sample_discover_cards = [c for c in hand_cards[:3]] if len(hand_cards) >= 3 else []
        discover_tri_pick_res: Optional[DiscoverTriPickResult] = None
        if sample_discover_cards:
            discover_tri_pick_res = LiveDiscoverAdvisor.evaluate_tri_pick(
                candidate_cards=sample_discover_cards,
                friendly_hp=friendly_hp,
                enemy_hp=enemy_hp,
                friendly_board_atk=f_atk,
                enemy_board_atk=e_atk,
                hand_size=len(hand_cards),
                available_mana=current_mana,
                card_db=self.card_db,
                is_facing_lethal=is_lethal_peril,
            )

        # Real-Time Live Win Rate Calculation (实时对局即时胜率)
        live_winrate: WinRateReport = WinRateEstimator.calculate_winrate(
            friendly_hp=friendly_hp,
            enemy_hp=enemy_hp,
            friendly_board_atk=f_atk,
            enemy_board_atk=e_atk,
            friendly_minion_count=len(f_minions),
            enemy_minion_count=len(e_minions),
            friendly_hand_count=len(hand_cards),
            enemy_hand_count=enemy_hand_count,
            current_turn=turn_number,
            has_immediate_lethal=False,
            has_two_turn_lethal=is_two_turn_lockout,
        )
        winrate_delta = round(live_winrate.winrate_pct - getattr(self, "_last_winrate_pct", 50.0), 1)
        self._last_winrate_pct = live_winrate.winrate_pct

        # 7.3. Variance & Risk-Tolerance Policy (Driven by Live Win Rate)
        planned_acts = action_tree_res.best_branch.action_sequence if action_tree_res.best_branch else []
        variance_rep: VariancePolicyReport = VarianceEvaluator.evaluate_risk_policy(
            winrate_pct=live_winrate.winrate_pct,
            planned_actions=planned_acts,
        )

        # 7.4 Overextension Guard (极小化极大防过度铺场熔断器)
        next_m = min(10, current_mana + 1)
        overextension_res: OverextensionAssessment = AOEOverextensionGuard.check_overextension(
            friendly_minions=f_minions,
            opponent_class=opponent_class,
            next_turn_mana=next_m,
            enemy_hp=enemy_hp,
        )

        # 7.4.1 Fatigue & Endgame Horizon (疲劳与不可逆终局推演)
        fatigue_rep: FatigueEndgameReport = FatigueEndgameHorizon.calculate_endgame_horizon(
            my_deck_count=max(1, 30 - turn_number - 3),
            my_hand=[c.name for c in hand_cards],
            my_hp=friendly_hp,
            my_armor=0,
            opp_deck_count=max(1, 30 - turn_number - 3),
            opp_hand_count=enemy_hand_count,
            opp_hp=enemy_hp,
            opp_armor=0,
            opp_class=opponent_class,
            current_turn=turn_number,
        )

        # 7.4.2 Bayesian Hand Role Fingerprint Report
        bayesian_hand_rep: HandAgeIntelReport = self.hand_age_intel.update_turn(turn_number)

        # 7.5. Macro Tactical Compass (Greed vs Tempo Balance)
        from .tactical_compass import TacticalCompass, TacticalCompassReport
        compass_rep: TacticalCompassReport = TacticalCompass.evaluate_compass(
            friendly_hp=friendly_hp,
            enemy_hp=enemy_hp,
            friendly_board_atk=f_atk,
            enemy_board_atk=e_atk,
            friendly_hand_count=len(hand_cards),
            enemy_hand_count=enemy_hand_count,
            enemy_minion_count=len(e_minions),
            current_turn=turn_number,
        )

        def _format_beatdown_clock(friendly_clock: int, enemy_threat: int) -> str:
            fc_str = "--" if friendly_clock >= 15 or friendly_clock <= 0 else f"{friendly_clock}回合"
            ec_str = "安全" if enemy_threat >= 15 or enemy_threat <= 0 else f"{enemy_threat}回合"
            if fc_str == "--" and ec_str == "安全":
                return "斩杀时钟: 我方 -- | 敌方 安全"
            return f"我方斩杀钟: {fc_str} | 敌方威胁钟: {ec_str}"

        # 8. Real-time Tactical Optimizations Suite
        # 8.1 Next-Turn Key Threat Cards
        next_turn_threats = BurstDamageGuard.get_next_turn_key_cards(opponent_class, min(10, turn_number + 1))

        # 8.2 Draw & RNG First Directive
        draw_directive = getattr(seq_res, "draw_first_directive", "")

        # 8.3 Lethal Cushion & Safety Margin Analysis
        enemy_effective_hp = enemy_hp
        can_atk_minions = [m for m in f_minions if m.get("can_attack", True)]
        board_face_dmg = sum(m.get("attack", 0) for m in can_atk_minions)
        t1_total = getattr(two_turn_plan, "turn1_face_damage", 0) or board_face_dmg
        overkill = t1_total - enemy_effective_hp
        if overkill > 0 and t1_total >= enemy_effective_hp:
            lethal_cushion_str = f"🛡️ 溢出斩杀 (+{overkill} 点伤害，安全容错高)"
        elif overkill == 0 and t1_total >= enemy_effective_hp and enemy_effective_hp > 0:
            lethal_cushion_str = "🎯 精准斩杀 (刚好斩杀，无伤害容错)"
        elif getattr(two_turn_plan, "is_two_turn_lethal", False):
            lethal_cushion_str = f"⏳ 两回合叫杀 (下轮保底斩杀 {two_turn_plan.projected_turn2_damage} 点)"
        elif enemy_effective_hp > t1_total and t1_total > 0:
            lethal_cushion_str = f"⚔️ 斩杀差距: 还差 {enemy_effective_hp - t1_total} 点伤害"
        else:
            lethal_cushion_str = ""

        # 8.4 Checklist Steps & Dual Plan B Steps
        if action_tree_res.best_branch and action_tree_res.best_branch.action_sequence:
            checklist_steps = list(action_tree_res.best_branch.action_sequence)
        elif rec_seq:
            checklist_steps = list(rec_seq[:4])
        else:
            checklist_steps = []

        if action_tree_res.alternative_branches and action_tree_res.alternative_branches[0].action_sequence:
            plan_b_steps = list(action_tree_res.alternative_branches[0].action_sequence)
        else:
            plan_b_steps = []

        # 8.5 RNG & Discover Cumulative Probability Analysis
        parsed_enemies = self._parse_board_minions(enemy_board)
        rng_report = RngProbabilityEngine.scan_hand_for_rng(hand_cards, parsed_enemies, opponent_class)

        # 8.6 Personal Weakness & Habit Reminder
        personal_alert = PersonalWeaknessProfiler.get_instance().get_realtime_turn_alert(
            turn=turn_number,
            current_mana=current_mana,
            opponent_class=opponent_class,
        ) or ""

        # 8.7 Board Resilience & Anti-Wipe Monte Carlo Simulation
        parsed_friendlies = self._parse_board_minions(friendly_board)
        rem_hand = max(0, len(hand_cards) - len(checklist_steps))
        resilience_rep = BoardResilienceEvaluator.evaluate_board_resilience(
            friendly_minions=parsed_friendlies,
            remaining_hand_size=rem_hand,
            opponent_class=opponent_class,
            opponent_mana=turn_number + 1,
        )
        if action_tree_res.best_branch:
            action_tree_res.best_branch.resilience_score = resilience_rep.resilience_score
            action_tree_res.best_branch.resilience_badge = resilience_rep.badge_text

        # 8.8 Hypergeometric Odds, Decision Tree Topology & Tilt Guard
        from .hypergeometric_odds import HypergeometricOddsEngine
        from .tactical_tree_visualizer import TacticalDecisionTree
        from .tilt_guard import TiltGuard

        hyper_rep = HypergeometricOddsEngine.evaluate_deck_odds(
            remaining_deck=deck_cards,
            enemy_hp=enemy_hp,
            friendly_hp=friendly_hp,
            enemy_board_attack=e_atk,
            draws_next_turn=1,
        )

        tree_root = TacticalDecisionTree.build_tree(
            action_tree_res=action_tree_res,
            current_mana=current_mana,
            friendly_hp=friendly_hp,
            enemy_hp=enemy_hp,
            opponent_class=opponent_class,
        )
        tree_dict = TacticalDecisionTree.to_dict(tree_root)
        tilt_rep = TiltGuard.get_instance().evaluate_tilt()

        # 8.7. Monte Carlo RNG Simulation & VaR
        from .monte_carlo_var import MonteCarloVarEngine, MonteCarloVarReport
        var_rep: Optional[MonteCarloVarReport] = None
        var_summary_str = ""
        for c in hand_cards:
            if c.cost <= current_mana:
                c_u = (c.name or "").upper()
                if "奥术飞弹" in c_u or "ARCANE MISSILES" in c_u or "疯狂投弹者" in c_u:
                    var_rep = MonteCarloVarEngine.simulate_random_missiles(
                        action_name=c.name or "随机弹幕",
                        missile_count=3,
                        damage_per_missile=1,
                        enemy_minions=[{"name": m.get("name", ""), "hp": m.get("health", 1), "divine_shield": m.get("divine_shield", False)} for m in e_minions],
                        enemy_hero_hp=enemy_hp,
                    )
                    break
                elif "闪电风暴" in c_u or "LIGHTNING STORM" in c_u:
                    var_rep = MonteCarloVarEngine.simulate_aoe_damage_roll(
                        spell_name=c.name or "闪电风暴",
                        min_dmg=2,
                        max_dmg=3,
                        enemy_minions=[{"hp": m.get("health", 1), "divine_shield": m.get("divine_shield", False)} for m in e_minions],
                    )
                    break
        if var_rep:
            var_summary_str = f"{var_rep.risk_badge}: {var_rep.strategic_verdict}"

        # 8.9 First-Principles Ultimate Engines (v22)
        played_minions_list = []
        spent_for_ghost = 0
        if mana_eff_plan and mana_eff_plan.current_turn_plays:
            for c in mana_eff_plan.current_turn_plays:
                spent_for_ghost += c.cost
                if getattr(c, "card_type", "") == "MINION":
                    played_minions_list.append({
                        "name": getattr(c, "name", "随从"),
                        "attack": getattr(c, "attack", 2) or 2,
                        "health": getattr(c, "health", 2) or 2,
                    })

        ghost_board_res = TacticalGhostBoardSimulator.simulate_turn_outcome(
            friendly_minions=f_minions,
            enemy_minions=e_minions,
            played_minions=played_minions_list,
            optimal_trades=trade_steps,
            trade_actions=trade_res.actions,
            face_damage=trade_res.total_face_damage,
            current_mana=current_mana,
            spent_mana=spent_for_ghost,
            enemy_hp=enemy_hp,
        )

        punish_envelope_res = OpponentPunishEnvelopeCalculator.calculate_envelope(
            opponent_class=opponent_class,
            current_turn_mana=current_mana,
            enemy_board_attack=e_atk,
        )

        mana_leak_res = ZeroLeakManaAuditor.audit_mana_spending(
            available_mana=current_mana,
            spent_mana=spent_for_ghost,
            hand_cards=hand_cards,
            hero_power_cost=2,
            hero_power_available=True,
        )

        # Group the real remaining deck by card id -> (CardInfo, copies)
        _deck_groups: Dict[str, List[Any]] = {}
        for c in deck_cards:
            key = getattr(c, "id", "") or getattr(c, "name", "")
            if key in _deck_groups:
                _deck_groups[key][1] += 1
            else:
                _deck_groups[key] = [c, 1]
        rem_deck_tuples = [(g[0], g[1]) for g in _deck_groups.values()]
        miracle_out_res = MiracleOutFilter.evaluate_miracle_outs(
            winrate_pct=live_winrate.winrate_pct,
            remaining_cards=rem_deck_tuples,
            player_hp=friendly_hp,
            enemy_hp=enemy_hp,
            friendly_board_atk=f_atk,
            enemy_board_atk=e_atk,
        )

        if use_llm and self._gemini_client:
            try:
                rec = self._evaluate_play_with_llm(
                    turn_number, current_mana, hand_cards, friendly_board, enemy_board, opponent_class
                )
                rec.posture_mode = posture_res.posture_mode
                rec.beatdown_clock = _format_beatdown_clock(posture_res.friendly_clock_turns, posture_res.enemy_threat_turns)
                rec.optimal_trades = trade_steps
                rec.aoe_threats = aoe_alerts
                rec.play_sequence = seq_res.recommended_sequence
                rec.positioning_advice = positioning
                rec.face_pivot_warning = face_pivot
                rec.burst_safety_warning = burst_safety
                rec.matchup_blueprint = matchup_strat.core_gameplan
                rec.mana_efficiency_advice = mana_eff_plan.advice_text if mana_eff_plan else ""
                rec.punish_assessment = punish_res.tactical_advice
                rec.card_advantage_directive = res_plan.strategic_directive
                rec.blunder_alerts = blunder_directives
                rec.two_turn_lethal_advice = two_turn_plan.recommendation if two_turn_plan.is_two_turn_lethal else ""
                rec.mulligan_hand_reading = hand_read_str
                rec.action_tree_summary = action_tree_res.comparison_summary
                rec.discovery_radar_warning = disc_radar_res.tactical_warning
                rec.play_sequence = rec_seq
                rec.best_branch = action_tree_res.best_branch
                rec.alt_branch = action_tree_res.alternative_branches[0] if action_tree_res.alternative_branches else None
                rec.compass_directive = compass_rep.macro_directive
                rec.opponent_burst_danger = burst_report
                rec.discover_guidance = disc_guidance
                rec.variance_policy = variance_rep.variance_directive
                rec.checklist_steps = checklist_steps
                rec.draw_first_directive = draw_directive
                rec.next_turn_threat_cards = next_turn_threats
                rec.lethal_cushion = lethal_cushion_str
                rec.plan_b_steps = plan_b_steps
                rec.rng_report = rng_report
                rec.personal_weakness_reminder = personal_alert
                rec.resilience_report = resilience_rep
                rec.resilience_verdict = resilience_rep.detailed_verdict
                rec.hypergeometric_report = hyper_rep
                rec.hypergeometric_summary = hyper_rep.gamble_recommendation
                rec.tilt_summary = f"{tilt_rep.tier_label}: {tilt_rep.action_directive}"
                rec.mind_reading_summary = hand_read_str
                rec.decision_tree_dict = tree_dict
                rec.two_turn_lockout = is_two_turn_lockout
                rec.two_turn_lockout_directive = lockout_directive
                rec.two_turn_lockout_badge = lockout_badge
                rec.mana_flow_plan = mana_eff_plan
                rec.mana_flow_tag = getattr(mana_eff_plan, "flow_tag", "") if mana_eff_plan else ""
                rec.mana_flow_preview = getattr(mana_eff_plan, "step_preview", "") if mana_eff_plan else ""
                rec.beatdown_pivot_alert = pivot_alert
                rec.beatdown_pivot_text = getattr(pivot_alert, "action_directive", "") if pivot_alert else ""
                rec.discover_tri_pick = discover_tri_pick_res
                rec.secret_probing_plan = secret_probing_plan
                rec.secret_probing_directive = getattr(secret_probing_plan, "safest_attack_directive", "")
                rec.live_winrate_report = live_winrate
                rec.live_winrate_pct = live_winrate.winrate_pct
                rec.live_winrate_delta = winrate_delta
                rec.live_winrate_tier = live_winrate.win_tier
                rec.live_winrate_driver = live_winrate.key_advantage_factor
                rec.overextension_assessment = overextension_res
                rec.fatigue_endgame_report = fatigue_rep
                rec.bayesian_hand_report = bayesian_hand_rep
                rec.ghost_board_snapshot = ghost_board_res
                rec.opponent_punish_envelope = punish_envelope_res
                rec.mana_leak_audit = mana_leak_res
                rec.miracle_out_report = miracle_out_res
                rec.data_complete = data_complete
                rec.data_warnings = data_warnings
                return rec
            except Exception as e:
                logger.warning(f"LLM Play call failed: {e}. Using fallback.")

        # Heuristic play fallback - powered by 2-Turn Continuous Mana Efficiency
        suggested = []
        spent_mana = 0
        if mana_eff_plan and mana_eff_plan.current_turn_plays:
            for c in mana_eff_plan.current_turn_plays:
                stats_str = f" {c.attack}/{c.health}" if c.attack is not None else ""
                suggested.append(f"打出: 【{c.name}】 ({c.cost}费{stats_str})")
            spent_mana = mana_eff_plan.current_spent
            rem_after = current_mana - spent_mana
            if rem_after >= 2:
                suggested.append(f"使用【英雄技能】(消耗 2 费，剩余 {rem_after - 2} 费)")
        else:
            affordable = [c for c in hand_cards if c.cost <= current_mana]
            affordable.sort(key=lambda c: c.cost, reverse=True)
            for c in affordable:
                if spent_mana + c.cost <= current_mana:
                    stats_str = f" {c.attack}/{c.health}" if c.attack is not None else ""
                    suggested.append(f"打出: 【{c.name}】 ({c.cost}费{stats_str})")
                    spent_mana += c.cost
            remaining_mana = current_mana - spent_mana
            if remaining_mana >= 2:
                suggested.append(f"使用【英雄技能】(消耗 2 费，剩余 {remaining_mana - 2} 费)")
            elif not suggested:
                if current_mana >= 2:
                    suggested = ["打出: 使用【英雄技能】压制场面或过牌"]
                else:
                    suggested = ["当前费用不足以打出手牌，考虑转甲/射箭或等待下回合"]

        # Risk warning synthesis
        if aoe_alerts:
            warning = aoe_alerts[0]
        else:
            opp_cn = get_class_cn(opponent_class)
            warning = f"留意【{opp_cn}】下回合关键解牌与斩杀线"

        mana_text = mana_eff_plan.advice_text if mana_eff_plan else f"规划本回合消耗 {spent_mana}/{current_mana} 费，追求法力利用率最大化"
        trade_text = trade_res.tactical_summary or "优先以小换大进行随从交换"

        if not checklist_steps:
            checklist_steps = list(suggested)

        return PlayRecommendation(
            suggested_plays=suggested,
            mana_plan=mana_text,
            trading_plan=trade_text,
            risk_warning=f"⚠️ {warning}",
            raw_reasoning="[内置战术逻辑引擎提供]",
            posture_mode=posture_res.posture_mode,
            beatdown_clock=_format_beatdown_clock(posture_res.friendly_clock_turns, posture_res.enemy_threat_turns),
            optimal_trades=trade_steps,
            aoe_threats=aoe_alerts,
            play_sequence=rec_seq,
            positioning_advice=positioning,
            face_pivot_warning=face_pivot,
            burst_safety_warning=burst_safety,
            matchup_blueprint=matchup_strat.core_gameplan,
            mana_efficiency_advice=mana_eff_plan.advice_text if mana_eff_plan else "",
            punish_assessment=punish_res.tactical_advice,
            card_advantage_directive=res_plan.strategic_directive,
            blunder_alerts=blunder_directives,
            two_turn_lethal_advice=two_turn_plan.recommendation if two_turn_plan.is_two_turn_lethal else "",
            mulligan_hand_reading=hand_read_str,
            action_tree_summary=action_tree_res.comparison_summary,
            discovery_radar_warning=disc_radar_res.tactical_warning,
            best_branch=action_tree_res.best_branch,
            alt_branch=action_tree_res.alternative_branches[0] if action_tree_res.alternative_branches else None,
            compass_directive=compass_rep.macro_directive,
            opponent_burst_danger=burst_report,
            discover_guidance=disc_guidance,
            variance_policy=variance_rep.variance_directive,
            checklist_steps=checklist_steps,
            draw_first_directive=draw_directive,
            next_turn_threat_cards=next_turn_threats,
            lethal_cushion=lethal_cushion_str,
            plan_b_steps=plan_b_steps,
            rng_report=rng_report,
            personal_weakness_reminder=personal_alert,
            resilience_report=resilience_rep,
            resilience_verdict=resilience_rep.detailed_verdict,
            hypergeometric_report=hyper_rep,
            hypergeometric_summary=hyper_rep.gamble_recommendation,
            tilt_summary=f"{tilt_rep.tier_label}: {tilt_rep.action_directive}",
            mind_reading_summary=hand_read_str,
            decision_tree_dict=tree_dict,
            var_report=var_rep,
            var_summary=var_summary_str,
            two_turn_lockout=is_two_turn_lockout,
            two_turn_lockout_directive=lockout_directive,
            two_turn_lockout_badge=lockout_badge,
            mana_flow_plan=mana_eff_plan,
            mana_flow_tag=getattr(mana_eff_plan, "flow_tag", "") if mana_eff_plan else "",
            mana_flow_preview=getattr(mana_eff_plan, "step_preview", "") if mana_eff_plan else "",
            beatdown_pivot_alert=pivot_alert,
            beatdown_pivot_text=getattr(pivot_alert, "action_directive", "") if pivot_alert else "",
            discover_tri_pick=discover_tri_pick_res,
            secret_probing_plan=secret_probing_plan,
            secret_probing_directive=getattr(secret_probing_plan, "safest_attack_directive", ""),
            live_winrate_report=live_winrate,
            live_winrate_pct=live_winrate.winrate_pct,
            live_winrate_delta=winrate_delta,
            live_winrate_tier=live_winrate.win_tier,
            live_winrate_driver=live_winrate.key_advantage_factor,
            overextension_assessment=overextension_res,
            fatigue_endgame_report=fatigue_rep,
            bayesian_hand_report=bayesian_hand_rep,
            ghost_board_snapshot=ghost_board_res,
            opponent_punish_envelope=punish_envelope_res,
            mana_leak_audit=mana_leak_res,
            miracle_out_report=miracle_out_res,
            data_complete=data_complete,
            data_warnings=data_warnings,
        )

    def evaluate_play_turn_stream(
        self,
        turn_number: int,
        current_mana: int,
        hand_cards: List[CardInfo],
        friendly_board: List[str],
        enemy_board: List[str],
        opponent_class: str = "UNKNOWN",
        token_callback: Optional[Callable[[str], None]] = None,
    ) -> PlayRecommendation:
        """
        Streamed real-time tactical evaluation with token-by-token output.
        """
        if use_llm and self._gemini_client:
            try:
                hand_meta = "\n".join([f"- {c.name} ({c.cost}费 {c.card_type}): {c.clean_text}" for c in hand_cards])
                friendly_str = ", ".join(friendly_board) if friendly_board else "空场"
                enemy_str = ", ".join(enemy_board) if enemy_board else "空场"
                prompt = f"""你是《炉石传说》全球顶尖职业选手。请为本回合提供最佳战术推演。
【回合数】: 第 {turn_number} 回合
【可用水晶】: {current_mana}
【对手职业】: {opponent_class}
【我方场面】: {friendly_str}
【敌方场面】: {enemy_str}
【我方可用手牌】:
{hand_meta}

请以 JSON 格式输出打法建议：
{{
  "suggested_plays": ["出牌动作1", "出牌动作2"],
  "mana_plan": "法力利用规划",
  "trading_plan": "随从交换细节",
  "risk_warning": "防AOE与对手下回合斩杀提示"
}}
"""
                response = self._gemini_client.generate_content(prompt, stream=True)
                chunks = []
                for chunk in response:
                    text_chunk = getattr(chunk, "text", "")
                    if text_chunk:
                        chunks.append(text_chunk)
                        if token_callback:
                            token_callback(text_chunk)
                accumulated = "".join(chunks)
                parsed = self._extract_json(accumulated)
                if parsed:
                    return PlayRecommendation(
                        suggested_plays=parsed.get("suggested_plays", []),
                        mana_plan=parsed.get("mana_plan", ""),
                        trading_plan=parsed.get("trading_plan", ""),
                        risk_warning=parsed.get("risk_warning", ""),
                        raw_reasoning=accumulated,
                    )
            except Exception as e:
                logger.warning(f"Streaming LLM Play call failed: {e}. Falling back to heuristic.")

        rec = self.evaluate_play_turn(
            turn_number, current_mana, hand_cards, friendly_board, enemy_board, opponent_class
        )
        if token_callback:
            for s in rec.suggested_plays:
                token_callback(f"{s}\n")
        return rec

    def _evaluate_play_with_llm(
        self,
        turn_number: int,
        current_mana: int,
        hand_cards: List[CardInfo],
        friendly_board: List[str],
        enemy_board: List[str],
        opponent_class: str,
    ) -> PlayRecommendation:
        hand_meta = "\n".join([f"- {c.name} ({c.cost}费 {c.card_type}): {c.clean_text}" for c in hand_cards])
        friendly_str = ", ".join(friendly_board) if friendly_board else "空场"
        enemy_str = ", ".join(enemy_board) if enemy_board else "空场"

        prompt = f"""你是《炉石传说》全球顶尖职业选手。请为本回合提供最佳战术推演。
【回合数】: 第 {turn_number} 回合
【可用水晶】: {current_mana}
【对手职业】: {opponent_class}
【我方场面】: {friendly_str}
【敌方场面】: {enemy_str}
【我方可用手牌】:
{hand_meta}

请以 JSON 格式输出打法建议：
{{
  "suggested_plays": ["出牌动作1", "出牌动作2"],
  "mana_plan": "法力利用规划",
  "trading_plan": "随从交换细节",
  "risk_warning": "防AOE与对手下回合斩杀提示"
}}
"""
        genai = _get_genai()
        resp = None
        models_to_try = [self.model_name, "gemini-2.0-flash", "gemini-1.5-flash-latest", "gemini-2.5-flash", "gemini-1.5-pro"]
        for m_name in models_to_try:
            try:
                clean_name = m_name.replace("models/", "").strip()
                if not self._gemini_model or getattr(self._gemini_model, "_model_name", "") != f"models/{clean_name}":
                    if genai:
                        self._gemini_model = genai.GenerativeModel(model_name=clean_name, generation_config={"temperature": self.temperature})
                if self._gemini_model:
                    resp = self._gemini_model.generate_content(prompt)
                    if resp:
                        self.model_name = clean_name
                        break
            except Exception as e:
                if "404" in str(e) or "not found" in str(e).lower():
                    continue
                logger.debug(f"LLM model attempt {m_name} failed: {e}")

        if not resp:
            raise RuntimeError("All Gemini candidate models failed to generate content")

        parsed = self._extract_json(resp.text.strip()) or {}

        return PlayRecommendation(
            suggested_plays=parsed.get("suggested_plays", ["稳固场面节奏"]),
            mana_plan=parsed.get("mana_plan", "合理倾泻法力"),
            trading_plan=parsed.get("trading_plan", "优质交换控场"),
            risk_warning=parsed.get("risk_warning", "注意敌方关键解牌"),
            raw_reasoning=resp.text.strip(),
        )

    # =========================================================================
    # Utility Helpers
    # =========================================================================
    @staticmethod
    def calculate_mana_curve(deck: List[CardInfo]) -> List[int]:
        """Calculates 8-bucket mana curve: [0, 1, 2, 3, 4, 5, 6, 7+]"""
        curve = [0] * 8
        for card in deck:
            cost = card.cost
            if cost < 0:
                cost = 0
            bucket = min(cost, 7)
            curve[bucket] += 1
        return curve

    @staticmethod
    def _extract_json(text: str) -> Optional[Dict[str, Any]]:
        """Safely extracts JSON payload from LLM markdown code blocks."""
        try:
            # Try direct load
            return json.loads(text)
        except Exception:
            pass

        # Look for ```json ... ```
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except Exception:
                pass

        # Search for first { to last }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except Exception:
                pass

        return None

    def _deserialize_draft_recommendation(self, data: Dict[str, Any]) -> DraftRecommendation:
        evals = []
        for e in data.get("cards_evaluations", []):
            e_dict = dict(e)
            sat_data = e_dict.get("saturation_assessment")
            if isinstance(sat_data, dict):
                e_dict["saturation_assessment"] = SaturationAssessment(**sat_data)
            evals.append(CardEvaluation(**e_dict))
        return DraftRecommendation(
            best_card_index=data.get("best_card_index", 0),
            best_card_name=data.get("best_card_name", ""),
            cards_evaluations=evals,
            curve_advice=data.get("curve_advice", ""),
            overall_strategy=data.get("overall_strategy", ""),
            is_cached=True,
            raw_reasoning=data.get("raw_reasoning", ""),
        )
