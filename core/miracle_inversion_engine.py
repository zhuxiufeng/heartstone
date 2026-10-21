"""
Desperation & Miracle Line Inversion (极限胜率倒逼与奇迹绝境算法)
- Dynamically shifts risk posture based on winrate:
  * Absolute Control (Winrate >= 70%): Zero-risk, play around all burst and topdecks.
  * Balanced EV (30% <= Winrate < 70%): Standard value-maximizing trades.
  * Miracle Gamble (Winrate < 20%): Conventional line is 0% win; inverts logic to find the solitary 5-15% miracle out line (ignore board, gamble face, pray for topdeck).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional


class RiskAttitude(str, Enum):
    ABSOLUTE_CONTROL = "ABSOLUTE_CONTROL"  # 绝对稳健风控模式: 防一切暴毙上限
    BALANCED_EV = "BALANCED_EV"            # 标准期望均衡模式: 等价交换
    MIRACLE_GAMBLE = "MIRACLE_GAMBLE"      # 极限奇迹豪赌模式: 死中求活，放弃防守


@dataclass
class MiracleGamblePath:
    is_miracle_needed: bool
    risk_attitude: RiskAttitude
    attitude_label: str
    conventional_winrate_pct: float
    miracle_winrate_pct: float
    winrate_gain_pct: float
    gamble_line_directive: str
    gamble_hypotheses: List[str]
    required_topdecks: List[str]
    speech_warning: str


class MiracleInversionEngine:
    """
    Evaluates when a game is mathematically lost via standard play,
    and calculates the singular miracle path to victory.
    """

    DIRECT_DAMAGE_CARDS = {
        "火球术": 6, "杀戮命令": 5, "横扫": 4, "刺骨": 4, "神圣惩击": 3,
        "闪电箭": 3, "暗影震击": 3, "生化炸弹": 4, "吸血鬼之血": 5, "火车王里诺艾": 6
    }

    @classmethod
    def evaluate_game_attitude(
        cls,
        winrate_pct: float,
        player_hp: int,
        enemy_hp: int,
        enemy_board_attack: int,
        player_board_attack: int,
        deck_remaining: Optional[List[str]] = None,
    ) -> MiracleGamblePath:
        """
        Determines current risk attitude and computes miracle line if in critical desperation.
        """
        deck = deck_remaining or []

        if winrate_pct >= 70.0:
            return MiracleGamblePath(
                is_miracle_needed=False,
                risk_attitude=RiskAttitude.ABSOLUTE_CONTROL,
                attitude_label="🛡️ 绝对稳健风控 (大优求稳)",
                conventional_winrate_pct=winrate_pct,
                miracle_winrate_pct=winrate_pct,
                winrate_gain_pct=0.0,
                gamble_line_directive="大局已定，防一切敌方直伤上限与AOE，稳健白吃护脸保胜。",
                gamble_hypotheses=[],
                required_topdecks=[],
                speech_warning="大优势对局！我们不贪不浪，优先清光对面随从，稳扎稳打拿下！",
            )

        if winrate_pct >= 25.0:
            return MiracleGamblePath(
                is_miracle_needed=False,
                risk_attitude=RiskAttitude.BALANCED_EV,
                attitude_label="⚖️ 标准价值平衡 (均势博弈)",
                conventional_winrate_pct=winrate_pct,
                miracle_winrate_pct=winrate_pct,
                winrate_gain_pct=0.0,
                gamble_line_directive="保持场面价值最大化互换，合理争夺场面主导权。",
                gamble_hypotheses=[],
                required_topdecks=[],
                speech_warning="均势局，按照标准随从价值进行交换。",
            )

        # Desperation zone: winrate < 25%, player dying or hopelessly behind
        # Conventional line gives almost 0% chance against lethal board
        hp_deficit = enemy_hp - player_board_attack
        # Find outs in deck
        damage_outs = [c for c in deck if any(d in c for d in cls.DIRECT_DAMAGE_CARDS)]
        if not damage_outs:
            damage_outs = ["直伤法术/冲锋随从"]

        # If enemy has lethal on board next turn, conventional trading delays 1 turn then dies
        conventional_chance = max(1.0, winrate_pct)
        # Miracle line: ignore trades, all go face, hope enemy cannot heal and we topdeck lethal
        miracle_chance = min(35.0, round(conventional_chance + 12.5, 1))

        hypotheses = [
            "假定对手下回合手中无嘲讽随从或群体吸血护脸",
            f"本回合全员打脸压血，将对手压至 {max(1, hp_deficit)} 血进入绝对斩杀线",
            f"下回合神抽牌库中的直伤手段 ({', '.join(damage_outs[:2])}) 完成反杀",
        ]

        return MiracleGamblePath(
            is_miracle_needed=True,
            risk_attitude=RiskAttitude.MIRACLE_GAMBLE,
            attitude_label="⚡ 绝境奇迹逆转 (放弃防守死中求活)",
            conventional_winrate_pct=conventional_chance,
            miracle_winrate_pct=miracle_chance,
            winrate_gain_pct=round(miracle_chance - conventional_chance, 1),
            gamble_line_directive=f"常规打法已无生路！立刻放弃解场，全部打脸将敌方压至 {max(1, hp_deficit)} 血，赌下回合神抽直伤逆天改命！",
            gamble_hypotheses=hypotheses,
            required_topdecks=damage_outs[:3],
            speech_warning="常规解场必输无疑！听我的，直接全员走脸拼死一搏，赌下回合神抽翻盘！",
        )
