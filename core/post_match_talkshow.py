"""
PostMatchTalkshow: 30-Second Esports Podcast & Witty Post-Mortem Talk Show Narrator.
Generates broadcast-style sports commentary scripts analyzing match MVPs, pivotal turns,
clutch miracle outs, and blunder lessons with entertaining conversational banter.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger("PostMatchTalkshow")


@dataclass
class TalkshowScriptReport:
    result: str                 # "WIN" or "LOSS"
    total_turns: int
    match_grade: str            # "S 宗师无暇", "A 卓越发挥", "B 惊险翻盘", "C 伏笔失利"
    turning_point_turn: int
    mvp_card_or_play: str
    podcast_audio_script: str
    host_summary_one_liner: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result": self.result,
            "total_turns": self.total_turns,
            "match_grade": self.match_grade,
            "turning_point": self.turning_point_turn,
            "mvp": self.mvp_card_or_play,
            "script": self.podcast_audio_script,
            "one_liner": self.host_summary_one_liner,
        }


class PostMatchTalkshow:
    """Produces snappy 30-second broadcast talkshow scripts."""

    @classmethod
    def generate_talkshow(
        cls,
        result: str,
        total_turns: int,
        blunder_count: int = 0,
        mvp_card: str = "核心战力随从",
        turning_point_turn: int = 6,
        hero_class: str = "Mage",
        opp_class: str = "Priest",
    ) -> TalkshowScriptReport:
        is_win = (result.upper() == "WIN")

        if is_win:
            if blunder_count == 0:
                grade = "S 宗师无暇"
                one_liner = "行云流水的零失误运营，堪称教科书级竞技场教学！"
                script = (
                    f"欢迎来到大师赛后速评！恭喜选手赢下这场精彩的对决！"
                    f"整场比赛总共历经 {total_turns} 个回合，真正的转折点发生在第 {turning_point_turn} 回合。"
                    f"选手顶住压力，在关键时刻凭借【{mvp_card}】打出极高质量的场面展开。"
                    f"更难能可贵的是，全场 0 伏笔、出牌次序严谨如精算师，综合评级毫无争议获得 S 级！下把继续保持！"
                )
            else:
                grade = "A 卓越发挥"
                one_liner = "虽有微小次序瑕疵，但大局观与战术压制力完胜对手！"
                script = (
                    f"恭喜拿下胜利！这场对战打得相当热闹，总共耗时 {total_turns} 回合。"
                    f"第 {turning_point_turn} 回合可以说是全场的风水岭，【{mvp_card}】立下了汗马功劳。"
                    f"美中不足的是对局中有 {blunder_count} 处小伏笔，比如出牌次序可以更优化，不过瑕不掩瑜，综合评级 A 级，稳步前行！"
                )
        else:
            if blunder_count >= 2:
                grade = "C 伏笔失利"
                one_liner = "痛定思痛！微操次序与防AOE意识仍有显著提升空间。"
                script = (
                    f"非常遗憾输掉了这场比赛。回顾整个 {total_turns} 回合的交锋，"
                    f"痛点主要集中在第 {turning_point_turn} 回合的决策偏差，以及全场出现的 {blunder_count} 处关键伏笔。"
                    f"切记下把务必严格遵循【先过牌、再解场、防范对手高费清场】的大师法则，调整好心态，下一把直接翻盘！"
                )
            else:
                grade = "B 尽力局遗憾"
                one_liner = "牌序稍显逆风，已打出当前手牌条件下的最高战术上限。"
                script = (
                    f"非常可惜！这把打到第 {total_turns} 回合，选手在面对劣势时已经尽力做出了最优交换。"
                    f"第 {turning_point_turn} 回合受制于发牌员的制裁，未能抽到关键解牌。整体操作水平在线，无需气馁，重振旗鼓再战下一轮！"
                )

        return TalkshowScriptReport(
            result="WIN" if is_win else "LOSS",
            total_turns=total_turns,
            match_grade=grade,
            turning_point_turn=turning_point_turn,
            mvp_card_or_play=mvp_card,
            podcast_audio_script=script,
            host_summary_one_liner=one_liner,
        )
