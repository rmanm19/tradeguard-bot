#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TradeGuard — Supervisor / نگهبان ربات
=====================================
ربات را در یک زیرفرآیند اجرا می‌کند و اگر کرش کرد یا خروجی گرفت،
خودکار دوباره بالا می‌آوردش. صفر وابستگی.

    python run_forever.py              # اجرای دائمی (روی VPS / PC)
    python run_forever.py --status     # وضعیت فعلی
    python run_forever.py --max-seconds 19800   # برای GitHub Actions
    python run_forever.py --no-alert   # بدون پیام هشدار به ادمین
"""

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE = Path(__file__).resolve().parent
BOT = BASE / "bot.py"
STATE = BASE / "supervisor_state.json"
LOG = BASE / "bot_run.log"
ENV = BASE / ".env"

READY_MARKERS = ("آماده است", "connected as", "متصل شد", "ready")
CRASH_WINDOW = 30.0          # اگر کمتر از این ثانیه زنده ماند = کرش سریع
MAX_FAST_CRASHES = 6
ALERT_COOLDOWN = 600.0

# ── انتشار بدون انتظار ──────────────────────────────────────────
# هر جاب GitHub Actions تا ~۵ ساعت و ۴۰ دقیقه زنده می‌ماند و concurrency
# اجازه نمی‌دهد جاب تازه شروع شود. بدون این بررسی، یک push روی main تا
# ۶ ساعت روی «کد قدیمی» اجرا می‌شد. اینجا هر چند دقیقه فهرست فایل‌های
# tradeguard-pro روی main را از API می‌گیریم؛ اگر یکی از فایل‌های زمانِ
# اجرا عوض شده باشد، تمیز خارج می‌شویم تا جابِ در صف با کد تازه بالا بیاید.
RESTART_FLAG = BASE / "restart.flag"
PROBE_SEC_DEFAULT = 240      # ۴ دقیقه
RUNTIME_FILES = ("bot.py", "run_forever.py", "db_crypt.py")


MAX_LOG_BYTES = 5 * 1024 * 1024


def log(msg: str) -> None:
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        if LOG.exists() and LOG.stat().st_size > MAX_LOG_BYTES:
            old = LOG.with_suffix(".log.1")
            try:
                if old.exists():
                    old.unlink()
                LOG.rename(old)
            except Exception:
                LOG.write_text("", encoding="utf-8")
        with LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def load_env() -> dict:
    env = dict(os.environ)
    if ENV.exists():
        for raw in ENV.read_text(encoding="utf-8", errors="replace").splitlines():
            raw = raw.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            k, v = raw.split("=", 1)
            env.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return env


def tg_notify(env: dict, text: str) -> None:
    token = env.get("BOT_TOKEN", "").strip()
    admin = env.get("ADMIN_USER_ID", "").strip()
    if not token or not admin or ":" not in token:
        return
    try:
        data = urllib.parse.urlencode(
            {"chat_id": admin, "text": text[:3800], "parse_mode": "HTML"}
        ).encode()
        urllib.request.urlopen(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=data,
            timeout=15,
        ).close()
    except Exception as exc:
        log(f"(هشدار تلگرام ارسال نشد: {exc})")


def _git_blob_sha(data: bytes) -> str:
    """SHA-1 همان چیزی که گیت برای محتوای فایل می‌سازد (blob).

    با این کار می‌توان محتوای فایل محلی را با «sha» برگشتی از API گیت‌هاب
    مقایسه کرد، بدون دانلود فایل.
    """
    h = hashlib.sha1()
    h.update(b"blob %d\0" % len(data))
    h.update(data)
    return h.hexdigest()


def _gh_get(url: str, env: dict, accept: str, timeout: float = 10.0) -> bytes:
    tok = (env.get("GITHUB_TOKEN") or "").strip()
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "tradeguard-supervisor", "Accept": accept},
    )
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def remote_code_changed(env: dict, files=RUNTIME_FILES, timeout: float = 10.0):
    """آیا فایل‌های زمانِ اجرا روی main عوض شده‌اند؟

    برمی‌گرداند (changed, names):
      True/False  → پاسخ قطعی
      None        → نشد بررسی کرد (شبکه/توکن/سهمیه) — هیچ کاری نکن

    فقط تغییر *کد* باعث ری‌استارت می‌شود؛ کامیت‌های [skip ci] مثل
    همگام‌سازی تنظیمات مینی‌اپ (که هر چند دقیقه یک‌بار است) SHA شاخه را
    جلو می‌برند ولی این فایل‌ها را دست نمی‌زنند، پس ربات را بی‌دلیل
    ری‌استارت نمی‌کنند.
    """
    if not (env.get("GITHUB_TOKEN") or "").strip():
        # بدون توکن، سهمیهٔ ۶۰ درخواست در ساعتِ IP مشترک رانر را نسوزان
        return None, []
    repo = (env.get("GITHUB_REPOSITORY") or "").strip()
    if not repo:
        return None, []
    branch = (env.get("DEPLOY_BRANCH") or "main").strip() or "main"
    try:
        listing = json.loads(
            _gh_get(
                f"https://api.github.com/repos/{repo}/contents/tradeguard-pro?ref={branch}",
                env,
                "application/vnd.github+json",
                timeout,
            ).decode("utf-8", "replace")
        )
    except Exception:
        return None, []
    if not isinstance(listing, list):
        return None, []

    remote = {
        e.get("name"): e.get("sha")
        for e in listing
        if isinstance(e, dict) and e.get("type") == "file"
    }

    suspects = []
    for name in files:
        local = BASE / name
        if not local.exists() or not remote.get(name):
            continue
        try:
            if _git_blob_sha(local.read_bytes()) != remote[name]:
                suspects.append(name)
        except Exception:
            return None, []
    if not suspects:
        return False, []

    # تأیید با محتوای واقعی: اگر فقط پایان خط (CRLF) فرق کند، ری‌استارت
    # بی‌پایان می‌شد. یک بار دانلود می‌کنیم و بعد از یکسان‌سازی مقایسه می‌کنیم.
    confirmed = []
    for name in suspects:
        try:
            body = _gh_get(
                f"https://api.github.com/repos/{repo}/contents/tradeguard-pro/{name}?ref={branch}",
                env,
                "application/vnd.github.raw",
                timeout,
            )
        except Exception:
            return None, []
        local = (BASE / name).read_bytes()
        if body.replace(b"\r\n", b"\n") != local.replace(b"\r\n", b"\n"):
            confirmed.append(name)
    return bool(confirmed), confirmed


def read_restart_request() -> str:
    """درخواست ری‌استارت دستی (دستور /restart در ربات) را می‌خواند."""
    try:
        if not RESTART_FLAG.exists():
            return ""
        raw = RESTART_FLAG.read_text(encoding="utf-8", errors="replace").strip()
    except Exception:
        return ""
    return raw or "دستور ادمین"


def clear_restart_request() -> None:
    try:
        if RESTART_FLAG.exists():
            RESTART_FLAG.unlink()
    except Exception:
        pass


def start_deploy_probe(env: dict, probe_sec: float, stopping: dict, stop_info: dict,
                       child_ref: dict) -> None:
    """ترد پس‌زمینه: هر probe_sec یک‌بار چک می‌کند کد main جلو رفته یا نه."""
    if probe_sec <= 0:
        return

    def loop() -> None:
        while not stopping["flag"]:
            waited = 0.0
            while waited < probe_sec:
                if stopping["flag"]:
                    return
                time.sleep(0.5)
                waited += 0.5

            reason = read_restart_request()
            if reason:
                stop_info["why"] = f"درخواست ری‌استارت ({reason})"
            else:
                changed, names = remote_code_changed(env)
                if changed:
                    stop_info["why"] = "کد جدید روی main: " + "، ".join(names)
                elif changed is None:
                    log("… بررسی کد جدید ممکن نشد (شبکه/توکن) — دور بعد دوباره")
            if not stop_info["why"]:
                continue

            log("↻ " + stop_info["why"] + " — خروج تمیز تا اجرای صف با کد تازه شروع کند")
            stopping["flag"] = True
            proc = child_ref.get("p")
            if proc is not None and proc.poll() is None:
                try:
                    proc.terminate()
                except Exception:
                    pass
            return

    threading.Thread(target=loop, name="deploy-probe", daemon=True).start()


def write_state(**kw) -> None:
    data = {}
    if STATE.exists():
        try:
            data = json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data.update(kw)
    data["updated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        STATE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def show_status() -> None:
    if not STATE.exists():
        print("\n  هیچ وضعیتی ثبت نشده — ربات هنوز با run_forever اجرا نشده.\n")
        return
    d = json.loads(STATE.read_text(encoding="utf-8"))
    pid = d.get("pid")
    alive = False
    if pid:
        try:
            os.kill(int(pid), 0)
            alive = True
        except Exception:
            alive = False
    print(f"""
  ┌─────────────────────────────────────────────┐
  │  وضعیت نگهبان TradeGuard                    │
  ├─────────────────────────────────────────────┤
     ربات زنده      : {'✅ بله' if alive else '❌ نه'}
     PID            : {pid or '-'}
     تعداد ری‌استارت: {d.get('restarts', 0)}
     آخرین شروع    : {d.get('started', '-')}
     آخرین خروج    : {d.get('last_exit', '-')}
     آپدیت         : {d.get('updated', '-')}
  └─────────────────────────────────────────────┘
