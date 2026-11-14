#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تنظیم و بازبینی پروفایل کانال — بدون نیاز به دست‌زدن به چت ربات.

چرا این فایل هست؟ چون بعضی کارها (عنوان/توضیحات/عکس/پین) از داخل GitHub Actions
هم قابل انجام‌اند؛ این‌طور لازم نیست مالک کانال دستی چیزی را در تلگرام عوض کند.

اجرا (معمولاً از workflow «Channel Profile»):
    LANG=en APPLY=1 FORCE=1 python channel_profile.py

متغیرها:
    BOT_TOKEN   توکن ربات (Secret)
    LANG        en | fa        (پیش‌فرض en)
    CHANNEL     آیدی/یوزرنیم کانال؛ اگر خالی باشد از دیتابیس رمزگشایی‌شده خوانده می‌شود
    APPLY       1 = تغییر بده، 0 = فقط گزارش (پیش‌فرض 0)
    FORCE       1 = حتی اگر چیزی از قبل ست شده بود، با مقدار استاندارد جایگزین کن

هیچ رمزی چاپ نمی‌شود و هیچ تغییری بدون APPLY=1 انجام نمی‌شود.
"""
from __future__ import annotations

import json
import mimetypes
import os
import sqlite3
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
DB_PATH = HERE / "tradeguard.db"
AVATAR = HERE / "bot_avatar.png"

# ── متن‌های استاندارد (هم‌راستا با bot.py؛ تست هم‌خوانی دارد) ──────────────
TEXTS = {
    "en": {
        "title": "TradeGuard — Crypto & Prop Radar",
        "desc": (
            "📡 Live funding & Open Interest radar for prop traders.\n"
            "🎁 Growth phase: full radar, alerts, AI copilot and MT5/TV files are free.\n"
            "🧠 Daily education · 🌍 6-language mini app, no install"
        ),
        "start_tail": "start=channel_en",
        "welcome": (
            "👋 *Welcome to TradeGuard*\n\n"
            "Live funding and Open Interest radar, risk-management education, and the tools behind them.\n"
            "🎁 Everything is free during the growth phase — full radar, alerts, AI copilot, MT5 and TradingView files.\n\n"
            "👇 Open the 6-language mini app (nothing to install):"
        ),
        "btn": "🚀 Open the mini app",
    },
    "fa": {
        "title": "TradeGuard — رادار ریسک بازار",
        "desc": (
            "📡 رادار زندهٔ فاندینگ و OI آن‌چین + آموزش مدیریت ریسک برای تریدر پراپ.\n"
            "🎁 دورهٔ رشد: رادار کامل، هشدارها، مربی AI و فایل MT5/TV رایگان است.\n"
            "🧠 آموزش روزانه · 🌍 مینی‌اپ ۶ زبانه بدون نصب"
        ),
        "start_tail": "start=channel",
        "welcome": (
            "👋 *به کانال TradeGuard خوش آمدید*\n\n"
            "اینجا رادار زندهٔ فاندینگ و OI آن‌چین، آموزش مدیریت ریسک و معرفی ابزارها را می‌بینید.\n"
            "🎁 این روزها همه‌چیز رایگان است.\n\n👇 مینی‌اپ ۶ زبانه، بدون نصب:"
        ),
        "btn": "🚀 باز کردن مینی‌اپ",
    },
}
DESC_LIMIT = 255
TITLE_LIMIT = 128


def env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


def api(method: str, payload: dict, token: str, timeout: float = 25.0) -> dict:
    """فراخوانی JSON سادهٔ Bot API."""
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="ignore")
        try:
            return json.loads(raw)
        except Exception:
            return {"ok": False, "description": raw[:200]}
    except Exception as exc:  # network
        return {"ok": False, "description": str(exc)}


def api_upload_photo(chat_id: str, path: Path, token: str) -> dict:
    """setChatPhoto با multipart (تنها راه آپلود عکس از پایتون استاندارد)."""
    if not path.exists():
        return {"ok": False, "description": f"avatar not found: {path.name}"}
    boundary = f"----TGProfile{uuid.uuid4().hex}"
    parts: list[bytes] = []
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{chat_id}\r\n".encode())
    ctype = mimetypes.guess_type(path.name)[0] or "image/png"
    parts.append(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"avatar{path.suffix}\"\r\n"
        f"Content-Type: {ctype}\r\n\r\n".encode()
    )
    parts.append(path.read_bytes() + b"\r\n")
    parts.append(f"--{boundary}--".encode())
    body = b"".join(parts)
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/setChatPhoto",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return {"ok": False, "description": exc.read().decode("utf-8", errors="ignore")[:200]}
    except Exception as exc:
        return {"ok": False, "description": str(exc)}


def debug_db() -> None:
    """گزارش تشخیصی امن: فقط کلیدهای تنظیمات، بدون مقدار حساس."""
    print(f"::notice::DEBUG DB: {DB_PATH.name} exists={DB_PATH.exists()}")
    if not DB_PATH.exists():
        base = HERE / ".dbcache"
        print(f"::notice::DEBUG .dbcache exists={base.exists()}")
        if base.exists():
            for f in sorted(base.iterdir()):
                print(f"::notice::DEBUG file {f.name} {f.stat().st_size}B")
        return
    try:
        with sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True) as conn:
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            print(f"::notice::DEBUG tables: {','.join(tables)}")
            if "settings" in tables:
                keys = [r[0] for r in conn.execute("SELECT key FROM settings ORDER BY key")]
                print(f"::notice::DEBUG settings keys({len(keys)}): {','.join(keys[:20])}")
                for k in ("PUBLIC_CHANNEL_ID", "PUBLIC_CHANNEL_EN_ID"):
                    row = conn.execute("SELECT value FROM settings WHERE key = ?", (k,)).fetchone()
                    print(f"::notice::DEBUG {k}={row[0] if row else 'NONE'}")
    except Exception as exc:
        print(f"::error title=DEBUG DB read failed::{exc}")


def setting(key: str) -> str:
    """خواندن تنظیمات از دیتابیس رمزگشایی‌شده (اگر وجود داشته باشد)."""
    if not DB_PATH.exists():
        return ""
    try:
        with sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True) as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return str(row[0]) if row and row[0] else ""
    except Exception:
        return ""


def bot_status(token: str, channel: str, bot_id) -> tuple[str, dict]:
    """وضعیت ربات در یک کانال: ('administrator'|'member'|'?' , rights)."""
    if not bot_id:
        return "?", {}
    res = api("getChatMember", {"chat_id": channel, "user_id": bot_id}, token)
    if not res.get("ok"):
        return "?", {}
    member = res.get("result") or {}
    return str(member.get("status") or "?"), member


def probe_candidates(candidates: list[str], token: str, bot_id) -> tuple[str, list[str]]:
    """چند نام را امتحان می‌کند و اولین کانالی را برمی‌گرداند که ربات در آن ادمین است.

    چرا؟ چون Bot API فهرست «کانال‌های من» را نمی‌دهد. فقط کانال‌هایی پذیرفته
    می‌شوند که همین ربات در آن‌ها ادمین است، پس امکان دست‌زدن به کانال غریبه صفر است.
    """
    log: list[str] = []
    for cand in candidates:
        cand = cand.strip()
        if not cand:
            continue
        if not cand.startswith("@") and not cand.lstrip("-").isdigit():
            cand = "@" + cand
        info = api("getChat", {"chat_id": cand}, token)
        if not info.get("ok"):
            log.append(f"   ✖ {cand}: {(info.get('description') or '')[:60]}")
            continue
        chat = info.get("result") or {}
        status, member = bot_status(token, cand, bot_id)
        title = chat.get("title") or "?"
        if status in ("administrator", "creator"):
            log.append(f"   ✅ {cand}: «{title}» — ربات {status}")
            return cand, log
        log.append(f"   ⚠ {cand}: «{title}» وجود دارد ولی ربات ادمین نیست ({status})")
    return "", log


def resolve_channel(lang: str) -> tuple[str, str]:
    """کانال مقصد: ورودی دستی، وگرنه تنظیمات ذخیره‌شدهٔ ربات."""
    given = env("CHANNEL")
    if given:
        return given, "ورودی workflow"
    key = "PUBLIC_CHANNEL_EN_ID" if lang == "en" else "PUBLIC_CHANNEL_ID"
    stored = setting(key)
    if stored:
        return stored, f"دیتابیس ({key})"
    alt = env("PUBLIC_CHANNEL_EN_ID" if lang == "en" else "PUBLIC_CHANNEL_ID")
    if alt:
        return alt, "متغیر محیطی"
    return "", ""


def describe(chat: dict) -> dict:
    return {
        "title": chat.get("title") or chat.get("username") or "",
        "username": chat.get("username") or "",
        "desc_len": len(str(chat.get("description") or "")),
        "has_photo": bool(chat.get("photo")),
        "has_pin": bool(chat.get("pinned_message")),
        "type": chat.get("type") or "",
    }


def main() -> int:
    lang = env("LANG", "en").lower()
    if lang not in TEXTS:
        lang = "en"
    t = TEXTS[lang]
    apply_changes = env("APPLY", "0") in ("1", "true", "yes")
    force = env("FORCE", "0") in ("1", "true", "yes")
    token = env("BOT_TOKEN")
    if not token:
        print("::error title=بدون توکن::BOT_TOKEN تنظیم نشده است.")
        return 2

    if env("DEBUG", "0") in ("1", "true", "yes"):
        debug_db()
    channel, source = resolve_channel(lang)
    bot_id = (api("getMe", {}, token).get("result") or {}).get("id")
    if "," in channel or (source == "ورودی workflow" and not channel.startswith("@")):
        candidates = [c for c in channel.replace("\n", ",").split(",") if c.strip()]
        if len(candidates) > 1 or "," in channel:
            print(f"🔎 {len(candidates)} نام کاندید بررسی می‌شود…")
            channel, probe_log = probe_candidates(candidates, token, bot_id)
            print("\n".join(probe_log))
            if not channel:
                print("::error title=هیچ کاندیدی تأیید نشد::ربات در هیچ‌کدام از این کانال‌ها ادمین نیست.")
                return 6
            source = "کاندید تأییدشده"
    print(f"🌍 زبان: {lang} · کانال: {channel or '—'} · منبع: {source or '—'}")
    if not channel:
        print("::error title=کانال پیدا نشد::نه ورودی CHANNEL بود و نه PUBLIC_CHANNEL_* در دیتابیس.")
        print("::notice::کانال را دستی بده: workflow را با channel=@your_channel اجرا کن.")
        return 3

    info = api("getChat", {"chat_id": channel}, token)
    if not info.get("ok"):
        print(f"::error title=کانال خوانده نشد::{(info.get('description') or '')[:160]}")
        return 4
    chat = info.get("result") or {}
    cur = describe(chat)
    print("📋 وضعیت فعلی:")
    print(f"::notice::وضعیت فعلی · عنوان: {cur['title']}")
    print(f"::notice::وضعیت فعلی · یوزرنیم: @{cur['username']}" if cur["username"] else "   • یوزرنیم: — (خصوصی)")
    print(f"::notice::وضعیت فعلی · توضیحات: {cur['desc_len']} کاراکتر")
    print(f"::notice::وضعیت فعلی · عکس: {'YES' if cur['has_photo'] else 'NO'} · پین: {'YES' if cur['has_pin'] else 'NO'}")

    me = api("getChatMember", {"chat_id": channel, "user_id": (api("getMe", {}, token).get("result") or {}).get("id")}, token)
    member = (me.get("result") or {}) if me.get("ok") else {}
    rights = member.get("status") or "?"
    can_info = bool(member.get("can_change_info"))
    can_pin = bool(member.get("can_pin_messages"))
    can_post = bool(member.get("can_post_messages"))
    print(f"::notice::دسترسی ربات: {rights} · تغییر اطلاعات: {'YES' if can_info else 'NO'}"
          f" · پین: {'✅' if can_pin else '❌'} · ارسال: {'✅' if can_post else '❌'}")

    if rights not in ("administrator", "creator"):
        print("::error title=ربات ادمین نیست::ربات باید ادمین کانال باشد تا بتواند پروفایل را ست کند.")
        return 5

    desired_desc = t["desc"]
    bot_user = (api("getMe", {}, token).get("result") or {}).get("username") or "TradeGuard1_bot"
    tail = f"\n👇 {'Start' if lang == 'en' else 'شروع'}: t.me/{bot_user}?{t['start_tail']}"
    desired_desc = (desired_desc + tail)[:DESC_LIMIT]
    desired_title = t["title"][:TITLE_LIMIT]

    results: list[tuple[str, bool, str]] = []

    def step(label: str, need: bool, fn) -> None:
        if not need:
            results.append((label, True, "از قبل درست بود"))
            return
        if not apply_changes:
            results.append((label, True, "فقط پیشنهاد (APPLY=0)"))
            return
        res = fn()
        ok = bool(res.get("ok"))
        results.append((label, ok, "" if ok else str(res.get("description") or "")[:120]))

    title_needed = force or (desired_title.lower() not in (cur["title"] or "").lower()
                             and "tradeguard" not in (cur["title"] or "").lower())
    step("📝 عنوان", title_needed, lambda: api("setChatTitle", {"chat_id": channel, "title": desired_title}, token))
    step("🧾 توضیحات", force or cur["desc_len"] < 40,
         lambda: api("setChatDescription", {"chat_id": channel, "description": desired_desc}, token))
    step("🖼 عکس پروفایل", force or not cur["has_photo"],
         lambda: api_upload_photo(channel, AVATAR, token))

    def pin_welcome() -> dict:
        sent = api("sendMessage", {
            "chat_id": channel,
            "text": t["welcome"],
            "parse_mode": "Markdown",
            "reply_markup": {"inline_keyboard": [[{"text": t["btn"],
                                                   "url": f"https://t.me/{bot_user}?{t['start_tail']}"}]]},
        }, token)
        if not sent.get("ok"):
            return sent
        mid = (sent.get("result") or {}).get("message_id")
        if not mid:
            return {"ok": False, "description": "message_id missing"}
        return api("pinChatMessage", {"chat_id": channel, "message_id": mid, "disable_notification": True}, token)

    repin = env("REPIN", "0") in ("1", "true", "yes")
    step("📌 پیام خوش‌آمد + پین", not cur["has_pin"] or (force and repin), pin_welcome)

    print("\n🧾 نتیجه:")
    failed = 0
    for label, ok, detail in results:
        print(f"::notice::{'OK' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))
        if not ok:
            failed += 1

    if not apply_changes:
        print("\nℹ️ APPLY=0 بود؛ هیچ تغییری اعمال نشد.")
        print(f"   عنوان پیشنهادی: {desired_title}")
        print(f"   توضیحات پیشنهادی ({len(desired_desc)} کاراکتر):\n{desired_desc}")
        return 0

    after = describe((api("getChat", {"chat_id": channel}, token).get("result") or {}))
    print("\n📋 وضعیت بعد از تغییر:")
    print(f"::notice::بعد از تغییر · عنوان: {after['title']}")
    print(f"   • یوزرنیم: @{after['username']}" if after["username"] else "   • یوزرنیم: — (خصوصی)")
    print(f"::notice::بعد از تغییر · توضیحات: {after['desc_len']} کاراکتر")
    print(f"::notice::بعد از تغییر · عکس: {'YES' if after['has_photo'] else 'NO'} · پین: {'YES' if after['has_pin'] else 'NO'}")
    print(f"::notice::لینک عمومی: https://t.me/{after['username']}" if after["username"] else "")
    print("\n🔗 یوزرنیم کانال را فقط Bot API نمی‌تواند عوض کند؛ آن را مالک در تلگرام ست می‌کند.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
