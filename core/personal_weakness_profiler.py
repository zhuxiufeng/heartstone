"""
PersonalWeaknessProfiler: Long-term player weakness & blunder heatmap profiler.
Tracks player decision patterns across multiple matches, diagnoses tactical blind spots,
evaluates playing styles (over-passive, over-extending, mana inefficient),
and provides tailored real-time defense reminders.
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("PersonalWeaknessProfiler")


def get_default_profile_file() -> Path:
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).resolve().parent
    else:
        base_dir = Path(__file__).resolve().parent.parent
    return base_dir / "cache" / "personal_weakness_profile.json"


PROFILE_FILE = get_default_profile_file()


@dataclass
class BlunderEntry:
    turn: int
    blunder_type: str    # "MANA_WASTE", "MISSED_LETHAL", "PASSIVE_TRADING", "AOE_OVEREXTEND", "SUBOPTIMAL_ORDER"
    description: str
    impact_score: int    # 1 to 10 scale


@dataclass
class MatchBlunderRecord:
    match_id: str
    timestamp: float
    hero_class: str
    opponent_class: str
    result: str          # "WIN" or "LOSS"
    total_turns: int
    blunders: List[BlunderEntry] = field(default_factory=list)


@dataclass
class WeaknessDiagnosis:
    total_matches: int
    total_turns_analyzed: int
    overall_accuracy_pct: float
    playstyle_tag: str
    phase_blunders: Dict[str, int]       # "early" (T1-4), "mid" (T5-7), "late" (T8+)
    category_counts: Dict[str, int]      # per blunder_type
    top_blind_spots: List[str] = field(default_factory=list)
    actionable_advice: List[str] = field(default_factory=list)
    summary_text: str = ""


class PersonalWeaknessProfiler:
    """Manages persistent match blunder logs and generates psychological / tactical diagnostic radar."""

    _instance: Optional[PersonalWeaknessProfiler] = None

    def __init__(self, file_path: Path = PROFILE_FILE) -> None:
        self.file_path = file_path
        self.records: List[MatchBlunderRecord] = []
        self._load()

    @classmethod
    def get_instance(cls) -> PersonalWeaknessProfiler:
        if cls._instance is None:
            cls._instance = PersonalWeaknessProfiler()
        return cls._instance

    def _load(self) -> None:
        if not self.file_path.exists():
            return
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.records = []
                for m in data.get("matches", []):
                    blunders = [BlunderEntry(**b) for b in m.get("blunders", [])]
                    self.records.append(MatchBlunderRecord(
                        match_id=m.get("match_id", ""),
                        timestamp=m.get("timestamp", 0.0),
                        hero_class=m.get("hero_class", "UNKNOWN"),
                        opponent_class=m.get("opponent_class", "UNKNOWN"),
                        result=m.get("result", "UNKNOWN"),
                        total_turns=m.get("total_turns", 0),
                        blunders=blunders,
                    ))
        except Exception as e:
            logger.warning(f"Failed to load weakness profile from {self.file_path}: {e}")

    def _save(self) -> None:
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "matches": [asdict(r) for r in self.records]
            }
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save weakness profile to {self.file_path}: {e}")

    def record_match_blunders(
        self,
        match_id: str,
        hero_class: str,
        opponent_class: str,
        result: str,
        total_turns: int,
        blunders: List[BlunderEntry],
    ) -> None:
        """Appends a completed match's blunder evaluation to history."""
        import time
        rec = MatchBlunderRecord(
            match_id=match_id,
            timestamp=time.time(),
            hero_class=hero_class,
            opponent_class=opponent_class,
            result=result,
            total_turns=total_turns,
            blunders=blunders,
        )
        self.records.append(rec)
        self._save()

    def diagnose_weaknesses(self) -> WeaknessDiagnosis:
        """Generates comprehensive tactical blind spot diagnosis across historical matches."""
        total_matches = len(self.records)
        if total_matches == 0:
            return WeaknessDiagnosis(
                total_matches=0,
                total_turns_analyzed=0,
                overall_accuracy_pct=100.0,
                playstyle_tag="新手蓄力阶段 (暂无历史对局)",
                phase_blunders={"early": 0, "mid": 0, "late": 0},
                category_counts={"MANA_WASTE": 0, "MISSED_LETHAL": 0, "PASSIVE_TRADING": 0, "AOE_OVEREXTEND": 0, "SUBOPTIMAL_ORDER": 0},
                top_blind_spots=["暂无足够历史对战记录，完成对局后将自动生成短板诊断。"],
                actionable_advice=["持续进行竞技场对战，AI 将自动分析您的出牌节奏与决策失误。"],
                summary_text="暂无历史数据",
            )

        total_turns = sum(r.total_turns for r in self.records)
        total_blunders = sum(len(r.blunders) for r in self.records)

        # Accuracy estimation: 100 - (blunders / total_turns * 35)
        accuracy = max(55.0, min(99.5, 100.0 - (total_blunders / max(total_turns, 1)) * 32.0))

        phases = {"early": 0, "mid": 0, "late": 0}
        categories: Dict[str, int] = {
            "MANA_WASTE": 0,
            "MISSED_LETHAL": 0,
            "PASSIVE_TRADING": 0,
            "AOE_OVEREXTEND": 0,
            "SUBOPTIMAL_ORDER": 0,
        }

        for r in self.records:
            for b in r.blunders:
                if b.turn <= 4:
                    phases["early"] += 1
                elif b.turn <= 7:
                    phases["mid"] += 1
                else:
                    phases["late"] += 1

                b_type = b.blunder_type
                if b_type in categories:
                    categories[b_type] += 1
                else:
                    categories[b_type] = 1

        # Classify style tag
        if total_blunders > 0:
            passive_ratio = categories["PASSIVE_TRADING"] / total_blunders
            overextend_ratio = categories["AOE_OVEREXTEND"] / total_blunders
            mana_ratio = categories["MANA_WASTE"] / total_blunders

            if passive_ratio >= 0.35:
                style = "过度稳健控场型 (偏好解场，易错失斩杀窗口)"
            elif overextend_ratio >= 0.30:
                style = "激进铺场型 (缺乏防AOE意识，易遭清场崩盘)"
            elif mana_ratio >= 0.35:
                style = "节奏脱节型 (中期法力空耗偏高，压制力不足)"
            else:
                style = "全能进阶型 (决策较均衡，微调即可冲刺12胜)"
        else:
            style = "无瑕大师型 (零显著伏笔)"

        # Formulate top blind spots
        blind_spots: List[str] = []
        advices: List[str] = []

        if categories["MANA_WASTE"] > 0:
            blind_spots.append(f"⚡ 水晶空耗: 共记录 {categories['MANA_WASTE']} 次中期费用未打满，导致场面节奏被动")
            advices.append("第 4~6 回合尽量规划满费动作或结合英雄技能，避免空余 2 点以上水晶")

        if categories["AOE_OVEREXTEND"] > 0:
            blind_spots.append(f"💥 防AOE过铺: 共记录 {categories['AOE_OVEREXTEND']} 次在对手关键AOE回合前过度投入手牌随从")
            advices.append("进入 6~7 费前注意保留手牌续航，优先保全随从脱离致命伤害线而非盲目铺杂毛")

        if categories["PASSIVE_TRADING"] > 0:
            blind_spots.append(f"🎯 错失抢脸时机: 共记录 {categories['PASSIVE_TRADING']} 次优势局面下过度进行不利随从交换")
            advices.append("当对手血量进入 15 点斩杀射程且我方场攻占优时，果断转守为攻直取敌方英雄")

        if categories["SUBOPTIMAL_ORDER"] > 0:
            blind_spots.append(f"🎲 动作顺序颠倒: 共记录 {categories['SUBOPTIMAL_ORDER']} 次未先过牌或随机判定便提前下怪")
            advices.append("牢记『过牌与高随机性卡牌先行』铁律，获取最大信息量后再锁定随从走位与攻击")

        if categories["MISSED_LETHAL"] > 0:
            blind_spots.append(f"💀 错失斩杀线: 共记录 {categories['MISSED_LETHAL']} 次当回合或下回合斩杀线遗漏")
            advices.append("回合开始优先计算全场直伤与法术爆发总和，避免惯性解场错过终结游戏机会")

        if not blind_spots:
            blind_spots.append("恭喜！近期对局未检测到明显的系统性决策失误。")
            advices.append("继续保持敏锐的斩杀嗅觉与稳健的法力曲线规划。")

        summary = (
            f"📊 历史对局诊断 ({total_matches}场/{total_turns}回合): 综合决策精度 {accuracy:.1f}% | "
            f"打法画像【{style}】 | 最需注意: {blind_spots[0]}"
        )

        return WeaknessDiagnosis(
            total_matches=total_matches,
            total_turns_analyzed=total_turns,
            overall_accuracy_pct=round(accuracy, 1),
            playstyle_tag=style,
            phase_blunders=phases,
            category_counts=categories,
            top_blind_spots=blind_spots,
            actionable_advice=advices,
            summary_text=summary,
        )

    def get_realtime_turn_alert(
        self,
        turn: int,
        current_mana: int,
        opponent_class: str,
    ) -> Optional[str]:
        """Provides a proactive, personalized reminder if the current turn aligns with player's known blunder habits."""
        diagnosis = self.diagnose_weaknesses()
        if diagnosis.total_matches < 1:
            return None

        # Check early/mid mana habits
        if 4 <= turn <= 6 and diagnosis.category_counts.get("MANA_WASTE", 0) >= 2:
            return "💡 个人习惯提醒: 历史数据显示您在此阶段常空耗费用，请务必打满节奏或转技能！"

        # Check Mage / Priest T7 AOE habits
        opp_upper = (opponent_class or "").upper()
        if turn in (6, 7) and opp_upper in ("MAGE", "PRIEST", "WARLOCK") and diagnosis.category_counts.get("AOE_OVEREXTEND", 0) >= 2:
            return f"💡 个人习惯提醒: 对阵【{opponent_class}】下回合关键AOE在即，历史数据显示您易在此过铺，防全清！"

        # Check passive trade habits
        if turn >= 7 and diagnosis.category_counts.get("PASSIVE_TRADING", 0) >= 2:
            return "💡 个人习惯提醒: 后期均势下注意计算抢脸回合数，避免惯性全解错失赛点！"

        return None