""")


def main() -> int:
    ap = argparse.ArgumentParser(description="TradeGuard bot supervisor")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--max-seconds", type=int, default=0,
                    help="بعد از این مدت با خیال راحت خارج شو (برای GitHub Actions)")
    ap.add_argument("--no-alert", action="store_true", help="بدون پیام تلگرام")
    ap.add_argument("--once", action="store_true", help="فقط یک بار اجرا کن (بدون ری‌استارت)")
    ap.add_argument("--probe-seconds", type=float, default=None,
                    help="هر چند ثانیه کد main را چک کن (۰ = خاموش؛ پیش‌فرض ۲۴۰)")
    args = ap.parse_args()

    if args.status:
        show_status()
        return 0

    if not BOT.exists():
        log(f"❌ bot.py پیدا نشد در {BOT}")
        return 1

    env = load_env()
    token = env.get("BOT_TOKEN", "").strip()
    if not token or "your_telegram_bot_token" in token:
        log("❌ BOT_TOKEN تنظیم نشده. فایل tradeguard-pro/.env را بساز.")
        return 1

    stopping = {"flag": False}

    def on_signal(signum, _frame):
        stopping["flag"] = True
        log(f"سیگنال {signum} دریافت شد — خروج تمیز…")

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            signal.signal(sig, on_signal)
        except Exception:
            pass

    probe_sec = args.probe_seconds
    if probe_sec is None:
        try:
            probe_sec = float(env.get("RESTART_PROBE_SEC", PROBE_SEC_DEFAULT))
        except Exception:
            probe_sec = float(PROBE_SEC_DEFAULT)

    stop_info = {"why": ""}          # "" یعنی خروج عادی/کرشی، نه به‌روزرسانی
    child_ref = {"p": None}
    probe_stop = {"flag": False}     # تردِ بررسی را خاموش می‌کند

    t_start = time.time()
    restarts = 0
    fatal_reason = ""        # خطای «خودش درست نمی‌شود» → تلاش مجدد بی‌فایده است
    fast_crashes = 0
    backoff = 5
    last_alert = 0.0

    log("═" * 56)
    log("🛡  نگهبان TradeGuard فعال شد — ربات را زنده نگه می‌دارم")
    _sha = (env.get("GITHUB_SHA") or "").strip()
    log(f"🧩 کد در حال اجرا: {_sha[:7] or 'نامشخص (اجرای محلی)'}")
    if probe_sec > 0 and (env.get("GITHUB_TOKEN") or "").strip():
        log(f"🔄 بررسی کد جدید هر {int(probe_sec)} ثانیه — بعد از push، ربات خودش "
            f"تمیز خارج می‌شود تا کد تازه بالا بیاید")
    elif probe_sec > 0:
        log("ℹ️  بررسی خودکار کد جدید خاموش است (GITHUB_TOKEN نیست) — "
            "ری‌استارت دستی با ساخت فایل restart.flag")
    log("═" * 56)

    start_deploy_probe(env, probe_sec, probe_stop, stop_info, child_ref)

    while not stopping["flag"]:
        if args.max_seconds and (time.time() - t_start) >= args.max_seconds:
            log(f"⏱  سقف زمان ({args.max_seconds}s) پر شد — خروج تمیز برای ادامه در اجرای بعدی")
            break

        write_state(pid=None, started=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    restarts=restarts, status="starting")
        log(f"▶  اجرای bot.py (تلاش #{restarts + 1})")

        child = None
        ran_ok = False
        try:
            child = subprocess.Popen(
                [sys.executable, "-u", str(BOT)],
                cwd=str(BASE),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            child_ref["p"] = child
            write_state(pid=child.pid, status="running")
            started = time.time()

            assert child.stdout is not None
            for line in child.stdout:
                line = line.rstrip("\n")
                if line:
                    # خطوط دستورِ GitHub Actions (::error:: …) نباید تودرتو شوند،
                    # وگرنه Annotation در صفحه اجرا نمایش داده نمی‌شود
                    log(line if line.lstrip().startswith("::") else "   " + line)
                    low = line.lower()
                    if ("unauthorized" in low or '"error_code":401' in low.replace(" ", "")) and not fatal_reason:
                        fatal_reason = "توکن ربات با تلگرام نمی‌خواند (401 Unauthorized)"
                    if any(m in low for m in READY_MARKERS):
                        if not ran_ok:
                            print("::notice title=ربات متصل شد::آماده دریافت پیام — در تلگرام /start بزنید", flush=True)
                        ran_ok = True
                        if fast_crashes:
                            fast_crashes = 0
                            backoff = 5
                if stopping["flag"]:
                    child.terminate()
                    break

            rc = child.wait(timeout=20)
        except Exception as exc:
            log(f"⚠  خطا در اجرای زیرفرآیند: {exc}")
            rc = -1
        finally:
            if child and child.poll() is None:
                try:
                    child.terminate()
                    child.wait(timeout=10)
                except Exception:
                    try:
                        child.kill()
                    except Exception:
                        pass

        if stopping["flag"]:
            break

        # خروج به‌خاطر کد جدید یا درخواست ادمین: ری‌استارت نکن؛ بگذار جابِ
        # در صف (که با تازه‌ترین کد main شروع می‌شود) جایش را بگیرد.
        if stop_info["why"]:
            break

        lived = time.time() - (started if 'started' in dir() else time.time())
        if args.once:
            log(f"■  اجرای تک‌باره تمام شد (کد {rc})")
            write_state(status="stopped", last_exit=f"rc={rc}")
            return 0

        if fatal_reason or rc in (2, 3):
            reason = fatal_reason or ("BOT_TOKEN تنظیم نشده" if rc == 2 else "اتصال به تلگرام برقرار نشد")
            log(f"⛔ توقف بدون تلاش مجدد: {reason}")
            log("   → توکن BotFather را دوباره بردارید و Secret با نام BOT_TOKEN را به‌روز کنید")
            log("   → GitHub ─ Settings ─ Secrets and variables ─ Actions ─ BOT_TOKEN")
            if not args.no_alert:
                tg_notify(env, f"⛔ <b>TradeGuard</b>\n{reason}\n"
                               "توکن را در Secret با نام <code>BOT_TOKEN</code> به‌روز کنید.")
            write_state(status="stopped", pid=None, last_exit=f"rc={rc} ({reason})")
            return 1

        restarts += 1
        write_state(restarts=restarts, last_exit=f"rc={rc} after {int(lived)}s", pid=None, status="restarting")

        if lived < CRASH_WINDOW:
            fast_crashes += 1
        else:
            fast_crashes = 0
            backoff = 5

        if fast_crashes >= MAX_FAST_CRASHES:
            log(f"⛔ {fast_crashes} کرش سریع پشت‌سرهم — نگهبان متوقف شد تا لاگ را ببینی.")
            log(f"   لاگ: {LOG}")
            if not args.no_alert:
                tg_notify(env, "⛔ <b>TradeGuard</b>\nربات ۶ بار پشت‌سرهم کرش کرد و نگهبان متوقف شد.\n"
                               f"کد خروج: <code>{rc}</code>\nلاگ را در سرور ببین.")
            return 1

        if fast_crashes >= 1 and time.time() - last_alert > ALERT_COOLDOWN:
            last_alert = time.time()
            if not args.no_alert and not ran_ok:
                tg_notify(env, f"⚠️ <b>TradeGuard</b>\nربات کرش کرد (کد {rc}) — در حال راه‌اندازی مجدد…")
        elif ran_ok and time.time() - last_alert > ALERT_COOLDOWN and restarts > 1:
            last_alert = time.time()
            if not args.no_alert:
                tg_notify(env, "✅ <b>TradeGuard</b>\nربات دوباره آنلاین شد.")

        wait = backoff if fast_crashes else 3
        log(f"↻  ری‌استارت در {wait} ثانیه (کد خروج {rc})")
        if fast_crashes:
            print(
                f"::warning title=ری‌استارت #{restarts}::ربات {int(lived)} ثانیه زنده ماند و با کد {rc} مرد — "
                f"تلاش بعدی تا {wait} ثانیه دیگر",
                flush=True,
            )
        for _ in range(int(wait * 2)):
            if stopping["flag"]:
                break
            time.sleep(0.5)
        backoff = min(backoff * 2, 300)

    clear_restart_request()
    if stop_info["why"]:
        uptime = int(time.time() - t_start)
        write_state(status="restart-for-deploy", pid=None,
                    last_exit=f"deploy: {stop_info['why']}", started=None)
        log(f"■  خروج برای به‌روزرسانی پس از {uptime} ثانیه — «{stop_info['why']}»")
        print(f"::notice title=ری‌استارت برای کد جدید::{stop_info['why']}", flush=True)
        if not args.no_alert:
            tg_notify(
                env,
                "♻️ <b>TradeGuard</b>\n"
                "کد جدید روی <code>main</code> منتشر شد؛ ربات تمیز خارج شد تا "
                "اجرای بعدی با کد تازه بالا بیاید.\n"
                f"دلیل: {stop_info['why']}\n"
                f"مدت این اجرا: {uptime // 60} دقیقه",
            )
        return 0

    write_state(status="stopped", pid=None)
    log("■  نگهبان خاموش شد.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
