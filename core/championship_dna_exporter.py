"""
ChampionshipDnaExporter: Arena 12-Win Deck Archetype DNA Rating & High-Res Victory Infographic Exporter.
Analyzes deck composition against 12-win championship standards (curve balance, card tier quality,
functional tool quotas, and synergy density) and renders high-definition victory share posters.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .card_db import CardInfo
from .draft_quota_tracker import DraftQuotaTracker

logger = logging.getLogger("ChampionshipDnaExporter")


@dataclass
class ChampionshipDnaReport:
    dna_score: int                 # 0 to 100
    archetype_tier: str            # "12_WINS_CHAMPION", "9_TO_11_WINS", "6_TO_8_WINS", "STRUGGLE"
    dna_title: str                 # e.g. "👑 94分 · 黄金12胜冲榜相貌 (节奏中速法)"
    curve_score: int               # 0 to 25
    quality_score: int             # 0 to 30
    quota_score: int               # 0 to 25
    synergy_score: int             # 0 to 20
    strengths: List[str] = field(default_factory=list)
    vulnerabilities: List[str] = field(default_factory=list)
    tactical_verdict: str = ""


class ChampionshipDnaExporter:
    """Evaluates championship DNA index and renders victory poster images."""

    @classmethod
    def evaluate_deck_dna(
        cls,
        deck: List[CardInfo],
        hero_class: str = "法师",
    ) -> ChampionshipDnaReport:
        """Evaluates overall 12-win blueprint fit across 4 foundational dimensions."""
        if not deck:
            return ChampionshipDnaReport(
                dna_score=50,
                archetype_tier="6_TO_8_WINS",
                dna_title="⚖️ 50分 · 雏形阶段套牌",
                curve_score=10,
                quality_score=15,
                quota_score=15,
                synergy_score=10,
                strengths=["套牌处于初建阶段"],
                vulnerabilities=["尚无足够卡牌评估"],
                tactical_verdict="继续选牌以解锁完整的套牌基因图谱",
            )

        # 1. Curve Score (0-25 pts)
        curve = [0] * 8
        for c in deck:
            cost = min(getattr(c, "cost", 2), 7)
            curve[cost] += 1

        curve_score = 0
        if 4 <= curve[2] <= 8:
            curve_score += 10
        elif curve[2] >= 2:
            curve_score += 6

        if 5 <= (curve[3] + curve[4]) <= 11:
            curve_score += 10
        elif (curve[3] + curve[4]) >= 3:
            curve_score += 6

        if 1 <= curve[7] <= 4:
            curve_score += 5
        elif curve[7] == 0:
            curve_score += 2

        # 2. Quality Score (0-30 pts)
        quality_pts = 0
        for c in deck:
            rarity = (getattr(c, "rarity", "") or "").upper()
            if rarity == "LEGENDARY":
                quality_pts += 1.8
            elif rarity == "EPIC":
                quality_pts += 1.2
            elif rarity == "RARE":
                quality_pts += 0.8
            else:
                quality_pts += 0.5
        quality_score = max(10, min(30, int(round(quality_pts))))

        # 3. Quota Score (0-25 pts)
        quota_rep = DraftQuotaTracker.evaluate_deck_quotas(deck, pick_number=len(deck))
        optimal_count = sum(1 for q in quota_rep.quotas if q.status == "OPTIMAL")
        deficit_count = sum(1 for q in quota_rep.quotas if "DEFICIT" in q.status)
        quota_score = max(5, min(25, optimal_count * 4 - deficit_count * 2 + 10))

        # 4. Synergy Score (0-20 pts)
        tribes: Dict[str, int] = {}
        for c in deck:
            race = (getattr(c, "race", "") or "").upper()
            if race:
                tribes[race] = tribes.get(race, 0) + 1
        max_tribe_count = max(tribes.values()) if tribes else 0
        synergy_score = min(20, 8 + max_tribe_count * 2)

        total_dna = max(35, min(99, 15 + curve_score + quality_score + quota_score + synergy_score))

        strengths = []
        vulns = []

        if curve_score >= 20:
            strengths.append("💎 前中期展开丝滑，不易卡手断节奏")
        else:
            vulns.append("⚠️ 前期2-3费随从曲线存在断档风险")

        if quota_score >= 18:
            strengths.append("🗡️ 单解、过牌与突袭工具组件配比极其完善")
        else:
            vulns.append("⚠️ 缺乏关键大解或续航过牌组件")

        if quality_score >= 24:
            strengths.append("👑 包含多张超标质变单卡，上限极高")

        if not strengths:
            strengths.append("⚖️ 基础攻防兼备，具备平稳过牌与随从交换能力")

        if total_dna >= 88:
            tier = "12_WINS_CHAMPION"
            title = f"👑 {total_dna}分 · 黄金12胜冲榜相貌 ({hero_class})"
            verdict = "套牌结构与组件配比达到顶级水准，具备直冲12胜冠军的扎实底蕴！"
        elif total_dna >= 75:
            tier = "9_TO_11_WINS"
            title = f"⭐ {total_dna}分 · 9~11胜优质强牌 ({hero_class})"
            verdict = "套牌整体非常扎实，细节决策拉满有望冲击12胜钥匙！"
        elif total_dna >= 60:
            tier = "6_TO_8_WINS"
            title = f"⚖️ {total_dna}分 · 6~8胜平稳回本套牌 ({hero_class})"
            verdict = "中规中矩的均势套牌，注重控场随从交换可稳定保本冲高。"
        else:
            tier = "STRUGGLE"
            title = f"⚠️ {total_dna}分 · 需精细运营的冷门套牌 ({hero_class})"
            verdict = "组件有所欠缺，需依赖神抽与对手失误破局。"

        return ChampionshipDnaReport(
            dna_score=total_dna,
            archetype_tier=tier,
            dna_title=title,
            curve_score=curve_score,
            quality_score=quality_score,
            quota_score=quota_score,
            synergy_score=synergy_score,
            strengths=strengths,
            vulnerabilities=vulns,
            tactical_verdict=verdict,
        )

    @classmethod
    def export_victory_infographic(
        cls,
        output_path: str,
        deck: List[CardInfo],
        hero_class: str = "法师",
        wins: int = 12,
        losses: int = 1,
    ) -> bool:
        """
        Renders a sleek high-res PNG share card summarizing match results,
        mana curve, championship DNA rating, and full decklist.
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            logger.warning("Pillow not installed; cannot export graphical poster.")
            return False

        width = 680
        height = 920
        img = Image.new("RGB", (width, height), color="#0f172a")
        draw = ImageDraw.Draw(img)

        # Background gradient banner
        draw.rectangle([(0, 0), (width, 140)], fill="#1e293b")
        draw.line([(0, 140), (width, 140)], fill="#3b82f6", width=3)

        report = cls.evaluate_deck_dna(deck, hero_class)

        # Text banner
        try:
            font_title = ImageFont.truetype("msyh.ttc", 24)
            font_sub = ImageFont.truetype("msyh.ttc", 14)
            font_body = ImageFont.truetype("msyh.ttc", 12)
        except Exception:
            font_title = font_sub = font_body = ImageFont.load_default()

        draw.text((24, 20), f"🏆 炉石竞技场战报 · {wins} 胜 {losses} 负", fill="#fbbf24", font=font_title)
        draw.text((24, 60), f"职业: {hero_class} | {report.dna_title}", fill="#38bdf8", font=font_sub)
        draw.text((24, 90), f"战术研判: {report.tactical_verdict}", fill="#94a3b8", font=font_body)

        # DNA score rating badge
        draw.rectangle([(width - 150, 20), (width - 24, 110)], fill="#0f172a", outline="#fbbf24", width=2)
        draw.text((width - 135, 30), "12胜相貌指数", fill="#fde68a", font=font_body)
        draw.text((width - 120, 52), f"{report.dna_score}", fill="#fbbf24", font=font_title)
        draw.text((width - 138, 86), "CHAMPION DNA", fill="#64748b", font=font_body)

        # Curve Chart Area
        draw.rectangle([(24, 160), (width - 24, 280)], fill="#1e293b", outline="#334155")
        draw.text((36, 170), "📊 法力曲线分布 (Mana Curve)", fill="#e2e8f0", font=font_sub)

        curve = [0] * 8
        for c in deck:
            cost = min(getattr(c, "cost", 2), 7)
            curve[cost] += 1
        max_c = max(max(curve), 1)

        bar_w = 48
        start_x = 50
        base_y = 265
        for i in range(8):
            bx = start_x + i * 72
            h_bar = int((curve[i] / max_c) * 60)
            draw.rectangle([(bx, base_y - h_bar), (bx + bar_w, base_y)], fill="#38bdf8")
            lbl = f"{i}费" if i < 7 else "7+费"
            draw.text((bx + 8, base_y + 4), lbl, fill="#94a3b8", font=font_body)
            draw.text((bx + 14, base_y - h_bar - 16), str(curve[i]), fill="#f8fafc", font=font_body)

        # Decklist columns
        draw.rectangle([(24, 300), (width - 24, height - 50)], fill="#1e293b", outline="#334155")
        draw.text((36, 310), f"📜 冠军套牌全卡表 (共 {len(deck)} 张)", fill="#e2e8f0", font=font_sub)

        # Render 2 columns of cards
        col1_x = 40
        col2_x = 350
        y_off = 340
        for idx, c in enumerate(deck[:30]):
            col = col1_x if idx < 15 else col2_x
            row_y = y_off + (idx % 15) * 32
            c_name = getattr(c, "name", f"卡牌#{idx+1}")
            c_cost = getattr(c, "cost", 2)
            c_type = "随从" if (getattr(c, "card_type", "") == "MINION") else "法术"
            draw.rectangle([(col, row_y), (col + 280, row_y + 26)], fill="#0f172a", outline="#334155")
            draw.rectangle([(col, row_y), (col + 24, row_y + 26)], fill="#0284c7")
            draw.text((col + 6, row_y + 5), str(c_cost), fill="#fff", font=font_body)
            draw.text((col + 32, row_y + 5), c_name, fill="#f1f5f9", font=font_body)
            draw.text((col + 235, row_y + 5), c_type, fill="#64748b", font=font_body)

        # Footer
        draw.text((width // 2 - 130, height - 32), "Hearthstone Arena AI · 冠军战报生成器", fill="#475569", font=font_body)

        try:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            img.save(output_path, "PNG")
            logger.info(f"Exported victory infographic to {output_path}")
            return True
        except Exception as e:
            logger.warning(f"Failed to save infographic to {output_path}: {e}")
            return False
