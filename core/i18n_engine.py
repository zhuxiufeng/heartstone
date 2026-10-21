"""
I18nEngine: Internationalization & Dual-Language Localization Engine.
Supports dynamic hot-switching between Simplified Chinese (zh-CN) and English (en-US)
across Overlay UI, Web Companion, Voice Coach, and Replay Reports.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("I18nEngine")


TRANSLATION_TABLE: Dict[str, Dict[str, str]] = {
    "zh-CN": {
        # App & Window
        "app_title": "炉石传说 竞技场大师 AI 助手",
        "tab_draft": "选牌建议",
        "tab_play": "对局战术",
        "tab_history": "对局历史",
        "tab_settings": "偏好设置",
        "btn_capsule_mode": "极简胶囊",
        "btn_expand_mode": "展开全景",
        "btn_tactical_tree": "战术决策树",
        "btn_review_dashboard": "复盘仪表盘",
        "btn_obs_overlay": "OBS推流面板",

        # Game Phase
        "phase_mulligan": "起手调度",
        "phase_early": "前期节奏争夺",
        "phase_mid": "中期资源交换",
        "phase_late": "残局斩杀冲刺",
        "phase_fatigue": "疲劳决战时刻",

        # Posture
        "posture_aggressive": "全军突击抢脸 (Aggressive)",
        "posture_control": "稳健控场交换 (Control)",
        "posture_all_in": "孤注一掷搏命 (All-In)",
        "posture_balanced": "滚雪球均势 (Balanced)",

        # Topdeck & Odds
        "topdeck_title": "牌库精算与神抽矩阵",
        "topdeck_miracle": "翻盘神抽",
        "topdeck_lethal": "终结斩杀",
        "topdeck_aoe": "范围清场",
        "topdeck_survival": "护脸续命",
        "topdeck_brick": "暂时鬼抽/卡手",
        "topdeck_ratio": "随从/法术/武器",

        # Multi-Turn Lookahead
        "lookahead_title": "多回合前瞻推演",
        "lookahead_counter_threat": "对手关键反打",
        "lookahead_survival_rate": "T+1场面存活率",
        "lookahead_anti_punish": "防反制保底策略",

        # Leak Buster
        "leak_title": "伏笔盲区审计",
        "leak_score": "无瑕度评分",
        "leak_missed_lethal": "错失直接斩杀",
        "leak_draw_order": "未先过牌次序伏笔",
        "leak_aura_order": "光环随从后置伏笔",
        "leak_shield_waste": "高攻破圣盾损耗",
        "leak_aoe_overextend": "高危回合过度铺场",
        "leak_mana_float": "严重空余法力水晶",

        # Voice Coach
        "coach_lethal": "警告：当前场面伤害已达斩杀线，直接斩杀敌方英雄！",
        "coach_aoe": "注意防范对手下回合高危全场清场！",
        "coach_tilt": "检测到连续受挫心态波动，深呼吸保持稳健打法！",

        # Hotkeys
        "hotkey_overlay_hint": "Ctrl+Shift+H: 显隐悬浮窗",
        "hotkey_tree_hint": "Ctrl+Shift+T: 决策树",
        "hotkey_snapshot_hint": "Ctrl+Shift+S: 战局诊断截图",
    },
    "en-US": {
        # App & Window
        "app_title": "Hearthstone Arena Grandmaster AI",
        "tab_draft": "Draft Assistant",
        "tab_play": "Combat Tactics",
        "tab_history": "Match History",
        "tab_settings": "Settings",
        "btn_capsule_mode": "Capsule HUD",
        "btn_expand_mode": "Expand Full",
        "btn_tactical_tree": "Decision Tree",
        "btn_review_dashboard": "Review Dashboard",
        "btn_obs_overlay": "OBS Overlay",

        # Game Phase
        "phase_mulligan": "Mulligan Phase",
        "phase_early": "Early Game (T1-T4)",
        "phase_mid": "Mid Game (T5-T7)",
        "phase_late": "Late Game (T8+)",
        "phase_fatigue": "Fatigue Showdown",

        # Posture
        "posture_aggressive": "Aggressive Face Rush",
        "posture_control": "Board Control Trading",
        "posture_all_in": "Desperation All-In",
        "posture_balanced": "Snowball Balanced",

        # Topdeck & Odds
        "topdeck_title": "Remaining Deck & Topdeck Matrix",
        "topdeck_miracle": "Miracle Out",
        "topdeck_lethal": "Lethal Finisher",
        "topdeck_aoe": "Board Clear",
        "topdeck_survival": "Survival / Taunt",
        "topdeck_brick": "Brick / Inactive",
        "topdeck_ratio": "Minion/Spell/Weapon",

        # Multi-Turn Lookahead
        "lookahead_title": "Multi-Turn Lookahead",
        "lookahead_counter_threat": "Opponent Punish Threat",
        "lookahead_survival_rate": "T+1 Survival Rate",
        "lookahead_anti_punish": "Anti-Punish Plan B",

        # Leak Buster
        "leak_title": "Leak Buster Audit",
        "leak_score": "Tactical Flawless Score",
        "leak_missed_lethal": "Missed Direct Lethal",
        "leak_draw_order": "Suboptimal Draw Order",
        "leak_aura_order": "Aura Played After Attacks",
        "leak_shield_waste": "Divine Shield Overkill",
        "leak_aoe_overextend": "Overextended into Heavy Sweeper",
        "leak_mana_float": "Heavy Mana Floated",

        # Voice Coach
        "coach_lethal": "Lethal alert: We have exact lethal damage on board and in hand!",
        "coach_aoe": "Warning: Expect heavy on-curve board wipe next turn!",
        "coach_tilt": "Tilt alert detected. Take a breath and stick to high-EV lines.",

        # Hotkeys
        "hotkey_overlay_hint": "Ctrl+Shift+H: Toggle Overlay",
        "hotkey_tree_hint": "Ctrl+Shift+T: Decision Tree",
        "hotkey_snapshot_hint": "Ctrl+Shift+S: Diagnostic Snapshot",
    },
}


class I18nEngine:
    """Manages multi-language string lookup and locale state."""

    _instance: Optional[I18nEngine] = None

    def __init__(self, initial_locale: str = "zh-CN") -> None:
        self._current_locale = initial_locale if initial_locale in TRANSLATION_TABLE else "zh-CN"

    @classmethod
    def get_instance(cls) -> I18nEngine:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_locale(self, locale_code: str) -> bool:
        if locale_code in TRANSLATION_TABLE:
            self._current_locale = locale_code
            logger.info(f"I18n locale switched to: {locale_code}")
            return True
        logger.warning(f"Unsupported locale code: {locale_code}")
        return False

    def get_locale(self) -> str:
        return self._current_locale

    def get_available_locales(self) -> List[Dict[str, str]]:
        return [
            {"code": "zh-CN", "name": "简体中文 (Chinese)"},
            {"code": "en-US", "name": "English (US)"},
        ]

    def translate(self, key: str, default: Optional[str] = None, **kwargs: Any) -> str:
        loc_table = TRANSLATION_TABLE.get(self._current_locale, TRANSLATION_TABLE["zh-CN"])
        val = loc_table.get(key)
        if val is None:
            # Fallback to zh-CN
            val = TRANSLATION_TABLE["zh-CN"].get(key, default or key)
        if kwargs:
            try:
                return val.format(**kwargs)
            except Exception:
                return val
        return val


def t(key: str, default: Optional[str] = None, **kwargs: Any) -> str:
    """Convenience helper for quick translation lookup."""
    return I18nEngine.get_instance().translate(key, default=default, **kwargs)
