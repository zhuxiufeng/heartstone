"""
EsportsCaster: Interactive Voice Q&A & AI Esports Commentary Engine.
Interprets natural language voice inquiries (Face vs Trade, Lethal Check, Threat Forecast)
and generates broadcast-grade, high-energy esports caster commentary on epic match moments.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger("EsportsCaster")


class CasterEventType:
    LETHAL_REACHED = "LETHAL_REACHED"
    TOPDECK_MIRACLE = "TOPDECK_MIRACLE"
    FLAWLESS_TURN = "FLAWLESS_TURN"
    HEAVY_SWEEPER_PUNISH = "HEAVY_SWEEPER_PUNISH"
    CRITICAL_GAMBLE = "CRITICAL_GAMBLE"
    COMEBACK = "COMEBACK"


@dataclass
class VoiceAnswer:
    intent: str
    question: str
    short_verdict: str
    voice_audio_line: str
    confidence: float


@dataclass
class CasterCommentary:
    event_type: str
    headline: str
    commentary_text: str
    energy_level: str       # "HIGH", "EXTREME", "LEGENDARY"


class EsportsCaster:
    """Provides voice question answering and excitement-driven esports commentary."""

    COMMENTARY_LINES = {
        CasterEventType.LETHAL_REACHED: [
            ("⚡ 斩杀时刻到来！", "不可思议的绝杀时机！场面直伤完全拉满，零伏笔直取首级赢下比赛！", "LEGENDARY"),
            ("⚡ 胜负已分！", "精准的数学计算！伤害完全吻合，恭喜选手拿下这场天王山对局！", "HIGH"),
        ],
        CasterEventType.TOPDECK_MIRACLE: [
            ("🌟 奇迹神抽！！", "这就是竞技场的神谕！牌库唯一的绝境翻盘张在最后一刻拔地而起！", "LEGENDARY"),
            ("🌟 命运抉择！", "真正的右手第一张神抽！绝处逢生，对手彻底绝望！", "EXTREME"),
        ],
        CasterEventType.FLAWLESS_TURN: [
            ("💎 行云流水！", "出牌次序无懈可击！先过牌后铺场，细节拉满的大师级回合！", "HIGH"),
            ("💎 职业级微操！", "控场与场攻分配近乎完美，不浪费任何一点有效战力！", "HIGH"),
        ],
        CasterEventType.HEAVY_SWEEPER_PUNISH: [
            ("🛡️ 教科书级防AOE！", "手牌续航留得恰到好处！对手即使交出全场清场，也根本无法挽回大势！", "HIGH"),
        ],
        CasterEventType.CRITICAL_GAMBLE: [
            ("🔥 孤注一掷搏命！", "退无可退，唯有全军走脸搏命一击！狭路相逢勇者胜！", "EXTREME"),
        ],
    }

    @classmethod
    def answer_voice_query(
        cls,
        query: str,
        game_state: Dict[str, Any],
    ) -> VoiceAnswer:
        """Parses natural voice questions and generates instant spoken tactical verdicts."""
        q = query.strip()
        has_lethal = bool(game_state.get("is_lethal", False))
        posture = game_state.get("posture_mode", "BALANCED")
        enemy_hp = game_state.get("enemy_hp", 30)
        threat_card = game_state.get("punish_card", "常规清场")
        winrate = game_state.get("winrate_pct", 50.0)

        # 1. Lethal Intent
        if any(w in q for w in ["斩杀", "能赢吗", "能杀吗", "斩了吗"]):
            if has_lethal:
                return VoiceAnswer(
                    intent="CHECK_LETHAL",
                    question=q,
                    short_verdict="可以斩杀！",
                    voice_audio_line="场面直伤已完全达成斩杀，全员走脸直接拿下！",
                    confidence=0.98,
                )
            else:
                return VoiceAnswer(
                    intent="CHECK_LETHAL",
                    question=q,
                    short_verdict="暂未斩杀",
                    voice_audio_line=f"当前场面尚未满足斩杀，敌方剩余{enemy_hp}血，继续控场或压低血线。",
                    confidence=0.92,
                )

        # 2. Face vs Trade Intent
        if any(w in q for w in ["走脸", "打脸", "解场", "打哪个", "换不换"]):
            if "AGGRESSIVE" in posture or "ALL_IN" in posture:
                return VoiceAnswer(
                    intent="FACE_OR_TRADE",
                    question=q,
                    short_verdict="全力打脸！",
                    voice_audio_line="当前处于进攻优势时钟，无视杂兵，全军突击打脸施压！",
                    confidence=0.95,
                )
            elif "CONTROL" in posture:
                return VoiceAnswer(
                    intent="FACE_OR_TRADE",
                    question=q,
                    short_verdict="稳健解场",
                    voice_audio_line="我方血线告急，优先稳健白吃解场，化解敌方高威胁随从。",
                    confidence=0.93,
                )
            else:
                return VoiceAnswer(
                    intent="FACE_OR_TRADE",
                    question=q,
                    short_verdict="控场白吃",
                    voice_audio_line="当前处于均势对局，优先用小杂兵做最优随从交换。",
                    confidence=0.88,
                )

        # 3. Threat Forecaster Intent
        if any(w in q for w in ["防什么", "注意什么", "小心什么", "下回合"]):
            return VoiceAnswer(
                intent="WHAT_TO_PREVENT",
                question=q,
                short_verdict=f"防{threat_card}",
                voice_audio_line=f"注意防范对手下回合的【{threat_card}】，注意随从血量分散并保留后手。",
                confidence=0.94,
            )

        # 4. Winrate Intent
        if any(w in q for w in ["胜率", "局势", "优劣"]):
            return VoiceAnswer(
                intent="CHECK_WINRATE",
                question=q,
                short_verdict=f"胜率 {int(winrate)}%",
                voice_audio_line=f"当前战局推算胜率约为百分之{int(winrate)}，稳扎稳打即可占据上风。",
                confidence=0.90,
            )

        # Default fallback
        directive = game_state.get("coach_directive", "按费平滑出牌，稳固随从交换优势。")
        return VoiceAnswer(
            intent="GENERAL_ADVICE",
            question=q,
            short_verdict="平稳运营",
            voice_audio_line=directive,
            confidence=0.75,
        )

    @classmethod
    def get_commentary(cls, event_type: str) -> CasterCommentary:
        """Retrieves hype commentary for notable battle events."""
        options = cls.COMMENTARY_LINES.get(event_type, cls.COMMENTARY_LINES[CasterEventType.FLAWLESS_TURN])
        headline, text, energy = options[0]
        return CasterCommentary(
            event_type=event_type,
            headline=headline,
            commentary_text=text,
            energy_level=energy,
        )
