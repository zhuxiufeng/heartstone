"""
WebCompanion: LAN Second-Screen Mobile Web Server.
Runs an ultra-lightweight HTTP server on port 8899 so players can open their
smartphone or tablet on their local network as a dedicated tactical HUD.
Supports two-way interactive control: touch-based checklist toggling,
route A/B switching, ghost board projection, quota radar, and sub-50ms live synchronization.
"""

from __future__ import annotations

import json
import logging
import socket
import threading
import time
try:
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer as HTTPServer
except ImportError:
    from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, List, Optional

logger = logging.getLogger("WebCompanion")

_CURRENT_STATE: Dict[str, Any] = {
    "mode": "WAITING",
    "turn": 1,
    "mana": 1,
    "max_mana": 1,
    "opponent_hero": "等待对局",
    "archetype": "--",
    "winrate_pct": 50.0,
    "win_tier": "均势博弈",
    "plan_a_title": "等待出牌推演...",
    "plan_a_steps": [],
    "plan_a_ev": 0.0,
    "plan_b_title": "",
    "plan_b_steps": [],
    "plan_b_ev": 0.0,
    "active_plan": "A",
    "checked_steps": [],
    "blunder_alert": "",
    "compass_directive": "系统就绪，等待对战回合开始",
    "hand_warnings": [],
    "burst_danger": "",
    "discover_guidance": "",
    "variance_policy": "",
    "curve_foresight": "",
    "positioning_advice": "",
    "draw_first_directive": "",
    "next_turn_threat_cards": [],
    "lethal_cushion": "",
    "ghost_board_summary": "",
    "quota_strip": "",
    "negative_deductions": [],
    "rng_badge": "",
    "personal_habit_reminder": "",
    "resilience_badge": "",
    "resilience_verdict": "",
    "championship_dna": "",
    "hypergeometric_gamble": "",
    "tilt_status": "",
    "mind_reading_summary": "",
    "decision_tree_ascii": "",
    "topdeck_summary": "",
    "topdeck_matrix": {},
    "lookahead_summary": "",
    "lookahead_table": "",
    "game_phase": "EARLY_GAME",
    "game_phase_zh": "前期节奏争夺",
    "game_phase_weights": {},
    "leak_score": 100.0,
    "leak_grade": "S 宗师无暇",
    "leak_summary": "",
    "capsule_summary": "",
    "locale": "zh-CN",
    "secrets_summary": "",
    "hand_age_summary": "",
    "matchup_sandbox": {},
    "career_summary": "",
    "copilot_plan": {},
    "hand_silhouette": {},
    "future_draft_forecast": {},
    "what_if_report": {},
    "talkshow_podcast": {},
}

