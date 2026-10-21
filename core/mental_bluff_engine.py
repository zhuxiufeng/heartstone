"""
Mental Model & Strategic Bluffing Engine (对手心智模型与心理战博弈引擎)
- Analyzes opponent playstyle: Aggressive Rusher, Meticulous Control, Rookie Blunder, Balanced.
- Computes Strategic Bluff Expected Value (Bluff EV): feigning lethal/burst posture to force cautious opponents into suboptimal defensive trades.
- Dynamically calculates bait tolerance for AOE sweepers based on opponent aggression.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any


class OpponentStyle(str, Enum):
    AGGRESSIVE_RUSHER = "AGGRESSIVE_RUSHER"      # 激进冒进型: 快节奏, 极度偏爱走脸, 忽视防守
    METICULOUS_CONTROL = "METICULOUS_CONTROL"    # 严谨控场型: 长思考, 悬浮卡牌, 极重解场防守
    ROOKIE_BLUNDER = "ROOKIE_BLUNDER"            # 新手伏笔型: 次序颠倒, 错漏点伤, 不防奥秘
    BALANCED_STANDARD = "BALANCED_STANDARD"      # 标准稳健型: 正常节奏, 均衡交换


@dataclass
class OpponentMentalProfile:
    style: OpponentStyle
    style_label: str
    confidence_pct: float
    avg_turn_duration_sec: float
    hover_rate_per_turn: float
    trade_preference_score: float  # -1.0 (纯走脸) ~ +1.0 (纯控场)
    bait_tolerance_factor: float   # 贪牌钓鱼系数: >1.2 对快攻可贪留AOE, <0.8 对控制立即解场
    bluff_vulnerability_score: float  # 0.0 ~ 1.0 被诈唬成功率 (控场型最高)
    tactical_advice: str


@dataclass
class BluffOpportunity:
    is_viable: bool
    bluff_action: str
    bluff_ev: float
    success_probability_pct: float
    opponent_reaction_prediction: str
    fail_risk_description: str
    speech_prompt: str


class MentalBluffEngine:
    """
    Evaluates opponent psychological playstyle and calculates high-level bluffing/baiting plays.
    """

    @staticmethod
    def analyze_opponent_style(turn_history: Optional[List[Dict[str, Any]]] = None) -> OpponentMentalProfile:
        """
        Analyzes opponent telemetry: turn time, card hovers, trades vs face ratio.
        """
        if not turn_history:
            # Default profile for unknown opponent
            return OpponentMentalProfile(
                style=OpponentStyle.BALANCED_STANDARD,
                style_label="标准稳健型 (平衡博弈)",
                confidence_pct=60.0,
                avg_turn_duration_sec=25.0,
                hover_rate_per_turn=2.0,
                trade_preference_score=0.1,
                bait_tolerance_factor=1.0,
                bluff_vulnerability_score=0.45,
                tactical_advice="对手风格中规中矩，按标准场面价值进行等价交换。",
            )

        total_turns = len(turn_history)
        total_duration = sum(t.get("duration_sec", 25.0) for t in turn_history)
        total_hovers = sum(t.get("card_hovers", 2) for t in turn_history)
        face_attacks = sum(t.get("face_attacks", 1) for t in turn_history)
        trade_attacks = sum(t.get("trade_attacks", 1) for t in turn_history)
        blunders_observed = sum(t.get("blunders", 0) for t in turn_history)

        avg_dur = total_duration / max(1, total_turns)
        avg_hover = total_hovers / max(1, total_turns)
        total_attacks = max(1, face_attacks + trade_attacks)
        trade_score = (trade_attacks - face_attacks) / total_attacks  # -1.0 to 1.0

        if blunders_observed >= 2 or (trade_score < -0.3 and blunders_observed >= 1):
            style = OpponentStyle.ROOKIE_BLUNDER
            label = "新手伏笔型 (漏洞较多)"
            conf = min(95.0, 50.0 + blunders_observed * 20.0)
            bait_factor = 1.3
            bluff_vuln = 0.25  # Beginners often ignore bluff signals and hit face anyway
            advice = "对手经验较浅、容易漏算伏笔，无需过度防备高难度连击，稳扎稳打即可快速制胜。"
        elif avg_dur > 35.0 and avg_hover >= 3.0 and trade_score > 0.2:
            style = OpponentStyle.METICULOUS_CONTROL
            label = "严谨控场型 (深思熟虑)"
            conf = min(92.0, 60.0 + (avg_dur - 30.0) * 1.5)
            bait_factor = 0.75  # Don't get greedy, they hold answers
            bluff_vuln = 0.85  # Very susceptible to bluffing since they fear losing
            advice = "对手打法极其谨慎、习惯做最坏打算。可在劣势时果断假装满手斩杀，诱其放弃场面主动防守。"
        elif trade_score < -0.4 and avg_dur < 18.0:
            style = OpponentStyle.AGGRESSIVE_RUSHER
            label = "激进冒进型 (无脑抢脸)"
            conf = min(90.0, 55.0 + abs(trade_score) * 35.0)
            bait_factor = 1.4  # Highly vulnerable to AOE greed
            bluff_vuln = 0.15  # Will just ignore bluffs and smash face
            advice = "对手急于抢脸、视随从互换为无物。建议适当引诱其铺场，随后准时打出 AOE 实行毁灭性打击。"
        else:
            style = OpponentStyle.BALANCED_STANDARD
            label = "标准稳健型 (常规节奏)"
            conf = 65.0
            bait_factor = 1.0
            bluff_vuln = 0.50
            advice = "对手打法均衡成熟，执行标准场面价值互换，注意控场节奏。"

        return OpponentMentalProfile(
            style=style,
            style_label=label,
            confidence_pct=round(conf, 1),
            avg_turn_duration_sec=round(avg_dur, 1),
            hover_rate_per_turn=round(avg_hover, 1),
            trade_preference_score=round(trade_score, 2),
            bait_tolerance_factor=round(bait_factor, 2),
            bluff_vulnerability_score=round(bluff_vuln, 2),
            tactical_advice=advice,
        )

    @staticmethod
    def evaluate_strategic_bluff(
        player_health: int,
        opponent_health: int,
        board_attack: int,
        hand_damage_available: int,
        opponent_profile: OpponentMentalProfile,
        current_winrate: float,
    ) -> BluffOpportunity:
        """
        Determines whether feigning lethal (bluffing) is mathematically superior when behind.
        """
        # If already ahead, no need to bluff
        if current_winrate >= 60.0:
            return BluffOpportunity(
                is_viable=False,
                bluff_action="保持常规优势压制",
                bluff_ev=0.0,
                success_probability_pct=0.0,
                opponent_reaction_prediction="当前胜率充足，无需冒险诈唬。",
                fail_risk_description="无",
                speech_prompt="",
            )

        # Total apparent threat = board_attack
        # Actual total burst = board_attack + hand_damage_available
        # Threat deficit to kill = opponent_health - board_attack
        apparent_lethal_danger = board_attack >= (opponent_health - 6)  # Appears close to lethal

        # Opponent vulnerability depends on style
        base_bluff_chance = opponent_profile.bluff_vulnerability_score * 100.0

        if apparent_lethal_danger and opponent_profile.style == OpponentStyle.METICULOUS_CONTROL:
            # High EV bluff: caution causes opponent to panic trade
            bluff_ev = round(18.5 * opponent_profile.bluff_vulnerability_score, 1)
            succ_pct = min(88.0, base_bluff_chance + 10.0)
            return BluffOpportunity(
                is_viable=True,
                bluff_action="虚张声势：全员激进走脸，伪装手握直伤斩杀",
                bluff_ev=bluff_ev,
                success_probability_pct=succ_pct,
                opponent_reaction_prediction="对手为严谨控场型，受到斩杀威胁后将大概率放弃进攻，全力下怪护脸或交出核心大解。",
                fail_risk_description="若对手手里捏有群体吸血或绝对清场，下回合可能反击；但在当前劣势下，此举收益期望最高。",
                speech_prompt="这把劣势很大！对面是谨慎控场型，我们全员打脸装作有斩杀，逼他自乱阵脚主动防守！",
            )
        elif apparent_lethal_danger and opponent_profile.style == OpponentStyle.BALANCED_STANDARD:
            bluff_ev = 8.5
            succ_pct = 52.0
            return BluffOpportunity(
                is_viable=True,
                bluff_action="战术施压：随从走脸压进 10 血斩杀警戒线",
                bluff_ev=bluff_ev,
                success_probability_pct=succ_pct,
                opponent_reaction_prediction="对手有半数概率转入防守姿态进行保命解场。",
                fail_risk_description="若对手计算出我方手牌不足，可能直接竞速反攻。",
                speech_prompt="走脸压迫血线，给对手制造斩杀心理压力！",
            )
        else:
            return BluffOpportunity(
                is_viable=False,
                bluff_action="稳健防守解场",
                bluff_ev=-5.0,
                success_probability_pct=20.0,
                opponent_reaction_prediction="对手为冒进型或新手，对斩杀施压不敏感，强行走脸将被敌方随从反向踢死。",
                fail_risk_description="切勿无脑抢脸，对手不会交解牌，会被对手直接踢脸终结。",
                speech_prompt="",
            )
