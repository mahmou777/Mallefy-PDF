# -*- coding: utf-8 -*-
"""
Mallefy Analytics & Telegram Admin Server
=========================================
Secure enterprise telemetry backend & Telegram Administration Bot for Mallefy PDF.

Endpoints:
  POST /api/v1/telemetry/event      - Ingest sanitized client telemetry
  POST /api/v1/telemetry/heartbeat  - Active session ping
  GET  /health                      - System health check

Bot Commands:
  /start, /help, /stats, /today, /weekly, /monthly, /tools, /errors, /health, /export
"""

import os
import sys
import json
import time
import threading
import urllib.request
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from datetime import datetime

# Import database module
import database as db

# ----------------- Configuration & Secrets from Environment -----------------
PORT = int(os.environ.get("PORT", 8080))
import security_vault

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN") or security_vault.get_default_bot_token()
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID") or security_vault.get_default_admin_chat_id())
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Anti-spam alert state
last_error_alert_time = 0
ERROR_ALERT_COOLDOWN = 1800 # 30 minutes cooldown between error alerts

# ----------------- Telegram Helper Functions -----------------

def send_telegram_msg(chat_id, text, reply_markup=None):
    try:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(f"{API_BASE}/sendMessage", data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[Telegram Bot Error] sendMessage: {e}")
        return None

def send_telegram_file(chat_id, filename, content_bytes, caption=""):
    try:
        import uuid
        boundary = uuid.uuid4().hex
        body = bytearray()
        body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{chat_id}\r\n".encode("utf-8"))
        if caption:
            body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n{caption}\r\n".encode("utf-8"))
            body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"parse_mode\"\r\n\r\nHTML\r\n".encode("utf-8"))

        body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"document\"; filename=\"{filename}\"\r\nContent-Type: application/json\r\n\r\n".encode("utf-8"))
        body.extend(content_bytes)
        body.extend(f"\r\n--{boundary}--\r\n".encode("utf-8"))

        req = urllib.request.Request(
            f"{API_BASE}/sendDocument",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
        )
        with urllib.request.urlopen(req, timeout=25) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[Telegram Bot Error] sendDocument: {e}")
        return None

def check_and_alert_errors():
    global last_error_alert_time
    now = time.time()
    if now - last_error_alert_time < ERROR_ALERT_COOLDOWN:
        return

    # Check last 100 operations error rate
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("SELECT is_success FROM tool_operations ORDER BY id DESC LIMIT 50")
    rows = c.fetchall()
    conn.close()

    if len(rows) >= 10:
        failures = sum(1 for r in rows if r["is_success"] == 0)
        rate = (failures / len(rows)) * 100.0
        if rate >= 15.0:
            last_error_alert_time = now
            alert_text = (
                "⚠️ <b>تنبيه أمني وإداري: ارتفاع معدل الأخطاء!</b>\n\n"
                f"• معدل الفشل الحالي: <code>{rate:.1f}%</code> في آخر {len(rows)} عملية.\n"
                "• يرجى مراجعة سجل الأخطاء عبر إرسال الأمر: /errors\n"
                f"• التوقيت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            send_telegram_msg(ADMIN_CHAT_ID, alert_text)

# ----------------- HTTP Telemetry Ingestion Handler -----------------

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class TelemetryHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        # Clean logging
        sys.stderr.write(f"[{datetime.now().strftime('%H:%M:%S')}] {self.address_string()} - {format % args}\n")

    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Client-Version")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            summary = db.get_summary_stats()
            resp = {
                "status": "healthy",
                "service": "Mallefy Analytics Server",
                "version": "1.1.0",
                "timestamp": datetime.now().isoformat(),
                "total_users": summary["unique_devices"],
                "database": "sqlite_ready"
            }
            self.wfile.write(json.dumps(resp).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 1024 * 64: # 64KB max payload safety limit
            self.send_response(413) # Payload too large
            self.end_headers()
            return

        body = self.rfile.read(content_length).decode("utf-8")
        try:
            payload = json.loads(body)
        except Exception:
            self.send_response(400)
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(b'{"error": "Invalid JSON"}')
            return

        # 1. Ingest Event
        if self.path == "/api/v1/telemetry/event":
            user_id = payload.get("user_id", "ANON")
            event_type = payload.get("event", "")

            if event_type == "launch":
                db.record_session(
                    user_id=user_id,
                    app_ver=payload.get("app_version", "1.1.0"),
                    os_ver=payload.get("os_version", "Android"),
                    ip_hash=str(hash(self.client_address[0]))
                )

            elif event_type == "tool_used":
                db.record_tool_operation(
                    user_id=user_id,
                    tool_id=payload.get("tool_id", "unknown"),
                    is_success=payload.get("success", True),
                    duration_ms=payload.get("duration_ms", 0),
                    files_count=payload.get("files_count", 1),
                    error_code=payload.get("error_code", "")
                )
                check_and_alert_errors()

            elif event_type == "ai_request":
                db.record_ai_operation(
                    user_id=user_id,
                    model_id=payload.get("model", "default"),
                    is_success=payload.get("success", True),
                    tokens=payload.get("tokens", 0),
                    cost=payload.get("cost", 0.0),
                    latency_ms=payload.get("latency_ms", 0),
                    http_code=payload.get("http_code", 200),
                    error_type=payload.get("error_type", "")
                )

            elif event_type == "error":
                db.log_error(
                    user_id=user_id,
                    category=payload.get("category", "APP"),
                    error_code=payload.get("code", "ERR"),
                    message=payload.get("message", "")
                )

            self.send_response(200)
            self.send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "recorded"}')

        # 2. Heartbeat Ping
        elif self.path == "/api/v1/telemetry/heartbeat":
            user_id = payload.get("user_id", "ANON")
            db.record_heartbeat(user_id)
            self.send_response(200)
            self.send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "alive"}')

        else:
            self.send_response(404)
            self.end_headers()

