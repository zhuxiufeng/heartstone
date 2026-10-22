"""
Micro-Meta Climate Radar & Live Deck Drift (环境微气候自适应雷达与天梯暗流感知)
- Detects localized meta shifts across recent matches (Aggro Overload, Control Attrition, OTK Burst, Midrange Tempo).
- Computes dynamic weight drift multipliers for card drafts and mulligans (e.g. +35% anti-aggro sweepers when aggro is rampant).
- Provides actionable micro-climate reports.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional


class MetaClimateType(str, Enum):
    AGGRO_OVERLOAD = "AGGRO_OVERLOAD"        # 快攻泛滥: 快节奏极限走脸激增
    CONTROL_ATTRITION = "CONTROL_ATTRITION"  # 控制沼泽: 慢速防战/牧师内卷
    COMBO_BURST = "COMBO_BURST"              # OTK爆发: 高直伤组合技偏多
    MIDRANGE_TEMPO = "MIDRANGE_TEMPO"        # 中速按费: 传统生物节奏占优
    BALANCED_ECOSYSTEM = "BALANCED_ECOSYSTEM"# 均衡生态: 职业分布平缓


@dataclass
class ClimateDriftMultipliers:
    anti_aggro_removal: float = 1.0     # 前期群解/单解权重修正
    early_taunt_survival: float = 1.0   # 低费嘲讽护脸权重
    greed_value_generation: float = 1.0 # 贪婪过牌/厚度资源权重
    burst_finishers: float = 1.0        # 直伤终结者权重


@dataclass
class MicroMetaReport:
    climate_type: MetaClimateType
    climate_label: str
    sample_match_count: int
    aggro_ratio_pct: float
    control_ratio_pct: float
    combo_ratio_pct: float
    dominant_class: str
    multipliers: ClimateDriftMultipliers
    mulligan_adjustment_advice: str
    summary_markdown: str


class MicroMetaClimateRadar:
    """
    Analyzes live match logs to detect hyper-local meta drift.
    """

    @classmethod
    def analyze_recent_meta(cls, recent_matches: Optional[List[Dict[str, Any]]] = None) -> MicroMetaReport:
        """
        Processes the last 5-20 match records to compute climate drift.
        """
        matches = recent_matches or []
        total = len(matches)

        if total == 0:
            # Default balanced baseline
            return MicroMetaReport(
                climate_type=MetaClimateType.BALANCED_ECOSYSTEM,
                climate_label="⚖️ 均衡生态微气候 (职业分布均匀)",
                sample_match_count=0,
                aggro_ratio_pct=33.3,
                control_ratio_pct=33.3,
                combo_ratio_pct=33.3,
                dominant_class="Neutral",
                multipliers=ClimateDriftMultipliers(),
                mulligan_adjustment_advice="环境平衡，遵循卡组标准起手留牌曲线。",
                summary_markdown="**当前环境微气候**: 暂无近期比赛样本，采用标准均衡权重。",
            )

        aggro_count = 0
        control_count = 0
        combo_count = 0
        class_counts: Dict[str, int] = {}

        for m in matches:
            opp_class = m.get("opp_class", "Neutral")
            class_counts[opp_class] = class_counts.get(opp_class, 0) + 1

            turns = m.get("duration_turns", 8)
            archetype = str(m.get("opp_archetype", "")).upper()

            if "AGGRO" in archetype or "FACE" in archetype or turns <= 6:
                aggro_count += 1
            elif "CONTROL" in archetype or "BLOOD" in archetype or turns >= 11:
                control_count += 1
            elif "COMBO" in archetype or "OTK" in archetype:
                combo_count += 1
            else:
                # Default bucket by turns
                if turns <= 7:
                    aggro_count += 1
                else:
                    control_count += 1

        aggro_pct = round((aggro_count / total) * 100.0, 1)
        control_pct = round((control_count / total) * 100.0, 1)
        combo_pct = round((combo_count / total) * 100.0, 1)

        dominant_class = max(class_counts.items(), key=lambda x: x[1])[0] if class_counts else "Unknown"

        # Determine climate type
        if aggro_pct >= 50.0:
            ctype = MetaClimateType.AGGRO_OVERLOAD
            label = "🔥 快攻过载预警 (快节奏抢脸泛滥)"
            mults = ClimateDriftMultipliers(
                anti_aggro_removal=1.35,
                early_taunt_survival=1.30,
                greed_value_generation=0.75,
                burst_finishers=1.10,
            )
            advice = "当前分段快攻横行！起手无条件全力寻找 1~3 费低费解牌与嘲讽随从，严禁保留高费慢速牌！"
        elif control_pct >= 50.0:
            ctype = MetaClimateType.CONTROL_ATTRITION
            label = "🛡️ 控制消耗沼泽 (慢速内卷与厚度较量)"
            mults = ClimateDriftMultipliers(
                anti_aggro_removal=0.85,
                early_taunt_survival=0.80,
                greed_value_generation=1.40,
                burst_finishers=1.25,
            )
            advice = "当前分段慢速极多！起手可大胆保留过牌核心与制胜大哥，注重长线资源卡差。"
        elif combo_pct >= 40.0:
            ctype = MetaClimateType.COMBO_BURST
            label = "⚡ OTK 爆发高发区 (小心空场直伤)"
            mults = ClimateDriftMultipliers(
                anti_aggro_removal=0.90,
                early_taunt_survival=1.20,
                greed_value_generation=0.85,
                burst_finishers=1.35,
            )
            advice = "直伤组合技活跃！保持血线健康并主动提速施压，迫使对手在启动前被迫交出斩杀组件解场。"
        else:
            ctype = MetaClimateType.BALANCED_ECOSYSTEM
            label = "⚖️ 均衡生态 (多职业百花齐放)"
            mults = ClimateDriftMultipliers()
            advice = "天梯环境健康均衡，按照卡组黄金曲线留牌即可。"

        md = (
            f"**分段实时微气候感知 (近 {total} 场实战采样)**:\n"
            f"• **气候定性**: **{label}**\n"
            f"• **偏向构成**: 快攻 {aggro_pct}% | 控制 {control_pct}% | 爆发组合 {combo_pct}%\n"
            f"• **最高频遭遇职业**: 【{dominant_class}】\n"
            f"• **战术权重修正**: 低费解牌 ×{mults.anti_aggro_removal:.2f} | 嘲讽生存 ×{mults.early_taunt_survival:.2f} | 资源厚度 ×{mults.greed_value_generation:.2f}\n"
            f"• **大师调度指南**: {advice}"
        )

        return MicroMetaReport(
            climate_type=ctype,
            climate_label=label,
            sample_match_count=total,
            aggro_ratio_pct=aggro_pct,
            control_ratio_pct=control_pct,
            combo_ratio_pct=combo_pct,
            dominant_class=dominant_class,
            multipliers=mults,
            mulligan_adjustment_advice=advice,
            summary_markdown=md,
        )
