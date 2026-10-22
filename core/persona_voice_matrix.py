"""
Multi-Persona Dynamic Voice Matrix (多重人格动态大师声线矩阵)
- Four distinct vocal persona engines:
  1. PRO_COACH (严肃职业教头): Calm, analytical, tempo-oriented, professional.
  2. HYPE_CASTER (激情电竞解说): Energetic, hype-inducing, explosive shoutcasting on lethals and topdecks.
  3. SARCASTIC_BUDDY (毒舌傲娇牌友): Humorous, witty, friendly bantering and blunder teasing.
  4. ZEN_MASTER (禅宗冥想大师): Ethereal, tranquil, automatically intervenes when player is tilted.
- Seamless auto-adaptation based on player psychological state.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional


class VoicePersona(str, Enum):
    PRO_COACH = "PRO_COACH"              # 严肃职业教头
    HYPE_CASTER = "HYPE_CASTER"          # 激情电竞解说
    SARCASTIC_BUDDY = "SARCASTIC_BUDDY"  # 毒舌傲娇牌友
    ZEN_MASTER = "ZEN_MASTER"            # 禅宗冥想大师


@dataclass
class PersonaMatrixResponse:
    active_persona: VoicePersona
    persona_title: str
    spoken_line: str
    audio_pitch_shift: float  # -1.0 to +1.0
    audio_speed_rate: float   # 0.8 to 1.3
    all_persona_lines: Dict[str, str]
    auto_switched_due_to_tilt: bool
    summary_markdown: str


class PersonaVoiceMatrix:
    """
    Renders contextual voice speech across 4 expressive coaching personas.
    """

    @classmethod
    def render_voice(
        cls,
        scenario: str = "GENERAL_STEP",
        context: Optional[Dict[str, Any]] = None,
        preferred_persona: VoicePersona = VoicePersona.PRO_COACH,
        is_player_tilted: bool = False,
    ) -> PersonaMatrixResponse:
        """
        Synthesizes spoken coaching tailored to selected persona and tilt state.
        """
        ctx = context or {}
        action = ctx.get("action", "先过牌后下怪")
        card = ctx.get("card", "关键牌")

        # Situational lines for each persona
        lines: Dict[VoicePersona, str] = {}

        if scenario == "LETHAL_CLIMAX":
            lines[VoicePersona.PRO_COACH] = f"斩杀确定，总伤害已超阈值，执行走脸终结。"
            lines[VoicePersona.HYPE_CASTER] = f"斩杀了！全员走脸直接灌顶！太不可思议了，瞬间带走比赛！"
            lines[VoicePersona.SARCASTIC_BUDDY] = f"行了别折腾对面随从了，直接踢脸对面就爆了，别给对面留面子！"
            lines[VoicePersona.ZEN_MASTER] = f"万法归一，因果已定，直接请敌方离场即可。"

        elif scenario == "BLUNDER_WARNING":
            lines[VoicePersona.PRO_COACH] = f"警报！出牌次序违规，必须先过牌再打出随从！"
            lines[VoicePersona.HYPE_CASTER] = f"等等！先别出怪！先开过牌看神抽，别把冠军给送了！"
            lines[VoicePersona.SARCASTIC_BUDDY] = f"住手啊大厨！你这先下怪再过牌，下饭操作直接看饱观众了！"
            lines[VoicePersona.ZEN_MASTER] = f"心急则智昏，先明照手牌，再定下乾坤。"

        elif scenario == "DESPERATE_GAMBLE":
            lines[VoicePersona.PRO_COACH] = f"常规胜率低于 15%，切换绝境模式，放弃解场全员打脸。"
            lines[VoicePersona.HYPE_CASTER] = f"这把常规解场必死！听解说的，全员直接走脸拼死一搏，赌下回合神抽翻盘！"
            lines[VoicePersona.SARCASTIC_BUDDY] = f"别搁这儿刮痧解场慢性自杀了，全给我糊他脸上，死也要站着死！"
            lines[VoicePersona.ZEN_MASTER] = f"置之死地而后生，舍弃微末羁绊，方见逆天契机。"

        else:  # GENERAL_STEP
            lines[VoicePersona.PRO_COACH] = f"执行第 1 步：{action}，稳步巩固场面优势。"
            lines[VoicePersona.HYPE_CASTER] = f"漂亮的操作！打出【{card}】，节奏牢牢握在我们手中！"
            lines[VoicePersona.SARCASTIC_BUDDY] = f"按我说的打，别自己瞎操作，这一手下去对面直接抓头发。"
            lines[VoicePersona.ZEN_MASTER] = f"顺应牌理，行如流水，每一步皆是心流。"

        # If player is tilted, ZEN_MASTER automatically intervenes
        auto_tilt = False
        if is_player_tilted and preferred_persona != VoicePersona.ZEN_MASTER:
            active_p = VoicePersona.ZEN_MASTER
            auto_tilt = True
            title = "🕊️ 禅宗冥想大师 (情绪守护自动介入)"
            line = "心若止水，莫为一时之得失所扰。深呼吸，牌局自会明朗。"
            pitch = -0.15
            speed = 0.90
        else:
            active_p = preferred_persona
            title_map = {
                VoicePersona.PRO_COACH: "👔 严肃职业教头 (Pro Coach)",
                VoicePersona.HYPE_CASTER: "🎙️ 激情电竞解说 (Hype Caster)",
                VoicePersona.SARCASTIC_BUDDY: "😎 毒舌傲娇牌友 (Sarcastic Buddy)",
                VoicePersona.ZEN_MASTER: "🕊️ 禅宗冥想大师 (Zen Master)",
            }
            title = title_map[active_p]
            line = lines[active_p]

            audio_settings = {
                VoicePersona.PRO_COACH: (0.0, 1.05),
                VoicePersona.HYPE_CASTER: (0.2, 1.25),
                VoicePersona.SARCASTIC_BUDDY: (0.1, 1.15),
                VoicePersona.ZEN_MASTER: (-0.15, 0.90),
            }
            pitch, speed = audio_settings[active_p]

        all_lines_str = {k.value: v for k, v in lines.items()}

        md = (
            f"**多重人格大师声线矩阵 ({title})**:\n"
            f"• **当前语音播报**: “{line}”\n"
            f"• **音频声学参数**: 音调微调 {pitch:+.2f} | 语速倍率 {speed:.2f}x\n"
            f"• **四大声优剧场台词库**:\n"
            f"  - 严肃教头: “{lines[VoicePersona.PRO_COACH]}”\n"
            f"  - 激情解说: “{lines[VoicePersona.HYPE_CASTER]}”\n"
            f"  - 毒舌牌友: “{lines[VoicePersona.SARCASTIC_BUDDY]}”\n"
            f"  - 禅宗大师: “{lines[VoicePersona.ZEN_MASTER]}”"
        )

        return PersonaMatrixResponse(
            active_persona=active_p,
            persona_title=title,
            spoken_line=line,
            audio_pitch_shift=pitch,
            audio_speed_rate=speed,
            all_persona_lines=all_lines_str,
            auto_switched_due_to_tilt=auto_tilt,
            summary_markdown=md,
        )