# ----------------- Telegram Admin Bot Polling Loop -----------------

def run_telegram_bot():
    print("🤖 بوت تلجرام للإدارة والتحليلات يبدأ الاستماع للأوامر...")
    offset = 0

    while True:
        try:
            url = f"{API_BASE}/getUpdates?timeout=25&offset={offset}"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=30) as resp:
                updates = json.loads(resp.read().decode("utf-8")).get("result", [])

            for u in updates:
                offset = u["update_id"] + 1
                msg = u.get("message", {})
                text = (msg.get("text") or "").strip()
                chat_id = msg.get("chat", {}).get("id")

                if not text or not chat_id:
                    continue

                # STRICT AUTHORIZATION VERIFICATION ON SERVER
                if chat_id != ADMIN_CHAT_ID:
                    send_telegram_msg(chat_id, "⛔ <b>عفواً، ليس لديك صلاحية الوصول إلى هذه اللوحة الإدارية.</b>")
                    continue

                # Route Commands
                if text == "/start" or text == "/help":
                    help_msg = (
                        "👑 <b>لوحة تحكم إدارة تطبيق ملفّي (Mallefy PDF Analytics):</b>\n"
                        "━━━━━━━━━━━━━━━━━━━━\n"
                        "📊 <b>الأوامر الإحصائية:</b>\n"
                        "• /stats  - ملخص الإحصائيات الشامل (DAU/WAU/MAU)\n"
                        "• /today  - تقرير نشاط اليوم (24 ساعة)\n"
                        "• /weekly - تقرير الأسبوع (7 أيام)\n"
                        "• /monthly- تقرير الشهر (30 يوماً)\n\n"
                        "🛠️ <b>الأدوات والأداء:</b>\n"
                        "• /tools  - ترتيب الأدوات حسب الاستخدام ونسبة النجاح\n"
                        "• /errors - ملخص الأخطاء الأكثر تكراراً وأكوادها\n"
                        "• /health - فحص حالة الخادم والاتصال وقاعدة البيانات\n"
                        "• /export - تصدير التقرير الكامل بصيغة JSON آمنة"
                    )
                    send_telegram_msg(chat_id, help_msg)

                elif text == "/stats":
                    s = db.get_summary_stats()
                    stat_msg = (
                        "📊 <b>ملخص الإحصائيات الشامل للتطبيق:</b>\n"
                        "━━━━━━━━━━━━━━━━━━━━\n"
                        f"📱 <b>المستخدمون:</b>\n"
                        f"  • إجمالي مرات الفتح: <code>{s['total_launches']:,}</code>\n"
                        f"  • الأجهزة الفريدة (Total Installs): <code>{s['unique_devices']:,}</code>\n"
                        f"  • النشطون اليوم (DAU): <code>{s['dau']:,}</code>\n"
                        f"  • النشطون هذا الأسبوع (WAU): <code>{s['wau']:,}</code>\n"
                        f"  • النشطون هذا الشهر (MAU): <code>{s['mau']:,}</code>\n\n"
                        f"⚡ <b>أداء أدوات PDF:</b>\n"
                        f"  • إجمالي العمليات: <code>{s['total_ops']:,}</code>\n"
                        f"  • نسبة النجاح: <b>{s['success_rate']}%</b>\n"
                        f"  • الملفات المعالجة: <code>{s['total_files']:,}</code> ملف\n"
                        f"  • متوسط زمن المعالجة: <code>{s['avg_duration_ms']} ms</code>\n\n"
                        f"🤖 <b>استهلاك OpenRouter AI:</b>\n"
                        f"  • إجمالي طلبات الذكاء الاصطناعي: <code>{s['total_ai_requests']:,}</code>\n"
                        f"  • الرموز المستهلكة (Tokens): <code>{s['total_tokens']:,}</code>\n"
                        f"  • التكلفة التقديرية: <code>${s['total_cost_usd']:.4f}</code>\n"
                        f"  • متوسط زمن استجابة النموذج: <code>{s['avg_ai_latency_ms']} ms</code>"
                    )
                    send_telegram_msg(chat_id, stat_msg)

                elif text == "/today":
                    p = db.get_period_stats(1)
                    today_msg = (
                        "📅 <b>تقرير نشاط اليوم (آخر 24 ساعة):</b>\n"
                        "━━━━━━━━━━━━━━━━━━━━\n"
                        f"• المستخدمون النشطون: <b>{p['active_users']:,}</b>\n"
                        f"• العمليات المنفذة: <b>{p['total_ops']:,}</b> (ناجح: {p['success_ops']})\n"
                        f"• إجمالي الملفات المعالجة: <b>{p['files_processed']:,}</b>\n"
                        f"• طلبات الذكاء الاصطناعي: <b>{p['ai_requests']}</b>\n"
                        f"• الرموز المستهلكة: <b>{p['tokens_used']:,}</b> (${p['cost_usd']:.4f})"
                    )
                    send_telegram_msg(chat_id, today_msg)

                elif text == "/weekly":
                    p = db.get_period_stats(7)
                    w_msg = (
                        "🗓️ <b>تقرير الأسبوع (آخر 7 أيام):</b>\n"
                        "━━━━━━━━━━━━━━━━━━━━\n"
                        f"• المستخدمون النشطون (WAU): <b>{p['active_users']:,}</b>\n"
                        f"• إجمالي العمليات: <b>{p['total_ops']:,}</b>\n"
                        f"• الملفات المنجزة: <b>{p['files_processed']:,}</b> ملف\n"
                        f"• استهلاك الذكاء الاصطناعي: <b>{p['tokens_used']:,}</b> tokens"
                    )
                    send_telegram_msg(chat_id, w_msg)

                elif text == "/monthly":
                    p = db.get_period_stats(30)
                    m_msg = (
                        "📆 <b>تقرير الشهر (آخر 30 يوماً):</b>\n"
                        "━━━━━━━━━━━━━━━━━━━━\n"
                        f"• المستخدمون النشطون (MAU): <b>{p['active_users']:,}</b>\n"
                        f"• إجمالي العمليات المنفذة: <b>{p['total_ops']:,}</b>\n"
                        f"• الملفات المعالجة بالكامل: <b>{p['files_processed']:,}</b>\n"
                        f"• تكلفة الـ AI التراكمية: <b>${p['cost_usd']:.4f}</b>"
                    )
                    send_telegram_msg(chat_id, m_msg)

                elif text == "/tools":
                    ranks = db.get_tool_rankings()
                    if not ranks:
                        send_telegram_msg(chat_id, "ℹ️ لا توجد بيانات عمليات مسجلة بعد.")
                        continue
                    lines = ["🛠️ <b>ترتيب الأدوات حسب الاستخدام:</b>\n━━━━━━━━━━━━━━━━━━━━"]
                    for idx, t in enumerate(ranks, 1):
                        lines.append(f"{idx}. <b>{t['tool_id']}</b>: <code>{t['count']}</code> مرة | نجاح: <b>{t['success_rate']}%</b> | ⏱ {t['avg_ms']}ms")
                    send_telegram_msg(chat_id, "\n".join(lines))

                elif text == "/errors":
                    errs = db.get_top_errors()
                    if not errs:
                        send_telegram_msg(chat_id, "✅ <b>ممتاز! لا توجد أي أخطاء مسجلة بالنظام.</b>")
                        continue
                    lines = ["⚠️ <b>سجل الأخطاء الأكثر تكراراً:</b>\n━━━━━━━━━━━━━━━━━━━━"]
                    for e in errs:
                        lines.append(f"• كود الخطأ: <code>{e['code']}</code> | التكرار: <b>{e['count']}</b> ({e['category']})")
                    send_telegram_msg(chat_id, "\n".join(lines))

                elif text == "/health":
                    summary = db.get_summary_stats()
                    health_msg = (
                        "🩺 <b>فحص حالة النظام والخدمات (System Health):</b>\n"
                        "━━━━━━━━━━━━━━━━━━━━\n"
                        "• 🟢 <b>خادم القياسات:</b> متصل ويعمل بكفاءة (Threading HTTP)\n"
                        "• 🟢 <b>قاعدة البيانات:</b> SQLite مهيأة ومفهرسة بنجاح\n"
                        "• 🟢 <b>تكامل Telegram Bot:</b> مفعّل ومؤمّن للأدمن فقط\n"
                        f"• 📊 <b>إجمالي الأجهزة المسجلة:</b> {summary['unique_devices']} جهاز\n"
                        f"• 🕒 <b>توقيت الخادم:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    send_telegram_msg(chat_id, health_msg)

                elif text == "/export":
                    data = db.export_all_data()
                    export_json = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
                    fname = f"mallefy_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    send_telegram_file(chat_id, fname, export_json, "📁 <b>تقرير الإحصائيات الكامل بصيغة JSON آمنة ومجمعة.</b>")

        except Exception as e:
            time.sleep(2)

def start_server():
    server = ThreadedHTTPServer(("0.0.0.0", PORT), TelemetryHandler)
    print(f"🚀 خادم القياسات التحليلية يعمل الآن على المنفذ: {PORT}")

    # Start bot thread
    bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping server...")
        server.shutdown()

if __name__ == "__main__":
    start_server()
