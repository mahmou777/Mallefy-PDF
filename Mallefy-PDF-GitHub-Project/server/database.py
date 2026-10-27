# -*- coding: utf-8 -*-
"""
Mallefy Analytics Engine — Persistent Database Layer (SQLite)
=============================================================
Manages persistent analytical telemetry for the Mallefy PDF mobile app:
- User sessions & unique pseudonymous device IDs (DAU / WAU / MAU)
- Tool operations & file processing counts
- Error logging & crash taxonomy
- AI usage, token counts, and cost accounting
"""

import sqlite3
import os
import time
from datetime import datetime, date, timedelta

DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "mallefy_analytics.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()

    # 1. Sessions table (Unique Devices / Launches)
    c.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        app_version TEXT,
        os_version TEXT,
        ip_hash TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_sessions_created ON sessions(created_at)")

    # 2. Tool operations table
    c.execute("""
    CREATE TABLE IF NOT EXISTS tool_operations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        tool_id TEXT NOT NULL,
        is_success INTEGER NOT NULL,
        duration_ms INTEGER,
        files_count INTEGER DEFAULT 1,
        error_code TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_tool_ops_tool ON tool_operations(tool_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_tool_ops_created ON tool_operations(created_at)")

    # 3. AI Requests table
    c.execute("""
    CREATE TABLE IF NOT EXISTS ai_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        model_id TEXT NOT NULL,
        is_success INTEGER NOT NULL,
        tokens_used INTEGER DEFAULT 0,
        estimated_cost REAL DEFAULT 0.0,
        latency_ms INTEGER,
        http_code INTEGER,
        error_type TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_ai_created ON ai_requests(created_at)")

    # 4. Error log table
    c.execute("""
    CREATE TABLE IF NOT EXISTS error_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        category TEXT,
        error_code TEXT,
        message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

def record_session(user_id, app_ver, os_ver, ip_hash=""):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
    INSERT INTO sessions (user_id, app_version, os_version, ip_hash)
    VALUES (?, ?, ?, ?)
    """, (user_id, app_ver, os_ver, ip_hash))
    conn.commit()
    conn.close()

def record_heartbeat(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
    UPDATE sessions SET last_heartbeat = CURRENT_TIMESTAMP
    WHERE user_id = ? AND created_at >= datetime('now', '-1 day')
    """, (user_id,))
    conn.commit()
    conn.close()

def record_tool_operation(user_id, tool_id, is_success, duration_ms, files_count=1, error_code=""):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
    INSERT INTO tool_operations (user_id, tool_id, is_success, duration_ms, files_count, error_code)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, tool_id, 1 if is_success else 0, duration_ms, files_count, error_code))
    conn.commit()
    conn.close()

def record_ai_operation(user_id, model_id, is_success, tokens=0, cost=0.0, latency_ms=0, http_code=200, error_type=""):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
    INSERT INTO ai_requests (user_id, model_id, is_success, tokens_used, estimated_cost, latency_ms, http_code, error_type)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, model_id, 1 if is_success else 0, tokens, cost, latency_ms, http_code, error_type))
    conn.commit()
    conn.close()

def log_error(user_id, category, error_code, message):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
    INSERT INTO error_logs (user_id, category, error_code, message)
    VALUES (?, ?, ?, ?)
    """, (user_id, category, error_code, message[:500]))
    conn.commit()
    conn.close()

# ----------------- Aggregations for Telegram Admin Bot -----------------

def get_summary_stats():
    conn = get_connection()
    c = conn.cursor()

    # Total launches
    c.execute("SELECT COUNT(*) FROM sessions")
    total_launches = c.fetchone()[0]

    # Unique devices
    c.execute("SELECT COUNT(DISTINCT user_id) FROM sessions")
    unique_devices = c.fetchone()[0]

    # DAU (last 24 hours)
    c.execute("SELECT COUNT(DISTINCT user_id) FROM sessions WHERE created_at >= datetime('now', '-1 day')")
    dau = c.fetchone()[0]

    # WAU (last 7 days)
    c.execute("SELECT COUNT(DISTINCT user_id) FROM sessions WHERE created_at >= datetime('now', '-7 days')")
    wau = c.fetchone()[0]

    # MAU (last 30 days)
    c.execute("SELECT COUNT(DISTINCT user_id) FROM sessions WHERE created_at >= datetime('now', '-30 days')")
    mau = c.fetchone()[0]

    # Total tool operations
    c.execute("SELECT COUNT(*), SUM(is_success), SUM(files_count), AVG(duration_ms) FROM tool_operations")
    row = c.fetchone()
    total_ops = row[0] or 0
    success_ops = row[1] or 0
    total_files = row[2] or 0
    avg_duration = round(row[3] or 0)

    # AI Stats
    c.execute("SELECT COUNT(*), SUM(is_success), SUM(tokens_used), SUM(estimated_cost), AVG(latency_ms) FROM ai_requests")
    row_ai = c.fetchone()
    total_ai = row_ai[0] or 0
    success_ai = row_ai[1] or 0
    total_tokens = row_ai[2] or 0
    total_cost = row_ai[3] or 0.0
    avg_latency = round(row_ai[4] or 0)

    conn.close()

    return {
        "total_launches": total_launches,
        "unique_devices": unique_devices,
        "dau": dau,
        "wau": wau,
        "mau": mau,
        "total_ops": total_ops,
        "success_ops": success_ops,
        "success_rate": round((success_ops / total_ops * 100), 1) if total_ops else 100.0,
        "total_files": total_files,
        "avg_duration_ms": avg_duration,
        "total_ai_requests": total_ai,
        "success_ai": success_ai,
        "total_tokens": total_tokens,
        "total_cost_usd": total_cost,
        "avg_ai_latency_ms": avg_latency
    }

def get_period_stats(days=1):
    conn = get_connection()
    c = conn.cursor()

    time_filter = f"-{days} days" if days > 1 else "-24 hours"

    c.execute(f"SELECT COUNT(DISTINCT user_id) FROM sessions WHERE created_at >= datetime('now', '{time_filter}')")
    active_users = c.fetchone()[0]

    c.execute(f"SELECT COUNT(*), SUM(is_success), SUM(files_count) FROM tool_operations WHERE created_at >= datetime('now', '{time_filter}')")
    row = c.fetchone()
    total_ops = row[0] or 0
    success_ops = row[1] or 0
    files = row[2] or 0

    c.execute(f"SELECT COUNT(*), SUM(tokens_used), SUM(estimated_cost) FROM ai_requests WHERE created_at >= datetime('now', '{time_filter}')")
    ai_row = c.fetchone()
    ai_requests = ai_row[0] or 0
    tokens = ai_row[1] or 0
    cost = ai_row[2] or 0.0

    conn.close()
    return {
        "active_users": active_users,
        "total_ops": total_ops,
        "success_ops": success_ops,
        "files_processed": files,
        "ai_requests": ai_requests,
        "tokens_used": tokens,
        "cost_usd": cost
    }

def get_tool_rankings():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
    SELECT tool_id, COUNT(*) as cnt, SUM(is_success) as succ, AVG(duration_ms) as avg_dur
    FROM tool_operations
    GROUP BY tool_id
    ORDER BY cnt DESC
    LIMIT 15
    """)
    rows = c.fetchall()
    conn.close()
    return [{
        "tool_id": r["tool_id"],
        "count": r["cnt"],
        "success": r["succ"] or 0,
        "success_rate": round(((r["succ"] or 0) / r["cnt"] * 100), 1) if r["cnt"] else 0,
        "avg_ms": round(r["avg_dur"] or 0)
    } for r in rows]

def get_top_errors():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
    SELECT error_code, COUNT(*) as cnt, category
    FROM error_logs
    GROUP BY error_code
    ORDER BY cnt DESC
    LIMIT 10
    """)
    rows = c.fetchall()
    conn.close()
    return [{"code": r["error_code"] or "UNKNOWN", "count": r["cnt"], "category": r["category"]} for r in rows]

def export_all_data():
    conn = get_connection()
    c = conn.cursor()
    summary = get_summary_stats()
    tools = get_tool_rankings()
    errors = get_top_errors()
    conn.close()
    return {
        "export_date": datetime.now().isoformat(),
        "summary": summary,
        "tools_ranking": tools,
        "top_errors": errors
    }

init_db()
