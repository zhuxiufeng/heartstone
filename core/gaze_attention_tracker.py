"""
Webcam Gaze & Blindspot Attention Tracker (免外设摄像头视线注意力与盲区热力追踪)
- Estimates player visual attention across 4 critical screen zones:
  1. PLAYER_HAND (我方手牌)
  2. ENEMY_BOARD (敌方随从场面)
  3. ENEMY_SECRETS (敌方英雄与奥秘区)
  4. MANA_AND_DECK (法力水晶与记牌器)
- Detects dangerous visual blindspots (e.g. 10+ seconds ignoring active secrets or taunts).
- Triggers gentle heads-up audio and overlay warnings.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional


class ScreenRegion(str, Enum):
    PLAYER_HAND = "PLAYER_HAND"          # 我方手牌区
    ENEMY_BOARD = "ENEMY_BOARD"          # 敌方随从区
    ENEMY_SECRETS = "ENEMY_SECRETS"      # 敌方英雄与奥秘区
    MANA_AND_DECK = "MANA_AND_DECK"      # 法力水晶与记牌器


@dataclass
class RegionAttentionData:
    region: ScreenRegion
    region_label: str
    attention_pct: float
    dwell_duration_sec: float
    seconds_unattended: float
    has_active_threat: bool
    is_blindspot_alert: bool


@dataclass
class GazeTrackingReport:
    active_blindspot_alert: bool
    primary_focus_region: ScreenRegion
    focus_stability_score: float  # 0.0 ~ 100.0
    regions: Dict[str, RegionAttentionData]
    speech_warning: str
    summary_markdown: str


class GazeAttentionTracker:
    """
    Evaluates real-time gaze telemetry to prevent tunnel-vision blunders.
    """

    @classmethod
    def evaluate_gaze_distribution(
        cls,
        gaze_samples: Optional[List[Dict[str, Any]]] = None,
        enemy_has_secrets: bool = False,
        enemy_has_taunt_or_poison: bool = False,
    ) -> GazeTrackingReport:
        """
        Calculates gaze allocation and alerts if vital zones are neglected.
        """
        samples = gaze_samples or []
        total_samples = len(samples)

        # Default counts
        counts = {r: 0 for r in ScreenRegion}
        unattended = {
            ScreenRegion.PLAYER_HAND: 1.0,
            ScreenRegion.ENEMY_BOARD: 2.0,
            ScreenRegion.ENEMY_SECRETS: 12.0 if enemy_has_secrets else 0.0,
            ScreenRegion.MANA_AND_DECK: 4.0,
        }

        if total_samples > 0:
            for s in samples:
                reg = s.get("region")
                if reg in ScreenRegion._value2member_map_:
                    enum_reg = ScreenRegion(reg)
                    counts[enum_reg] += 1

            for s in samples:
                for r in ScreenRegion:
                    if s.get("region") == r.value:
                        unattended[r] = s.get("seconds_unattended", unattended[r])

        else:
            # Baseline natural distribution
            counts[ScreenRegion.PLAYER_HAND] = 45
            counts[ScreenRegion.ENEMY_BOARD] = 35
            counts[ScreenRegion.ENEMY_SECRETS] = 10
            counts[ScreenRegion.MANA_AND_DECK] = 10
            total_samples = 100

        # Calculate percentages
        region_dict: Dict[str, RegionAttentionData] = {}
        blindspot_alert = False
        speech = ""

        # Check Enemy Secrets Blindspot
        sec_unattended = unattended[ScreenRegion.ENEMY_SECRETS]
        secret_blindspot = enemy_has_secrets and (sec_unattended >= 10.0 or counts[ScreenRegion.ENEMY_SECRETS] < 5)

        # Check Enemy Board Blindspot
        board_unattended = unattended[ScreenRegion.ENEMY_BOARD]
        board_blindspot = enemy_has_taunt_or_poison and (board_unattended >= 8.0 or counts[ScreenRegion.ENEMY_BOARD] < 10)

        for r in ScreenRegion:
            pct = round((counts[r] / max(1, total_samples)) * 100.0, 1)
            is_bs = False
            has_threat = False

            if r == ScreenRegion.ENEMY_SECRETS:
                has_threat = enemy_has_secrets
                is_bs = secret_blindspot
            elif r == ScreenRegion.ENEMY_BOARD:
                has_threat = enemy_has_taunt_or_poison
                is_bs = board_blindspot

            label_map = {
                ScreenRegion.PLAYER_HAND: "我方手牌区",
                ScreenRegion.ENEMY_BOARD: "敌方随从区",
                ScreenRegion.ENEMY_SECRETS: "敌方奥秘/英雄区",
                ScreenRegion.MANA_AND_DECK: "法力水晶与记牌器",
            }

            region_dict[r.value] = RegionAttentionData(
                region=r,
                region_label=label_map[r],
                attention_pct=pct,
                dwell_duration_sec=round(counts[r] * 0.1, 1),
                seconds_unattended=unattended[r],
                has_active_threat=has_threat,
                is_blindspot_alert=is_bs,
            )

        # Primary focus
        primary_reg = max(counts.items(), key=lambda x: x[1])[0]

        if secret_blindspot:
            blindspot_alert = True
            speech = "视线预警！对手头顶挂有奥秘，但你的视线已遗漏该区域超过 10 秒，出牌前务必先探奥秘！"
        elif board_blindspot:
            blindspot_alert = True
            speech = "视线预警！敌方场上存在嘲讽或剧毒随从，你的视线长时间未聚焦敌方场面，切勿盲目打脸！"

        stability = 88.0 if not blindspot_alert else 55.0

        md = (
            f"**免外设视线注意力与盲区热力雷达**:\n"
            f"• **视线盲区告警**: **{'🚨 触发高危盲区警报' if blindspot_alert else '✅ 全局注视健康'}**\n"
            f"• **主注视区域**: 【{primary_reg.value}】 ({region_dict[primary_reg.value].attention_pct}%)\n"
            f"• **热力分布**:\n"
            f"  - 我方手牌: {region_dict[ScreenRegion.PLAYER_HAND.value].attention_pct}%\n"
            f"  - 敌方随从: {region_dict[ScreenRegion.ENEMY_BOARD.value].attention_pct}%\n"
            f"  - 敌方奥秘: {region_dict[ScreenRegion.ENEMY_SECRETS.value].attention_pct}% (未注视: {region_dict[ScreenRegion.ENEMY_SECRETS.value].seconds_unattended:.1f}s)\n"
            f"  - 水晶记牌: {region_dict[ScreenRegion.MANA_AND_DECK.value].attention_pct}%\n"
            f"• **大师提示**: {speech if speech else '选手视线分配均衡，对战注意力极佳。'}"
        )

        return GazeTrackingReport(
            active_blindspot_alert=blindspot_alert,
            primary_focus_region=primary_reg,
            focus_stability_score=stability,
            regions=region_dict,
            speech_warning=speech,
            summary_markdown=md,
        )
