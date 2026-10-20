"""
MatchReviewDashboardGenerator: Interactive Post-Match Review & Blunder Heatmap Dashboard.
Generates a standalone, fully interactive HTML dashboard with:
- SVG Winrate Swing Timeline Chart
- Turn Decision Accuracy Heatmap Strip (Brilliant / Best / Good / Inaccuracy / Blunder)
- Interactive Turn Inspector (Board snapshot, Hand, Plan difference, Topdeck Luck)
- Printable / Exportable Match Performance Dossier
"""

from __future__ import annotations

import html
import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .turn_replayer import MatchReplaySummary, TurnReviewNode

logger = logging.getLogger("MatchReviewDashboard")


class MatchReviewDashboardGenerator:
    """Generates an interactive, standalone HTML replay report."""

    _latest_html: str = ""

    @classmethod
    def get_latest_html(cls) -> str:
        return cls._latest_html

    @classmethod
    def generate_dashboard_html(
        cls,
        summary: MatchReplaySummary,
        friendly_class: str = "WARRIOR",
        opponent_class: str = "MAGE",
        output_dir: Optional[str] = None,
    ) -> str:
        """
        Builds the standalone HTML dashboard and writes it to disk if output_dir is given.
        """
        is_win = summary.result.upper() == "WIN"
        win_color = "#10b981" if is_win else "#ef4444"
        win_badge = "🏆 最终胜利 (VICTORY)" if is_win else "💀 惜败告终 (DEFEAT)"

        # Prepare timeline points for SVG Winrate Chart
        turns = summary.turn_nodes
        total_turns = len(turns)
        width = 720
        height = 180
        padding = 40

        chart_points = []
        svg_circles = []
        svg_labels = []

        if total_turns > 1:
            step_x = (width - 2 * padding) / (total_turns - 1)
        else:
            step_x = 0

        for i, node in enumerate(turns):
            x = padding + i * step_x
            wr = max(0.0, min(100.0, float(node.ai_winrate)))
            # SVG y coordinate: 100% winrate at padding_top, 0% at height - padding
            y = (height - padding) - (wr / 100.0) * (height - 2 * padding)
            chart_points.append(f"{x:.1f},{y:.1f}")

            # Circle color based on blunder
            c_fill = node.grade_color
            r = "6" if "Blunder" in node.action_grade or node.had_lethal else "4"
            svg_circles.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{c_fill}" stroke="#0f172a" stroke-width="2" '
                f'onclick="selectTurn({i})" style="cursor: pointer;" data-turn="{node.turn_number}">'
                f'<title>回合 {node.turn_number}: 胜率 {wr:.1f}%, 评级: {html.escape(node.action_grade)}</title>'
                f'</circle>'
            )
            svg_labels.append(
                f'<text x="{x:.1f}" y="{height - 10}" fill="#94a3b8" font-size="10" text-anchor="middle">T{node.turn_number}</text>'
            )

        points_str = " ".join(chart_points) if chart_points else f"{padding},{height/2}"

        # Heatmap Blocks
        heatmap_blocks = []
        for i, node in enumerate(turns):
            heatmap_blocks.append(
                f'<div class="heatmap-block" style="background: {node.grade_color};" '
                f'onclick="selectTurn({i})" title="回合 {node.turn_number}: {html.escape(node.action_grade)}">'
                f'T{node.turn_number}'
                f'</div>'
            )
        heatmap_html = "".join(heatmap_blocks)

        # JSON data for client-side interactivity
        turns_data = []
        for node in turns:
            turns_data.append({
                "turn": node.turn_number,
                "mana": f"{node.mana}/{node.max_mana}",
                "friendly_hp": node.friendly_hp,
                "enemy_hp": node.enemy_hp,
                "grade": node.action_grade,
                "grade_color": node.grade_color,
                "score": node.score,
                "winrate": f"{node.ai_winrate:.1f}%",
                "comment": node.analysis_comment,
                "ai_plan": node.ai_best_plan,
                "player_plays": node.player_actual_plays,
                "friendly_board": node.friendly_board,
                "enemy_board": node.enemy_board,
                "hand_cards": node.hand_cards,
                "had_lethal": node.had_lethal,
            })
        turns_json = json.dumps(turns_data, ensure_ascii=False)

        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>炉石竞技场复盘报告 · {friendly_class} vs {opponent_class}</title>
    <style>
        :root {{
            --bg: #090d16;
            --card-bg: #111827;
            --border: #1e293b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent: #38bdf8;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: var(--bg);
            color: var(--text-main);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            padding: 24px;
            display: flex;
            justify-content: center;
        }}
        .container {{
            max-width: 900px;
            width: 100%;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }}
        .header {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-left: 6px solid {win_color};
        }}
        .title-box h1 {{
            font-size: 20px;
            font-weight: 700;
            margin-bottom: 6px;
        }}
        .title-box .sub {{
            color: var(--text-muted);
            font-size: 13px;
        }}
        .score-pill {{
            text-align: right;
        }}
        .score-val {{
            font-size: 28px;
            font-weight: 800;
            color: {win_color};
        }}
        .score-sub {{
            font-size: 11px;
            color: var(--text-muted);
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 12px;
        }}
        .stat-card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 12px;
            text-align: center;
        }}
        .stat-card .val {{
            font-size: 20px;
            font-weight: 700;
            margin-bottom: 4px;
        }}
        .stat-card .lbl {{
            font-size: 11px;
            color: var(--text-muted);
        }}
        .section-card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
        }}
        .section-title {{
            font-size: 15px;
            font-weight: 600;
            color: var(--accent);
            margin-bottom: 14px;
            display: flex;
            justify-content: space-between;
        }}
        /* SVG Timeline */
        .chart-box {{
            width: 100%;
            background: rgba(15, 23, 42, 0.4);
            border-radius: 8px;
            padding: 10px;
            overflow-x: auto;
        }}
        svg {{
            width: 100%;
            height: 180px;
            display: block;
        }}
        /* Heatmap */
        .heatmap-strip {{
            display: flex;
            gap: 6px;
            overflow-x: auto;
            padding: 8px 0;
        }}
        .heatmap-block {{
            flex: 1;
            min-width: 44px;
            height: 38px;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 11px;
            font-weight: 700;
            color: #ffffff;
            cursor: pointer;
            transition: transform 0.15s ease, filter 0.15s ease;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }}
        .heatmap-block:hover {{
            transform: translateY(-2px);
            filter: brightness(1.2);
        }}
        /* Inspector */
        .inspector-box {{
            margin-top: 16px;
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 16px;
        }}
        .inspector-head {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 1px solid var(--border);
        }}
        .plan-diff {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin-top: 12px;
        }}
        .plan-box {{
            background: rgba(30, 41, 59, 0.5);
            padding: 12px;
            border-radius: 6px;
            border-left: 3px solid var(--accent);
        }}
        .plan-box h4 {{
            font-size: 12px;
            margin-bottom: 8px;
            color: var(--text-muted);
        }}
        .step-li {{
            font-size: 12px;
            color: var(--text-main);
            margin-bottom: 4px;
            line-height: 1.4;
        }}
        .board-tag {{
            display: inline-block;
            background: rgba(56, 189, 248, 0.1);
            color: #38bdf8;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 11px;
            margin: 2px 4px 2px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <div class="title-box">
                <h1>{win_badge} · {friendly_class} vs {opponent_class}</h1>
                <div class="sub">总回合数: {summary.total_turns} 回合 · 综合评级: {summary.grade_tier}</div>
            </div>
            <div class="score-pill">
                <div class="score-val">{summary.overall_accuracy_pct:.1f}%</div>
                <div class="score-sub">整体对局决策准确度 (Accuracy)</div>
            </div>
        </div>

        <!-- Metric Grid -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="val" style="color: #a855f7;">{summary.brilliant_count}</div>
                <div class="lbl">★ 妙手 (Brilliant)</div>
            </div>
            <div class="stat-card">
                <div class="val" style="color: #10b981;">{summary.best_count}</div>
                <div class="lbl">✅ 最佳 (Best)</div>
            </div>
            <div class="stat-card">
                <div class="val" style="color: #38bdf8;">{summary.good_count}</div>
                <div class="lbl">⚖️ 良好 (Good)</div>
            </div>
            <div class="stat-card">
                <div class="val" style="color: #eab308;">{summary.inaccuracy_count}</div>
                <div class="lbl">⚠️ 疑问手 (Inaccuracy)</div>
            </div>
            <div class="stat-card">
                <div class="val" style="color: #ef4444;">{summary.blunder_count}</div>
                <div class="lbl">❌ 严重伏笔 (Blunder)</div>
            </div>
        </div>

        <!-- SVG Winrate Chart -->
        <div class="section-card">
            <div class="section-title">
                <span>📈 胜率波动走势图 (Winrate Swing Timeline)</span>
                <span style="font-size: 11px; color: var(--text-muted);">点击节点可查看单回合详情</span>
            </div>
            <div class="chart-box">
                <svg viewBox="0 0 {width} {height}">
                    <line x1="{padding}" y1="{height/2}" x2="{width - padding}" y2="{height/2}" stroke="#334155" stroke-dasharray="4" stroke-width="1" />
                    <text x="10" y="{padding + 10}" fill="#64748b" font-size="10">100%</text>
                    <text x="10" y="{height/2 + 3}" fill="#64748b" font-size="10">50%</text>
                    <text x="10" y="{height - padding}" fill="#64748b" font-size="10">0%</text>
                    <polyline fill="none" stroke="#38bdf8" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" points="{points_str}" />
                    {"".join(svg_circles)}
                    {"".join(svg_labels)}
                </svg>
            </div>
        </div>

        <!-- Blunder Heatmap Strip -->
        <div class="section-card">
            <div class="section-title">
                <span>🔥 回合失误热力带 (Blunder Heatmap Strip)</span>
            </div>
            <div class="heatmap-strip">
                {heatmap_html}
            </div>

            <!-- Interactive Turn Inspector -->
            <div class="inspector-box" id="inspector-container">
                <div class="inspector-head">
                    <div>
                        <span id="inspect-turn-lbl" style="font-weight: 700; font-size: 15px; margin-right: 8px;">回合 1 详情</span>
                        <span id="inspect-grade-badge" style="padding: 2px 8px; border-radius: 4px; font-size: 11px; background: #10b981; color: white;">最佳 (Best)</span>
                    </div>
                    <div style="font-size: 12px; color: var(--text-muted);">
                        水晶: <span id="inspect-mana" style="color: #38bdf8;">1/1</span> | 我方: <span id="inspect-fhp" style="color: #34d399;">30</span> HP | 敌方: <span id="inspect-ehp" style="color: #f87171;">30</span> HP
                    </div>
                </div>

                <div id="inspect-comment" style="font-size: 13px; color: #cbd5e1; line-height: 1.5; margin-bottom: 12px;"></div>

                <div class="plan-diff">
                    <div class="plan-box" style="border-left-color: #38bdf8;">
                        <h4>🤖 AI 推荐最佳路线 (Best Plan)</h4>
                        <div id="inspect-ai-steps"></div>
                    </div>
                    <div class="plan-box" style="border-left-color: #fbbf24;">
                        <h4>👤 玩家实际出牌 (Actual Play)</h4>
                        <div id="inspect-player-steps"></div>
                    </div>
                </div>

                <div style="margin-top: 14px; font-size: 11px; color: var(--text-muted);">
                    场面快照: <span id="inspect-board-tags"></span>
                </div>
            </div>
        </div>
    </div>

    <script>
        const turnsData = {turns_json};

        function selectTurn(index) {{
            if (!turnsData || !turnsData[index]) return;
            const t = turnsData[index];
            document.getElementById('inspect-turn-lbl').innerText = `回合 ${{t.turn}} 详情 (胜率 ${{t.winrate}})`;
            const badge = document.getElementById('inspect-grade-badge');
            badge.innerText = t.grade;
            badge.style.background = t.grade_color;
            document.getElementById('inspect-mana').innerText = t.mana;
            document.getElementById('inspect-fhp').innerText = t.friendly_hp;
            document.getElementById('inspect-ehp').innerText = t.enemy_hp;
            document.getElementById('inspect-comment').innerText = t.comment;

            // AI steps
            const aiBox = document.getElementById('inspect-ai-steps');
            aiBox.innerHTML = '';
            (t.ai_plan || []).forEach(step => {{
                const d = document.createElement('div');
                d.className = 'step-li';
                d.innerText = `➔ ${{step}}`;
                aiBox.appendChild(d);
            }});
            if (!t.ai_plan || t.ai_plan.length === 0) {{
                aiBox.innerHTML = '<div class="step-li" style="color:#64748b;">(无打出动作/转甲过牌)</div>';
            }}

            // Player steps
            const pBox = document.getElementById('inspect-player-steps');
            pBox.innerHTML = '';
            (t.player_plays || []).forEach(step => {{
                const d = document.createElement('div');
                d.className = 'step-li';
                d.innerText = `• ${{step}}`;
                pBox.appendChild(d);
            }});
            if (!t.player_plays || t.player_plays.length === 0) {{
                pBox.innerHTML = '<div class="step-li" style="color:#64748b;">(结束回合)</div>';
            }}

            // Board tags
            const tagsBox = document.getElementById('inspect-board-tags');
            tagsBox.innerHTML = '';
            (t.friendly_board || []).forEach(m => {{
                const sp = document.createElement('span');
                sp.className = 'board-tag';
                sp.innerText = `友: ${{m}}`;
                tagsBox.appendChild(sp);
            }});
            (t.enemy_board || []).forEach(m => {{
                const sp = document.createElement('span');
                sp.className = 'board-tag';
                sp.style.color = '#f87171';
                sp.style.background = 'rgba(239, 68, 68, 0.1)';
                sp.innerText = `敌: ${{m}}`;
                tagsBox.appendChild(sp);
            }});
        }}

        // Select first turn initially
        if (turnsData.length > 0) {{
            selectTurn(0);
        }}
    </script>
</body>
</html>
"""
        cls._latest_html = html_content

        # Write to disk if output_dir is configured
        if output_dir:
            try:
                p_dir = Path(output_dir)
                p_dir.mkdir(parents=True, exist_ok=True)
                file_path = p_dir / f"match_review_{int(time.time())}.html"
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                logger.info(f"Exported match review dashboard to {file_path}")
            except Exception as e:
                logger.warning(f"Failed to export match review HTML: {e}")

        return html_content
