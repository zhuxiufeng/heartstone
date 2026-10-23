"""
ArenaCareerVault: Long-Term Player Career Records, 12-Win Trophy Showcase & Infographic Exporter.
Tracks long-term arena winrates per class, average wins per run, 12-win mastery achievements,
and exports high-resolution, self-contained HTML/SVG battle infographics for sharing.
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ArenaCareerVault")


def get_default_career_file() -> Path:
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).resolve().parent
    else:
        base_dir = Path(__file__).resolve().parent.parent
    return base_dir / "cache" / "arena_career_vault.json"


CAREER_FILE = get_default_career_file()


@dataclass
class ArenaRunRecord:
    run_id: str
    timestamp: float
    hero_class: str
    wins: int
    losses: int
    deck_card_names: List[str] = field(default_factory=list)
    mvp_card: str = ""
    is_twelve_wins: bool = False


@dataclass
class CareerSummary:
    total_runs: int
    total_wins: int
    total_losses: int
    overall_winrate_pct: float
    average_wins_per_run: float
    twelve_win_trophies: int
    best_hero_class: str
    best_hero_winrate_pct: float
    hero_breakdown: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    summary_markdown: str = ""


class ArenaCareerVault:
    """Manages persistent career database and generates shareable match infographics."""

    _instance: Optional[ArenaCareerVault] = None

    def __init__(self, file_path: Path = CAREER_FILE) -> None:
        self.file_path = file_path
        self.runs: List[ArenaRunRecord] = []
        self._load()

    @classmethod
    def get_instance(cls) -> ArenaCareerVault:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load(self) -> None:
        if not self.file_path.exists():
            return
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.runs = [
                    ArenaRunRecord(
                        run_id=item["run_id"],
                        timestamp=item["timestamp"],
                        hero_class=item["hero_class"],
                        wins=item["wins"],
                        losses=item["losses"],
                        deck_card_names=item.get("deck_card_names", []),
                        mvp_card=item.get("mvp_card", ""),
                        is_twelve_wins=item.get("is_twelve_wins", item["wins"] >= 12),
                    )
                    for item in data.get("runs", [])
                ]
                # Sync to DuckDB
                try:
                    from .duckdb_manager import DuckDBManager
                    db = DuckDBManager.get_instance()
                    if db.is_available() and db.query_scalar("SELECT count(*) FROM career_runs") == 0:
                        for r in self.runs:
                            db.record_career_run(
                                run_id=r.run_id,
                                timestamp=r.timestamp,
                                hero_class=r.hero_class,
                                wins=r.wins,
                                losses=r.losses,
                                deck_cards=r.deck_card_names,
                                mvp_card=r.mvp_card,
                                is_twelve_wins=r.is_twelve_wins,
                            )
                except Exception as ex:
                    logger.debug(f"DuckDB career sync on load: {ex}")
        except Exception as e:
            logger.warning(f"Failed to load career data: {e}")

    def save(self) -> None:
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            data = {"runs": [asdict(r) for r in self.runs]}
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save career data: {e}")

    def record_run(self, hero_class: str, wins: int, losses: int, deck_card_names: Optional[List[str]] = None, mvp_card: str = "") -> ArenaRunRecord:
        import time
        rec = ArenaRunRecord(
            run_id=f"RUN_{int(time.time())}",
            timestamp=time.time(),
            hero_class=hero_class.upper(),
            wins=wins,
            losses=losses,
            deck_card_names=deck_card_names or [],
            mvp_card=mvp_card,
            is_twelve_wins=(wins >= 12),
        )
        self.runs.append(rec)
        self.save()
        try:
            from .duckdb_manager import DuckDBManager
            db = DuckDBManager.get_instance()
            if db.is_available():
                db.record_career_run(
                    run_id=rec.run_id,
                    timestamp=rec.timestamp,
                    hero_class=rec.hero_class,
                    wins=rec.wins,
                    losses=rec.losses,
                    deck_cards=rec.deck_card_names,
                    mvp_card=rec.mvp_card,
                    is_twelve_wins=rec.is_twelve_wins,
                )
        except Exception as e:
            logger.debug(f"DuckDB record_run sync: {e}")
        return rec

    def get_duckdb_summary(self) -> Optional[Dict[str, Any]]:
        """Calculates multi-dimensional career statistics via DuckDB vectorized OLAP."""
        try:
            from .duckdb_manager import DuckDBManager
            db = DuckDBManager.get_instance()
            if db.is_available():
                return db.aggregate_career_summary()
        except Exception as e:
            logger.debug(f"DuckDB get_duckdb_summary error: {e}")
        return None

    def get_summary(self) -> CareerSummary:
        total_runs = len(self.runs)
        if total_runs == 0:
            return CareerSummary(
                total_runs=0,
                total_wins=0,
                total_losses=0,
                overall_winrate_pct=0.0,
                average_wins_per_run=0.0,
                twelve_win_trophies=0,
                best_hero_class="--",
                best_hero_winrate_pct=0.0,
                summary_markdown="暂无竞技场生涯记录，开始一局竞技场建立档案！",
            )

        total_wins = sum(r.wins for r in self.runs)
        total_losses = sum(r.losses for r in self.runs)
        total_matches = total_wins + total_losses
        overall_wr = (total_wins / max(1, total_matches)) * 100.0
        avg_wins = total_wins / total_runs
        trophies = sum(1 for r in self.runs if r.is_twelve_wins)

        # Hero breakdown
        hero_stats: Dict[str, Dict[str, Any]] = {}
        for r in self.runs:
            h = r.hero_class
            if h not in hero_stats:
                hero_stats[h] = {"runs": 0, "wins": 0, "losses": 0}
            hero_stats[h]["runs"] += 1
            hero_stats[h]["wins"] += r.wins
            hero_stats[h]["losses"] += r.losses

        best_h = "--"
        best_h_wr = 0.0
        for h, s in hero_stats.items():
            tot = s["wins"] + s["losses"]
            wr = (s["wins"] / max(1, tot)) * 100.0
            s["winrate_pct"] = round(wr, 1)
            if wr > best_h_wr and tot >= 3:
                best_h_wr = wr
                best_h = h

        md = (
            f"**竞技场生涯大盘**: 累计 {total_runs} 轮竞技场 (场均胜场 **{avg_wins:.2f}** 胜 / 总胜率 **{overall_wr:.1f}%**)\n"
            f"• 🏆 **12胜辉煌通关**: **{trophies}** 次\n"
            f"• 👑 **最佳本命职业**: **{best_h}** (胜率 **{best_h_wr:.1f}%**)"
        )

        return CareerSummary(
            total_runs=total_runs,
            total_wins=total_wins,
            total_losses=total_losses,
            overall_winrate_pct=overall_wr,
            average_wins_per_run=avg_wins,
            twelve_win_trophies=trophies,
            best_hero_class=best_h,
            best_hero_winrate_pct=best_h_wr,
            hero_breakdown=hero_stats,
            summary_markdown=md,
        )

    def generate_shareable_infographic_html(self, run: Optional[ArenaRunRecord] = None) -> str:
        """Generates self-contained standalone HTML infographic card."""
        summary = self.get_summary()
        current_run = run or (self.runs[-1] if self.runs else None)

        hero = current_run.hero_class if current_run else "MAGE"
        wins = current_run.wins if current_run else 12
        losses = current_run.losses if current_run else 2
        is_12 = (wins >= 12)

        badge_color = "#f59e0b" if is_12 else "#3b82f6"
        badge_title = "🏆 12胜 宗师通关认证" if is_12 else f"⚔️ {wins}胜 竞技场战报"

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>炉石传说 竞技场战绩荣誉卡</title>
    <style>
        body {{
            background: #090d16;
            color: #f1f5f9;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            padding: 20px;
        }}
        .card {{
            background: linear-gradient(135deg, #131d31 0%, #0d1527 100%);
            border: 2px solid {badge_color};
            border-radius: 16px;
            width: 480px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.6);
            overflow: hidden;
            padding: 28px;
        }}
        .header {{
            text-align: center;
            border-bottom: 1px solid #1e293b;
            padding-bottom: 16px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            color: {badge_color};
            font-size: 24px;
            margin: 0 0 8px 0;
        }}
        .score-box {{
            display: flex;
            justify-content: space-around;
            background: rgba(15, 23, 42, 0.7);
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 20px;
        }}
        .stat {{
            text-align: center;
        }}
        .stat-val {{
            font-size: 32px;
            font-weight: 800;
            color: #38bdf8;
        }}
        .stat-lbl {{
            font-size: 12px;
            color: #94a3b8;
            margin-top: 4px;
        }}
        .career-section {{
            background: #1e293b;
            border-radius: 10px;
            padding: 14px;
            font-size: 13px;
            line-height: 1.6;
        }}
        .footer {{
            text-align: center;
            font-size: 11px;
            color: #64748b;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <h1>{badge_title}</h1>
            <div style="color: #cbd5e1; font-weight: 600;">职业: {hero}</div>
        </div>
        <div class="score-box">
            <div class="stat">
                <div class="stat-val" style="color: {badge_color};">{wins}</div>
                <div class="stat-lbl">胜场 (Wins)</div>
            </div>
            <div class="stat">
                <div class="stat-val" style="color: #ef4444;">{losses}</div>
                <div class="stat-lbl">败场 (Losses)</div>
            </div>
            <div class="stat">
                <div class="stat-val">{wins / max(1, wins + losses) * 100:.0f}%</div>
                <div class="stat-lbl">本轮胜率</div>
            </div>
        </div>
        <div class="career-section">
            <div style="font-weight: bold; color: #38bdf8; margin-bottom: 6px;">🏅 生涯总数据</div>
            <div>• 累计总轮次: {summary.total_runs} 轮 (场均 {summary.average_wins_per_run:.2f} 胜)</div>
            <div>• 生涯胜率: {summary.overall_winrate_pct:.1f}% (胜 {summary.total_wins} / 负 {summary.total_losses})</div>
            <div>• 12胜宗师通关: {summary.twelve_win_trophies} 次</div>
            <div>• 最佳本命职业: {summary.best_hero_class} ({summary.best_hero_winrate_pct:.1f}%)</div>
        </div>
        <div class="footer">
            Hearthstone Grandmaster AI Assistant • 巅峰大师认证战报
        </div>
    </div>
</body>
</html>"""
        return html