_REPLAY_DATA: Dict[str, Any] = {}
_STATE_VERSION: int = 1


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>炉石战术副屏 · Hearthstone AI HUD</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Microsoft YaHei", sans-serif; }
        body { background: #0f172a; color: #f8fafc; padding: 12px; padding-bottom: 24px; -webkit-font-smoothing: antialiased; }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 8px; margin-bottom: 10px; }
        .title { font-size: 16px; font-weight: bold; color: #38bdf8; display: flex; align-items: center; gap: 6px; }
        .turn-badge { background: #065f46; color: #6ee7b7; font-size: 12px; font-weight: bold; padding: 3px 8px; border-radius: 12px; }
        
        .winrate-card { background: #1e293b; border-radius: 8px; padding: 10px; margin-bottom: 10px; border-left: 4px solid #3b82f6; }
        .winrate-head { display: flex; justify-content: space-between; font-size: 13px; color: #94a3b8; margin-bottom: 4px; }
        .winrate-val { font-size: 22px; font-weight: bold; color: #38bdf8; }
        .progress-bar { height: 6px; background: #334155; border-radius: 3px; overflow: hidden; margin-top: 6px; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, #38bdf8, #10b981); width: 50%; transition: width 0.4s ease; }

        .blunder-banner { display: none; border-radius: 6px; padding: 8px; margin-bottom: 10px; font-size: 12px; }
        
        /* Two-way tabs */
        .plan-tabs { display: flex; gap: 8px; margin-bottom: 10px; }
        .plan-tab-btn { flex: 1; padding: 8px 10px; border-radius: 6px; font-size: 12px; font-weight: bold; border: 1px solid #475569; background: #1e293b; color: #94a3b8; cursor: pointer; text-align: center; transition: all 0.2s; }
        .plan-tab-btn.active-a { background: #0284c7; color: #ffffff; border-color: #38bdf8; box-shadow: 0 0 8px rgba(56, 189, 248, 0.4); }
        .plan-tab-btn.active-b { background: #d97706; color: #ffffff; border-color: #fbbf24; box-shadow: 0 0 8px rgba(251, 191, 36, 0.4); }

        .card { background: #1e293b; border-radius: 8px; padding: 10px; margin-bottom: 10px; }
        .card-plan-a { border-left: 4px solid #38bdf8; }
        .card-plan-b { border-left: 4px solid #fbbf24; }
        .card-title { font-size: 13px; font-weight: bold; margin-bottom: 6px; display: flex; justify-content: space-between; }
        
        /* Interactive Step Item */
        .step-item { display: flex; align-items: flex-start; gap: 8px; font-size: 12px; color: #e2e8f0; margin-bottom: 6px; padding: 6px 8px; border-radius: 6px; background: rgba(15, 23, 42, 0.4); cursor: pointer; user-select: none; transition: background 0.15s; }
        .step-item:active { background: rgba(56, 189, 248, 0.2); }
        .step-checkbox { width: 16px; height: 16px; border-radius: 4px; border: 1.5px solid #64748b; display: flex; align-items: center; justify-content: center; font-size: 11px; flex-shrink: 0; margin-top: 1px; }
        .step-item.checked .step-checkbox { background: #10b981; border-color: #10b981; color: #fff; }
        .step-item.checked .step-text { text-decoration: line-through; color: #64748b; }
        
        .compass-card { background: rgba(30, 41, 59, 0.7); border-radius: 6px; padding: 8px; font-size: 12px; color: #cbd5e1; border: 1px dashed #475569; }
        .footer { text-align: center; font-size: 10px; color: #64748b; margin-top: 14px; }
    </style>
</head>
<body>
    <div class="header">
        <div class="title">⚔️ 炉石对战掌上副屏</div>
        <div class="turn-badge" id="turn-badge">⚡ 回合 1 | 💎 1/1</div>
    </div>

    <!-- Tilt & Fatigue Status Header Badge -->
    <div id="tilt-banner" style="display: none; background: rgba(30, 41, 59, 0.85); border: 1px solid #475569; border-radius: 6px; padding: 6px 10px; font-size: 11px; margin-bottom: 8px; color: #94a3b8;">
        <span id="tilt-text">🎯 专注巅峰: 状态正佳</span>
    </div>

    <!-- Winrate & Match Status -->
    <div class="winrate-card">
        <div class="winrate-head">
            <span id="opp-label">对手: 等待检测</span>
            <span id="win-tier">均势博弈</span>
        </div>
        <div class="winrate-val" id="winrate-val">50.0%</div>
        <div class="progress-bar">
            <div class="progress-fill" id="progress-fill"></div>
        </div>
    </div>

    <!-- Alerts Banners -->
    <div class="blunder-banner" id="blunder-banner" style="background: #7f1d1d; border-left: 4px solid #ef4444; color: #fee2e2;">
        ⚠️ 伏笔拦截警报: <span id="blunder-text"></span>
    </div>

    <div class="blunder-banner" id="draw-banner" style="background: #78350f; border-left: 4px solid #f59e0b; color: #fef3c7;">
        🎲 不确定性先行铁律: <span id="draw-text"></span>
    </div>

    <div class="blunder-banner" id="burst-banner" style="background: #991b1b; border-left: 4px solid #ef4444; color: #fee2e2;">
        🚨 敌方绝杀警报: <span id="burst-text"></span>
    </div>

    <div class="blunder-banner" id="habit-banner" style="background: #312e81; border-left: 4px solid #818cf8; color: #e0e7ff;">
        💡 短板防范: <span id="habit-text"></span>
    </div>

    <!-- Arena 12-Win Quota Radar Card (Visible in Draft) -->
    <div class="card" id="quota-card" style="display: none; border-left: 4px solid #f59e0b;">
        <div class="card-title" style="color: #fbbf24;">🎯 竞技场 12 胜套牌定额雷达</div>
        <div id="quota-content" style="font-size: 11px; color: #e2e8f0; line-height: 1.5;"></div>
    </div>

    <!-- Championship DNA Rating Card (Draft/Result) -->
    <div class="card" id="dna-card" style="display: none; border-left: 4px solid #eab308;">
        <div class="card-title" style="color: #facc15;">👑 12 胜冠军套牌基因相貌</div>
        <div id="dna-content" style="font-size: 11px; color: #fef08a; line-height: 1.5;"></div>
    </div>

    <!-- Next-Turn Threat Radar -->
    <div class="card" id="threat-card" style="display: none; border-left: 4px solid #6366f1;">
        <div class="card-title">
            <span style="color: #a5b4fc;">🔮 对手下回合高危牌</span>
            <span id="lethal-cushion-badge" style="color: #34d399; font-size: 11px;"></span>
        </div>
        <div id="threat-items" style="font-size: 11px; color: #e2e8f0; line-height: 1.5;"></div>
    </div>

    <!-- Ghost Board Post-Trade State Preview -->
    <div class="card" id="ghost-card" style="display: none; border-left: 4px solid #14b8a6;">
        <div class="card-title" style="color: #2dd4bf;">👻 残局幽灵投影 (随从交换后存活预测)</div>
        <div id="ghost-content" style="font-size: 11px; color: #ccfbf1; line-height: 1.5;"></div>
    </div>

    <!-- RNG & Discover Cumulative Odds -->
    <div class="card" id="rng-card" style="display: none; border-left: 4px solid #ec4899;">
        <div class="card-title" style="color: #f472b6;">🎲 随机判定与发现概率透视</div>
        <div id="rng-content" style="font-size: 11px; color: #fdf2f8; line-height: 1.5;"></div>
    </div>

    <!-- Negative Hand Deduction Tree -->
    <div class="card" id="deduction-card" style="display: none; border-left: 4px solid #a855f7;">
        <div class="card-title" style="color: #c084fc;">🚫 敌方手牌逆向排查树</div>
        <div id="deduction-content" style="font-size: 11px; color: #f3e8ff; line-height: 1.5;"></div>
    </div>

    <!-- Hypergeometric Gamble Odds -->
    <div class="card" id="hyper-card" style="display: none; border-left: 4px solid #a855f7;">
        <div class="card-title" style="color: #c084fc;">🎲 牌库超几何神抽期望与搏命建议</div>
        <div id="hyper-content" style="font-size: 11px; color: #e2e8f0; line-height: 1.5;"></div>
    </div>

    <!-- Mind-Reading Opponent Dossier -->
    <div class="card" id="mind-card" style="display: none; border-left: 4px solid #06b6d4;">
        <div class="card-title" style="color: #22d3ee;">🧠 敌方手牌心战透视 (Mind-Reading)</div>
        <div id="mind-content" style="font-size: 11px; color: #cbd5e1; line-height: 1.5;"></div>
    </div>

    <!-- Tactical Decision Topology Tree -->
    <div class="card" id="tree-card" style="display: none; border-left: 4px solid #10b981;">
        <div class="card-title" style="color: #34d399;">🌲 战术多分支决策拓扑树</div>
        <div id="tree-content" style="font-size: 10px; color: #cbd5e1; line-height: 1.4; font-family: monospace; white-space: pre-wrap; background: rgba(15, 23, 42, 0.6); padding: 8px; border-radius: 4px;"></div>
    </div>

    <!-- Two-Way Route Switcher Tabs -->
    <div class="plan-tabs" id="plan-tabs-bar">
        <button class="plan-tab-btn active-a" id="tab-a" onclick="switchActivePlan('A')">🏆 方案 A · 最优线</button>
        <button class="plan-tab-btn" id="tab-b" onclick="switchActivePlan('B')">⚖️ 方案 B · 备选线</button>
    </div>

    <!-- Plan A Card -->
    <div class="card card-plan-a" id="plan-a-card">
        <div class="card-title">
            <span style="color: #38bdf8;">🏆 方案 A · 动作清单 (点击打勾)</span>
            <div>
                <span id="plan-a-resilience" style="color: #38bdf8; font-size: 11px; margin-right: 6px;"></span>
                <span id="plan-a-ev" style="color: #6ee7b7; font-size: 11px;">EV: +0.0</span>
            </div>
        </div>
        <div id="plan-a-steps"><div class="step-item"><div class="step-text">等待对战推演数据...</div></div></div>
        <div id="plan-a-extra" style="margin-top: 6px; font-size: 11px; color: #94a3b8; line-height: 1.4;"></div>
    </div>

    <!-- Plan B Card -->
    <div class="card card-plan-b" id="plan-b-card" style="display: none;">
        <div class="card-title">
            <span style="color: #fbbf24;">⚖️ 方案 B · 动作清单</span>
            <span id="plan-b-ev" style="color: #fde047; font-size: 11px;">EV: +0.0</span>
        </div>
        <div id="plan-b-steps"></div>
    </div>

    <!-- Compass & Discover Guidance -->
    <div class="compass-card" id="compass-box">
        🧭 战术罗盘: <span id="compass-text">系统就绪，等待回合数据...</span>
    </div>

    <div class="compass-card" id="discover-box" style="display: none; border-left: 3px solid #06b6d4; margin-top: 8px;">
        🔮 抓取导向: <span id="discover-text"></span>
    </div>

    <!-- Turn-by-Turn Replay Card -->
    <div class="card" id="replay-card" style="display: none; border-left: 4px solid #8b5cf6; margin-top: 10px;">
        <div class="card-title">
            <span style="color: #a78bfa;">🔍 步步复盘分析</span>
            <span id="replay-accuracy" style="color: #34d399; font-size: 11px; font-weight: bold;">精度: --%</span>
        </div>
        <div id="replay-badges" style="display: flex; gap: 4px; font-size: 10px; margin-bottom: 8px; flex-wrap: wrap;"></div>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <button id="replay-prev" onclick="stepReplay(-1)" style="background: #334155; color: #fff; border: 1px solid #475569; padding: 4px 10px; border-radius: 4px; font-size: 11px;">◀ 上一回合</button>
            <span id="replay-turn-indicator" style="font-size: 12px; font-weight: bold; color: #38bdf8;">第 1 回合</span>
            <button id="replay-next" onclick="stepReplay(1)" style="background: #334155; color: #fff; border: 1px solid #475569; padding: 4px 10px; border-radius: 4px; font-size: 11px;">下一回合 ▶</button>
        </div>
        <div id="replay-turn-content" style="background: rgba(15, 23, 42, 0.6); padding: 8px; border-radius: 6px; font-size: 11px; line-height: 1.5;"></div>
    </div>

    <div class="footer">
        HearthstoneArenaAI LAN Companion · 全双工交互版
    </div>

    <script>
        let currentReplay = null;
        let replayIndex = 0;
        let localCheckedSteps = new Set();
        let currentActivePlan = 'A';

        async function switchActivePlan(plan) {
            currentActivePlan = plan;
            const tabA = document.getElementById('tab-a');
            const tabB = document.getElementById('tab-b');
            const cardA = document.getElementById('plan-a-card');
            const cardB = document.getElementById('plan-b-card');

            if (plan === 'A') {
                tabA.className = 'plan-tab-btn active-a';
                tabB.className = 'plan-tab-btn';
                cardA.style.opacity = '1.0';
                if (cardB.dataset.hasSteps === 'true') {
                    cardB.style.opacity = '0.55';
                }
            } else {
                tabA.className = 'plan-tab-btn';
                tabB.className = 'plan-tab-btn active-b';
                cardA.style.opacity = '0.55';
                cardB.style.opacity = '1.0';
            }

            try {
                await fetch('/api/plan/select', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ plan: plan })
                });
            } catch (e) {}
        }

        async function toggleStep(index) {
            const isChecked = !localCheckedSteps.has(index);
            if (isChecked) {
                localCheckedSteps.add(index);
            } else {
                localCheckedSteps.delete(index);
            }
            updateStepDom(index, isChecked);

            try {
                await fetch('/api/checklist/toggle', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ index: index, checked: isChecked })
                });
            } catch (e) {}
        }

        function updateStepDom(index, isChecked) {
            const el = document.getElementById(`step-item-${index}`);
            if (el) {
                if (isChecked) {
                    el.classList.add('checked');
                    el.querySelector('.step-checkbox').innerText = '✔';
                } else {
                    el.classList.remove('checked');
                    el.querySelector('.step-checkbox').innerText = '';
                }
            }
        }

        function renderReplayTurn() {
            if (!currentReplay || !currentReplay.turns || currentReplay.turns.length === 0) return;
            const node = currentReplay.turns[replayIndex];
            document.getElementById('replay-turn-indicator').innerText = `第 ${node.turn_number} / ${currentReplay.total_turns} 回合`;
            
            const content = document.getElementById('replay-turn-content');
            content.innerHTML = `
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span style="color: ${node.grade_color}; font-weight: bold;">${node.action_grade}</span>
                    <span style="color: #cbd5e1;">得分: ${node.score}</span>
                </div>
                <div style="color: #94a3b8; margin-bottom: 4px;">💎 水晶: ${node.mana}/${node.max_mana} | ❤️ 我方: ${node.friendly_hp} vs 敌方: ${node.enemy_hp}</div>
                <div style="color: #f8fafc; margin-bottom: 4px;"><b>诊断:</b> ${node.analysis_comment}</div>
                <div style="color: #38bdf8; margin-bottom: 2px;"><b>🤖 AI最优线:</b> ${node.ai_best_plan.join(' ➔ ') || '空过'}</div>
                <div style="color: #a7f3d0;"><b>👤 玩家实战:</b> ${node.player_actual_plays.join('、') || '空过/无记录'}</div>
            `;
        }

        function stepReplay(delta) {
            if (!currentReplay || !currentReplay.turns) return;
            replayIndex = Math.max(0, Math.min(currentReplay.turns.length - 1, replayIndex + delta));
            renderReplayTurn();
        }

        async function fetchReplay() {
            try {
                const res = await fetch('/api/replay');
                const data = await res.json();
                if (data && data.turns && data.turns.length > 0) {
                    currentReplay = data;
                    const rc = document.getElementById('replay-card');
                    rc.style.display = 'block';
                    document.getElementById('replay-accuracy').innerText = `精度: ${data.overall_accuracy_pct}% 【${data.grade_tier}】`;
                    
                    const badges = document.getElementById('replay-badges');
                    badges.innerHTML = `
                        <span style="color: #06b6d4;">★ ${data.brilliant_count}</span>
                        <span style="color: #10b981;">✅ ${data.best_count}</span>
                        <span style="color: #38bdf8;">⚖️ ${data.good_count}</span>
                        <span style="color: #f97316;">⚠️ ${data.inaccuracy_count}</span>
                        <span style="color: #ef4444;">❌ ${data.blunder_count}</span>
                    `;
                    renderReplayTurn();
                }
            } catch (e) {}
        }

        let lastKnownEtag = '';
        async function fetchState() {
            try {
                const headers = lastKnownEtag ? { 'If-None-Match': lastKnownEtag } : {};
                const res = await fetch('/api/state', { headers });
                if (res.status === 304) {
                    return; // 304 Not Modified: 0KB overhead, zero DOM mutations
                }
                const etag = res.headers.get('ETag');
                if (etag) lastKnownEtag = etag;
                const data = await res.json();
                
                document.getElementById('turn-badge').innerText = `⚡ 回合 ${data.turn} | 💎 ${data.mana}/${data.max_mana}`;
                document.getElementById('opp-label').innerText = `对手: ${data.opponent_hero} ${data.archetype ? '(' + data.archetype + ')' : ''}`;
                document.getElementById('win-tier').innerText = data.win_tier || '均势博弈';
                
                const winrate = data.winrate_pct || 50.0;
                document.getElementById('winrate-val').innerText = `${winrate}%`;
                document.getElementById('progress-fill').style.width = `${Math.max(5, Math.min(95, winrate))}%`;

                // Banners
                const bb = document.getElementById('blunder-banner');
                if (data.blunder_alert) {
                    bb.style.display = 'block';
                    document.getElementById('blunder-text').innerText = data.blunder_alert;
                } else {
                    bb.style.display = 'none';
                }

                const drawBanner = document.getElementById('draw-banner');
                if (data.draw_first_directive) {
                    drawBanner.style.display = 'block';
                    document.getElementById('draw-text').innerText = data.draw_first_directive;
                } else {
                    drawBanner.style.display = 'none';
                }

                const burstBanner = document.getElementById('burst-banner');
                if (data.burst_danger) {
                    burstBanner.style.display = 'block';
                    document.getElementById('burst-text').innerText = data.burst_danger;
                } else {
                    burstBanner.style.display = 'none';
                }

                const habitBanner = document.getElementById('habit-banner');
                if (data.personal_habit_reminder) {
                    habitBanner.style.display = 'block';
                    document.getElementById('habit-text').innerText = data.personal_habit_reminder;
                } else {
                    habitBanner.style.display = 'none';
                }

                // Arena 12-Win Quota Strip
                const quotaCard = document.getElementById('quota-card');
                if (data.quota_strip) {
                    quotaCard.style.display = 'block';
                    document.getElementById('quota-content').innerHTML = `<b>套牌定额状况:</b> ${data.quota_strip}`;
                } else {
                    quotaCard.style.display = 'none';
                }

                // Next-Turn Threat Radar
                const threatCard = document.getElementById('threat-card');
                if (data.next_turn_threat_cards && data.next_turn_threat_cards.length > 0) {
                    threatCard.style.display = 'block';
                    const itemsHtml = data.next_turn_threat_cards.map(c => 
                        `<div style="margin-bottom: 3px;">• <b style="color: #fbbf24;">【${c.name}】</b> (${c.cost}费): ${c.effect} <span style="color: #94a3b8;">(${c.tip})</span></div>`
                    ).join('');
                    document.getElementById('threat-items').innerHTML = itemsHtml;
                    if (data.lethal_cushion) {
                        document.getElementById('lethal-cushion-badge').innerText = data.lethal_cushion;
                    }
                } else {
                    threatCard.style.display = 'none';
                }

                // Ghost Board
                const ghostCard = document.getElementById('ghost-card');
                if (data.ghost_board_summary) {
                    ghostCard.style.display = 'block';
                    document.getElementById('ghost-content').innerHTML = data.ghost_board_summary;
                } else {
                    ghostCard.style.display = 'none';
                }

                // RNG Odds
                const rngCard = document.getElementById('rng-card');
                if (data.rng_badge) {
                    rngCard.style.display = 'block';
                    document.getElementById('rng-content').innerHTML = data.rng_badge;
                } else {
                    rngCard.style.display = 'none';
                }

                // Negative Deductions
                const dedCard = document.getElementById('deduction-card');
                if (data.negative_deductions && data.negative_deductions.length > 0) {
                    dedCard.style.display = 'block';
                    const dedHtml = data.negative_deductions.map(d =>
                        `<div style="margin-bottom: 2px;">• 槽位#${d.slot}: ${d.deduction}</div>`
                    ).join('');
                    document.getElementById('deduction-content').innerHTML = dedHtml;
                } else {
                    dedCard.style.display = 'none';
                }

                // Synchronize Checked Steps from Server
                if (Array.isArray(data.checked_steps)) {
                    localCheckedSteps = new Set(data.checked_steps);
                }

                // Plan A Interactive Steps
                document.getElementById('plan-a-ev').innerText = `EV: +${data.plan_a_ev || 0.0}`;
                if (data.resilience_badge) {
                    document.getElementById('plan-a-resilience').innerText = data.resilience_badge;
                } else {
                    document.getElementById('plan-a-resilience').innerText = '';
                }

                const dnaCard = document.getElementById('dna-card');
                if (data.championship_dna) {
                    dnaCard.style.display = 'block';
                    document.getElementById('dna-content').innerHTML = data.championship_dna;
                } else {
                    dnaCard.style.display = 'none';
                }
                const paSteps = document.getElementById('plan-a-steps');
                if (data.plan_a_steps && data.plan_a_steps.length > 0) {
                    paSteps.innerHTML = data.plan_a_steps.map((s, idx) => {
                        const isChecked = localCheckedSteps.has(idx);
                        return `
                            <div class="step-item ${isChecked ? 'checked' : ''}" id="step-item-${idx}" onclick="toggleStep(${idx})">
                                <div class="step-checkbox">${isChecked ? '✔' : ''}</div>
                                <div class="step-text"><b>${idx+1}.</b> ${s}</div>
                            </div>
                        `;
                    }).join('');
                }
                const paExtra = document.getElementById('plan-a-extra');
                let extraLines = [];
                if (data.positioning_advice) extraLines.push(`📐 站位: ${data.positioning_advice}`);
                if (data.curve_foresight) extraLines.push(`⚡ 曲线: ${data.curve_foresight}`);
                if (data.variance_policy) extraLines.push(`🎲 博弈: ${data.variance_policy}`);
                paExtra.innerHTML = extraLines.map(l => `<div>${l}</div>`).join('');

                // Plan B
                const pbCard = document.getElementById('plan-b-card');
                if (data.plan_b_steps && data.plan_b_steps.length > 0) {
                    pbCard.style.display = 'block';
                    pbCard.dataset.hasSteps = 'true';
                    document.getElementById('plan-b-ev').innerText = `EV: +${data.plan_b_ev || 0.0}`;
                    document.getElementById('plan-b-steps').innerHTML = data.plan_b_steps.map((s, idx) => 
                        `<div class="step-item"><div class="step-text"><b>${idx+1}.</b> ${s}</div></div>`
                    ).join('');
                } else {
                    pbCard.style.display = 'none';
                    pbCard.dataset.hasSteps = 'false';
                }

                // Compass
                if (data.compass_directive) {
                    document.getElementById('compass-text').innerText = data.compass_directive;
                }

                // Discover Guidance
                const discBox = document.getElementById('discover-box');
                if (data.discover_guidance) {
                    discBox.style.display = 'block';
                    document.getElementById('discover-text').innerText = data.discover_guidance;
                } else {
                    discBox.style.display = 'none';
                }

                // Tilt & Fatigue status
                const tiltBanner = document.getElementById('tilt-banner');
                if (data.tilt_status) {
                    tiltBanner.style.display = 'block';
                    document.getElementById('tilt-text').innerText = data.tilt_status;
                } else {
                    tiltBanner.style.display = 'none';
                }

                // Hypergeometric gamble odds
                const hyperCard = document.getElementById('hyper-card');
                if (data.hypergeometric_gamble) {
                    hyperCard.style.display = 'block';
                    document.getElementById('hyper-content').innerText = data.hypergeometric_gamble;
                } else {
                    hyperCard.style.display = 'none';
                }

                // Mind reading
                const mindCard = document.getElementById('mind-card');
                if (data.mind_reading_summary) {
                    mindCard.style.display = 'block';
                    document.getElementById('mind-content').innerText = data.mind_reading_summary;
                } else {
                    mindCard.style.display = 'none';
                }

                // Decision tree topology
                const treeCard = document.getElementById('tree-card');
                if (data.decision_tree_ascii) {
                    treeCard.style.display = 'block';
                    document.getElementById('tree-content').innerText = data.decision_tree_ascii;
                } else {
                    treeCard.style.display = 'none';
                }
            } catch (err) {}
        }

        setInterval(fetchState, 500);
        setInterval(fetchReplay, 2500);
        fetchState();
        fetchReplay();
    </script>
</body>
</html>
"""


OBS_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>炉石竞技场 AI · OBS 直播挂件</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background: transparent;
            overflow: hidden;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
            color: #f8fafc;
            padding: 10px;
        }
        .obs-container {
            width: 360px;
            background: rgba(15, 23, 42, 0.85);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid rgba(56, 189, 248, 0.3);
            border-radius: 12px;
            padding: 12px 14px;
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.5), 0 0 15px rgba(56, 189, 248, 0.12);
            display: flex;
            flex-direction: column;
            gap: 10px;
            animation: fadeIn 0.3s ease;
        }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes pulseLethal {
            0% { box-shadow: 0 0 0 rgba(239, 68, 68, 0.4); }
            50% { box-shadow: 0 0 20px rgba(239, 68, 68, 0.9); }
            100% { box-shadow: 0 0 0 rgba(239, 68, 68, 0.4); }
        }
        .header-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(51, 65, 85, 0.5);
            padding-bottom: 6px;
        }
        .logo-box {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 13px;
            font-weight: 700;
            color: #38bdf8;
            letter-spacing: 0.5px;
        }
        .live-dot {
            width: 8px;
            height: 8px;
            background: #ef4444;
            border-radius: 50%;
            display: inline-block;
            box-shadow: 0 0 8px #ef4444;
        }
        .winrate-badge {
            font-size: 12px;
            font-weight: 800;
            color: #34d399;
            background: rgba(16, 185, 129, 0.15);
            padding: 2px 8px;
            border-radius: 10px;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }
        .lethal-banner {
            display: none;
            background: linear-gradient(90deg, #dc2626, #f59e0b, #dc2626);
            background-size: 200% 200%;
            color: #ffffff;
            font-size: 12px;
            font-weight: 800;
            text-align: center;
            padding: 6px 8px;
            border-radius: 6px;
            animation: pulseLethal 1.2s infinite;
            text-shadow: 0 1px 2px rgba(0,0,0,0.8);
        }
        .coach-box {
            background: rgba(30, 41, 59, 0.6);
            border-left: 3px solid #8b5cf6;
            border-radius: 4px;
            padding: 6px 10px;
            font-size: 11px;
            line-height: 1.4;
            color: #e2e8f0;
        }
        .coach-title {
            color: #a78bfa;
            font-weight: 700;
            margin-bottom: 2px;
            display: flex;
            align-items: center;
            gap: 4px;
        }
        .tilt-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 10px;
            color: #94a3b8;
        }
        .tilt-bar-bg {
            flex: 1;
            margin-left: 8px;
            height: 5px;
            background: rgba(51, 65, 85, 0.5);
            border-radius: 3px;
            overflow: hidden;
        }
        .tilt-bar-fill {
            width: 15%;
            height: 100%;
            background: #10b981;
            transition: width 0.3s ease, background 0.3s ease;
        }
        .action-box {
            font-size: 11px;
        }
        .action-step {
            display: flex;
            align-items: center;
            gap: 6px;
            margin-bottom: 4px;
            color: #f1f5f9;
        }
        .action-num {
            background: rgba(56, 189, 248, 0.2);
            color: #38bdf8;
            border-radius: 50%;
            width: 16px;
            height: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 9px;
            font-weight: 700;
        }
        .chips-row {
            display: flex;
            flex-wrap: wrap;
            gap: 4px;
            font-size: 10px;
        }
        .chip {
            background: rgba(51, 65, 85, 0.4);
            padding: 2px 6px;
            border-radius: 4px;
            color: #cbd5e1;
            border: 1px solid rgba(71, 85, 105, 0.4);
        }
    </style>
</head>
<body>
    <div class="obs-container">
        <div class="header-row">
            <div class="logo-box">
                <span class="live-dot"></span>
                <span>ARENA PRO HUD</span>
            </div>
            <div class="winrate-badge" id="obs-winrate">胜率 50.0%</div>
        </div>

        <div class="lethal-banner" id="obs-lethal">
            ⚡ LETHAL 发现绝杀战机！立即走脸终结 ⚡
        </div>

        <div class="coach-box" id="obs-coach-box">
            <div class="coach-title">🎙️ 教练指令 (Pro Coach)</div>
            <div id="obs-coach-text">等待战术数据推送...</div>
        </div>

        <div class="action-box" id="obs-actions-box">
            <div id="obs-steps-list"></div>
        </div>

        <div class="chips-row" id="obs-chips">
            <div class="chip" id="obs-slot-chip" style="display:none; color:#38bdf8;">📐 站位: 推荐 Slot 0</div>
            <div class="chip" id="obs-var-chip" style="display:none; color:#f59e0b;">🎲 VaR: P50收割</div>
            <div class="chip" id="obs-arch-chip" style="display:none; color:#c084fc;">🔮 对手: 均势中速</div>
        </div>

        <div class="tilt-row">
            <span id="obs-tilt-label">心态: 心平气和 (0)</span>
            <div class="tilt-bar-bg">
                <div class="tilt-bar-fill" id="obs-tilt-fill"></div>
            </div>
        </div>
    </div>

    <script>
        async function updateObs() {
            try {
                const res = await fetch('/api/state');
                if (res.status !== 200) return;
                const d = await res.json();

                if (d.winrate_pct !== undefined) {
                    const wr = parseFloat(d.winrate_pct).toFixed(1);
                    const el = document.getElementById('obs-winrate');
                    el.innerText = `胜率 ${wr}%`;
                    if (wr >= 60) { el.style.color = '#34d399'; }
                    else if (wr <= 40) { el.style.color = '#f87171'; }
                    else { el.style.color = '#38bdf8'; }
                }

                const lth = document.getElementById('obs-lethal');
                if ((d.burst_danger && d.burst_danger.includes('斩杀')) || d.is_lethal || (d.plan_a_title && d.plan_a_title.includes('斩杀'))) {
                    lth.style.display = 'block';
                } else {
                    lth.style.display = 'none';
                }

                const cText = document.getElementById('obs-coach-text');
                if (d.coach_directive) {
                    cText.innerText = d.coach_directive;
                } else if (d.compass_directive) {
                    cText.innerText = d.compass_directive;
                } else if (d.resilience_verdict) {
                    cText.innerText = d.resilience_verdict;
                } else {
                    cText.innerText = "按费平滑拍怪，保持场面主动权。";
                }

                const sList = document.getElementById('obs-steps-list');
                sList.innerHTML = '';
                const steps = d.plan_a_steps || [];
                steps.slice(0, 3).forEach((st, idx) => {
                    const div = document.createElement('div');
                    div.className = 'action-step';
                    div.innerHTML = `<span class="action-num">${idx+1}</span><span>${st}</span>`;
                    sList.appendChild(div);
                });

                const slotChip = document.getElementById('obs-slot-chip');
                if (d.positioning_advice) {
                    slotChip.style.display = 'inline-block';
                    slotChip.innerText = d.positioning_advice.slice(0, 26);
                } else {
                    slotChip.style.display = 'none';
                }

                const varChip = document.getElementById('obs-var-chip');
                if (d.rng_badge) {
                    varChip.style.display = 'inline-block';
                    varChip.innerText = d.rng_badge.slice(0, 24);
                } else {
                    varChip.style.display = 'none';
                }

                const archChip = document.getElementById('obs-arch-chip');
                if (d.archetype && d.archetype !== '--') {
                    archChip.style.display = 'inline-block';
                    archChip.innerText = `🔮 ${d.archetype.split(' ')[0]}`;
                } else {
                    archChip.style.display = 'none';
                }

                if (d.tilt_status) {
                    const tLbl = document.getElementById('obs-tilt-label');
                    tLbl.innerText = d.tilt_status.slice(0, 18);
                    const fill = document.getElementById('obs-tilt-fill');
                    if (d.tilt_status.includes('高危') || d.tilt_status.includes('极危')) {
                        fill.style.width = '85%';
                        fill.style.background = '#ef4444';
                    } else if (d.tilt_status.includes('警戒')) {
                        fill.style.width = '55%';
                        fill.style.background = '#f59e0b';
                    } else {
                        fill.style.width = '25%';
                        fill.style.background = '#10b981';
                    }
                }
            } catch(e) {}
        }
        setInterval(updateObs, 250);
        updateObs();
    </script>
</body>
</html>
"""


class WebCompanionHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Silent logger to prevent console spam

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            data = json.loads(post_data)
        except Exception:
            data = {}

        global _CURRENT_STATE, _STATE_VERSION
        if self.path == "/api/checklist/toggle":
            idx = int(data.get("index", 0))
            is_checked = bool(data.get("checked", True))
            checked_set = set(_CURRENT_STATE.get("checked_steps", []))
            if is_checked:
                checked_set.add(idx)
            else:
                checked_set.discard(idx)
            _CURRENT_STATE["checked_steps"] = sorted(list(checked_set))
            _STATE_VERSION += 1
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "checked_steps": _CURRENT_STATE["checked_steps"]}).encode("utf-8"))
        elif self.path == "/api/plan/select":
            plan = str(data.get("plan", "A")).upper()
            _CURRENT_STATE["active_plan"] = plan
            _STATE_VERSION += 1
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "active_plan": plan}).encode("utf-8"))
        elif self.path == "/api/i18n/set":
            from .i18n_engine import I18nEngine
            new_loc = str(data.get("locale", "zh-CN"))
            success = I18nEngine.get_instance().set_locale(new_loc)
            _CURRENT_STATE["locale"] = new_loc
            _STATE_VERSION += 1
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "locale": new_loc, "success": success}).encode("utf-8"))
        elif self.path == "/api/remote/command":
            from .mobile_remote_controller import MobileRemoteController
            cmd = str(data.get("command", "")).upper()
            params = data.get("params", {})
            result = MobileRemoteController.get_instance().dispatch(cmd, params)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": result.status,
                "command": result.command,
                "message": result.message,
                "payload": result.payload,
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/copilot/advance":
            from .master_copilot import MasterCoPilotEngine
            step = MasterCoPilotEngine.get_instance().advance_current_step()
            if MasterCoPilotEngine.get_instance().current_plan:
                _CURRENT_STATE["copilot_plan"] = MasterCoPilotEngine.get_instance().current_plan.to_dict()
                _STATE_VERSION += 1
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "ok",
                "advanced_to": step.to_dict() if step else None,
                "is_completed": MasterCoPilotEngine.get_instance().current_plan.is_completed if MasterCoPilotEngine.get_instance().current_plan else True,
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/copilot/intercept":
            from .pre_cast_blunder_interceptor import PreCastBlunderInterceptor
            alert = PreCastBlunderInterceptor.check_action(
                intended_action_type=data.get("action_type", "ATTACK"),
                intended_source_name=data.get("source_name", ""),
                intended_target_name=data.get("target_name", ""),
                enemy_hp=int(data.get("enemy_hp", 30)),
                board_total_lethal_damage=int(data.get("lethal_damage", 0)),
                available_mana=int(data.get("available_mana", 1)),
                target_has_divine_shield=bool(data.get("has_divine_shield", False)),
                source_attack=int(data.get("source_attack", 0)),
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "ok",
                "has_intercept": alert is not None,
                "alert": alert.to_dict() if alert else None,
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/what_if":
            from .what_if_sandbox import WhatIfSandbox
            report = WhatIfSandbox.simulate_what_if(
                turn=int(data.get("turn", 5)),
                actual_action_desc=data.get("actual_action", "全铺走脸"),
                what_if_action_desc=data.get("what_if_action", "白吃解场控场"),
                start_friendly_hp=int(data.get("friendly_hp", 20)),
                start_enemy_hp=int(data.get("enemy_hp", 20)),
                start_friendly_board_atk=int(data.get("friendly_board_atk", 6)),
                start_enemy_board_atk=int(data.get("enemy_board_atk", 4)),
                opponent_has_aoe_next_turn=bool(data.get("opponent_has_aoe", False)),
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(report.to_dict(), ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/lens":
            from .instant_card_lens import InstantCardLens
            q = data.get("query", "火球术")
            breakdown = InstantCardLens.inspect(q)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(breakdown.to_dict(), ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/mental/profile":
            from .mental_bluff_engine import MentalBluffEngine
            history = data.get("turn_history", [])
            profile = MentalBluffEngine.analyze_opponent_style(history)
            bluff = MentalBluffEngine.evaluate_strategic_bluff(
                player_health=int(data.get("player_health", 20)),
                opponent_health=int(data.get("opponent_health", 20)),
                board_attack=int(data.get("board_attack", 6)),
                hand_damage_available=int(data.get("hand_damage", 0)),
                opponent_profile=profile,
                current_winrate=float(data.get("current_winrate", 45.0)),
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "profile": {
                    "style": profile.style.value,
                    "style_label": profile.style_label,
                    "confidence_pct": profile.confidence_pct,
                    "avg_turn_duration_sec": profile.avg_turn_duration_sec,
                    "hover_rate_per_turn": profile.hover_rate_per_turn,
                    "trade_preference_score": profile.trade_preference_score,
                    "bait_tolerance_factor": profile.bait_tolerance_factor,
                    "bluff_vulnerability_score": profile.bluff_vulnerability_score,
                    "tactical_advice": profile.tactical_advice,
                },
                "bluff": {
                    "is_viable": bluff.is_viable,
                    "bluff_action": bluff.bluff_action,
                    "bluff_ev": bluff.bluff_ev,
                    "success_probability_pct": bluff.success_probability_pct,
                    "opponent_reaction_prediction": bluff.opponent_reaction_prediction,
                    "fail_risk_description": bluff.fail_risk_description,
                    "speech_prompt": bluff.speech_prompt,
                }
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/tactical/setup":
            from .tactical_setup_planner import TacticalSetupPlanner
            plans = TacticalSetupPlanner.plan_setup_lines(
                friendly_board=data.get("friendly_board", []),
                enemy_board=data.get("enemy_board", []),
                friendly_hand=data.get("friendly_hand", []),
                current_mana=int(data.get("current_mana", 4)),
                next_turn_mana=int(data.get("next_turn_mana", 5)),
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            plans_data = [{
                "category": p.category.value,
                "name": p.name,
                "confidence_score": p.confidence_score,
                "t0_action_description": p.t0_action_description,
                "t1_payoff_description": p.t1_payoff_description,
                "expected_tempo_gain": p.expected_tempo_gain,
                "summary_markdown": p.summary_markdown,
                "steps": [
                    {
                        "turn_offset": s.turn_offset,
                        "action_type": s.action_type,
                        "card_or_minion_name": s.card_or_minion_name,
                        "target_name": s.target_name,
                        "intent": s.intent,
                    } for s in p.steps
                ]
            } for p in plans]
            self.wfile.write(json.dumps({"plans": plans_data, "total_plans": len(plans_data)}, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/miracle/path":
            from .miracle_inversion_engine import MiracleInversionEngine
            res = MiracleInversionEngine.evaluate_game_attitude(
                winrate_pct=float(data.get("winrate_pct", 15.0)),
                player_hp=int(data.get("player_hp", 10)),
                enemy_hp=int(data.get("enemy_hp", 16)),
                enemy_board_attack=int(data.get("enemy_board_attack", 12)),
                player_board_attack=int(data.get("player_board_attack", 6)),
                deck_remaining=data.get("deck_remaining", []),
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "is_miracle_needed": res.is_miracle_needed,
                "risk_attitude": res.risk_attitude.value,
                "attitude_label": res.attitude_label,
                "conventional_winrate_pct": res.conventional_winrate_pct,
                "miracle_winrate_pct": res.miracle_winrate_pct,
                "winrate_gain_pct": res.winrate_gain_pct,
                "gamble_line_directive": res.gamble_line_directive,
                "gamble_hypotheses": res.gamble_hypotheses,
                "required_topdecks": res.required_topdecks,
                "speech_warning": res.speech_warning,
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/reinforce/evolve":
            from .self_evolving_reinforcement import SelfEvolvingReinforcement
            cards = data.get("deck_cards", ["奥术智慧", "火球术", "寒冰箭"])
            ser = SelfEvolvingReinforcement()
            weights = ser.run_local_self_play(cards)
            blindspots = ser.get_active_blindspot_warnings()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "ok",
                "evolved_weights": {
                    k: {
                        "card_name": v.card_name,
                        "base_weight": v.base_weight,
                        "evolving_delta": v.evolving_delta,
                        "effective_weight": v.effective_weight,
                        "meta_affinity_trend": v.meta_affinity_trend,
                    } for k, v in weights.items()
                },
                "blindspots": [
                    {
                        "blindspot_id": b.blindspot_id,
                        "category": b.category,
                        "occurrence_count": b.occurrence_count,
                        "severity_level": b.severity_level,
                        "description": b.description,
                        "coaching_rule": b.coaching_rule,
                    } for b in blindspots
                ]
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/fatigue/horizon":
            from .fatigue_endgame_horizon import FatigueEndgameHorizon
            rep = FatigueEndgameHorizon.calculate_endgame_horizon(
                my_deck_count=int(data.get("my_deck_count", 5)),
                my_hand=data.get("my_hand", []),
                my_hp=int(data.get("my_hp", 20)),
                my_armor=int(data.get("my_armor", 0)),
                opp_deck_count=int(data.get("opp_deck_count", 2)),
                opp_hand_count=int(data.get("opp_hand_count", 4)),
                opp_hp=int(data.get("opp_hp", 18)),
                opp_armor=int(data.get("opp_armor", 0)),
                opp_class=data.get("opp_class", "Warrior"),
                current_turn=int(data.get("current_turn", 12)),
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "verdict": rep.verdict.value,
                "verdict_label": rep.verdict_label,
                "fatigue_differential_turns": rep.fatigue_differential_turns,
                "strategic_directive": rep.strategic_directive,
                "summary_markdown": rep.summary_markdown,
                "my_resource": {
                    "remaining_cards": rep.my_resource.remaining_cards_count,
                    "effective_health": rep.my_resource.total_effective_health,
                    "removal_value": rep.my_resource.total_removal_value,
                },
                "opp_resource": {
                    "remaining_cards": rep.opp_resource.remaining_cards_count,
                    "effective_health": rep.opp_resource.total_effective_health,
                    "removal_value": rep.opp_resource.total_removal_value,
                }
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/voice/ask":
            from .interactive_voice_brain import InteractiveVoiceBrain
            q = data.get("query", "大师我下回合能斩杀吗？")
            ans = InteractiveVoiceBrain.answer_query(q, _CURRENT_STATE)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "intent": ans.intent.value,
                "recognized_query": ans.recognized_query,
                "spoken_answer": ans.spoken_answer,
                "tactical_action_ref": ans.tactical_action_ref,
                "confidence_score": ans.confidence_score,
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/climate/meta":
            from .micro_meta_climate import MicroMetaClimateRadar
            matches = data.get("matches", [])
            rep = MicroMetaClimateRadar.analyze_recent_meta(matches)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "climate_type": rep.climate_type.value,
                "climate_label": rep.climate_label,
                "sample_match_count": rep.sample_match_count,
                "aggro_ratio_pct": rep.aggro_ratio_pct,
                "control_ratio_pct": rep.control_ratio_pct,
                "combo_ratio_pct": rep.combo_ratio_pct,
                "dominant_class": rep.dominant_class,
                "multipliers": {
                    "anti_aggro_removal": rep.multipliers.anti_aggro_removal,
                    "early_taunt_survival": rep.multipliers.early_taunt_survival,
                    "greed_value_generation": rep.multipliers.greed_value_generation,
                    "burst_finishers": rep.multipliers.burst_finishers,
                },
                "mulligan_adjustment_advice": rep.mulligan_adjustment_advice,
                "summary_markdown": rep.summary_markdown,
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/secret/causal_tree":
            from .secret_causal_forest import SecretCausalForest
            seq = SecretCausalForest.calculate_optimal_probes(
                active_secret_count=int(data.get("active_secret_count", 2)),
                opponent_class=data.get("opponent_class", "Mage"),
                friendly_board=data.get("friendly_board", []),
                friendly_hand=data.get("friendly_hand", []),
                available_mana=int(data.get("available_mana", 5)),
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "total_expected_loss": seq.total_expected_loss,
                "safest_line_description": seq.safest_line_description,
                "deadlock_detected": seq.deadlock_detected,
                "summary_markdown": seq.summary_markdown,
                "steps": [
                    {
                        "step_order": s.step_order,
                        "probe_type": s.probe_type.value,
                        "card_or_source_name": s.card_or_source_name,
                        "target_description": s.target_description,
                        "targeted_secrets": s.targeted_secrets,
                        "loss_ev_score": s.loss_ev_score,
                        "rationale": s.rationale,
                    } for s in seq.steps
                ]
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/flow/tilt":
            from .flow_tilt_guardian import FlowTiltGuardian
            res = FlowTiltGuardian.evaluate_player_state(
                loss_streak=int(data.get("loss_streak", 0)),
                avg_turn_sec=float(data.get("avg_turn_sec", 25.0)),
                click_jitter_apm=float(data.get("click_jitter_apm", 80.0)),
                consecutive_matches=int(data.get("consecutive_matches", 1)),
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "flow_score": res.flow_score,
                "tilt_tier": res.tilt_tier.value,
                "tier_label": res.tier_label,
                "is_intervention_needed": res.is_intervention_needed,
                "recommended_cooldown_sec": res.recommended_cooldown_sec,
                "spoken_comfort_line": res.spoken_comfort_line,
                "tactical_guidance": res.tactical_guidance,
                "summary_markdown": res.summary_markdown,
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/hover/intent":
            from .hover_intent_radar import HoverIntentRadar
            alert = HoverIntentRadar.analyze_hover_telemetry(
                hover_events=data.get("hover_events", []),
                player_health=int(data.get("player_health", 20)),
                friendly_board=data.get("friendly_board", []),
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "intent": alert.intent.value,
                "intent_label": alert.intent_label,
                "threat_tier": alert.threat_tier,
                "confidence_pct": alert.confidence_pct,
                "target_entity": alert.target_entity,
                "warning_spoken_line": alert.warning_spoken_line,
                "defensive_countermeasure": alert.defensive_countermeasure,
                "summary_markdown": alert.summary_markdown,
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/highlight/reel":
            from .auto_highlight_reel import AutoHighlightReel
            pkg = AutoHighlightReel.generate_highlight_reel(
                match_id=str(data.get("match_id", "current_match")),
                turn_snapshots=data.get("turn_snapshots", []),
                match_result=str(data.get("match_result", "VICTORY")),
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "climax_type": pkg.climax_type.value,
                "title": pkg.title,
                "climax_turn": pkg.climax_turn,
                "drama_score": pkg.drama_score,
                "total_duration_sec": pkg.total_duration_sec,
                "export_filename": pkg.export_filename,
                "summary_markdown": pkg.summary_markdown,
                "storyboard": [
                    {
                        "start_sec": f.start_sec,
                        "end_sec": f.end_sec,
                        "camera_scene": f.camera_scene,
                        "lower_third_caption": f.lower_third_caption,
                        "voiceover_script": f.voiceover_script,
                        "sound_effect_cue": f.sound_effect_cue,
                    } for f in pkg.storyboard
                ]
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/bgs/reactor":
            from .battlegrounds_mode_reactor import BattlegroundsModeReactor
            rep = BattlegroundsModeReactor.evaluate_tavern_turn(
                current_tier=int(data.get("current_tier", 3)),
                upgrade_cost=int(data.get("upgrade_cost", 6)),
                available_gold=int(data.get("available_gold", 7)),
                hero_health=int(data.get("hero_health", 28)),
                board_minions=data.get("board_minions", []),
                tavern_minions=data.get("tavern_minions", []),
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "active_comp": rep.active_comp.value,
                "comp_label": rep.comp_label,
                "comp_tier_rank": rep.comp_tier_rank,
                "upgrade_eval": {
                    "current_tier": rep.upgrade_eval.current_tier,
                    "upgrade_cost": rep.upgrade_eval.upgrade_cost,
                    "should_upgrade_now": rep.upgrade_eval.should_upgrade_now,
                    "tempo_loss_hp_estimate": rep.upgrade_eval.tempo_loss_hp_estimate,
                    "recommendation_label": rep.upgrade_eval.recommendation_label,
                    "detailed_logic": rep.upgrade_eval.detailed_logic,
                },
                "combat_sim": {
                    "win_pct": rep.combat_sim.win_pct,
                    "tie_pct": rep.combat_sim.tie_pct,
                    "loss_pct": rep.combat_sim.loss_pct,
                    "expected_damage_taken": rep.combat_sim.expected_damage_taken,
                    "positioning_advice": rep.combat_sim.positioning_advice,
                },
                "summary_markdown": rep.summary_markdown,
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/council/debate":
            from .council_of_champions import CouncilOfChampions
            rep = CouncilOfChampions.convene_council(
                player_hp=int(data.get("player_hp", 20)),
                enemy_hp=int(data.get("enemy_hp", 20)),
                board_total_attack=int(data.get("board_total_attack", 6)),
                enemy_threat_level=data.get("enemy_threat_level", "MODERATE"),
                winrate_pct=float(data.get("winrate_pct", 50.0)),
                has_hand_burst=bool(data.get("has_hand_burst", False)),
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "verdict": rep.verdict.value,
                "verdict_label": rep.verdict_label,
                "final_recommended_action": rep.final_recommended_action,
                "council_consensus_score": rep.council_consensus_score,
                "debate_conflict_focus": rep.debate_conflict_focus,
                "opinions": [
                    {
                        "persona": o.persona.value,
                        "persona_title": o.persona_title,
                        "recommended_line": o.recommended_line,
                        "action_type": o.action_type,
                        "confidence_score": o.confidence_score,
                        "argument": o.argument,
                    } for o in rep.opinions
                ],
                "summary_markdown": rep.summary_markdown,
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/gaze/attention":
            from .gaze_attention_tracker import GazeAttentionTracker
            rep = GazeAttentionTracker.evaluate_gaze_distribution(
                gaze_samples=data.get("gaze_samples", []),
                enemy_has_secrets=bool(data.get("enemy_has_secrets", False)),
                enemy_has_taunt_or_poison=bool(data.get("enemy_has_taunt", False)),
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "active_blindspot_alert": rep.active_blindspot_alert,
                "primary_focus_region": rep.primary_focus_region.value,
                "focus_stability_score": rep.focus_stability_score,
                "speech_warning": rep.speech_warning,
                "regions": {
                    k: {
                        "region_label": v.region_label,
                        "attention_pct": v.attention_pct,
                        "seconds_unattended": v.seconds_unattended,
                        "is_blindspot_alert": v.is_blindspot_alert,
                    } for k, v in rep.regions.items()
                },
                "summary_markdown": rep.summary_markdown,
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/persona/speak":
            from .persona_voice_matrix import PersonaVoiceMatrix, VoicePersona
            p_str = data.get("persona", "PRO_COACH")
            persona = VoicePersona(p_str) if p_str in VoicePersona._value2member_map_ else VoicePersona.PRO_COACH
            res = PersonaVoiceMatrix.render_voice(
                scenario=data.get("scenario", "GENERAL_STEP"),
                context=data.get("context", {}),
                preferred_persona=persona,
                is_player_tilted=bool(data.get("is_tilted", False)),
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "active_persona": res.active_persona.value,
                "persona_title": res.persona_title,
                "spoken_line": res.spoken_line,
                "audio_pitch_shift": res.audio_pitch_shift,
                "audio_speed_rate": res.audio_speed_rate,
                "all_persona_lines": res.all_persona_lines,
                "auto_switched_due_to_tilt": res.auto_switched_due_to_tilt,
                "summary_markdown": res.summary_markdown,
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/acoustic/emotion":
            from .acoustic_emotion_guard import AcousticEmotionGuard
            rep = AcousticEmotionGuard.analyze_voice_telemetry(
                pitch_jitter=float(data.get("pitch_jitter", 0.05)),
                sigh_detected=bool(data.get("sigh_detected", False)),
                speech_wpm=float(data.get("speech_wpm", 120.0)),
                peak_volume_db=float(data.get("peak_volume_db", -20.0)),
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "frustration_index": rep.frustration_index,
                "state": rep.state.value,
                "state_label": rep.state_label,
                "comfort_response": rep.comfort_response,
                "action_protocol": rep.action_protocol,
                "summary_markdown": rep.summary_markdown,
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/deck/synthesize":
            from .genetic_deck_architect import GeneticDeckArchitect
            deck = GeneticDeckArchitect.synthesize_counter_deck(
                target_class=data.get("target_class", "Priest"),
                climate_type=data.get("climate_type", "AGGRO_OVERLOAD"),
                generations=int(data.get("generations", 30)),
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "deck_name": deck.deck_name,
                "target_class": deck.target_class,
                "counter_archetype": deck.counter_archetype,
                "fitness_score": deck.fitness_score,
                "deckstring": deck.deckstring,
                "mana_curve": deck.mana_curve,
                "summary_markdown": deck.summary_markdown,
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/tcg/philosophy":
            from .universal_tcg_theory import UniversalTcgTheoryEngine
            rep = UniversalTcgTheoryEngine.evaluate_board_philosophy(
                player_hp=int(data.get("player_hp", 20)),
                enemy_hp=int(data.get("enemy_hp", 20)),
                my_board_mana_value=int(data.get("my_board_mana", 8)),
                enemy_board_mana_value=int(data.get("enemy_board_mana", 6)),
                my_hand_count=int(data.get("my_hand_count", 4)),
                enemy_hand_count=int(data.get("enemy_hand_count", 3)),
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "dominant_axiom": rep.dominant_axiom.value,
                "axiom_title": rep.axiom_title,
                "origin_game": rep.origin_game,
                "tempo_vs_value_balance": rep.tempo_vs_value_balance,
                "life_as_fuel_efficiency": rep.life_as_fuel_efficiency,
                "philosophical_doctrine": rep.philosophical_doctrine,
                "tactical_execution_directive": rep.tactical_execution_directive,
                "summary_markdown": rep.summary_markdown,
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/ui/theme":
            from ui.acrylic_effects import AuraState, AcrylicGlassHelper
            aura_str = data.get("aura", "IDLE_CYBER")
            aura = AuraState(aura_str) if aura_str in AuraState._value2member_map_ else AuraState.IDLE_CYBER
            qss = AcrylicGlassHelper.get_glass_stylesheet(aura)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "ok",
                "aura": aura.value,
                "stylesheet": qss,
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/ui/island/notify":
            title = data.get("title", "⚡ 斩杀确定！")
            message = data.get("message", "全员打脸，直接带走！")
            color = data.get("color", "#f59e0b")
            duration = int(data.get("duration", 3500))
            _CURRENT_STATE["last_island_notification"] = {
                "title": title,
                "message": message,
                "color": color,
                "duration": duration,
            }
            _STATE_VERSION += 1
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "ok",
                "notification": _CURRENT_STATE["last_island_notification"],
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/ui/dock":
            from ui.magnetic_docking import MagneticDockingManager
            rect = data.get("hs_rect", [100, 100, 1920, 1080])
            mode = data.get("dock_mode", "TOP_RIGHT")
            anchor = MagneticDockingManager.compute_dock_coordinates(tuple(rect), dock_mode=mode)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "x": anchor.x,
                "y": anchor.y,
                "width": anchor.width,
                "height": anchor.height,
                "scale_factor": anchor.scale_factor,
                "is_snapped": anchor.is_snapped,
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/ui/streamer":
            active = bool(data.get("active", True))
            _CURRENT_STATE["is_streamer_mode"] = active
            _STATE_VERSION += 1
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "ok",
                "is_streamer_mode": active,
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/ui/prismatic/theme":
            from ui.prismatic_theme_engine import PrismaticThemeEngine
            theme_name = data.get("theme", "CYBER_NEON")
            engine = PrismaticThemeEngine(theme_name)
            preset = engine.get_current_theme()
            _CURRENT_STATE["theme"] = preset.name
            _STATE_VERSION += 1
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "ok",
                "theme": preset.to_dict(),
                "css_variables": engine.generate_css_variables(),
                "qss": engine.generate_qss(),
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/ui/board/tactics":
            arrows = data.get("arrows", [])
            slots = data.get("ghost_slots", [])
            _CURRENT_STATE["ar_tactics"] = {
                "arrows": arrows,
                "ghost_slots": slots,
            }
            _STATE_VERSION += 1
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "ok",
                "ar_tactics": _CURRENT_STATE["ar_tactics"],
            }, ensure_ascii=False).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        global _CURRENT_STATE, _REPLAY_DATA, _STATE_VERSION
        if self.path == "/" or self.path.startswith("/?"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
        elif self.path == "/api/state":
            current_etag = f'"{_STATE_VERSION}"'
            req_etag = self.headers.get("If-None-Match", "")
            if req_etag and req_etag.strip() == current_etag:
                self.send_response(304)
                self.send_header("ETag", current_etag)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                return

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("ETag", current_etag)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(json.dumps(_CURRENT_STATE, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/replay":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(json.dumps(_REPLAY_DATA, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/obs" or self.path.startswith("/obs?"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(OBS_HTML_TEMPLATE.encode("utf-8"))
        elif self.path in ("/review", "/review/latest") or self.path.startswith("/review"):
            from .match_review_dashboard import MatchReviewDashboardGenerator
            html_rep = MatchReviewDashboardGenerator.get_latest_html()
            if not html_rep:
                html_rep = "<html><body style='background:#090d16;color:#fff;font-family:sans-serif;padding:40px;text-align:center;'><h2>暂无最新对局复盘数据</h2><p>完成一场对局后将自动在此生成全维度交互式复盘大盘。</p></body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(html_rep.encode("utf-8"))
        elif self.path == "/api/meta/sync":
            from .hsreplay_sync import HsreplaySync
            HsreplaySync.get_instance().trigger_async_sync()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "message": "云端大数据增量同步已在后台触发"}).encode("utf-8"))
        elif self.path == "/api/topdeck":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(_CURRENT_STATE.get("topdeck_matrix", {}), ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/lookahead":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "summary": _CURRENT_STATE.get("lookahead_summary", ""),
                "table": _CURRENT_STATE.get("lookahead_table", ""),
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/phase":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "phase": _CURRENT_STATE.get("game_phase", "EARLY_GAME"),
                "phase_zh": _CURRENT_STATE.get("game_phase_zh", "前期节奏争夺"),
                "weights": _CURRENT_STATE.get("game_phase_weights", {}),
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/leak_buster":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "score": _CURRENT_STATE.get("leak_score", 100.0),
                "grade": _CURRENT_STATE.get("leak_grade", "S 宗师无暇"),
                "summary": _CURRENT_STATE.get("leak_summary", ""),
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/i18n":
            from .i18n_engine import I18nEngine
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "locale": I18nEngine.get_instance().get_locale(),
                "available_locales": I18nEngine.get_instance().get_available_locales(),
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/infographic":
            from .arena_career_vault import ArenaCareerVault
            card_html = ArenaCareerVault.get_instance().generate_shareable_infographic_html()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(card_html.encode("utf-8"))
        elif self.path == "/api/career":
            from .arena_career_vault import ArenaCareerVault
            summary = ArenaCareerVault.get_instance().get_summary()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "total_runs": summary.total_runs,
                "total_wins": summary.total_wins,
                "total_losses": summary.total_losses,
                "overall_winrate_pct": summary.overall_winrate_pct,
                "average_wins": summary.average_wins_per_run,
                "twelve_wins": summary.twelve_win_trophies,
                "best_hero": summary.best_hero_class,
                "summary_markdown": summary.summary_markdown,
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/hand/age":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"summary": _CURRENT_STATE.get("hand_age_summary", "")}, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/matchup/sandbox":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(_CURRENT_STATE.get("matchup_sandbox", {}), ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/copilot":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(_CURRENT_STATE.get("copilot_plan", {}), ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/hand/silhouette":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(_CURRENT_STATE.get("hand_silhouette", {}), ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/draft/forecast":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(_CURRENT_STATE.get("future_draft_forecast", {}), ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/talkshow":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(_CURRENT_STATE.get("talkshow_podcast", {}), ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/mental/profile":
            from .mental_bluff_engine import MentalBluffEngine
            profile = MentalBluffEngine.analyze_opponent_style()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "style": profile.style.value,
                "style_label": profile.style_label,
                "confidence_pct": profile.confidence_pct,
                "tactical_advice": profile.tactical_advice,
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/fatigue/horizon":
            from .fatigue_endgame_horizon import FatigueEndgameHorizon
            rep = FatigueEndgameHorizon.calculate_endgame_horizon(
                my_deck_count=int(_CURRENT_STATE.get("my_deck_count", 10)),
                my_hand=_CURRENT_STATE.get("my_hand", []),
                my_hp=int(_CURRENT_STATE.get("friendly_hp", 30)),
                my_armor=int(_CURRENT_STATE.get("friendly_armor", 0)),
                opp_deck_count=int(_CURRENT_STATE.get("opp_deck_count", 10)),
                opp_hand_count=int(_CURRENT_STATE.get("opp_hand_count", 4)),
                opp_hp=int(_CURRENT_STATE.get("opponent_health", 30)),
                opp_armor=int(_CURRENT_STATE.get("opp_armor", 0)),
                opp_class=_CURRENT_STATE.get("opponent_class", "Warrior"),
                current_turn=int(_CURRENT_STATE.get("turn", 5)),
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "verdict": rep.verdict.value,
                "verdict_label": rep.verdict_label,
                "strategic_directive": rep.strategic_directive,
                "summary_markdown": rep.summary_markdown,
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/blindspots":
            from .self_evolving_reinforcement import SelfEvolvingReinforcement
            ser = SelfEvolvingReinforcement()
            blindspots = ser.get_active_blindspot_warnings()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps([
                {
                    "blindspot_id": b.blindspot_id,
                    "category": b.category,
                    "occurrence_count": b.occurrence_count,
                    "severity_level": b.severity_level,
                    "description": b.description,
                    "coaching_rule": b.coaching_rule,
                } for b in blindspots
            ], ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/climate/meta":
            from .micro_meta_climate import MicroMetaClimateRadar
            rep = MicroMetaClimateRadar.analyze_recent_meta()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "climate_type": rep.climate_type.value,
                "climate_label": rep.climate_label,
                "summary_markdown": rep.summary_markdown,
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/flow/tilt":
            from .flow_tilt_guardian import FlowTiltGuardian
            res = FlowTiltGuardian.evaluate_player_state()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "flow_score": res.flow_score,
                "tilt_tier": res.tilt_tier.value,
                "tier_label": res.tier_label,
                "summary_markdown": res.summary_markdown,
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/bgs/reactor":
            from .battlegrounds_mode_reactor import BattlegroundsModeReactor
            rep = BattlegroundsModeReactor.evaluate_tavern_turn(current_tier=3, upgrade_cost=6, available_gold=7, hero_health=30)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "active_comp": rep.active_comp.value,
                "comp_label": rep.comp_label,
                "upgrade_recommendation": rep.upgrade_eval.recommendation_label,
                "summary_markdown": rep.summary_markdown,
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/council/debate":
            from .council_of_champions import CouncilOfChampions
            rep = CouncilOfChampions.convene_council(player_hp=20, enemy_hp=20, board_total_attack=6)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "verdict": rep.verdict.value,
                "verdict_label": rep.verdict_label,
                "final_recommended_action": rep.final_recommended_action,
                "summary_markdown": rep.summary_markdown,
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/gaze/attention":
            from .gaze_attention_tracker import GazeAttentionTracker
            rep = GazeAttentionTracker.evaluate_gaze_distribution()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "active_blindspot_alert": rep.active_blindspot_alert,
                "primary_focus_region": rep.primary_focus_region.value,
                "summary_markdown": rep.summary_markdown,
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/persona/speak":
            from .persona_voice_matrix import PersonaVoiceMatrix
            res = PersonaVoiceMatrix.render_voice()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "active_persona": res.active_persona.value,
                "persona_title": res.persona_title,
                "spoken_line": res.spoken_line,
                "summary_markdown": res.summary_markdown,
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/acoustic/emotion":
            from .acoustic_emotion_guard import AcousticEmotionGuard
            rep = AcousticEmotionGuard.analyze_voice_telemetry()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "frustration_index": rep.frustration_index,
                "state": rep.state.value,
                "state_label": rep.state_label,
                "summary_markdown": rep.summary_markdown,
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/tcg/philosophy":
            from .universal_tcg_theory import UniversalTcgTheoryEngine
            rep = UniversalTcgTheoryEngine.evaluate_board_philosophy(player_hp=20, enemy_hp=20, my_board_mana_value=8, enemy_board_mana_value=6, my_hand_count=4, enemy_hand_count=3)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "dominant_axiom": rep.dominant_axiom.value,
                "axiom_title": rep.axiom_title,
                "summary_markdown": rep.summary_markdown,
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/ui/theme":
            from ui.acrylic_effects import AuraState, AcrylicGlassHelper
            qss = AcrylicGlassHelper.get_glass_stylesheet(AuraState.IDLE_CYBER)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "ok",
                "current_theme": _CURRENT_STATE.get("theme", "WARM_OBSIDIAN_GOLD"),
                "glass_stylesheet": qss,
            }, ensure_ascii=False).encode("utf-8"))
        elif self.path == "/api/ui/dock":
            from ui.magnetic_docking import MagneticDockingManager
            anchor = MagneticDockingManager.compute_dock_coordinates((100, 100, 1920, 1080), dock_mode="TOP_RIGHT")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({
                "x": anchor.x,
                "y": anchor.y,
                "scale_factor": anchor.scale_factor,
                "is_snapped": anchor.is_snapped,
            }, ensure_ascii=False).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


class WebCompanionServer:
    """Manages the background LAN web server."""

    def __init__(self, port: int = 8899) -> None:
        self.port = port
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None
        self.local_ip = self._detect_local_ip()

    @staticmethod
    def _detect_local_ip() -> str:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = "127.0.0.1"
        finally:
            s.close()
        return ip

    def start(self) -> None:
        try:
            self.server = HTTPServer(("0.0.0.0", self.port), WebCompanionHandler)
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            logger.info(f"WebCompanion running on http://{self.local_ip}:{self.port}")
        except Exception as e:
            logger.warning(f"Could not start WebCompanion server: {e}")

    def stop(self) -> None:
        if self.server:
            try:
                self.server.shutdown()
                self.server.server_close()
            except Exception:
                pass

    @classmethod
    def update_state(cls, state_dict: Dict[str, Any]) -> None:
        global _CURRENT_STATE, _STATE_VERSION
        _CURRENT_STATE.update(state_dict)
        _STATE_VERSION += 1

    @classmethod
    def get_state(cls) -> Dict[str, Any]:
        global _CURRENT_STATE
        return dict(_CURRENT_STATE)

    @classmethod
    def update_replay(cls, summary: Any) -> None:
        global _REPLAY_DATA
        if not summary:
            return
        _REPLAY_DATA.clear()
        _REPLAY_DATA.update({
            "result": getattr(summary, "result", "WIN"),
            "total_turns": getattr(summary, "total_turns", 0),
            "overall_accuracy_pct": getattr(summary, "overall_accuracy_pct", 100.0),
            "grade_tier": getattr(summary, "grade_tier", "S"),
            "brilliant_count": getattr(summary, "brilliant_count", 0),
            "best_count": getattr(summary, "best_count", 0),
            "good_count": getattr(summary, "good_count", 0),
            "inaccuracy_count": getattr(summary, "inaccuracy_count", 0),
            "blunder_count": getattr(summary, "blunder_count", 0),
            "key_turning_turn": getattr(summary, "key_turning_turn", 1),
            "turns": [
                {
                    "turn_number": n.turn_number,
                    "mana": n.mana,
                    "max_mana": n.max_mana,
                    "friendly_hp": n.friendly_hp,
                    "enemy_hp": n.enemy_hp,
                    "action_grade": n.action_grade,
                    "grade_color": n.grade_color,
                    "score": n.score,
                    "ai_best_plan": n.ai_best_plan,
                    "player_actual_plays": n.player_actual_plays,
                    "analysis_comment": n.analysis_comment,
                    "blunder_alerts": n.blunder_alerts,
                    "aoe_threat": n.aoe_threat,
                    "ai_winrate": n.ai_winrate,
                    "ai_ev": n.ai_ev,
                }
                for n in getattr(summary, "turn_nodes", [])
            ],
        })

    def get_url(self) -> str:
        return f"http://{self.local_ip}:{self.port}"
