"""
Multi-Agent Council of Champions (世界冠军多元智囊团圆桌会诊)
- Three specialized virtual champion agents:
  1. The Aggro Specialist (极致快攻大师): Favors maximum face pressure, tempo leverage, and shortest kill turns.
  2. The Control Grandmaster (绝对控场棋圣): Favors zero-risk trades, sweeper containment, and board stability.
  3. The Miracle Maverick (绝处逢生奇术师): Uncovers obscure combos, tactical setup baits, and miracle topdeck lines.
- Consensus engine synthesizes debate viewpoints into a unified grandmaster verdict.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional


class ChampionPersona(str, Enum):
    AGGRO_SPECIALIST = "AGGRO_SPECIALIST"      # 快攻专精大师: 激进走脸、最短斩杀
    CONTROL_GRANDMASTER = "CONTROL_GRANDMASTER"# 控场棋圣: 绝对零风险稳健清场
    MIRACLE_MAVERICK = "MIRACLE_MAVERICK"      # 奇迹特化师: 冷门配合与长线做局


class DebateVerdict(str, Enum):
    UNANIMOUS_AGGRO = "UNANIMOUS_AGGRO"            # 智囊团全票通过: 全员抢脸走脸
    UNANIMOUS_CONTROL = "UNANIMOUS_CONTROL"        # 智囊团全票通过: 绝对解场控场
    SPLIT_COUNCIL_CONSENSUS = "SPLIT_COUNCIL_CONSENSUS" # 存在战术分歧: 加权折衷共识


@dataclass
class ChampionAdvise:
    persona: ChampionPersona
    persona_title: str
    recommended_line: str
    action_type: str  # FACE, TRADE, SETUP
    confidence_score: float  # 0 to 100
    argument: str


@dataclass
class CouncilDebateReport:
    verdict: DebateVerdict
    verdict_label: str
    final_recommended_action: str
    council_consensus_score: float
    opinions: List[ChampionAdvise]
    debate_conflict_focus: str
    summary_markdown: str


class CouncilOfChampions:
    """
    Hosts the multi-agent virtual grandmaster round-table consultation.
    """

    @classmethod
    def convene_council(
        cls,
        player_hp: int,
        enemy_hp: int,
        board_total_attack: int,
        enemy_threat_level: str = "MODERATE",
        winrate_pct: float = 50.0,
        has_hand_burst: bool = False,
    ) -> CouncilDebateReport:
        """
        Gathers opinions from 3 champions and establishes a consensus decision.
        """
        # 1. Aggro Specialist
        if enemy_hp <= (board_total_attack + 8) or winrate_pct < 25.0:
            aggro_line = "全员走脸灌顶！将敌方血线压进绝杀射程，抢占胜利先机！"
            aggro_conf = 95.0
            aggro_type = "FACE"
            aggro_arg = f"敌方仅剩 {enemy_hp} 血，场面总攻达 {board_total_attack}。此时不抢更待何时？"
        else:
            aggro_line = "小幅解怪保持场攻优势，主力随从继续给敌方英雄施压。"
            aggro_conf = 72.0
            aggro_type = "FACE"
            aggro_arg = "进攻是最好的防守，不能给对手喘息与下高费大哥的机会。"

        aggro_advise = ChampionAdvise(
            persona=ChampionPersona.AGGRO_SPECIALIST,
            persona_title="⚡ 极致快攻大师 (The Aggro Specialist)",
            recommended_line=aggro_line,
            action_type=aggro_type,
            confidence_score=aggro_conf,
            argument=aggro_arg,
        )

        # 2. Control Grandmaster
        if enemy_threat_level in ("CRITICAL", "HIGH") or player_hp <= 14:
            ctrl_line = "优先白吃清光敌方场面！杜绝任何暴毙可能，稳字当头！"
            ctrl_conf = 94.0
            ctrl_type = "TRADE"
            ctrl_arg = f"我方仅剩 {player_hp} 血，敌方场面威胁处于 {enemy_threat_level}，必须将场面清零！"
        else:
            ctrl_line = "稳健随从价值互换，保持场面随从血量在 AOE 安全阈值以上。"
            ctrl_conf = 78.0
            ctrl_type = "TRADE"
            ctrl_arg = "巩固场面战力优势，等待对手资源耗尽进入断怪期。"

        ctrl_advise = ChampionAdvise(
            persona=ChampionPersona.CONTROL_GRANDMASTER,
            persona_title="🛡️ 绝对控场棋圣 (The Control Grandmaster)",
            recommended_line=ctrl_line,
            action_type=ctrl_type,
            confidence_score=ctrl_conf,
            argument=ctrl_arg,
        )

        # 3. Miracle Maverick
        if has_hand_burst or winrate_pct < 25.0 or enemy_hp <= board_total_attack:
            mira_line = "绝境奇迹走脸！放弃防守做局赌下回合神抽终结！"
            mira_conf = 90.0
            mira_type = "SETUP"
            mira_arg = "常规打法慢性死亡，唯有奇迹线能创造翻盘胜率！"
        else:
            mira_line = "修血做局铺垫，为下回合的群解或斩杀创造黄金落点。"
            mira_conf = 82.0
            mira_type = "SETUP"
            mira_arg = "不要看眼前一回合，要看后两回合的协同爆发收益。"

        mira_advise = ChampionAdvise(
            persona=ChampionPersona.MIRACLE_MAVERICK,
            persona_title="🔮 绝处逢生奇术师 (The Miracle Maverick)",
            recommended_line=mira_line,
            action_type=mira_type,
            confidence_score=mira_conf,
            argument=mira_arg,
        )

        opinions = [aggro_advise, ctrl_advise, mira_advise]

        # Consensus Resolution
        face_votes = sum(1 for o in opinions if o.action_type in ("FACE", "SETUP") and "走脸" in o.recommended_line)
        trade_votes = sum(1 for o in opinions if o.action_type == "TRADE")

        if face_votes >= 2 and (enemy_hp <= board_total_attack or winrate_pct < 25.0):
            verdict = DebateVerdict.UNANIMOUS_AGGRO
            vlabel = "🎯 智囊团共识：激进走脸破局"
            final_action = aggro_line
            conflict = "控场棋圣略有顾虑，但快攻大师与奇术师强力主导走脸斩杀线。"
            score = 92.5
        elif trade_votes >= 2 or enemy_threat_level == "CRITICAL":
            verdict = DebateVerdict.UNANIMOUS_CONTROL
            vlabel = "🛡️ 智囊团共识：严谨白吃控场"
            final_action = ctrl_line
            conflict = "全员一致认为当前局势下解场收益与安全性远大于冒险抢脸。"
            score = 88.0
        else:
            verdict = DebateVerdict.SPLIT_COUNCIL_CONSENSUS
            vlabel = "⚖️ 智囊团折衷共识：兼顾控场与压血"
            final_action = "主力杂毛小怪解掉敌方高威胁随从，高攻随从打脸施压。"
            conflict = "快攻大师力主抢脸，控场棋圣要求全解，奇术师建议折衷修血。"
            score = 81.0

        md = (
            f"**世界冠军多元智囊团圆桌会诊 ({vlabel})**:\n"
            f"• **最终执行共识**: **{final_action}** (共识指数: {score:.1f} / 100)\n"
            f"• **专家分歧焦点**: {conflict}\n"
            f"• **三大冠军大师专属辩词**:\n"
            f"  1. {aggro_advise.persona_title}: “{aggro_advise.recommended_line}”\n"
            f"  2. {ctrl_advise.persona_title}: “{ctrl_advise.recommended_line}”\n"
            f"  3. {mira_advise.persona_title}: “{mira_advise.recommended_line}”"
        )

        return CouncilDebateReport(
            verdict=verdict,
            verdict_label=vlabel,
            final_recommended_action=final_action,
            council_consensus_score=score,
            opinions=opinions,
            debate_conflict_focus=conflict,
            summary_markdown=md,
        )
