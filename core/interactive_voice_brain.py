"""
Interactive Full-Duplex Voice Brain (全双工自然语言语音对战智脑)
- Real-time intent classification for spoken player queries during Hearthstone matches.
- Semantic intents: Lethal Check, Removal Advice, Draft Synergy, Threat Prediction, Miracle Lines, General Coaching.
- Crafts concise, natural, professional esports-grade spoken replies for TTS or companion HUD.
"""

from dataclasses import dataclass
from enum import Enum
import re
from typing import Dict, Any, Optional


class VoiceIntent(str, Enum):
    LETHAL_CHECK = "LETHAL_CHECK"            # 斩杀查询: "能斩杀吗？" / "对面能秒我吗？"
    REMOVAL_ADVICE = "REMOVAL_ADVICE"        # 解场决策: "要交大解吗？" / "怎么解最好？"
    DRAFT_SYNERGY = "DRAFT_SYNERGY"          # 抓牌配合: "这张牌能配合什么？"
    THREAT_PREDICTION = "THREAT_PREDICTION"  # 威胁预测: "对面下回合防什么？"
    MIRACLE_LINE = "MIRACLE_LINE"            # 绝境生路: "还有机会翻盘吗？"
    GENERAL_COACH = "GENERAL_COACH"          # 综合指导: "大师现在怎么打？"


@dataclass
class VoiceBrainResponse:
    intent: VoiceIntent
    recognized_query: str
    spoken_answer: str
    tactical_action_ref: str
    confidence_score: float


class InteractiveVoiceBrain:
    """
    Parses conversational questions from players and returns esports-master vocal answers.
    """

    INTENT_KEYWORDS = {
        VoiceIntent.LETHAL_CHECK: ["斩杀", "秒了", "死不死", "伤害够", "走脸能赢", "带走"],
        VoiceIntent.REMOVAL_ADVICE: ["解场", "交大解", "绝命乱斗", "打不打", "解不解", "怎么解", "换怪"],
        VoiceIntent.DRAFT_SYNERGY: ["配合", "选哪张", "抓牌", "抓哪张", "竞技场推荐", "协同"],
        VoiceIntent.THREAT_PREDICTION: ["防什么", "下回合出什么", "对面手牌", "有什么AOE", "烈焰风暴", "威胁"],
        VoiceIntent.MIRACLE_LINE: ["翻盘", "还能赢吗", "绝境", "奇迹", "投降", "还有救吗", "神抽"],
    }

    @classmethod
    def parse_intent(cls, query: str) -> VoiceIntent:
        """
        Extracts intent from query text using priority keyword matching.
        """
        clean_q = query.strip()
        for intent, kws in cls.INTENT_KEYWORDS.items():
            if any(k in clean_q for k in kws):
                return intent
        return VoiceIntent.GENERAL_COACH

    @classmethod
    def answer_query(cls, query: str, state: Optional[Dict[str, Any]] = None) -> VoiceBrainResponse:
        """
        Generates spoken answer based on query and live game state.
        """
        state = state or {}
        intent = cls.parse_intent(query)
        conf = 92.0

        if intent == VoiceIntent.LETHAL_CHECK:
            lethal_info = state.get("lethal_info", {})
            has_lethal = lethal_info.get("has_lethal", False)
            total_dmg = lethal_info.get("total_damage", 0)
            opp_hp = state.get("opponent_health", 30)

            if has_lethal:
                spoken = f"斩杀确定！当前总伤害高达 {total_dmg} 点，足以击穿敌方 {opp_hp} 血，直接全部走脸拿下！"
                action = "EXECUTE_LETHAL"
            else:
                deficit = max(0, opp_hp - total_dmg)
                spoken = f"暂时无法斩杀，场面加直伤总计 {total_dmg} 点，距离斩杀还差 {deficit} 点伤害。建议优先稳健解场控场。"
                action = "HOLD_CONTROL"

        elif intent == VoiceIntent.REMOVAL_ADVICE:
            enemy_threat = state.get("enemy_threat_level", "MODERATE")
            if enemy_threat in ("CRITICAL", "HIGH"):
                spoken = "当前敌方场面压力极大，属于致命威胁，建议果断打出核心解牌化解场面！"
                action = "CAST_CORE_REMOVAL"
            else:
                spoken = "当前敌方场面威胁有限，不建议过早交出核心大解，用杂毛小随从白吃互换即可。"
                action = "SAVE_REMOVAL_AND_TRADE"

        elif intent == VoiceIntent.DRAFT_SYNERGY:
            spoken = "在当前竞技场卡组中，优先抓取具备战吼过牌或机械属性的协同单卡，能够直接激活后续体系闭环。"
            action = "HIGHLIGHT_SYNERGY_CARD"

        elif intent == VoiceIntent.THREAT_PREDICTION:
            opp_class = state.get("opponent_class", "Mage")
            turn = state.get("turn", 5)
            if opp_class == "Mage" and turn >= 6:
                spoken = "重点防范法师 7 费的【烈焰风暴】全场打 4，随从血量尽量保持在 5 血以上，避免被一锅端！"
            elif opp_class == "Priest":
                spoken = "防范牧师群体狂乱或圣光炸弹，避免过度铺场单一大怪。"
            else:
                spoken = f"注意防范 {opp_class} 下回合按费拍出的大型嘲讽或直伤爆发。"
            action = "DISPLAY_AOE_THREAT"

        elif intent == VoiceIntent.MIRACLE_LINE:
            winrate = state.get("winrate", 50.0)
            if winrate < 20.0:
                spoken = "这把常规解场必输！听我的，直接全员走脸拼死一搏，赌下回合神抽直伤逆天改命！"
                action = "EXECUTE_MIRACLE_GAMBLE"
            else:
                spoken = f"当前胜率约 {round(winrate, 1)}%，战局完全在掌控中，无需冒险，稳扎稳打就能赢！"
                action = "PLAY_STANDARD"

        else:  # GENERAL_COACH
            spoken = "大师副驾建议：遵循黄金时序，先过牌探明手牌，再用随从白吃控场，最后按费下怪压制。"
            action = "EXECUTE_COPILOT_STEP_1"

        return VoiceBrainResponse(
            intent=intent,
            recognized_query=query,
            spoken_answer=spoken,
            tactical_action_ref=action,
            confidence_score=conf,
        )
