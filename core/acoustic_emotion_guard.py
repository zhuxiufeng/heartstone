"""
Acoustic Emotion & Voice Stress Guard (麦克风声学情绪与压力分析守护)
- Evaluates player acoustic voice telemetry: deep sigh acoustics, pitch variance, speech rate, and volume spikes.
- Calculates Frustration Index (0.0 to 100.0) and Emotional State.
- Dispatches soothing psych-comfort responses, humor interventions, or timeout suggestions before tilt turns fatal.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any


class AcousticState(str, Enum):
    CALM_SERENE = "CALM_SERENE"                    # 宁静沉稳: 专注平稳
    MILD_TENSION = "MILD_TENSION"                  # 轻微紧绷: 语速稍快
    HEAVY_SIGH_DEPRESSED = "HEAVY_SIGH_DEPRESSED"  # 叹息沮丧: 捕捉到深长叹气声
    EXPLOSIVE_RAGE = "EXPLOSIVE_RAGE"              # 破防狂暴: 音量激增、音调尖锐


@dataclass
class AcousticEmotionReport:
    frustration_index: float  # 0.0 ~ 100.0
    state: AcousticState
    state_label: str
    comfort_response: str
    action_protocol: str
    summary_markdown: str


class AcousticEmotionGuard:
    """
    Guards player mental health through acoustic stress and frustration analysis.
    """

    @classmethod
    def analyze_voice_telemetry(
        cls,
        pitch_jitter: float = 0.05,
        sigh_detected: bool = False,
        speech_wpm: float = 120.0,
        peak_volume_db: float = -20.0,
    ) -> AcousticEmotionReport:
        """
        Assesses emotional frustration level from raw acoustic metrics.
        """
        # Baseline frustration is 15.0
        idx = 15.0

        if sigh_detected:
            idx += 40.0

        if pitch_jitter > 0.25:
            idx += 25.0
        elif pitch_jitter > 0.15:
            idx += 12.0

        if peak_volume_db > -5.0:  # Loud shout / exclamation
            idx += 35.0
        elif peak_volume_db > -10.0:
            idx += 15.0

        if speech_wpm > 200.0:
            idx += 15.0

        final_idx = max(0.0, min(100.0, round(idx, 1)))

        if final_idx >= 75.0 or (peak_volume_db > -5.0 and pitch_jitter > 0.2):
            state = AcousticState.EXPLOSIVE_RAGE
            label = "💥 破防情绪暴击 (剧烈情绪起伏)"
            comfort = "我知道这把太搞人心态了！对面那手神抽简直离谱！深呼吸，咱不跟发牌员一般见识，先喝口冰水压压惊！"
            protocol = "强制战术暂停：立刻双手脱离鼠标，站起来拉伸 1 分钟，杜绝上头连点。"
        elif sigh_detected or final_idx >= 50.0:
            state = AcousticState.HEAVY_SIGH_DEPRESSED
            label = "😮‍💨 叹息压抑状态 (心态疲惫失落)"
            comfort = "听到你深深的一声叹气啦。打牌嘛，牌序不顺是常有的事，你的每一手决断都非常标准，下一把气运一定轮到咱们！"
            protocol = "轻度安抚模式：播放舒缓背景音乐，放缓下一回合出牌节奏。"
        elif final_idx >= 30.0 or speech_wpm > 160.0:
            state = AcousticState.MILD_TENSION
            label = "⚡ 稍显紧绷急躁 (语速加快)"
            comfort = "别急别急，时间非常充裕，看清水晶和过牌再打。"
            protocol = "节奏校准：回合开始前心中默数 3 秒再动牌。"
        else:
            state = AcousticState.CALM_SERENE
            label = "🌿 心平气和宁静 (最佳竞技状态)"
            comfort = "呼吸沉稳、语调从容，这才是大师该有的气场，继续保持！"
            protocol = "保持当前专注度，乘胜追击。"

        md = (
            f"**麦克风声学情绪与心理守护报告**:\n"
            f"• **挫败压抑指数**: **{final_idx:.1f} / 100**\n"
            f"• **情绪声学定级**: **{label}**\n"
            f"• **声学特征监测**: 深叹气捕捉: {'有' if sigh_detected else '无'} | 峰值分贝: {peak_volume_db:.1f} dB | 音频抖动: {pitch_jitter:.2f}\n"
            f"• **大师专属安抚**: “{comfort}”\n"
            f"• **冷静行动指南**: {protocol}"
        )

        return AcousticEmotionReport(
            frustration_index=final_idx,
            state=state,
            state_label=label,
            comfort_response=comfort,
            action_protocol=protocol,
            summary_markdown=md,
        )
