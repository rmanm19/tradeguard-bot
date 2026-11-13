#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سلف‌تست آفلاین TradeGuard
=========================
بدون اینترنت، بدون توکن واقعی، بدون پکیج خارجی.

    python selftest_offline.py

تمام تماس‌های تلگرام و صرافی‌ها با نسخه تقلبی جایگزین می‌شوند تا فقط
«سلامت منطق ربات» بررسی شود: ساخت دیتابیس، ثبت کاربر، منوها، اشتراک پرو،
دعوت دوستان، پرداخت Stars، دستورات /radar /scan /consistency /admin.

اگر این تست سبز شد، یعنی هر خطایی در GitHub Actions به توکن/شبکه مربوط است،
نه به کد.
"""

import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# توکن تقلبی — هیچ تماس واقعی زده نمی‌شود
os.environ["BOT_TOKEN"] = "123456789:AAtest-token-not-real-000000000000"
os.environ.pop("TG_DB_KEY", None)
os.environ.pop("ADMIN_USER_ID", None)
os.environ.pop("AI_API_KEY", None)
os.environ.pop("PRO_STATUS_PUSH", None)   # تست هرگز به ریپو پوش نمی‌کند
_STATUS_TMP = Path(tempfile.mkdtemp()) / "pro_users.json"
os.environ["PRO_STATUS_PATH"] = str(_STATUS_TMP)

import bot  # noqa: E402  (بعد از تنظیم متغیرها import می‌شود)

# در CI، FREE_MODE=1 از محیط می‌آید؛ تست باید از حالت پیش‌فرضِ خاموش شروع کند
# تا مسیر پرداخت هم بررسی شود (بخش «۷ه» خودش روشن/خاموش می‌کند).
bot.FREE_MODE = False

FAILS = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  ✅ {name}")
    else:
        print(f"  ❌ {name} {detail}")
        FAILS.append(name)


# ── جایگزینی شبکه ────────────────────────────────────────────────
SENT = []          # (api_method, payload)
# وضعیت کانال جعلی؛ تست‌ها می‌توانند آن را عوض کنند (پین/توضیحات/عکس)
CHAT_STATE = {"pinned_message": {"message_id": 42}, "description": "", "photo": None}
DOWNLOADS = []     # (chat_id, filename)


def fake_http_json(url, method="GET", payload=None, headers=None, timeout=12.0):
    api = url.rsplit("/", 1)[-1] if "api.telegram.org" in url else ""
    if api:
        SENT.append((api, payload or {}))
        if api == "getMe":
            return {"ok": True, "result": {"id": 987654321, "username": "TradeGuardTestBot", "is_bot": True}}
        if api == "getUpdates":
            return {"ok": True, "result": []}
        if api == "getChat":
            chat = {"id": -100123, "type": "channel", "title": "Test", "username": "testchannel"}
            if CHAT_STATE.get("pinned_message"):
                chat["pinned_message"] = CHAT_STATE["pinned_message"]
            if CHAT_STATE.get("description"):
                chat["description"] = CHAT_STATE["description"]
            if CHAT_STATE.get("photo"):
                chat["photo"] = CHAT_STATE["photo"]
            return {"ok": True, "result": chat}
        if api == "getChatMemberCount":
            return {"ok": True, "result": 1234}
        if api == "getChatMember":
            return {"ok": True, "result": {"status": "administrator",
                                           "can_post_messages": True, "can_pin_messages": True}}
        return {"ok": True, "result": {"message_id": len(SENT)}}
    # صرافی‌ها / AI — داده‌ی نمونه برمی‌گردانیم
    if "hyperliquid" in url:
        return [{"universe": [{"name": "BTC"}, {"name": "ETH"}]},
                [{"funding": "0.000125", "openInterest": "1000", "markPx": "60000"},
                 {"funding": "0.0008", "openInterest": "5000", "markPx": "3000"}]]
    if "okx.com" in url:
        return {"data": [{"fundingRate": "0.0005"}]}
    if "dexscreener" in url:
        return {"pairs": [{"chainId": "ethereum", "priceUsd": "0.000012",
                           "liquidity": {"usd": 250000},
                           "baseToken": {"symbol": "PEPE", "address": "0x6982508145454ce325ddbe47a25d4ec3d2311933"}}]}
    if "gopluslabs" in url:
        return {"result": {"0x6982": {"is_honeypot": "0", "buy_tax": "0", "sell_tax": "0.05"}}}
    if "alternative.me" in url:
        return {"data": [{"value": "63", "value_classification": "Greed"}]}
    return {}


def fake_send_document(chat_id, file_path, filename, caption=""):
    DOWNLOADS.append((chat_id, filename))
    return {"ok": True}


bot.http_json = fake_http_json
bot.tg_send_document = fake_send_document

# دیتابیس و .env موقت تا فایل‌های واقعی ربات دست نخورند
tmpdir = tempfile.mkdtemp(prefix="tgtest-")
bot.DB_PATH = Path(tmpdir) / "tradeguard.db"
bot.ENV_PATH = Path(tmpdir) / ".env"

ADMIN = 555000111
USER = 777000222
FRIEND = 888000333


def msg(text: str, uid: int = USER, lang: str = "fa") -> dict:
    return {
        "message_id": 1,
        "date": 0,
        "chat": {"id": uid, "type": "private"},
        "from": {"id": uid, "is_bot": False, "first_name": "Test", "language_code": lang},
        "text": text,
    }


def last_text() -> str:
    for api, payload in reversed(SENT):
        if api in ("sendMessage", "sendDocument", "editMessageText"):
            return str(payload.get("text") or payload.get("caption") or "")
    return ""


def count(api: str) -> int:
    return sum(1 for a, _ in SENT if a == api)


print("\n🧪 TradeGuard — سلف‌تست آفلاین\n")

print("۱) دیتابیس")
bot.init_db()
check("init_db بدون خطا", bot.DB_PATH.exists(), str(bot.DB_PATH))

print("\n۲) /start و ثبت کاربر")
bot.handle_message(msg("/start"))
check("پیام خوش‌آمد ارسال شد", count("sendMessage") >= 1)
check("متن خوش‌آمد فارسی است", "تریدگارد" in last_text().upper() or "TradeGuard" in last_text() or "خوش" in last_text())
with bot._db_lock:
    import sqlite3
    with sqlite3.connect(bot.DB_PATH) as conn:
        users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
check("کاربر در دیتابیس ثبت شد", users == 1, f"users={users}")

print("\n۳) زبان‌ها")
for code in ("en", "ru", "ar", "tr", "es"):
    n = len(SENT)
    bot.handle_message(msg("/start", uid=900000 + hash(code) % 1000, lang=code))
    check(f"زبان {code}", len(SENT) > n)

bot.handle_message(msg("/lang"))
check("منوی زبان با دکمه‌ها", "inline_keyboard" in str(SENT[-1][1].get("reply_markup")))
bot.handle_callback({"id": "cb1", "from": {"id": USER}, "data": "setlang_en",
                     "message": {"message_id": 5, "chat": {"id": USER}}})
check("تغییر زبان به en", bot.get_user_lang(USER) == "en")

print("\n۴) دستورات تحلیلی")
bot.handle_message(msg("/radar"))
check("/radar پاسخ داد", "sendMessage" in [a for a, _ in SENT])
bot.handle_message(msg("/scan PEPE"))
check("/scan پاسخ داد", count("sendMessage") > 0)
bot.handle_message(msg("/consistency 1200 600 40"))
check("/consistency محاسبه کرد", "Consistency" in last_text())
bot.handle_message(msg("/lot 10000 1 20"))
check("/lot محاسبه کرد", "Lot" in last_text() or "lot" in last_text())
bot.handle_message(msg("/guard"))
check("/guard پاسخ داد", count("sendMessage") > 0)
bot.handle_message(msg("/ai"))
check("/ai پاسخ داد (حالت بدون کلید AI)", count("sendMessage") > 0)

print("\n۵) پرو، فایل‌ها و پرداخت Stars")
bot.handle_message(msg("/pro"))
check("اینویس Stars ساخته شد", count("sendInvoice") >= 1, f"sendInvoice={count('sendInvoice')}")

payment = {
    "message_id": 9,
    "date": 0,
    "chat": {"id": USER, "type": "private"},
    "from": {"id": USER, "is_bot": False, "first_name": "Test", "language_code": "en"},
    "successful_payment": {"currency": "XTR", "total_amount": bot.SUBSCRIPTION_STARS,
                           "telegram_payment_charge_id": "test-charge-123"},
}
bot.handle_message(payment)
pro, exp = bot.is_user_pro(USER)
check("اشتراک PRO فعال شد", pro, f"pro={pro}")

# همان پرداخت باید وضعیت را برای مینی‌اپ هم منتشر کند
_status = __import__("json").loads(_STATUS_TMP.read_text(encoding="utf-8")) if _STATUS_TMP.exists() else {}
_key = bot.pro_status_key(USER)
check("بعد از پرداخت، فایل وضعیت مینی‌اپ به‌روز شد",
      int((_status.get("users", {}).get(_key) or {}).get("exp", 0)) > 0,
      str(list(_status.get("users", {}).keys())))

n_dl = len(DOWNLOADS)
for data in ("download_ea", "download_pine"):
    bot.handle_callback({"id": f"cb-{data}", "from": {"id": USER}, "data": data,
                         "message": {"message_id": 6, "chat": {"id": USER}}})
check("ارسال فایل .mq5 و .pine از دکمه‌های شیشه‌ای", len(DOWNLOADS) - n_dl == 2,
      f"downloads={DOWNLOADS[n_dl:]}")
check("نام فایل‌ها درست است",
      sorted(n for _, n in DOWNLOADS[n_dl:]) == ["TradeGuard_PropProtector.mq5", "TradeGuard_SmartRadar.pine"],
      str(DOWNLOADS[n_dl:]))

bot.handle_message(payment)  # پرداخت تکراری
with bot._db_lock:
    with sqlite3.connect(bot.DB_PATH) as conn:
        pays = conn.execute("SELECT COUNT(*) FROM payments").fetchone()[0]
check("پرداخت تکراری دوبار ثبت نشد", pays == 1, f"payments={pays}")

print("\n۶) موتور دعوت (۳ دوست = پرو رایگان)")
for i, friend in enumerate((FRIEND, FRIEND + 1, FRIEND + 2), start=1):
    bot.handle_message(msg(f"/start ref_{USER}", uid=friend))
cnt, unlocked = bot.get_user_referral_stats(USER)
check("شمارش دعوت‌ها", cnt == 3, f"count={cnt}")
check("پرو رایگان فعال شد", unlocked)

print("\n۷) امنیت پنل مدیر")
# بدون ADMIN_USER_ID: هیچ‌کس (جز اولین کاربر) نباید به پنل و دستورات مدیریتی دسترسی داشته باشد
before = count("sendMessage")
bot.handle_message(msg("/admin", uid=ADMIN))
check("کاربر عادی از پنل منع شد", count("sendMessage") > before and bot.ADMIN_USER_ID == "", f"admin={bot.ADMIN_USER_ID!r}")
before = count("sendMessage")
bot.handle_message(msg("/broadcast سلام به همه", uid=ADMIN))
check("ارسال همگانی برای غیرادمین قفل است", "✅" not in last_text())

bot.handle_message(msg("/admin"))  # USER اولین کاربر ربات است
check("اولین کاربر پنل را می‌بیند", "پنل" in last_text() or count("sendMessage") > before)
bot.handle_callback({"id": "cb-claim", "from": {"id": USER}, "data": "claim_admin",
                     "message": {"message_id": 7, "chat": {"id": USER}}})
check("ادعای ادمینی اولین کاربر ثبت شد", bot.ADMIN_USER_ID == str(USER), f"admin={bot.ADMIN_USER_ID!r}")

before = count("sendMessage")
bot.handle_callback({"id": "cb-claim2", "from": {"id": 424242}, "data": "claim_admin",
                     "message": {"message_id": 8, "chat": {"id": 424242}}})
check("ادمین دوم نمی‌تواند ربات را تصاحب کند", bot.ADMIN_USER_ID == str(USER))

before = count("sendMessage")
bot.handle_message(msg("/price 500", uid=424242))
check("/price برای غیرادمین قفل است", bot.SUBSCRIPTION_STARS != 500)
bot.handle_message(msg("/price 500"))
check("/price برای ادمین کار می‌کند", bot.SUBSCRIPTION_STARS == 500, f"price={bot.SUBSCRIPTION_STARS}")
bot.handle_message(msg("/seturl https://tg.mydomain.ir/app"))
check("/seturl توسط ادمین ذخیره شد", bot.get_setting("MINI_APP_URL") == "https://tg.mydomain.ir/app")

print("\n۷ب) پایداری تنظیمات بعد از ری‌استارت (سناریوی GitHub Actions)")
bot.ADMIN_USER_ID = ""
bot.MINI_APP_URL = "https://example.com"
bot.SUBSCRIPTION_STARS = 300
bot.apply_persisted_settings()
check("ادمین از دیتابیس بازیابی شد", bot.ADMIN_USER_ID == str(USER), f"admin={bot.ADMIN_USER_ID!r}")
check("قیمت از دیتابیس بازیابی شد", bot.SUBSCRIPTION_STARS == 500, f"price={bot.SUBSCRIPTION_STARS}")
check("لینک مینی‌اپ از دیتابیس بازیابی شد", bot.MINI_APP_URL == "https://tg.mydomain.ir/app")

print("\n۷ج) تفکیک واقعی منوی ادمین از منوی کاربر")

def kb_buttons(payload):
    kb = (payload or {}).get("reply_markup") or {}
    return [b for row in (kb.get("inline_keyboard") or []) for b in row]

def cb(data, uid):
    bot.handle_callback({"id": f"cb-{data}", "from": {"id": uid}, "data": data,
                         "message": {"message_id": 11, "chat": {"id": uid}}})

# --- منوی کاربر عادی ---
SENT.clear()
bot.handle_message(msg("/start", uid=424242))
user_btns = kb_buttons(SENT[-1][1] if SENT else {})
check("منوی کاربر عادی هیچ دکمه‌ی مدیریتی ندارد",
      not any(b.get("callback_data") == "admin_panel" for b in user_btns),
      str([b.get("callback_data") for b in user_btns]))
check("منوی کاربر عادی دکمه خرید دارد",
      any(b.get("callback_data") == "buy_pro" for b in user_btns))

# --- منوی ادمین ---
SENT.clear()
bot.handle_message(msg("/start"))
admin_btns = kb_buttons(SENT[-1][1] if SENT else {})
check("منوی ادمین دکمه «پنل مدیریت مؤسس» دارد",
      any(b.get("callback_data") == "admin_panel" for b in admin_btns))

# --- /admin برای غیرادمین ---
SENT.clear()
bot.handle_message(msg("/admin", uid=424242))
check("/admin برای غیرادمین باز نمی‌شود", "پنل مدیریت مؤسس" not in last_text())
check("به غیرادمین پیام رد دسترسی داده شد", "دسترسی" in last_text() or "مؤسس" in last_text())

# --- کال‌بک‌های ادمین برای غیرادمین ---
SENT.clear()
cb("adm_stats", 424242)
check("کال‌بک adm_stats برای غیرادمین اجرا نمی‌شود", "آمار کاربران" not in last_text())
check("به غیرادمین هشدار کال‌بک داده شد", any(a == "answerCallbackQuery" for a, _ in SENT))

# --- پنل ادمین و همه زیرصفحه‌ها ---
SENT.clear()
bot.handle_message(msg("/admin"))
check("پنل مؤسس باز شد", "پنل مدیریت مؤسس" in last_text())
sections = [("adm_stats", "آمار کاربران"), ("adm_revenue", "درآمد و فروش"),
            ("adm_users", "۱۰ کاربر آخر"), ("adm_health", "سلامت سیستم"),
            ("adm_channel", "کانال ویترین"), ("adm_url", "لینک مینی‌اپ"),
            ("adm_help_grant", "گرنت پرو"), ("adm_help_broadcast", "پیام همگانی")]
for data_key, marker in sections:
    SENT.clear()
    cb(data_key, USER)
    check(f"بخش {data_key} → «{marker}»", marker in last_text(), last_text()[:60])

# --- بازگشت به نمای کاربر ---
SENT.clear()
cb("user_view", USER)
back_btns = kb_buttons(SENT[-1][1] if SENT else {})
check("نمای کاربر از پنل، منوی کاربر را برمی‌گرداند",
      any(b.get("callback_data") == "radar" for b in back_btns))

# --- /id ---
SENT.clear()
bot.handle_message(msg("/id"))
check("/id شناسه عددی را نشان می‌دهد", str(USER) in last_text())

print("\n۷د) خرید Stars و دعوت واقعی (مسیر مینی‌اپ)")
import hashlib as _hashlib

# --- deep-link خرید: /start pro باید فاکتور بفرستد ---
BUYER = USER + 9000          # کاربر تازه (کاربر قبلی در تست پرداخت، پرو شده است)
SENT.clear()
bot.handle_message(msg("/start pro", uid=BUYER))
invoices = [pl for api, pl in SENT if api == "sendInvoice"]
check("/start pro فاکتور Stars می‌فرستد", len(invoices) == 1, f"sendInvoice×{len(invoices)}")
if invoices:
    inv = invoices[0]
    check("فاکتور با ارز XTR است", inv.get("currency") == "XTR", str(inv.get("currency")))
    check("قیمت فاکتور با SUBSCRIPTION_STARS یکی است",
          (inv.get("prices") or [{}])[0].get("amount") == bot.SUBSCRIPTION_STARS)
    check("payload فاکتور قابل تشخیص است", str(inv.get("payload", "")).startswith("tradeguard_pro"))
    check("provider_token برای Stars خالی است", inv.get("provider_token") == "")

# --- alias های دیگر ---
for alias in ("/start buy", "/buy", "/pro"):
    SENT.clear()
    bot.handle_message(msg(alias, uid=BUYER))
    check(f"«{alias}» هم فاکتور می‌فرستد", any(api == "sendInvoice" for api, _ in SENT))

# کاربری که از قبل پرو است به‌جای فاکتور تکراری، وضعیتش را می‌بیند
SENT.clear()
bot.handle_message(msg("/start pro", uid=USER))
check("کاربر پرو فاکتور تکراری نمی‌گیرد، وضعیتش را می‌بیند",
      not any(api == "sendInvoice" for api, _ in SENT) and "PRO" in last_text().upper())

# --- deep-link دعوت: لینک واقعی با آیدی خودِ کاربر ---
SENT.clear()
bot.handle_message(msg("/start invite", uid=USER))
txt = last_text()
ref_link = bot.invite_link(USER)
check("لینک دعوت با آیدی کاربر ساخته می‌شود", ref_link.endswith(f"?start=ref_{USER}"), ref_link)
check("/start invite لینک اختصاصی را می‌فرستد", ref_link in txt or f"start=ref_{USER}" in txt, txt[:80])
check("پیام دعوت پیشرفت واقعی را نشان می‌دهد",
      ("0" in txt) and ("3" in txt) and any(
          w in txt.lower() for w in ("دعوت", "invite", "referral", "davet", "приглаш", "دعو", "invit")),
      txt[:80])
SENT.clear()
bot.handle_message(msg("/invite", uid=USER))
check("دستور /invite هم لینک می‌دهد", f"start=ref_{USER}" in last_text())

# --- /status وضعیت واقعی را می‌گوید ---
SENT.clear()
bot.handle_message(msg("/status", uid=USER))
_st = last_text()
check("/status وضعیت اشتراک را نشان می‌دهد",
      ("PRO" in _st.upper()) and any(ch.isdigit() for ch in _st), _st[:80])

# --- pre_checkout: فقط فاکتور خود ربات تأیید می‌شود ---
SENT.clear()
bot.process_update({"update_id": 1, "pre_checkout_query": {
    "id": "pcq-ok", "invoice_payload": f"tradeguard_pro_30d_{bot.SUBSCRIPTION_STARS}",
    "currency": "XTR", "total_amount": bot.SUBSCRIPTION_STARS}})
answers = [pl for api, pl in SENT if api == "answerPreCheckoutQuery"]
check("pre_checkout معتبر تأیید می‌شود", answers and answers[-1].get("ok") is True, str(answers[-1:]))
SENT.clear()
bot.process_update({"update_id": 2, "pre_checkout_query": {
    "id": "pcq-bad", "invoice_payload": "hacker_payload", "currency": "XTR", "total_amount": 1}})
answers = [pl for api, pl in SENT if api == "answerPreCheckoutQuery"]
check("pre_checkout جعلی رد می‌شود", answers and answers[-1].get("ok") is False, str(answers[-1:]))

# --- وضعیت پرو برای مینی‌اپ (فایل عمومی، بدون آیدی خام) ---
tmp_status = Path(tempfile.mkdtemp()) / "pro_users.json"
old_status_file = bot.PRO_STATUS_FILE
bot.PRO_STATUS_FILE = tmp_status
bot.publish_pro_status([USER])
raw = tmp_status.read_text(encoding="utf-8")
data = __import__("json").loads(raw)
key = _hashlib.sha256(("tg-pro:" + str(USER)).encode()).hexdigest()[:16]
check("فایل وضعیت پرو ساخته می‌شود", isinstance(data.get("users"), dict), raw[:60])
check("کلید کاربر هش است، نه آیدی خام", key in data["users"] and str(USER) not in raw)
check("کاربر پرو در فایل exp دارد", int((data["users"].get(key) or {}).get("exp", 0)) > 0)
check("کلید pro_status_key با الگوریتم مینی‌اپ یکی است", bot.pro_status_key(USER) == key)
# بعد از انقضا باید حذف شود
with bot._db_lock, __import__("sqlite3").connect(bot.DB_PATH) as _c:
    _c.execute("UPDATE users SET pro_until = 0, referrals_count = 0 WHERE user_id = ?", (USER,))
bot.publish_pro_status([USER])
data2 = __import__("json").loads(tmp_status.read_text(encoding="utf-8"))
check("کاربر بدون پرو و بدون دعوت از فایل حذف می‌شود", key not in data2.get("users", {}), str(data2)[:60])
bot.PRO_STATUS_FILE = old_status_file

print("\n۷ه) دورهٔ رایگان (FREE_MODE) و ارتقای کانال")

# --- خاموش: رفتار پرداختی مثل قبل ---
bot.FREE_MODE = False
SENT.clear()
bot.handle_message(msg("/buy", uid=BUYER))
check("خاموش: /buy فاکتور می‌فرستد", any(a == "sendInvoice" for a, _ in SENT))
_newbie = FRIEND + 500
check("خاموش: کاربر تازه پرو نیست", bot.is_user_pro(_newbie)[0] is False)

# --- روشن: همه دسترسی دارند، پرداخت بسته است ---
bot.set_free_mode(True)
check("روشن: free_mode_active() درست است", bot.free_mode_active())
check("روشن: کاربر تازه هم دسترسی پرو دارد", bot.is_user_pro(_newbie)[0] is True)
check("روشن: وضعیت واقعی پرداخت دست‌نخورده است", bot.is_user_pro(_newbie, access=False)[0] is False)
SENT.clear()
bot.handle_message(msg("/buy", uid=BUYER))
check("روشن: /buy فاکتور نمی‌فرستد", not any(a == "sendInvoice" for a, _ in SENT))
check("روشن: /buy پیام دورهٔ رایگان می‌دهد",
      any(w in last_text() for w in ("رایگان", "free", "Free")), last_text()[:60])
SENT.clear()
bot.handle_message(msg("/start pro", uid=BUYER))
check("روشن: deep-link pro هم پرداخت نمی‌گیرد", not any(a == "sendInvoice" for a, _ in SENT))

# منوی شیشه‌ای: دکمهٔ خرید نبود، دکمهٔ دورهٔ رایگان باشد
kb = bot.main_keyboard(True, "fa")
cbs = [b.get("callback_data") for row in kb["inline_keyboard"] for b in row]
check("روشن: دکمهٔ خرید از منو حذف شده", "buy_pro" not in cbs)
check("روشن: دکمهٔ «دورهٔ رایگان» در منو هست", "free_info" in cbs)

# فایل وضعیت: پرچم freeMode منتشر شود
bot.publish_pro_status()
_status2 = __import__("json").loads(_STATUS_TMP.read_text(encoding="utf-8"))
check("فایل وضعیت freeMode=true را منتشر می‌کند", _status2.get("freeMode") is True, str(_status2)[:60])

# --- دستور ادمین فقط برای ادمین ---
SENT.clear()
bot.handle_message(msg("/freemode off", uid=BUYER))
check("غیرادمین نمی‌تواند حالت رایگان را عوض کند", bot.FREE_MODE is True)
SENT.clear()
bot.handle_message(msg("/freemode off"))
check("ادمین حالت رایگان را خاموش می‌کند", bot.FREE_MODE is False)
_status3 = __import__("json").loads(_STATUS_TMP.read_text(encoding="utf-8"))
check("فایل وضعیت freeMode=false شد", _status3.get("freeMode") is False)
bot.set_free_mode(True)   # برای تست‌های بعدی

# --- کانال: پست و پین ---
bot.PUBLIC_CHANNEL_ID = "@testchannel"
bot.BOT_USERNAME = "TradeGuardTestBot"
check("اعتبارسنجی کانال تستی", bot.validate_channel_target(silent=True) is True)
check("لینک کانال ساخته می‌شود", bot.channel_url() == "https://t.me/testchannel", bot.channel_url())
_posts = []
bot.tg_send_message = lambda chat_id, text, **kw: (_posts.append((chat_id, text, kw)) or {"ok": True, "result": {"message_id": len(_posts)}})
SENT.clear()
bot.handle_message(msg("/channelpost"))
_chan_posts = [pp for pp in _posts if pp[0] == "@testchannel"]
_kb_btns = [b["url"] for row in (_chan_posts[-1][2].get("reply_markup", {}) if _chan_posts else {}
                                  ).get("inline_keyboard", []) for b in row]
check("پست فوری کانال ارسال شد", bool(_chan_posts), str(_chan_posts[-1:]))
check("پست کانال ۳ فرصت برتر دارد",
      bool(_chan_posts) and (_chan_posts[-1][1].count("$") >= 3 or "🥇" in _chan_posts[-1][1]),
      _chan_posts[-1][1][:60] if _chan_posts else "")
check("پست کانال دو دکمهٔ مینی‌اپ و دعوت دارد", len(_kb_btns) == 2, str(_kb_btns))
SENT.clear()
bot.handle_message(msg("/channelpin"))
_chan_posts = [pp for pp in _posts if pp[0] == "@testchannel"]
check("پیام خوش‌آمد کانال ارسال شد", bool(_chan_posts) and "خوش آمدید" in _chan_posts[-1][1],
      _chan_posts[-1][1][:60] if _chan_posts else "")
check("درخواست پین ارسال شد", any(a == "pinChatMessage" for a, _ in SENT), str([a for a, _ in SENT]))
SENT.clear()
bot.handle_message(msg("/channelpost", uid=BUYER))
check("غیرادمین نمی‌تواند در کانال پست بگذارد", not any(a == "sendMessage" for a, _ in SENT))
SENT.clear()
_posts.clear()
bot.handle_message(msg("/channelstatus"))
_st = _posts[-1][1] if _posts else ""
check("/channelstatus تعداد اعضا را از تلگرام می‌خواند", "اعضا" in _st and "۱۲۳۴" in _st, _st[:120])
check("/channelstatus ادمین‌بودن ربات را نشان می‌دهد", "ادمین" in _st and "administrator" in _st, _st[:120])
check("/channelstatus وضعیت پین را می‌گوید", "پین‌شده" in _st, _st[:120])
check("/channelstatus پست خودکار را روشن و ۳ساعته نشان می‌دهد",
      "هر ۳ ساعت" in _st and "روشن" in _st, _st[-160:])
check("/channelstatus زمان آخرین پست را نشان می‌دهد", "آخرین پست خودکار" in _st and "پیش" in _st, _st[-120:])
check("/channelstatus زمان پست بعدی را می‌گوید", "پست بعدی" in _st, _st[-160:])
_posts.clear()
bot.handle_message(msg("/channelstatus", uid=BUYER))
check("غیرادمین وضعیت کانال را نمی‌گیرد",
      "وضعیت کانال" not in " ".join(pp[1] for pp in _posts), str(_posts[-1:]))

bot.PUBLIC_CHANNEL_ID = ""
_posts.clear()
bot.handle_message(msg("/channelstatus"))
_st2 = _posts[-1][1] if _posts else ""
check("بدون کانال، /channelstatus راهنمای فعال‌سازی می‌دهد",
      "تنظیم نشده" in _st2 and "/channel" in _st2, _st2[:120])
bot.FREE_MODE = False

print("\n۸) امنیت پیکربندی")
check("MINI_APP_URL تقلبی رد می‌شود", not bot.is_real_app_url("https://example.com"))
check("MINI_APP_URL واقعی قبول می‌شود", bot.is_real_app_url("https://tg.mydomain.ir/app"))
check("کیبورد زبان ۶ گزینه دارد",
      sum(len(r) for r in bot.language_keyboard()["inline_keyboard"]) == 6)
for lang in bot.SUPPORTED_LANGS:
    missing = [k for k in bot.BOT_STRINGS["en"] if k not in bot.BOT_STRINGS[lang]]
    check(f"ترجمه {lang} کامل است", not missing, str(missing[:5]))

print("\n۹) گزارش مدیریتی")
import sqlite3 as _sqlite  # noqa: E402

bot.ADMIN_USER_ID = str(USER)
_posts.clear()
bot.handle_message(msg("/report"))
_admin_posts = [pp for pp in _posts if pp[0] == USER]
_rep = _admin_posts[-1][1] if _admin_posts else ""
check("دستور /report برای ادمین گزارش می‌فرستد", "گزارش مدیریتی" in _rep, _rep[:80])
check("گزارش تعداد کاربران را از دیتابیس می‌خواند",
      "کاربران ربات" in _rep and any(ch.isdigit() for ch in _rep), _rep[:120])
check("گزارش وضعیت دورهٔ رایگان را نشان می‌دهد", "دورهٔ رایگان" in _rep, _rep[-120:])
_users_n = _sqlite.connect(bot.DB_PATH).execute("SELECT COUNT(*) FROM users").fetchone()[0]
check("عدد کاربران گزارش دقیقاً همان دیتابیس است",
      f"*{_users_n:,}*" in _rep, f"db={_users_n} report={_rep[:120]}")
check("گزارش جای خالی/«None» ندارد", "None" not in _rep, _rep[:120])
_posts.clear()
bot.handle_message(msg("/report", uid=BUYER))
check("غیرادمین گزارش نمی‌گیرد", "گزارش مدیریتی" not in " ".join(pp[1] for pp in _posts),
      str(_posts[-1:]))
_posts.clear()
bot.handle_message(msg("/stats", uid=BUYER))
check("غیرادمین با /stats هم گزارش نمی‌گیرد",
      "گزارش مدیریتی" not in " ".join(pp[1] for pp in _posts), str(_posts[-1:]))
bot.ADMIN_USER_ID = ""

print("\n۹٫۵) موتور محتوای کانال")
import calendar as _cal  # noqa: E402
import time as _time  # noqa: E402


def ts_at_hour(hour: int) -> int:
    g = _time.gmtime()
    return _cal.timegm((g.tm_year, g.tm_mon, g.tm_mday, hour, 0, 0))


check("بازهٔ ارسال: ظهر UTC مجاز است", bot.in_post_window(ts_at_hour(12)) is True)
check("بازهٔ ارسال: نیمه‌شب UTC مجاز نیست", bot.in_post_window(ts_at_hour(23)) is False)
check("فاصلهٔ پست خودکار ۳ ساعت است", bot.CHANNEL_POST_INTERVAL_SEC == 3 * 3600,
      str(bot.CHANNEL_POST_INTERVAL_SEC))
_cats = [bot.next_channel_category() for _ in range(len(bot.CHANNEL_CYCLE))]
check("چرخهٔ محتوا همهٔ دسته‌ها را می‌پوشاند", set(_cats) == {"radar", "edu", "feature"}, str(_cats))
_wrap = bot.next_channel_category()
check("چرخه پس از یک دور به ابتدا برمی‌گردد", _wrap == _cats[0], f"{_cats[0]} vs {_wrap}")
_e1, _ekb = bot.build_edu_post()
_e2, _ = bot.build_edu_post()
check("پست آموزشی ساخته می‌شود", "🎓" in _e1 and len(_e1) > 200, _e1[:60])
check("دو پست آموزشی پشت‌سرهم تکراری نیستند", _e1 != _e2)
check("پست آموزشی دکمهٔ مینی‌اپ دارد", "t.me/" in _ekb["inline_keyboard"][0][0]["url"])
_f1, _fkb = bot.build_feature_post()
check("پست معرفی قابلیت ساخته می‌شود", len(_f1) > 150, _f1[:60])
check("پست قابلیت، دکمهٔ دعوت هم دارد", len(_fkb["inline_keyboard"]) == 2)
_all_channel_text = " ".join(t + " " + b for t, b in bot.CHANNEL_EDU_POSTS + bot.CHANNEL_FEATURE_POSTS)
check("هیچ پست کانال وعدهٔ سود تضمینی ندارد",
      "تضمین" not in _all_channel_text and "سود قطعی" not in _all_channel_text)
check("تعریف‌ها بدون داده/توصیهٔ جعلی هستند (امضای آموزش)",
      "توصیهٔ سرمایه‌گذاری نیست" in _e1)
check("زمان پست بعدی توضیح انسانی دارد", len(bot.next_post_eta()) > 5, bot.next_post_eta())
_r, _rkb = bot.build_slot_post("radar")
check("اسلات رادار، پست دادهٔ زنده می‌دهد", "$" in _r and len(_rkb["inline_keyboard"]) >= 1)

_plan = bot.channel_plan(6)
check("برنامهٔ پست‌ها ۶ اسلات نشان می‌دهد", _plan.count("\n") >= 7 and "۱." in _plan, _plan[:80])
check("برنامه هر سه دسته را دارد", "🎓" in _plan and "✨" in _plan and "📡" in _plan, _plan[:200])
_posts.clear()
bot.handle_message(msg("/channelplan", uid=BUYER))
check("غیرادمین برنامهٔ محتوا را نمی‌بیند",
      "برنامهٔ پست" not in " ".join(pp[1] for pp in _posts), str(_posts[-1:]))
bot.ADMIN_USER_ID = str(USER)   # بخش ۹ این را خالی کرده بود
_posts.clear()
bot.PUBLIC_CHANNEL_ID = "@testchannel"
bot.handle_message(msg("/channelpost edu"))
_chan_last = [pp for pp in _posts if pp[0] == "@testchannel"]
check("/channelpost edu پست آموزشی می‌فرستد",
      bool(_chan_last) and "🎓" in _chan_last[-1][1], str(_chan_last[-1:])[:120])
_posts.clear()
bot.handle_message(msg("/channelpost feature"))
_chan_last = [pp for pp in _posts if pp[0] == "@testchannel"]
check("/channelpost feature پست معرفی قابلیت می‌فرستد",
      bool(_chan_last) and "داخل تلگرام" in _chan_last[-1][1]
      and "t.me/" in str((_chan_last[-1][2].get("reply_markup") or {})),
      str(_chan_last[-1:])[:140])
bot.PUBLIC_CHANNEL_ID = ""
bot.ADMIN_USER_ID = ""

print("\n۹٫۶) تکمیل پروفایل کانال")
_desc = bot.channel_description_text()
check("توضیحات کانال از سقف ۲۵۵ کاراکتر تلگرام رد نمی‌شود", len(_desc) <= 255, str(len(_desc)))
check("توضیحات کانال، لینک مینی‌اپ دارد",
      "t.me/" in _desc and "?start=channel" in _desc and bot.BOT_USERNAME in _desc, _desc[-70:])
check("توضیحات، ارزش پیشنهادی دارد", "رادار" in _desc and "آموزش" in _desc, _desc[:80])

bot.ADMIN_USER_ID = str(USER)
bot.PUBLIC_CHANNEL_ID = "@testchannel"
CHAT_STATE.update({"pinned_message": None, "description": "", "photo": None})  # کانال ناقص
UPLOADS = []
bot.tg_set_chat_photo = lambda chat_id, path: (UPLOADS.append((chat_id, str(path))) or {"ok": True})

SENT.clear()
_posts.clear()
bot.handle_message(msg("/channelinfo"))
_info = _posts[-1][1] if _posts else ""
check("/channelinfo چک‌لیست پروفایل می‌دهد", "تکمیل پروفایل کانال" in _info, _info[:80])
check("چک‌لیست عکس و توضیحات و پین را جدا نشان می‌دهد",
      "عکس پروفایل" in _info and "توضیحات" in _info and "پین‌شده" in _info, _info[:200])
check("چک‌لیست کارهای باقی‌مانده را می‌گوید", "باقی‌مانده" in _info or "کامل است" in _info, _info[-200:])

SENT.clear()
bot.handle_message(msg("/channeldesc"))
_setdesc = [pl for api, pl in SENT if api == "setChatDescription"]
check("/channeldesc توضیحات را روی کانال ست می‌کند", bool(_setdesc), str([a for a, _ in SENT]))
check("متن ارسالی همان متن آماده است",
      bool(_setdesc) and _setdesc[0]["description"] == _desc, str(_setdesc[:1])[:120])

SENT.clear()
bot.handle_message(msg("/channeldesc کانال تستی تریدگارد — رادار و آموزش"))
_setdesc = [pl for api, pl in SENT if api == "setChatDescription"]
check("/channeldesc متن دلخواه را می‌پذیرد",
      bool(_setdesc) and "کانال تستی" in _setdesc[0]["description"], str(_setdesc[:1])[:120])

SENT.clear()
bot.handle_message(msg("/channeltitle TradeGuard | رادار"))
_title = [pl for api, pl in SENT if api == "setChatTitle"]
check("/channeltitle عنوان را ست می‌کند", bool(_title) and "TradeGuard" in _title[0]["title"],
      str([a for a, _ in SENT]))

UPLOADS.clear()
_posts.clear()
bot.handle_message(msg("/channelphoto"))
check("/channelphoto فایل لوگو را آپلود می‌کند", len(UPLOADS) == 1, str(UPLOADS))
check("مسیر لوگو واقعاً وجود دارد", bot.CHANNEL_AVATAR_PATH.exists(), str(bot.CHANNEL_AVATAR_PATH))

SENT.clear()
UPLOADS.clear()
_posts.clear()
bot.handle_message(msg("/channelcomplete"))
_api_calls = [a for a, _ in SENT]
check("/channelcomplete توضیحات را ست می‌کند", "setChatDescription" in _api_calls, str(_api_calls))
check("/channelcomplete عکس می‌گذارد", len(UPLOADS) == 1, str(UPLOADS))
check("/channelcomplete پیام خوش‌آمد را پین می‌کند",
      "pinChatMessage" in _api_calls and any(pp[0] == "@testchannel" for pp in _posts), str(_api_calls))

SENT.clear()
UPLOADS.clear()
_posts.clear()
for _cmd in ("/channeldesc", "/channelphoto", "/channelcomplete", "/channeltitle", "/channelinfo"):
    bot.handle_message(msg(_cmd, uid=BUYER))
check("غیرادمین هیچ‌کدام از دستورهای پروفایل را اجرا نمی‌کند",
      not SENT and not UPLOADS, f"{SENT[:2]} | {UPLOADS}")

bot.PUBLIC_CHANNEL_ID = ""
bot.ADMIN_USER_ID = ""
CHAT_STATE.update({"pinned_message": {"message_id": 42}, "description": "", "photo": None})

print("\n۹٫۷) شرکا / لینک همکاری")
import json as _json  # noqa: E402

_pfile = Path(tempfile.mkdtemp()) / "partners.json"
bot.PARTNERS_FILE = _pfile
_pfile.write_text(_json.dumps({"disclosure": "لینک همکاری — ممکن است کمیسیون بگیریم.",
                               "partners": [{"name": "Prop Firm X", "note": "۵۰٪ تخفیف",
                                             "url": "https://t.me/propfirm_x", "badge": "۵۰٪"}]},
                              ensure_ascii=False), encoding="utf-8")
_partners = bot.load_partners()
check("partners.json خوانده می‌شود", len(_partners["partners"]) == 1, str(_partners)[:100])
_ptext = bot.partners_text()
check("متن /partners نام شریک را دارد", "Prop Firm X" in _ptext, _ptext[:80])
check("متن /partners لینک را دارد", "https://t.me/propfirm_x" in _ptext, _ptext[:120])
check("متن /partners افشای کمیسیون دارد", "کمیسیون" in _ptext, _ptext[-80:])
_posts.clear()
bot.handle_message(msg("/partners"))
check("دستور /partners برای کاربر عادی جواب می‌دهد",
      bool(_posts) and "Prop Firm X" in _posts[-1][1], str(_posts[-1:])[:120])

_pfile.write_text(_json.dumps({"partners": []}), encoding="utf-8")
_empty = bot.partners_text()
check("بدون شریک، پیام صادقانه است", "هنوز هیچ شریکی" in _empty, _empty[:60])
_posts.clear()
bot.handle_message(msg("/partners"))
check("دستور /partners با لیست خالی هم پاسخ می‌دهد",
      bool(_posts) and "هنوز هیچ شریکی" in _posts[-1][1], str(_posts[-1:])[:120])
_pfile.unlink()
check("فایل نبودن partners.json ربات را نمی‌شکند", bot.load_partners()["partners"] == [])

print("\n۹٫۸) رهگیری کلیک لینک شرکا")
_pfile2 = Path(tempfile.mkdtemp()) / "partners.json"
bot.PARTNERS_FILE = _pfile2
_pfile2.write_text(_json.dumps({"disclosure": "لینک همکاری — کمیسیون می‌گیریم.",
                                "partners": [{"id": "propfirm_x", "name": "Prop Firm X",
                                              "note": "۵۰٪ تخفیف", "url": "https://propfirmx.example/r/tg",
                                              "badge": "۵۰٪"}]}, ensure_ascii=False), encoding="utf-8")
check("شریک با id پیدا می‌شود", (bot.partner_by_id("propfirm_x") or {}).get("name") == "Prop Firm X")
check("id ناشناس None برمی‌گرداند", bot.partner_by_id("nope") is None)
_posts.clear()
bot.handle_message(msg("/start p_propfirm_x", uid=BUYER))
_landing = [pp for pp in _posts if pp[0] == BUYER]
check("لینک شرکا در ربات پیام مقصد می‌دهد", bool(_landing) and "Prop Firm X" in _landing[-1][1],
      str(_landing[-1:])[:120])
check("دکمهٔ رفتن به سایت شریک وجود دارد",
      bool(_landing) and "propfirmx.example" in str(_landing[-1][2].get("reply_markup") or {}),
      str(_landing[-1:])[:160])
check("کلیک شریک در دیتابیس ثبت می‌شود",
      bot.get_setting("partner_start_propfirm_x") == "1", bot.get_setting("partner_start_propfirm_x"))
bot.handle_message(msg("/start p_propfirm_x", uid=BUYER))
check("کلیک دوم شمارنده را ۲ می‌کند", bot.get_setting("partner_start_propfirm_x") == "2",
      bot.get_setting("partner_start_propfirm_x"))
_summary = dict(bot.partner_click_summary())
check("خلاصهٔ کلیک‌ها شریک را نشان می‌دهد", _summary.get("propfirm_x") == 2, str(_summary))
_posts.clear()
bot.handle_message(msg("/start p_ghost", uid=BUYER))
check("لینک شرکای نامعتبر، پیام صادقانه می‌دهد",
      bool(_posts) and "معتبر نیست" in _posts[-1][1], str(_posts[-1:])[:100])
_posts.clear()
bot.ADMIN_USER_ID = str(USER)
bot.handle_message(msg("/report"))
check("گزارش مدیریتی کلیک شرکا را دارد",
      bool(_posts) and "کلیک لینک شرکا" in _posts[-1][1], str(_posts[-1:])[:120])
bot.ADMIN_USER_ID = ""

print("\n" + "─" * 46)
if FAILS:
    print(f"❌ {len(FAILS)} تست شکست خورد: {', '.join(FAILS)}")
    sys.exit(1)
print(f"✅ همه تست‌ها سبز — {len(SENT)} تماس تلگرام، {len(DOWNLOADS)} فایل")
sys.exit(0)
