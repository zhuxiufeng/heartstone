"""
Opponent Hover Telemetry & Intent Radar (对手鼠标悬浮微操轨迹与潜意识意图嗅探)
- Intercepts and parses opponent in-game cursor targeting, card hovers, and arrow sweeps.
- Decodes subconscious micro-intents: Burst Lethal Math, Hard Removal Targeting, AOE Calculation, Hesitation Pass.
- Triggers instant defensive warnings (e.g. opponent counting lethal burst; must play taunt/heal).
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Any, Optional


class SubconsciousIntent(str, Enum):
    BURST_LETHAL_MATH = "BURST_LETHAL_MATH"            # 心算斩杀直伤: 在我方英雄与手牌间反复划线
    HARD_REMOVAL_TARGETING = "HARD_REMOVAL_TARGETING"  # 单解锁定: 悬浮单解法术并对准我方核心大哥
    AOE_CALCULATION = "AOE_CALCULATION"                # 清场算血: 鼠标依次扫过我方所有随从血量
    HESITATION_PASS = "HESITATION_PASS"                # 纠结卡手: 频繁切牌却无计可施，大概率卡手
    STANDARD_PLAY = "STANDARD_PLAY"                    # 常规操作: 正常随从交换与按费出牌


@dataclass
class OpponentIntentAlert:
    intent: SubconsciousIntent
    intent_label: str
    threat_tier: str  # CRITICAL, HIGH, MODERATE, LOW
    confidence_pct: float
    target_entity: Optional[str]
    warning_spoken_line: str
    defensive_countermeasure: str
    summary_markdown: str


class HoverIntentRadar:
    """
    Decodes opponent real-time telemetry into psychological and tactical intentions.
    """

    @classmethod
    def analyze_hover_telemetry(
        cls,
        hover_events: Optional[List[Dict[str, Any]]] = None,
        player_health: int = 20,
        friendly_board: Optional[List[Dict[str, Any]]] = None,
    ) -> OpponentIntentAlert:
        """
        Inspects opponent cursor patterns during the current turn.
        """
        events = hover_events or []
        board = friendly_board or []

        if not events:
            return OpponentIntentAlert(
                intent=SubconsciousIntent.STANDARD_PLAY,
                intent_label="常规正常操作",
                threat_tier="LOW",
                confidence_pct=60.0,
                target_entity=None,
                warning_spoken_line="",
                defensive_countermeasure="保持常规战术推演。",
                summary_markdown="**对手意图雷达**: 暂未捕捉到异常悬浮微操。",
            )

        # Count event types
        face_sweep_count = sum(1 for e in events if e.get("target_type") == "HERO_FACE")
        minion_sweep_count = sum(1 for e in events if e.get("target_type") == "MINION")
        hand_card_switch_count = sum(1 for e in events if e.get("action") == "HOVER_CARD")

        # 1. Burst Lethal Math: opponent swept arrow to player face >= 3 times
        if face_sweep_count >= 3:
            conf = min(96.0, 70.0 + face_sweep_count * 8.0)
            spoken = "极度危险！对手鼠标反复指向我方英雄，正在心算直伤爆发！手里极大概率捏着斩杀！"
            counter = "必须优先架设强力嘲讽墙、打出生命回复或吸血随从，绝对不能贪恋进攻！"
            return OpponentIntentAlert(
                intent=SubconsciousIntent.BURST_LETHAL_MATH,
                intent_label="🎯 心算直伤斩杀 (手握高额爆发)",
                threat_tier="CRITICAL",
                confidence_pct=conf,
                target_entity="我方英雄",
                warning_spoken_line=spoken,
                defensive_countermeasure=counter,
                summary_markdown=(
                    f"**对手意图预警**: **{spoken}**\n"
                    f"• **置信度**: {conf:.1f}%\n"
                    f"• **防范策略**: {counter}"
                ),
            )

        # 2. Hard Removal Targeting: opponent lingered on specific friendly big minion
        high_atk_minions = [m for m in board if m.get("attack", 0) >= 5 or m.get("health", 0) >= 5]
        lingered_minion = None
        for e in events:
            if e.get("target_type") == "MINION" and e.get("duration_sec", 0) >= 2.5:
                lingered_minion = e.get("target_name", "核心主力随从")
                break

        if lingered_minion:
            spoken = f"警报！对手鼠标长时间悬浮在我方【{lingered_minion}】上方，正在对准交解！"
            counter = f"若手里有亡语或圣盾增益，可考虑予以保护，或准备好后续次席随从填补战力真空。"
            return OpponentIntentAlert(
                intent=SubconsciousIntent.HARD_REMOVAL_TARGETING,
                intent_label="🗡️ 单解锁定 (密谋消灭核心)",
                threat_tier="HIGH",
                confidence_pct=88.0,
                target_entity=lingered_minion,
                warning_spoken_line=spoken,
                defensive_countermeasure=counter,
                summary_markdown=(
                    f"**对手意图预警**: **{spoken}**\n"
                    f"• **目标随从**: 【{lingered_minion}】\n"
                    f"• **对策建议**: {counter}"
                ),
            )

        # 3. AOE Calculation: mouse scanned across 3+ friendly minions
        if minion_sweep_count >= 3:
            spoken = "注意防范！对手正在依次审视我方随从血量，大概率手握 AOE 全场清场法术！"
            counter = "随从血量尽量通过增益拉开阶梯，避免全员处于同一斩杀线被一锅端。"
            return OpponentIntentAlert(
                intent=SubconsciousIntent.AOE_CALCULATION,
                intent_label="🌊 清场算血 (筹备群体AOE)",
                threat_tier="HIGH",
                confidence_pct=82.0,
                target_entity="我方全体随从",
                warning_spoken_line=spoken,
                defensive_countermeasure=counter,
                summary_markdown=(
                    f"**对手意图预警**: **{spoken}**\n"
                    f"• **置信度**: 82.0%\n"
                    f"• **对策建议**: {counter}"
                ),
            )

        # 4. Hesitation: switched cards 4+ times without playing
        if hand_card_switch_count >= 4:
            spoken = "对手连续反复切换手牌，但迟迟没有动作，表明手牌严重卡手、费用受阻！"
            counter = "抓住对手虚弱期，大胆提速站场或走脸施压，扩大场面优势！"
            return OpponentIntentAlert(
                intent=SubconsciousIntent.HESITATION_PASS,
                intent_label="🤔 纠结卡手 (陷入资源死局)",
                threat_tier="MODERATE",
                confidence_pct=78.0,
                target_entity=None,
                warning_spoken_line=spoken,
                defensive_countermeasure=counter,
                summary_markdown=(
                    f"**对手意图洞察**: **{spoken}**\n"
                    f"• **破局策略**: {counter}"
                ),
            )

        return OpponentIntentAlert(
            intent=SubconsciousIntent.STANDARD_PLAY,
            intent_label="常规交换节奏",
            threat_tier="LOW",
            confidence_pct=65.0,
            target_entity=None,
            warning_spoken_line="",
            defensive_countermeasure="保持常规最佳打法。",
            summary_markdown="**对手意图雷达**: 对手操作节奏自然平稳。",
        )
