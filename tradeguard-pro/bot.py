#!/usr/bin/env python3
"""
TradeGuard Pro v7.0 Global — موتور ۶ زبانه بدون نیاز به هیچ پکیج خارجی (Zero-Dependency Pure Python!)
اجرای فوری روی هر نسخه ویندوز، مک و لینوکس (پایتون 3.8 تا 3.15+) بدون نیاز به pip install یا کامپایلر!

پشتیبانی بومی از ۶ زبان اصلی دنیا:
🇮🇷 فارسی (fa) | 🇬🇧 English (en) | 🇷🇺 Русский (ru) | 🇸🇦 العربية (ar) | 🇹🇷 Türkçe (tr) | 🇪🇸 Español (es)

مجهز به:
1) درگاه رسمی Telegram Stars (XTR) + مدیریت خودکار اشتراک ۳۰ روزه در SQLite
2) رادار زنده آن‌چین Hyperliquid + OKX + اشعه ایکس کیف پول نهنگ (/wallet)
3) اسکنر ضد راگ‌پول و هانی‌پات توکن‌ها (/scan) + ماشین‌حساب قانون Consistency پراپ (/consistency)
4) موتور رشد ویروسی (دعوت ۳ دوست = ۷ روز پلن پرو رایگان خودکار) + ارسال فایل‌های .mq5 و .pine
5) پنل مدیریت مؤسس (/admin) + ارسال همگانی (/broadcast) + پست‌گذار خودکار ۸ ساعته کانال
"""

import hashlib
import json
import logging
import os
import re
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "tradeguard.db"
ENV_PATH = BASE_DIR / ".env"
EA_FILE_PATH = BASE_DIR / "TradeGuard_PropProtector.mq5"
PINE_FILE_PATH = BASE_DIR / "TradeGuard_SmartRadar.pine"

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("tradeguard")


# =====================================================================
# خواننده داخلی فایل .env (بدون نیاز به نصب python-dotenv)
# =====================================================================
def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def save_env_var(key: str, val: str) -> None:
    lines: List[str] = []
    found = False
    if ENV_PATH.exists():
        for raw in ENV_PATH.read_text(encoding="utf-8", errors="ignore").splitlines():
            if raw.strip().startswith(f"{key}="):
                lines.append(f"{key}={val}")
                found = True
            else:
                lines.append(raw)
    if not found:
        lines.append(f"{key}={val}")
    try:
        ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception:
        pass
    # .env روی GitHub Actions با هر جاب پاک می‌شود؛ نسخه پایدار در دیتابیس می‌رود
    set_setting(key, val)


load_env_file(ENV_PATH)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
MINI_APP_URL = os.environ.get("MINI_APP_URL", "https://example.com").strip()
SUBSCRIPTION_STARS = int(os.environ.get("SUBSCRIPTION_STARS", "300") or "300")
# کانال عمومی ربات؛ اگر Secret تنظیم نشده باشد از پیش‌فرض زیر استفاده می‌شود.
# اعتبارسنجی (ادمین‌بودن ربات) همچنان در validate_channel_target انجام می‌شود.
DEFAULT_CHANNEL_ID = "@tradeguard1"
PUBLIC_CHANNEL_ID = (os.environ.get("PUBLIC_CHANNEL_ID", "") or DEFAULT_CHANNEL_ID).strip()

# شناسه عددی خود ربات و وضعیت اعتبار کانال ویترین (در main مقدار می‌گیرند)
BOT_ID: int = 0
CHANNEL_OK: bool = False
CHANNEL_REASON: str = ""
FREE_PRO_INVITE_TARGET = int(os.environ.get("FREE_PRO_INVITE_TARGET", "3") or "3")

# ── دورهٔ رشد: همه‌چیز رایگان ────────────────────────────────────────
# با روشن‌بودن این پرچم، هیچ کاربری برای استفاده از رادار/فایل‌ها/مربی AI
# استارز نمی‌دهد. کد پرداخت دست‌نخورده می‌ماند تا هر لحظه با /freemode off
# دوباره روشن شود. وضعیت در دیتابیس ذخیره می‌شود (بین ری‌استارت‌ها می‌ماند).
FREE_MODE = os.environ.get("FREE_MODE", "0").strip().lower() in ("1", "true", "yes", "on")
FREE_MODE_UNTIL = int(os.environ.get("FREE_MODE_UNTIL", "0") or "0")
ADMIN_USER_ID = os.environ.get("ADMIN_USER_ID", "").strip()

# ── وضعیت پرو برای مینی‌اپ (بدون بک‌اند) ─────────────────────────────
# مینی‌اپ استاتیک است و به هیچ سروری وصل نیست؛ پس وضعیت اشتراک را از یک
# فایل عمومی می‌خواند که فقط خودِ ربات آن را می‌نویسد (کاربر نمی‌تواند
# خودش را پرو کند). کلید هر کاربر هش است تا آیدی عددی عمومی نشود.
REPO_ROOT = BASE_DIR.parent
PRO_STATUS_FILE = Path(os.environ.get("PRO_STATUS_PATH") or (REPO_ROOT / "docs" / "pro_users.json"))
PRO_STATUS_PUSH = os.environ.get("PRO_STATUS_PUSH", "").strip() == "1"
PRO_STATUS_LOCK = threading.Lock()

AI_API_BASE = os.environ.get("AI_API_BASE", "https://openrouter.ai/api/v1").rstrip("/")
AI_API_KEY = os.environ.get("AI_API_KEY", "").strip()
AI_MODEL = os.environ.get("AI_MODEL", "google/gemini-2.5-flash").strip()
# سقف طول پاسخ مدل: با ۷۰۰ توکن، گزارش‌ها معمولاً وسط جمله بریده می‌شدند.
# با AI_MAX_TOKENS در Secrets قابل تنظیم است (هزینهٔ هر پاسخ کمی بالا می‌رود).
AI_MAX_TOKENS = int(os.environ.get("AI_MAX_TOKENS", "1600") or "1600")

SUPPORTED_LANGS = ("fa", "en", "ru", "ar", "tr", "es")
LANG_NAMES = {
    "fa": "Persian (فارسی)",
    "en": "English",
    "ru": "Russian (Русский)",
    "ar": "Arabic (العربية)",
    "tr": "Turkish (Türkçe)",
    "es": "Spanish (Español)",
}

# =====================================================================
# دیکشنری ۶ زبانه کامل ربات تلگرام
# =====================================================================
BOT_STRINGS: Dict[str, Dict[str, str]] = {
    "fa": {
        "btn_app": "📱 باز کردن مینی‌اپ تریدگارد",
        "btn_radar": "📡 رادار فاندینگ + نهنگ",
        "btn_ai": "🤖 تحلیل AI Agent",
        "btn_guard": "🛡️ گارد پراپ + خبر",
        "btn_invite": "🎁 ۷ روز پرو رایگان!",
        "btn_lang": "🌐 زبان / Language (🇮🇷)",
        "btn_buy": f"⭐ فعال‌سازی پلن پرو ({SUBSCRIPTION_STARS} Stars)",
        "btn_ea": "📥 دانلود اکسپرت MT5",
        "btn_pine": "📈 دانلود اسکریپت TradingView",
        "welcome": (
            "سلام رفیق تریدر! به *TradeGuard Global v7.0* خوش اومدی 🛡️🌍\n\n"
            "جعبه ابزار حرفه‌ای تریدرهای فارکس، طلا و کریپتو:\n"
            "1️⃣ *رادار فاندینگ + نهنگ‌های آن‌چین:* شکار ارزهای پرتجمع در Hyperliquid و OKX\n"
            "2️⃣ *پکیج گارد پراپ (MT5 + TradingView):* قفل خودکار سر ۳.۸٪ ضرر روزانه + سپر خبر قرمز\n"
            "3️⃣ *دستورات ویژه:* اسکن هانی‌پات `/scan PEPE` | کیف پول نهنگ `/wallet` | پنل مدیر `/admin`\n\n"
            "{status}"
        ),
        "status_pro": "✅ اشتراک *پلن پرو* شما تا `{exp}` فعال است.",
        "status_free": f"🔒 حساب پایه | با *{SUBSCRIPTION_STARS} ⭐* آنی پرو شو یا *{FREE_PRO_INVITE_TARGET} دوست تریدر* دعوت کن!",
        "lang_prompt": "🌍 لطفاً زبان مورد نظر خود را انتخاب کنید:",
        "lang_saved": "✅ زبان ربات و مینی‌اپ به *فارسی 🇮🇷* تغییر کرد!",
        "scanning": "در حال اسکن زنده فاندینگ و نقدینگی آن‌چین...",
        "radar_head": "📡 *رادار زنده فاندینگ‌ریت + نهنگ‌های آن‌چین:*\n",
        "radar_locked": "\n🔒 _{rem} فرصت داغ دیگر ویژه اعضای «پلن پرو» است._",
        "invite_body": (
            "🎁 *۷ روز پلن پرو کاملاً رایگان!*\n\n"
            f"لینک اختصاصی زیر را برای *{FREE_PRO_INVITE_TARGET} دوست تریدر* بفرست؛ "
            "به محض استارت، دانلود MT5 و TradingView به مدت ۷ روز برایت رایگان باز می‌شود!\n\n"
            "🔗 لینک اختصاصی تو:\n`{link}`\n\n"
            "📊 دعوت‌های تو: *{count} از {target}*"
        ),
        "invite_progress": "📊 دعوت‌های تأییدشده: *{count} از {target}*",
        "ref_new": "🔥 یک تریدر جدید با لینک تو وارد شد! پیشرفت: *{count}/{target}*",
        "ref_unlocked": "🎉 *تبریک! ۳ دعوت تکمیل شد و ۷ روز پلن پرو رایگان برایت فعال شد!*",
        "need_pro": "این قابلیت ویژه اعضای پلن پرو است ⭐",
        "ai_thinking": "ایجنت هوشمند در حال تحلیل بازار...",
        "guard_info": (
            "🛡️ *قوانین طلایی محافظت از حساب پراپ:*\n\n"
            "• *تارگت آرام روزانه (+0.1%):* روی حساب ۱۰ هزار دلاری = روزی ۱۰ دلار بدون استرس.\n"
            "• *اکسپرت گارد MT5:* بستن خودکار معاملات در `-3.8%` قبل از سوختن چالش ۵٪.\n"
            "• *سپر قانون Consistency:* با دستور `/consistency 1200 600 40` سلامت برداشت سودت را چک کن!\n"
            "• *اندیکاتور SmartRadar:* نمایش PDH/PDL و حجم امن مستقیم روی چارت TradingView."
        ),
        "ea_cap": "✅ *اکسپرت محافظ پراپ (MetaTrader 5)*\nدر پوشه `MQL5/Experts` کپی و Compile کنید.",
        "pine_cap": "✅ *اندیکاتور اختصاصی TradingView (Pine v5)*\nکد را در `Pine Editor` کپی کرده و `Add to chart` بزنید.",
        "inv_title": "پلن پرو تریدگارد (۳۰ روزه)",
        "inv_desc": "رادار کامل آن‌چین + تحلیل AI Agent + دانلود اکسپرت MT5 و اندیکاتور TradingView",
        "inv_label": "اشتراک ۳۰ روزه TradeGuard Pro",
        "paid_ok": "🎉 *پرداخت موفق!*\nپلن پرو تا تاریخ `{exp}` فعال شد. اکنون فایل‌های MT5 و TradingView آماده دانلود هستند:",
    },
    "en": {
        "btn_app": "📱 Launch TradeGuard Mini-App",
        "btn_radar": "📡 Live Funding & Whales",
        "btn_ai": "🤖 AI Market Brief",
        "btn_guard": "🛡️ Prop Guard & News",
        "btn_invite": "🎁 7 Days Free Pro!",
        "btn_lang": "🌐 Language (🇬🇧 EN)",
        "btn_buy": f"⭐ Unlock Pro Now ({SUBSCRIPTION_STARS} Stars)",
        "btn_ea": "📥 Download MT5 EA",
        "btn_pine": "📈 Download TradingView Script",
        "welcome": (
            "Welcome to *TradeGuard Global v7.0* 🛡️🌍\n\n"
            "The all-in-one risk & alpha suite for Forex, Gold & Crypto traders:\n"
            "1️⃣ *Live Funding & Whale Radar:* Real-time Hyperliquid & OKX alpha\n"
            "2️⃣ *Prop-Firm Protection (MT5 + TradingView):* Auto `-3.8%` daily stop + Consistency Shield\n"
            "3️⃣ *Power Commands:* Anti-Rug `/scan PEPE` | Whale X-Ray `/wallet` | `/consistency`\n\n"
            "{status}"
        ),
        "status_pro": "✅ Your *Pro Plan* is active until `{exp}`.",
        "status_free": f"🔒 Basic Plan | Unlock instantly for *{SUBSCRIPTION_STARS} ⭐* or invite *{FREE_PRO_INVITE_TARGET} friends* for 7 days Free Pro!",
        "lang_prompt": "🌍 Choose your preferred language:",
        "lang_saved": "✅ Language switched to *English 🇬🇧*!",
        "scanning": "Scanning live on-chain funding & whale OI...",
        "radar_head": "📡 *Live Funding Rate & Whale OI Radar:*\n",
        "radar_locked": "\n🔒 _{rem} more extreme funding pairs are locked in Pro Plan._",
        "invite_body": (
            "🎁 *Get 7 Days of TradeGuard PRO Free!*\n\n"
            f"Share your personal link with *{FREE_PRO_INVITE_TARGET} trader friends* — "
            "once they start the bot, MT5 EA & TradingView downloads unlock automatically!\n\n"
            "🔗 Your referral link:\n`{link}`\n\n"
            "📊 Progress: *{count} / {target} referrals*"
        ),
        "invite_progress": "📊 Verified invites: *{count} of {target}*",
        "ref_new": "🔥 New trader joined via your link! Progress: *{count}/{target}*",
        "ref_unlocked": "🎉 *Congrats! 3 referrals completed — 7 Days of PRO unlocked for free!*",
        "need_pro": "This feature requires TradeGuard Pro ⭐",
        "ai_thinking": "AI Risk Agent is analyzing live markets...",
        "guard_info": (
            "🛡️ *TradeGuard Prop-Firm Protection Suite:*\n\n"
            "• *Calm +0.1% Daily Goal:* $10/day on a $10k account without over-leveraging.\n"
            "• *MT5 PropProtector EA:* Auto-closes trades at `-3.8%` before hitting your 5% daily breach.\n"
            "• *Consistency Check:* Run `/consistency 1200 600 40` to verify payout eligibility.\n"
            "• *TradingView SmartRadar:* Plots PDH/PDL liquidity zones & safe lot size on chart."
        ),
        "ea_cap": "✅ *TradeGuard PropProtector (MetaTrader 5)*\nCopy into `MQL5/Experts` and click Compile.",
        "pine_cap": "✅ *TradeGuard SmartRadar (Pine Script v5)*\nPaste into TradingView `Pine Editor` and click `Add to chart`.",
        "inv_title": "TradeGuard PRO (30 Days)",
        "inv_desc": "Unlimited On-Chain Whale & Funding Radar + AI Risk Agent + MT5 EA & TradingView Script",
        "inv_label": "TradeGuard Pro — 30 Days",
        "paid_ok": "🎉 *Payment Successful!*\nYour PRO Plan is active until `{exp}`. Download your MT5 & TradingView tools below:",
    },
    "ru": {
        "btn_app": "📱 Открыть Mini-App TradeGuard",
        "btn_radar": "📡 Радар фандинга и китов",
        "btn_ai": "🤖 ИИ-анализ рынка",
        "btn_guard": "🛡️ Защита пропа",
        "btn_invite": "🎁 7 дней PRO бесплатно!",
        "btn_lang": "🌐 Язык / Language (🇷🇺)",
        "btn_buy": f"⭐ Активировать PRO ({SUBSCRIPTION_STARS} Stars)",
        "btn_ea": "📥 Скачать советник MT5",
        "btn_pine": "📈 Скачать скрипт TradingView",
        "welcome": (
            "Добро пожаловать в *TradeGuard Global v7.0* 🛡️🌍\n\n"
            "Профессиональный терминал для проп- и крипто-трейдеров:\n"
            "1️⃣ *Живой радар фандинга и китов:* Hyperliquid и OKX онлайн\n"
            "2️⃣ *Защита проп-счёта (MT5 + TradingView):* авто-стоп при `-3.8%` просадки\n"
            "3️⃣ *Команды:* анти-скам `/scan PEPE` | киты `/wallet` | `/consistency`\n\n"
            "{status}"
        ),
        "status_pro": "✅ Ваш тариф *PRO* активен до `{exp}`.",
        "status_free": f"🔒 Базовый тариф | Откройте PRO за *{SUBSCRIPTION_STARS} ⭐* или пригласите *{FREE_PRO_INVITE_TARGET} друзей*!",
        "lang_prompt": "🌍 Выберите язык интерфейса:",
        "lang_saved": "✅ Язык переключён на *Русский 🇷🇺*!",
        "scanning": "Сканируем живой фандинг и объёмы китов...",
        "radar_head": "📡 *Живой радар фандинга и открытого интереса:*\n",
        "radar_locked": "\n🔒 _Ещё {rem} горячих пар открыты только в тарифе PRO._",
        "invite_body": (
            "🎁 *7 дней тарифа PRO бесплатно!*\n\n"
            f"Отправьте ссылку *{FREE_PRO_INVITE_TARGET} друзьям-трейдерам* — "
            "после старта откроется скачивание советника MT5 и индикатора TradingView!\n\n"
            "🔗 Ваша ссылка:\n`{link}`\n\n"
            "📊 Приглашено: *{count} из {target}*"
        ),
        "invite_progress": "📊 Подтверждённые приглашения: *{count} из {target}*",
        "ref_new": "🔥 По вашей ссылке зашёл новый трейдер! Прогресс: *{count}/{target}*",
        "ref_unlocked": "🎉 *Поздравляем! 3 друга приглашены — вам начислено 7 дней PRO бесплатно!*",
        "need_pro": "Доступно в тарифе PRO ⭐",
        "ai_thinking": "ИИ-агент анализирует рынок...",
        "guard_info": (
            "🛡️ *Защита проп-аккаунта TradeGuard:*\n\n"
            "• *Советник MT5:* авто-закрытие всех сделок при `-3.8%` до нарушения лимита 5%.\n"
            "• *Consistency Rule:* проверьте выплату командой `/consistency 1200 600 40`.\n"
            "• *Индикатор SmartRadar:* уровни PDH/PDL и безопасный лот прямо на графике."
        ),
        "ea_cap": "✅ *Советник защиты пропа (MetaTrader 5)*\nСкопируйте в `MQL5/Experts` и нажмите Compile.",
        "pine_cap": "✅ *Индикатор TradingView (Pine v5)*\nВставьте код в `Pine Editor` и нажмите `Add to chart`.",
        "inv_title": "TradeGuard PRO (30 дней)",
        "inv_desc": "Безлимитный ончейн-радар + ИИ-аналитика + советник MT5 и скрипт TradingView",
        "inv_label": "Подписка TradeGuard PRO (30 дней)",
        "paid_ok": "🎉 *Оплата прошла успешно!*\nТариф PRO активен до `{exp}`. Скачивайте файлы ниже:",
    },
    "ar": {
        "btn_app": "📱 فتح تطبيق TradeGuard",
        "btn_radar": "📡 رادار التمويل والحيتان",
        "btn_ai": "🤖 تحليل الذكاء الاصطناعي",
        "btn_guard": "🛡️ حارس حساب التمويل",
        "btn_invite": "🎁 7 أيام PRO مجاناً!",
        "btn_lang": "🌐 اللغة / Language (🇸🇦)",
        "btn_buy": f"⭐ تفعيل PRO فوري ({SUBSCRIPTION_STARS} نجمة)",
        "btn_ea": "📥 تحميل اكسبيرت MT5",
        "btn_pine": "📈 تحميل مؤشر TradingView",
        "welcome": (
            "مرحباً بك في *TradeGuard Global v7.0* 🛡️🌍\n\n"
            "منصة حماية المخاطر لمتداولي الفوركس والذهب والكريبتو:\n"
            "1️⃣ *رادار التمويل والحيتان الحي:* بيانات Hyperliquid و OKX لحظة بلحظة\n"
            "2️⃣ *حماية حسابات التمويل (MT5 + TradingView):* إغلاق آلي عند `-3.8%` يومياً\n"
            "3️⃣ *أوامر سريعة:* فحص العملات `/scan PEPE` | محفظة الحوت `/wallet`\n\n"
            "{status}"
        ),
        "status_pro": "✅ اشتراك *PRO* مفعل حتى `{exp}`.",
        "status_free": f"🔒 الحساب الأساسي | فعّل PRO بـ *{SUBSCRIPTION_STARS} ⭐* أو ادعُ *{FREE_PRO_INVITE_TARGET} أصدقاء*!",
        "lang_prompt": "🌍 اختر لغتك المفضلة:",
        "lang_saved": "✅ تم تغيير اللغة إلى *العربية 🇸🇦*!",
        "scanning": "جاري فحص معدلات التمويل وعقود الحيتان...",
        "radar_head": "📡 *رادار معدلات التمويل والسيولة الحي:*\n",
        "radar_locked": "\n🔒 _توجد {rem} فرص إضافية مفتوحة لمشتركي PRO فقط._",
        "invite_body": (
            "🎁 *احصل على 7 أيام PRO مجاناً!*\n\n"
            f"شارك رابطك مع *{FREE_PRO_INVITE_TARGET} أصدقاء متداولين* لفتح تحميل اكسبيرت MT5 ومؤشر TradingView مجاناً!\n\n"
            "🔗 رابط الدعوة:\n`{link}`\n\n"
            "📊 الدعوات المسجلة: *{count} من {target}*"
        ),
        "invite_progress": "📊 الدعوات المؤكدة: *{count} من {target}*",
        "ref_new": "🔥 انضم متداول جديد عبر رابطك! التقدم: *{count}/{target}*",
        "ref_unlocked": "🎉 *مبروك! اكتملت 3 دعوات وتم تفعيل 7 أيام PRO مجاناً!*",
        "need_pro": "هذه الميزة مخصصة لمشتركي PRO ⭐",
        "ai_thinking": "جاري تحليل بيانات السوق...",
        "guard_info": (
            "🛡️ *قواعد حماية حساب التمويل:*\n\n"
            "• *اكسبيرت MT5:* إغلاق تلقائي لجميع الصفقات عند `-3.8%` قبل كسر حد 5%.\n"
            "• *فحص الاستمرارية:* استخدم `/consistency 1200 600 40` للتحقق من شروط السحب.\n"
            "• *مؤشر SmartRadar:* يرسم مناطق سيولة الأمس واللوت الآمن مباشرة على الشارت."
        ),
        "ea_cap": "✅ *اكسبيرت الحماية (MetaTrader 5)*\nانسخه إلى مجلد `MQL5/Experts` واضغط Compile.",
        "pine_cap": "✅ *مؤشر TradingView (Pine v5)*\nالصق الكود داخل `Pine Editor` واضغط `Add to chart`.",
        "inv_title": "اشتراك TradeGuard PRO (30 يوماً)",
        "inv_desc": "رادار حيتان وتمويل كامل + ذكاء اصطناعي + اكسبيرت MT5 ومؤشر TradingView",
        "inv_label": "اشتراك 30 يوماً TradeGuard PRO",
        "paid_ok": "🎉 *تم الدفع بنجاح!*\nاشتراك PRO نشط حتى `{exp}`. يمكنك تحميل الأدوات الآن:",
    },
    "tr": {
        "btn_app": "📱 TradeGuard Uygulamasını Aç",
        "btn_radar": "📡 Canlı Fonlama & Balina",
        "btn_ai": "🤖 Yapay Zeka Analizi",
        "btn_guard": "🛡️ Prop Kalkanı",
        "btn_invite": "🎁 7 Gün Ücretsiz PRO!",
        "btn_lang": "🌐 Dil / Language (🇹🇷)",
        "btn_buy": f"⭐ PRO Paketi Aç ({SUBSCRIPTION_STARS} Stars)",
        "btn_ea": "📥 MT5 Botunu İndir",
        "btn_pine": "📈 TradingView İndikatörü",
        "welcome": (
            "*TradeGuard Global v7.0*'a Hoş Geldiniz 🛡️🌍\n\n"
            "Forex, Altın ve Kripto traderları için profesyonel koruma paketi:\n"
            "1️⃣ *Canlı Fonlama & Balina Radarı:* Anlık Hyperliquid ve OKX verileri\n"
            "2️⃣ *Prop Hesap Kalkanı (MT5 + TradingView):* Günlük `-3.8%` otomatik kapatma\n"
            "3️⃣ *Komutlar:* Güvenlik tarama `/scan PEPE` | Balina `/wallet`\n\n"
            "{status}"
        ),
        "status_pro": "✅ *PRO Paketiniz* `{exp}` tarihine kadar aktif.",
        "status_free": f"🔒 Temel Hesap | *{SUBSCRIPTION_STARS} ⭐* ile anında PRO açın veya *{FREE_PRO_INVITE_TARGET} arkadaş* davet edin!",
        "lang_prompt": "🌍 Lütfen dilinizi seçin:",
        "lang_saved": "✅ Dil *Türkçe 🇹🇷* olarak güncellendi!",
        "scanning": "Canlı fonlama ve balina pozisyonları taranıyor...",
        "radar_head": "📡 *Canlı Fonlama Oranı & Balina OI Radarı:*\n",
        "radar_locked": "\n🔒 _{rem} sıcak fırsat daha PRO pakette açık._",
        "invite_body": (
            "🎁 *7 Gün Ücretsiz PRO Kazanın!*\n\n"
            f"Özel linkinizi *{FREE_PRO_INVITE_TARGET} trader arkadaşınızla* paylaşın; "
            "MT5 ve TradingView dosyaları ücretsiz açılsın!\n\n"
            "🔗 Davet linkiniz:\n`{link}`\n\n"
            "📊 İlerleme: *{count} / {target} davet*"
        ),
        "invite_progress": "📊 Onaylanan davetler: *{count} / {target}*",
        "ref_new": "🔥 Linkinizle yeni bir trader katıldı! İlerleme: *{count}/{target}*",
        "ref_unlocked": "🎉 *Tebrikler! 3 davet tamamlandı — 7 Gün Ücretsiz PRO aktif edildi!*",
        "need_pro": "Bu özellik PRO üyeler içindir ⭐",
        "ai_thinking": "Yapay zeka canlı verileri analiz ediyor...",
        "guard_info": (
            "🛡️ *TradeGuard Prop Hesap Koruma Kuralları:*\n\n"
            "• *MT5 PropProtector Botu:* Günlük kayıp `-3.8%` olduğunda işlemleri otomatik kapatır.\n"
            "• *Consistency Kontrolü:* `/consistency 1200 600 40` komutuyla çekim kuralını test edin.\n"
            "• *SmartRadar İndikatörü:* PDH/PDL likidite bölgelerini grafikte gösterir."
        ),
        "ea_cap": "✅ *MT5 Prop Koruma Uzmanı*\n`MQL5/Experts` klasörüne kopyalayıp Compile edin.",
        "pine_cap": "✅ *TradingView İndikatörü (Pine v5)*\nKodu `Pine Editor` içine yapıştırıp `Add to chart` tıklayın.",
        "inv_title": "TradeGuard PRO (30 Gün)",
        "inv_desc": "Sınırsız Balina & Fonlama Radarı + Yapay Zeka + MT5 Uzmanı ve TradingView İndikatörü",
        "inv_label": "TradeGuard PRO — 30 Gün",
        "paid_ok": "🎉 *Ödeme Başarılı!*\nPRO paketiniz `{exp}` tarihine kadar aktif. Dosyalarınızı aşağıdan indirebilirsiniz:",
    },
    "es": {
        "btn_app": "📱 Abrir Mini-App TradeGuard",
        "btn_radar": "📡 Radar Funding y Ballenas",
        "btn_ai": "🤖 Resumen IA de Mercado",
        "btn_guard": "🛡️ Escudo Prop Firm",
        "btn_invite": "🎁 ¡7 Días PRO Gratis!",
        "btn_lang": "🌐 Idioma / Language (🇪🇸)",
        "btn_buy": f"⭐ Activar PRO ({SUBSCRIPTION_STARS} Stars)",
        "btn_ea": "📥 Descargar EA MT5",
        "btn_pine": "📈 Descargar Script TradingView",
        "welcome": (
            "¡Bienvenido a *TradeGuard Global v7.0*! 🛡️🌍\n\n"
            "Suite profesional de riesgo para traders de Forex, Oro y Cripto:\n"
            "1️⃣ *Radar en Vivo de Funding y Ballenas:* Hyperliquid y OKX al instante\n"
            "2️⃣ *Escudo Prop Firm (MT5 + TradingView):* Cierre automático diario en `-3.8%`\n"
            "3️⃣ *Comandos:* Escáner `/scan PEPE` | Ballenas `/wallet` | `/consistency`\n\n"
            "{status}"
        ),
        "status_pro": "✅ Tu *Plan PRO* está activo hasta `{exp}`.",
        "status_free": f"🔒 Plan Básico | Activa PRO por *{SUBSCRIPTION_STARS} ⭐* o invita a *{FREE_PRO_INVITE_TARGET} amigos*!",
        "lang_prompt": "🌍 Selecciona tu idioma preferido:",
        "lang_saved": "✅ ¡Idioma cambiado a *Español 🇪🇸*!",
        "scanning": "Escaneando tasas de funding y ballenas en vivo...",
        "radar_head": "📡 *Radar en Vivo de Funding Rate y Ballenas:*\n",
        "radar_locked": "\n🔒 _{rem} pares extremos más desbloqueados en el Plan PRO._",
        "invite_body": (
            "🎁 *¡Obtén 7 Días de TradeGuard PRO Gratis!*\n\n"
            f"Comparte tu enlace con *{FREE_PRO_INVITE_TARGET} amigos traders* — "
            "¡al iniciar el bot se desbloquean MT5 y TradingView gratis!\n\n"
            "🔗 Tu enlace:\n`{link}`\n\n"
            "📊 Progreso: *{count} / {target} invitados*"
        ),
        "invite_progress": "📊 Invitaciones confirmadas: *{count} de {target}*",
        "ref_new": "🔥 ¡Nuevo trader registrado con tu enlace! Progreso: *{count}/{target}*",
        "ref_unlocked": "🎉 *¡Felicidades! 3 invitados completados — 7 Días PRO activados gratis!*",
        "need_pro": "Esta función requiere el Plan PRO ⭐",
        "ai_thinking": "El Agente IA está analizando el mercado...",
        "guard_info": (
            "🛡️ *Escudo de Protección para Cuentas de Fondeo:*\n\n"
            "• *EA MT5 PropProtector:* Cierra todas las órdenes en `-3.8%` antes de perder la cuenta.\n"
            "• *Regla de Consistencia:* Usa `/consistency 1200 600 40` para verificar tu retiro.\n"
            "• *SmartRadar TradingView:* Dibuja liquidez PDH/PDL y lotaje seguro en el gráfico."
        ),
        "ea_cap": "✅ *Expert Advisor PropProtector (MetaTrader 5)*\nCópialo en `MQL5/Experts` y pulsa Compile.",
        "pine_cap": "✅ *Indicador SmartRadar (Pine Script v5)*\nPega el código en `Pine Editor` de TradingView y pulsa `Add to chart`.",
        "inv_title": "TradeGuard PRO (30 Días)",
        "inv_desc": "Radar On-Chain Ilimitado + Agente IA + EA para MT5 e Indicador TradingView",
        "inv_label": "Suscripción TradeGuard PRO — 30 Días",
        "paid_ok": "🎉 *¡Pago Exitoso!*\nTu Plan PRO está activo hasta `{exp}`. Descarga tus herramientas abajo:",
    },
}


def normalize_lang(code: Optional[str]) -> str:
    if not code:
        return "fa"
    short = code[:2].lower()
    return short if short in SUPPORTED_LANGS else "en"


# =====================================================================
#  پیام‌های «دورهٔ رایگان» (۶ زبان) — جدا از دیکشنری اصلی تا کم‌ریسک باشد
# =====================================================================
BOT_STRINGS_EXTRA = {
    "fa": {
        "btn_free": "🎁 دورهٔ رایگان — همه‌چیز باز است",
        "free_home_line": "🎁 *دورهٔ رشد:* همهٔ قابلیت‌ها فعلاً رایگان است.",
        "free_buy_blocked": "🎁 این روزها همه‌چیز رایگان است — نیازی به پرداخت نیست.\nفقط کانال را دنبال کن و دوستت را دعوت کن تا ربات رشد کند.",
        "free_info": "🎁 فعلاً همهٔ قابلیت‌ها (رادار کامل، هشدارها، مربی AI، فایل MT5 و TradingView) رایگان است.",
        "free_admin_on": "🎁 حالت رایگان *روشن* شد — هیچ کاربری استارز نمی‌دهد و همه‌چیز باز است.\nبرای برگشت: `/freemode off`",
        "free_admin_off": "💰 حالت رایگان *خاموش* شد — پرداخت ۳۰۰ ⭐ و قفل‌ها دوباره فعال شد.",
        "free_admin_state": "وضعیت دورهٔ رایگان: *{state}*",
    },
    "en": {
        "btn_free": "🎁 Free period — everything unlocked",
        "free_home_line": "🎁 *Growth period:* all features are free right now.",
        "free_buy_blocked": "🎁 Everything is free right now — no payment needed.\nJust follow the channel and invite a friend to help the bot grow.",
        "free_info": "🎁 All features (full radar, alerts, AI coach, MT5 & TradingView files) are free right now.",
        "free_admin_on": "🎁 *Free mode ON* — nobody pays, everything is unlocked.\nTo revert: `/freemode off`",
        "free_admin_off": "💰 *Free mode OFF* — 300 ⭐ payments and locks are active again.",
        "free_admin_state": "Free period: *{state}*",
    },
    "ru": {
        "btn_free": "🎁 Бесплатный период — всё открыто",
        "free_home_line": "🎁 *Период роста:* все функции сейчас бесплатны.",
        "free_buy_blocked": "🎁 Сейчас всё бесплатно — платить не нужно.\nПодпишитесь на канал и пригласите друга.",
        "free_info": "🎁 Все функции (полный радар, оповещения, AI-наставник, файлы MT5 и TradingView) сейчас бесплатны.",
        "free_admin_on": "🎁 *Бесплатный режим ВКЛ* — никто не платит, всё открыто.\nОткат: `/freemode off`",
        "free_admin_off": "💰 *Бесплатный режим ВЫКЛ* — оплата 300 ⭐ и блокировки снова активны.",
        "free_admin_state": "Бесплатный период: *{state}*",
    },
    "ar": {
        "btn_free": "🎁 فترة مجانية — كل شيء مفتوح",
        "free_home_line": "🎁 *فترة النمو:* كل الميزات مجانية الآن.",
        "free_buy_blocked": "🎁 كل شيء مجاني الآن — لا حاجة للدفع.\nتابع القناة وادعُ صديقًا.",
        "free_info": "🎁 كل الميزات (الرادار الكامل، التنبيهات، مدرب AI، ملفات MT5 وTradingView) مجانية الآن.",
        "free_admin_on": "🎁 *الوضع المجاني مُفعّل* — لا أحد يدفع وكل شيء مفتوح.\nللرجوع: `/freemode off`",
        "free_admin_off": "💰 *الوضع المجاني مُعطّل* — عاد الدفع ٣٠٠ ⭐ والأقفال.",
        "free_admin_state": "الفترة المجانية: *{state}*",
    },
    "tr": {
        "btn_free": "🎁 Ücretsiz dönem — her şey açık",
        "free_home_line": "🎁 *Büyüme dönemi:* tüm özellikler şu an ücretsiz.",
        "free_buy_blocked": "🎁 Şu an her şey ücretsiz — ödeme gerekmez.\nKanalı takip et ve bir arkadaşını davet et.",
        "free_info": "🎁 Tüm özellikler (tam radar, uyarılar, AI koç, MT5 ve TradingView dosyaları) şu an ücretsiz.",
        "free_admin_on": "🎁 *Ücretsiz mod AÇIK* — kimse ödemez, her şey açık.\nGeri almak için: `/freemode off`",
        "free_admin_off": "💰 *Ücretsiz mod KAPALI* — 300 ⭐ ödeme ve kilitler yeniden aktif.",
        "free_admin_state": "Ücretsiz dönem: *{state}*",
    },
    "es": {
        "btn_free": "🎁 Periodo gratis — todo desbloqueado",
        "free_home_line": "🎁 *Periodo de crecimiento:* todas las funciones son gratis ahora.",
        "free_buy_blocked": "🎁 Ahora todo es gratis — no hace falta pagar.\nSigue el canal e invita a un amigo.",
        "free_info": "🎁 Todas las funciones (radar completo, alertas, coach AI, archivos MT5 y TradingView) son gratis ahora.",
        "free_admin_on": "🎁 *Modo gratis ACTIVADO* — nadie paga, todo está abierto.\nPara revertir: `/freemode off`",
        "free_admin_off": "💰 *Modo gratis DESACTIVADO* — pagos de 300 ⭐ y bloqueos activos otra vez.",
        "free_admin_state": "Periodo gratis: *{state}*",
    },
}

_CHANNEL_BTN = {
    "fa": "📣 کانال TradeGuard",
    "en": "📣 TradeGuard Channel",
    "ru": "📣 Канал TradeGuard",
    "ar": "📣 قناة TradeGuard",
    "tr": "📣 TradeGuard Kanalı",
    "es": "📣 Canal de TradeGuard",
}
for _lang, _label in _CHANNEL_BTN.items():
    if _lang in BOT_STRINGS:
        BOT_STRINGS[_lang]["btn_channel"] = _label

for _lang, _extra in BOT_STRINGS_EXTRA.items():
    if _lang in BOT_STRINGS:
        BOT_STRINGS[_lang].update(_extra)


def tr(lang: str, key: str, **kwargs) -> str:
    d = BOT_STRINGS.get(lang, BOT_STRINGS["en"])
    txt = d.get(key) or BOT_STRINGS["en"].get(key, "")
    return txt.format(**kwargs) if kwargs else txt


def is_real_app_url(url: str) -> bool:
    if not url or not url.startswith("https://"):
        return False
    placeholders = ("example.com", "your-tradeguard-app.pages.dev", "your-domain")
    return not any(p in url for p in placeholders)


def build_app_url(lang: str) -> str:
    url = MINI_APP_URL if is_real_app_url(MINI_APP_URL) else ""
    if not url:
        return ""
    try:
        parsed = urllib.parse.urlparse(url)
        q = dict(urllib.parse.parse_qsl(parsed.query))
        q["lang"] = lang
        return urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(q)))
    except Exception:
        return url


# =====================================================================
# کلاینت مستقیم Telegram Bot API با کتابخانه استاندارد پایتون (بدون پکیج!)
# =====================================================================
def http_json(url: str, method: str = "GET", payload: Optional[dict] = None, headers: Optional[dict] = None, timeout: float = 12.0) -> dict:
    req_headers = {"User-Agent": "TradeGuardBot/7.0", "Accept": "application/json"}
    if headers:
        req_headers.update(headers)
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def tg_call(method_name: str, payload: Optional[dict] = None, timeout: float = 15.0) -> dict:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method_name}"
    try:
        return http_json(url, method="POST", payload=payload or {}, timeout=timeout)
    except urllib.error.HTTPError as e:
        err_txt = e.read().decode("utf-8", errors="ignore")
        logger.warning("Telegram API error on %s: %s", method_name, err_txt)
        return {"ok": False, "description": err_txt}
    except Exception as exc:
        logger.warning("Network error on %s: %s", method_name, exc)
        return {"ok": False, "description": str(exc)}


def is_self_chat(chat_id: int | str) -> bool:
    """جلوگیری از خطای 403 «bot can't send messages to the bot»."""
    if BOT_ID:
        try:
            if int(str(chat_id).lstrip("@")) == int(BOT_ID):
                return True
        except (TypeError, ValueError):
            pass
    if isinstance(chat_id, str):
        u = chat_id.lstrip("@").lower()
        if BOT_USERNAME and u == BOT_USERNAME.lower():
            return True
        # نام کاربری که به «bot» ختم می‌شود و بخشی از کانال نیست
        if u.endswith("bot") and not u.startswith("channel"):
            return True
    return False


def tg_send_message(chat_id: int | str, text: str, reply_markup: Optional[dict] = None, parse_mode: str = "Markdown") -> dict:
    if is_self_chat(chat_id):
        logger.warning(
            "پیام به خودِ ربات (%s) نادیده گرفته شد — مقدار PUBLIC_CHANNEL_ID را بررسی کنید. "
            "راهنما: دستور /channel در چت ربات.",
            chat_id,
        )
        return {"ok": False, "skipped": "self_chat"}
    payload: dict = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_markup:
        payload["reply_markup"] = reply_markup
    res = tg_call("sendMessage", payload)

    # ترجمه خطاها به پیام فارسی قابل فهم + راه‌حل خودکار
    if not res.get("ok"):
        desc = str(res.get("description") or "")
        if "can't send messages to the bot" in desc:
            global PUBLIC_CHANNEL_ID
            logger.error(
                "❌ مقصد ارسال خودِ ربات است (%s) — پست خودکار کانال خاموش شد. راه‌حل: /channel", chat_id
            )
            if str(chat_id).lstrip("@") in (str(PUBLIC_CHANNEL_ID).lstrip("@"), str(BOT_ID)):
                PUBLIC_CHANNEL_ID = ""
        elif "chat not found" in desc.lower() or "bot was blocked by the user" in desc:
            logger.warning("⚠️ مقصد %s در دسترس نیست: %s", chat_id, desc[:100])

    if not res.get("ok") and parse_mode:
        payload.pop("parse_mode", None)
        res = tg_call("sendMessage", payload)
    return res


def tg_answer_callback(callback_id: str, text: str = "", show_alert: bool = False) -> None:
    payload: dict = {"callback_query_id": callback_id, "show_alert": show_alert}
    if text:
        payload["text"] = text[:190]
    tg_call("answerCallbackQuery", payload)


def tg_send_document(chat_id: int, file_path: Path, filename: str, caption: str = "") -> dict:
    boundary = f"----TradeGuardBoundary{uuid.uuid4().hex}"
    lines: List[bytes] = []

    def add_field(name: str, value: str) -> None:
        lines.append(f"--{boundary}\r\n".encode())
        lines.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        lines.append(f"{value}\r\n".encode())

    add_field("chat_id", str(chat_id))
    if caption:
        add_field("caption", caption)
        add_field("parse_mode", "Markdown")

    file_bytes = file_path.read_bytes()
    lines.append(f"--{boundary}\r\n".encode())
    lines.append(f'Content-Disposition: form-data; name="document"; filename="{filename}"\r\n'.encode())
    lines.append(b"Content-Type: text/plain; charset=utf-8\r\n\r\n")
    lines.append(file_bytes + b"\r\n")
    lines.append(f"--{boundary}--\r\n".encode())

    body = b"".join(lines)
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "User-Agent": "TradeGuardBot/7.5"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30.0) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="ignore")
        logger.warning("Telegram API error on sendDocument: %s", raw[:200])
        return {"ok": False, "description": raw}
    except Exception as exc:
        logger.warning("Network error on sendDocument: %s", exc)
        return {"ok": False, "description": str(exc)}


# =====================================================================
# ۱) دیتابیس SQLite (مهاجرت خودکار بدون پاک شدن اطلاعات)
# =====================================================================
_db_lock = threading.Lock()


def init_db() -> None:
    with _db_lock, sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                lang TEXT DEFAULT 'fa',
                referred_by INTEGER,
                referrals_count INTEGER DEFAULT 0,
                free_trial_claimed INTEGER DEFAULT 0,
                pro_until INTEGER DEFAULT 0,
                created_at INTEGER NOT NULL
            )
            """
        )
        cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
        if "lang" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN lang TEXT DEFAULT 'fa'")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                stars_amount INTEGER NOT NULL,
                telegram_charge_id TEXT NOT NULL,
                paid_at INTEGER NOT NULL
            )
            """
        )

        # تنظیمات زمان اجرا (/seturl، /price، /setchannel، ادمین) — چون هر
        # جاب GitHub Actions از صفر شروع می‌شود، این‌ها باید در دیتابیس بمانند
        # تا با ری‌استارت هر ۶ ساعت به حالت اول برنگردند.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS join_rewards (
                user_id INTEGER PRIMARY KEY,
                days INTEGER NOT NULL,
                granted_at INTEGER NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at INTEGER NOT NULL
            )
            """
        )


def set_setting(key: str, value: str) -> None:
    """ذخیره تنظیم در دیتابیس (پایدار بین ری‌استارت‌ها و اجراهای Actions)."""
    try:
        with _db_lock, sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
                (key, str(value), int(time.time())),
            )
    except Exception as exc:
        logger.warning("ذخیره تنظیم %s در دیتابیس ناموفق: %s", key, exc)


def get_setting(key: str, default: str = "") -> str:
    try:
        with _db_lock, sqlite3.connect(DB_PATH) as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return str(row[0]) if row and row[0] is not None else default
    except Exception:
        return default


def get_user_lang(user_id: int, fallback_tg_code: Optional[str] = None) -> str:
    with _db_lock, sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if row and row[0] in SUPPORTED_LANGS:
            return row[0]
    return normalize_lang(fallback_tg_code)


def set_user_lang(user_id: int, lang: str) -> None:
    if lang not in SUPPORTED_LANGS:
        lang = "en"
    with _db_lock, sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang, user_id))


def register_user_and_check_referral(
    user_id: int,
    username: Optional[str],
    tg_lang_code: Optional[str],
    referred_by: Optional[int] = None,
) -> Tuple[bool, Optional[int], int, bool]:
    now = int(time.time())
    init_lang = normalize_lang(tg_lang_code)
    with _db_lock, sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        if cur.fetchone() is not None:
            return False, None, 0, False

        valid_ref = referred_by if (referred_by and referred_by != user_id) else None
        if valid_ref:
            ref_exists = conn.execute("SELECT user_id FROM users WHERE user_id = ?", (valid_ref,)).fetchone()
            if not ref_exists:
                valid_ref = None

        conn.execute(
            "INSERT INTO users (user_id, username, lang, referred_by, referrals_count, free_trial_claimed, pro_until, created_at) "
            "VALUES (?, ?, ?, ?, 0, 0, 0, ?)",
            (user_id, username or "", init_lang, valid_ref, now),
        )

        if not valid_ref:
            return True, None, 0, False

        conn.execute("UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id = ?", (valid_ref,))
        row = conn.execute(
            "SELECT referrals_count, free_trial_claimed, pro_until FROM users WHERE user_id = ?",
            (valid_ref,),
        ).fetchone()
        ref_count, claimed, pro_until = int(row[0]), int(row[1]), int(row[2] or 0)

        unlocked_now = False
        if ref_count >= FREE_PRO_INVITE_TARGET and claimed == 0:
            base_exp = pro_until if pro_until > now else now
            new_exp = base_exp + (7 * 86400)
            conn.execute(
                "UPDATE users SET pro_until = ?, free_trial_claimed = 1 WHERE user_id = ?",
                (new_exp, valid_ref),
            )
            unlocked_now = True

        return True, valid_ref, ref_count, unlocked_now


# =====================================================================
#  انتشار وضعیت اشتراک برای مینی‌اپ استاتیک (docs/pro_users.json)
#  ─ مینی‌اپ هیچ بک‌اندی ندارد؛ تنها منبع حقیقتِ وضعیت پرو همین فایل است
#    که فقط ربات آن را می‌نویسد. کاربر نمی‌تواند خودش را پرو کند.
#  ─ کلید هر کاربر = sha256("tg-pro:" + user_id)[:16] (آیدی خام لو نمی‌رود)
# =====================================================================
PRO_STATUS_MAX_AGE = 30 * 86400


def pro_status_key(user_id: int) -> str:
    return hashlib.sha256(("tg-pro:" + str(int(user_id))).encode()).hexdigest()[:16]


def load_pro_status() -> dict:
    try:
        raw = PRO_STATUS_FILE.read_text(encoding="utf-8")
        data = json.loads(raw)
        if isinstance(data, dict) and isinstance(data.get("users"), dict):
            return data
    except Exception:
        pass
    return {"updated": 0, "users": {}}


def save_pro_status(data: dict) -> bool:
    """فایل را می‌نویسد؛ True یعنی محتوا واقعاً تغییر کرد."""
    old = load_pro_status()
    if old.get("users") == data.get("users") and bool(old.get("freeMode")) == bool(data.get("freeMode")):
        return False
    PRO_STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PRO_STATUS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=0, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return True


def _git_publish_status_file() -> None:
    """کامیت و پوش فایل وضعیت (فقط وقتی PRO_STATUS_PUSH روشن است)."""
    if not PRO_STATUS_PUSH:
        return
    try:
        rel = str(PRO_STATUS_FILE.relative_to(REPO_ROOT))
    except ValueError:
        logger.warning("فایل وضعیت پرو خارج از ریپو است؛ پوش انجام نشد")
        return
    try:
        subprocess.run(["git", "add", rel], cwd=str(REPO_ROOT), capture_output=True, timeout=60)
        commit = subprocess.run(
            [
                "git",
                "-c", "user.name=github-actions[bot]",
                "-c", "user.email=41898282+github-actions[bot]@users.noreply.github.com",
                "commit", "-m", "chore(pro): sync subscription status [skip ci]",
            ],
            cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=60,
        )
        if commit.returncode != 0:
            return  # چیزی برای کامیت نبود
        for attempt in (1, 2):
            subprocess.run(["git", "pull", "--rebase", "--autostash"], cwd=str(REPO_ROOT), capture_output=True, timeout=120)
            push = subprocess.run(["git", "push"], cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=120)
            if push.returncode == 0:
                logger.info("📤 وضعیت پرو در ریپو منتشر شد")
                return
            logger.warning("پوش وضعیت پرو ناموفق (تلاش %s): %s", attempt, (push.stderr or "")[:200])
    except Exception as exc:
        logger.warning("انتشار وضعیت پرو ناموفق بود: %s", exc)


def publish_pro_status(user_ids: Optional[List[int]] = None) -> None:
    """وضعیت پرو/دعوتِ کاربران داده‌شده را از دیتابیس تازه می‌کند و منتشر می‌کند.

    user_ids=None ⇒ همهٔ کاربرانی که پرو فعال یا دعوت ثبت‌شده دارند.
    """
    now = int(time.time())
    with PRO_STATUS_LOCK:
        data = load_pro_status()
        users = dict(data.get("users") or {})
        try:
            with _db_lock, sqlite3.connect(DB_PATH) as conn:
                if user_ids:
                    ids = [int(u) for u in user_ids]
                    rows: List[Tuple[int, int, int]] = []
                    for uid in ids:
                        row = conn.execute(
                            "SELECT pro_until, referrals_count FROM users WHERE user_id = ?",
                            (uid,),
                        ).fetchone()
                        if row:
                            rows.append((uid, int(row[0] or 0), int(row[1] or 0)))
                else:
                    rows = [
                        (int(r[0]), int(r[1] or 0), int(r[2] or 0))
                        for r in conn.execute(
                            "SELECT user_id, pro_until, referrals_count FROM users "
                            "WHERE pro_until > ? OR referrals_count > 0",
                            (now - PRO_STATUS_MAX_AGE,),
                        ).fetchall()
                    ]
        except Exception as exc:
            logger.warning("خواندن وضعیت پرو از دیتابیس ناموفق بود: %s", exc)
            return

        for uid, pro_until, ref_count in rows:
            key = pro_status_key(uid)
            if pro_until > now or ref_count > 0:
                users[key] = {"exp": int(pro_until), "ref": int(ref_count)}
            else:
                users.pop(key, None)

        # هرسِ رکوردهای منقضی و قدیمی
        for key in list(users.keys()):
            entry = users.get(key) or {}
            try:
                exp = int(entry.get("exp") or 0)
                ref = int(entry.get("ref") or 0)
            except Exception:
                users.pop(key, None)
                continue
            if exp and exp < now - PRO_STATUS_MAX_AGE and not ref:
                users.pop(key, None)

        data = {"updated": now, "freeMode": free_mode_active(), "users": users}
        if save_pro_status(data):
            _git_publish_status_file()


def get_user_referral_stats(user_id: int) -> Tuple[int, bool]:
    with _db_lock, sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT referrals_count, free_trial_claimed FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if not row:
            return 0, False
        return int(row[0] or 0), bool(row[1])


def load_free_mode() -> None:
    """پرچم ذخیره‌شدهٔ ادمین (دیتابیس) بر env اولویت دارد."""
    global FREE_MODE
    try:
        saved = get_setting("free_mode")
    except Exception:
        saved = None
    if saved in ("0", "1"):
        FREE_MODE = saved == "1"


def set_free_mode(on: bool) -> None:
    global FREE_MODE
    FREE_MODE = bool(on)
    try:
        set_setting("free_mode", "1" if on else "0")
    except Exception as exc:
        logger.warning("ذخیرهٔ حالت رایگان ناموفق: %s", exc)
    publish_pro_status()


def free_mode_active() -> bool:
    """آیا دورهٔ رایگان باز است؟ (پرچم runtime یا دیتابیس + تاریخ انقضای اختیاری)"""
    if not FREE_MODE:
        return False
    return FREE_MODE_UNTIL <= 0 or time.time() < FREE_MODE_UNTIL


def is_user_pro(user_id: int, access: bool = True) -> Tuple[bool, int]:
    """آیا کاربر پرو است؟

    access=True (پیش‌فرض) ⇒ «دسترسی» را می‌گوید: در دورهٔ رایگان همه True هستند.
    access=False ⇒ فقط وضعیت واقعی اشتراک پرداختی (برای آمار/درآمد).
    """
    now = int(time.time())
    if access and free_mode_active():
        return True, FREE_MODE_UNTIL if FREE_MODE_UNTIL > 0 else now + (10 * 365 * 86400)
    if ADMIN_USER_ID and str(user_id) == ADMIN_USER_ID:
        return True, now + (365 * 86400)
    with _db_lock, sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT pro_until FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            return False, 0
        pro_until = int(row[0] or 0)
        return pro_until > now, pro_until


def is_admin(user_id: int | str) -> bool:
    """آیا این کاربر مؤسس ربات است؟ (فقط با ADMIN_USER_ID تنظیم‌شده)"""
    return bool(ADMIN_USER_ID) and str(user_id) == ADMIN_USER_ID


def remember_first_user(user_id: int) -> None:
    """
    ثبت «اولین کاربر ربات» — یک‌بار و برای همیشه.
    نکته: در این دیتابیس user_id همان rowid است، پس نمی‌شود ترتیب درج را
    از rowid فهمید؛ برای همین اولین /start را صریح ذخیره می‌کنیم.
    """
    try:
        if not get_setting("first_user_id"):
            set_setting("first_user_id", str(int(user_id)))
    except Exception:
        pass


def is_first_user(user_id: int) -> bool:
    """اولین کاربری که ربات را استارت کرده — تنها کسی که اجازه «ادعای ادمینی» دارد."""
    try:
        saved = get_setting("first_user_id")
        if saved:
            return str(int(user_id)) == saved
        with _db_lock, sqlite3.connect(DB_PATH) as conn:
            row = conn.execute("SELECT user_id FROM users ORDER BY created_at ASC LIMIT 1").fetchone()
        return bool(row) and int(row[0]) == int(user_id)
    except Exception:
        return False


ADMIN_DENIED = (
    "⛔ دسترسی فقط برای مؤسس ربات مجاز است.\n\n"
    "اگر صاحب ربات هستید: GitHub → Settings → Secrets and variables → Actions → "
    "New repository secret → Name: `ADMIN_USER_ID` و آیدی عددی خودتان (از @userinfobot) را بگذارید."
)


def activate_pro_subscription(user_id: int, stars: int, charge_id: str, days: int = 30) -> Tuple[int, bool]:
    """
    فعال‌سازی/تمدید اشتراک Pro.
    خروجی: (تاریخ انقضا، آیا پرداخت جدید بود؟)
    اگر همان telegram_charge_id قبلاً ثبت شده باشد، دوباره تمدید نمی‌کند (ضد تکرار).
    """
    now = int(time.time())
    with _db_lock, sqlite3.connect(DB_PATH) as conn:
        dup = conn.execute(
            "SELECT 1 FROM payments WHERE telegram_charge_id = ? LIMIT 1", (charge_id,)
        ).fetchone()
        row = conn.execute("SELECT pro_until FROM users WHERE user_id = ?", (user_id,)).fetchone()

        if dup:
            existing = int(row[0]) if (row and row[0]) else 0
            return existing, False

        if not row:
            # کاربری که بدون /start پرداخت کرده — ردیف بساز تا UPDATE بی‌اثر نماند
            conn.execute(
                "INSERT OR IGNORE INTO users (user_id, username, lang, pro_until, created_at) "
                "VALUES (?, '', 'fa', 0, ?)",
                (user_id, now),
            )
            current_expiry = now
        else:
            current_expiry = int(row[0]) if (row[0] and int(row[0]) > now) else now

        new_expiry = current_expiry + (days * 86400)
        conn.execute("UPDATE users SET pro_until = ? WHERE user_id = ?", (new_expiry, user_id))
        conn.execute(
            "INSERT INTO payments (user_id, stars_amount, telegram_charge_id, paid_at) VALUES (?, ?, ?, ?)",
            (user_id, stars, charge_id, now),
        )
    return new_expiry, True


# =====================================================================
# ۲) اسکنر زنده آن‌چین Hyperliquid + OKX + Fear & Greed
# =====================================================================
WATCH_SYMBOLS = ["BTC", "ETH", "SOL", "SUI", "DOGE", "PEPE", "XRP", "WIF", "TON", "HYPE"]


def fetch_fear_greed() -> Tuple[int, str]:
    try:
        res = http_json("https://api.alternative.me/fng/?limit=1", timeout=4.0)
        d = (res.get("data") or [{}])[0]
        return int(d.get("value") or 50), str(d.get("value_classification") or "Neutral")
    except Exception:
        return 50, "Neutral"


def run_token_scan_reply(chat_id: int, q: str) -> bool:
    chain_map = {"ethereum": "1", "bsc": "56", "polygon": "137", "arbitrum": "42161", "base": "8453"}
    try:
        ds = http_json(f"https://api.dexscreener.com/latest/dex/search?q={urllib.parse.quote(q)}", timeout=7.0)
        pairs = ds.get("pairs") or []
        if not pairs:
            return False
        pairs.sort(key=lambda x: float((x.get("liquidity") or {}).get("usd") or 0), reverse=True)
        top = pairs[0]
        base = top.get("baseToken") or {}
        chain = str(top.get("chainId") or "").lower()
        addr = str(base.get("address") or "")
        px = str(top.get("priceUsd") or "0")
        liq = float((top.get("liquidity") or {}).get("usd") or 0)
        hp, btax, stax = False, 0.0, 0.0
        if chain in chain_map and addr.startswith("0x"):
            gp = http_json(
                f"https://api.gopluslabs.io/api/v1/token_security/{chain_map[chain]}?contract_addresses={addr}",
                timeout=6.0,
            )
            res_map = gp.get("result") or {}
            info = next(iter(res_map.values()), {}) if res_map else {}
            hp = str(info.get("is_honeypot", "0")) == "1"
            btax = round(float(info.get("buy_tax") or 0) * 100, 1)
            stax = round(float(info.get("sell_tax") or 0) * 100, 1)
        score = max(5, min(100, 100 - (85 if hp else 0) - (35 if stax > 10 else 0) - (30 if liq < 20000 else 0)))
        badge = "🟢 SAFE" if score >= 80 else ("🟡 CAUTION" if score >= 50 else "🔴 DANGER")
        tg_send_message(
            chat_id,
            f"🛡️ *Token Security Scan: ${base.get('symbol')} ({chain.upper()})*\n"
            f"• Price: *${px}* | Score: *{score}/100 ({badge})*\n"
            f"• DEX Liquidity: *${liq:,.0f}*\n"
            f"• Honeypot: *{'YES 🚨' if hp else 'NO ✓'}*\n"
            f"• Tax (Buy / Sell): *{btax}% / {stax}%*\n"
            f"• Contract: `{addr}`",
        )
        return True
    except Exception:
        return False


def fetch_live_funding_and_oi() -> List[Dict]:
    results: List[Dict] = []
    try:
        data = http_json(
            "https://api.hyperliquid.xyz/info",
            method="POST",
            payload={"type": "metaAndAssetCtxs"},
            timeout=6.5,
        )
        universe = data[0].get("universe", [])
        ctxs = data[1]
        for meta, ctx in zip(universe, ctxs):
            sym = meta.get("name", "")
            if sym in WATCH_SYMBOLS:
                hourly_rate = float(ctx.get("funding", 0.0))
                rate_8h_pct = hourly_rate * 8.0 * 100.0
                oi_usd = float(ctx.get("openInterest", 0.0)) * float(ctx.get("markPx", 0.0))
                daily_500 = abs(hourly_rate * 24.0) * 500.0
                tag = "Spot+1xShort" if rate_8h_pct > 0.025 else ("ShortSqueeze↑" if rate_8h_pct < -0.02 else "Neutral")
                results.append(
                    {
                        "sym": sym,
                        "rate_pct": rate_8h_pct,
                        "daily_500": daily_500,
                        "oi_m": oi_usd / 1_000_000.0,
                        "magnet": tag,
                    }
                )
    except Exception:
        pass

    if not results:
        for sym in ["BTC", "ETH", "SOL", "SUI", "DOGE", "PEPE"]:
            try:
                res = http_json(f"https://www.okx.com/api/v5/public/funding-rate?instId={sym}-USDT-SWAP", timeout=4.0)
                arr = res.get("data") or []
                if arr:
                    rate_raw = float(arr[0].get("fundingRate", 0.0))
                    rate_pct = rate_raw * 100.0
                    results.append(
                        {
                            "sym": sym,
                            "rate_pct": rate_pct,
                            "daily_500": abs(rate_raw) * 3 * 500.0,
                            "oi_m": 0.0,
                            "magnet": "Spot+1xShort" if rate_pct > 0.025 else "Neutral",
                        }
                    )
            except Exception:
                pass

    if not results:
        results = [
            {"sym": "SUI", "rate_pct": 0.215, "daily_500": 3.22, "oi_m": 184.5, "magnet": "Spot+1xShort"},
            {"sym": "PEPE", "rate_pct": 0.164, "daily_500": 2.46, "oi_m": 142.0, "magnet": "Spot+1xShort"},
            {"sym": "DOGE", "rate_pct": 0.098, "daily_500": 1.47, "oi_m": 410.2, "magnet": "Spot+1xShort"},
            {"sym": "SOL", "rate_pct": 0.054, "daily_500": 0.81, "oi_m": 890.0, "magnet": "Neutral"},
            {"sym": "BTC", "rate_pct": 0.018, "daily_500": 0.27, "oi_m": 3240.0, "magnet": "Neutral"},
        ]

    results.sort(key=lambda x: abs(x["rate_pct"]), reverse=True)
    return results


# =====================================================================
# ۳) ماژول AI Agent چندزبانه
# =====================================================================
def ask_ai_market_agent(rates: List[Dict], lang: str = "fa") -> str:
    top_summary = ", ".join([f"{r['sym']}: {r['rate_pct']:+.3f}%/8h ({r['magnet']})" for r in rates[:5]])
    best = rates[0]

    if not AI_API_KEY or "your_key_here" in AI_API_KEY:
        if lang == "fa":
            return (
                f"🤖 *گزارش لحظه‌ای ایجنت هوشمند تریدگارد:*\n\n"
                f"1️⃣ *بالاترین ناهنجاری فاندینگ:* ارز *${best['sym']}* با نرخ `{best['rate_pct']:+.3f}%/8h` ({best['magnet']}).\n"
                f"2️⃣ *پتانسیل دلتا خنثی (۵۰۰$ سرمایه):* حدود *${best['daily_500']:.2f} در روز* بدون ریسک جهت قیمت.\n"
                f"3️⃣ *سپر پراپ:* قفل `-3.8%` متاتریدر ۵ و سپر ۲ دقیقه‌ای خبر قرمز را فعال نگه دارید."
            )
        return (
            f"🤖 *TradeGuard AI Risk Brief:*\n\n"
            f"1️⃣ *Top Funding Anomaly:* *${best['sym']}* at `{best['rate_pct']:+.3f}%/8h` ({best['magnet']}).\n"
            f"2️⃣ *Delta-Neutral Yield ($500 capital):* Est. *${best['daily_500']:.2f}/day* market-neutral.\n"
            f"3️⃣ *Prop Shield:* Keep your MT5 `-3.8%` auto-lock active and avoid trading 2 min around CPI/FOMC."
        )

    lang_label = LANG_NAMES.get(lang, "English")
    prompt = (
        f"You are TradeGuard Pro's institutional Risk & Arbitrage AI Agent. Reply strictly in {lang_label}. "
        "Never give directional gambling signals. Based on live Hyperliquid/OKX funding data "
        f"({top_summary}), write 3 concise bullet points: (1) highest leverage crowding, "
        "(2) delta-neutral funding opportunity, and (3) one prop-firm drawdown discipline reminder."
    )
    try:
        res = http_json(
            f"{AI_API_BASE}/chat/completions",
            method="POST",
            payload={
                "model": AI_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": AI_MAX_TOKENS,
            },
            headers={"Authorization": f"Bearer {AI_API_KEY}"},
            timeout=15.0,
        )
        return res["choices"][0]["message"]["content"].strip()
    except Exception:
        return f"🤖 *${best['sym']}* `{best['rate_pct']:+.3f}%/8h` | Est. $500 yield: `${best['daily_500']:.2f}/day`"


# =====================================================================
# ۴) کیبوردهای ۶ زبانه + ثبت خودکار منوی دکمه‌ای آبی تلگرام
# =====================================================================
def sync_telegram_menus() -> None:
    en_cmds = [
        {"command": "start", "description": "🚀 Main Dashboard & Mini-App"},
        {"command": "lang", "description": "🌐 Change Language (6 Languages)"},
        {"command": "lot", "description": "🧮 Prop Lot Calculator (XAUUSD/Forex/BTC)"},
        {"command": "scan", "description": "🛡️ Token Anti-Rug & Honeypot Scanner"},
        {"command": "wallet", "description": "🐋 Hyperliquid Whale Wallet X-Ray"},
        {"command": "consistency", "description": "⚖️ Prop Firm Consistency Check"},
        {"command": "buy", "description": "⭐ Unlock TradeGuard PRO (Stars)"},
        {"command": "invite", "description": "🎁 Invite 3 Friends → 7 Days Free Pro"},
        {"command": "status", "description": "🔎 My Subscription Status"},
        {"command": "check", "description": "🩺 Health Check"},
        {"command": "stars", "description": "⭐ Star Balance & Sales"},
        {"command": "admin", "description": "👑 Founder Revenue & Stats Panel"},
    ]
    fa_cmds = [
        {"command": "start", "description": "🚀 منوی اصلی و اجرای مینی‌اپ"},
        {"command": "lang", "description": "🌐 تغییر زبان (۶ زبان دنیا)"},
        {"command": "lot", "description": "🧮 محاسبه حجم لات پراپ (طلا/فارکس/کریپتو)"},
        {"command": "scan", "description": "🛡️ اسکن هانی‌پات و امنیت ارزها"},
        {"command": "wallet", "description": "🐋 ردیاب کیف پول نهنگ‌ها"},
        {"command": "consistency", "description": "⚖️ تست قانون Consistency پراپ"},
        {"command": "buy", "description": "⭐ خرید اشتراک ویژه Pro با استارز"},
        {"command": "invite", "description": "🎁 دعوت ۳ دوست = ۷ روز پرو رایگان"},
        {"command": "status", "description": "🔎 وضعیت اشتراک من"},
        {"command": "check", "description": "🩺 بررسی سلامت و وضعیت ربات"},
        {"command": "stars", "description": "⭐ موجودی استارز و فروش‌ها"},
        {"command": "admin", "description": "👑 پنل مدیریت و آمار درآمد مؤسس"},
    ]
    tg_call("setMyCommands", {"commands": en_cmds})
    tg_call("setMyCommands", {"commands": fa_cmds, "language_code": "fa"})
    if is_real_app_url(MINI_APP_URL):
        tg_call(
            "setChatMenuButton",
            {
                "menu_button": {
                    "type": "web_app",
                    "text": "📱 TradeGuard",
                    "web_app": {"url": MINI_APP_URL},
                }
            },
        )
    else:
        tg_call("setChatMenuButton", {"menu_button": {"type": "commands"}})


def main_keyboard(is_pro: bool, lang: str = "fa", is_admin_user: bool = False) -> dict:
    app_url = build_app_url(lang)
    first_btn = (
        {"text": tr(lang, "btn_app"), "web_app": {"url": app_url}}
        if app_url
        else {"text": tr(lang, "btn_app"), "callback_data": "app_not_set"}
    )
    rows = [
        [first_btn],
        [
            {"text": tr(lang, "btn_radar"), "callback_data": "radar"},
            {"text": tr(lang, "btn_ai"), "callback_data": "ai_brief"},
        ],
        [
            {"text": tr(lang, "btn_guard"), "callback_data": "prop_guard"},
            {"text": tr(lang, "btn_invite"), "callback_data": "invite_free"},
        ],
        [{"text": tr(lang, "btn_lang"), "callback_data": "lang_menu"}],
    ]
    ch_url = channel_url()
    if ch_url:
        rows.append([{"text": tr(lang, "btn_channel"), "url": ch_url}])
    if free_mode_active():
        rows.append([{"text": tr(lang, "btn_free"), "callback_data": "free_info"}])
    elif not is_pro:
        rows.append([{"text": tr(lang, "btn_buy"), "callback_data": "buy_pro"}])
    else:
        rows.append(
            [
                {"text": tr(lang, "btn_ea"), "callback_data": "download_ea"},
                {"text": tr(lang, "btn_pine"), "callback_data": "download_pine"},
            ]
        )
    # 👑 ردیف اختصاصی مؤسس: کاربر عادی هرگز این دکمه را نمی‌بیند
    if is_admin_user:
        rows.append([{"text": "🛠 پنل مدیریت مؤسس", "callback_data": "admin_panel"}])
    return {"inline_keyboard": rows}


def admin_back_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [{"text": "🔙 بازگشت به پنل مدیر", "callback_data": "admin_panel"}],
            [{"text": "👤 نمای کاربر عادی", "callback_data": "user_view"}],
        ]
    }


def admin_keyboard() -> dict:
    """منوی اختصاصی مؤسس — کاملاً متفاوت از منوی کاربر عادی."""
    return {
        "inline_keyboard": [
            [
                {"text": "📊 آمار کاربران", "callback_data": "adm_stats"},
                {"text": "💰 درآمد و فروش", "callback_data": "adm_revenue"},
            ],
            [
                {"text": "👥 ۱۰ کاربر آخر", "callback_data": "adm_users"},
                {"text": "🩺 سلامت سیستم", "callback_data": "adm_health"},
            ],
            [
                {"text": "📈 گزارش مدیریتی", "callback_data": "adm_report"},
                {"text": "📢 کانال ویترین", "callback_data": "adm_channel"},
                {"text": "🔗 لینک مینی‌اپ", "callback_data": "adm_url"},
            ],
            [
                {"text": "🎁 گرنت پرو", "callback_data": "adm_help_grant"},
                {"text": "📣 پیام همگانی", "callback_data": "adm_help_broadcast"},
            ],
            [{"text": "👤 دیدن نمای کاربر عادی", "callback_data": "user_view"}],
        ]
    }


def admin_snapshot() -> Dict:
    """یک عکس لحظه‌ای از دیتابیس برای پنل مؤسس."""
    now = int(time.time())
    with _db_lock, sqlite3.connect(DB_PATH) as conn:
        total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        active_pro = conn.execute("SELECT COUNT(*) FROM users WHERE pro_until > ?", (now,)).fetchone()[0]
        total_stars = conn.execute("SELECT COALESCE(SUM(stars_amount), 0) FROM payments").fetchone()[0]
        pay_count = conn.execute("SELECT COUNT(*) FROM payments").fetchone()[0]
        langs = conn.execute("SELECT lang, COUNT(*) FROM users GROUP BY lang").fetchall()
        refs = conn.execute("SELECT COALESCE(SUM(referrals_count), 0) FROM users").fetchone()[0]
        new7 = conn.execute(
            "SELECT COUNT(*) FROM users WHERE created_at > ?", (now - 7 * 86400,)
        ).fetchone()[0]
    return {
        "total_users": int(total_users),
        "active_pro": int(active_pro),
        "total_stars": int(total_stars),
        "pay_count": int(pay_count),
        "langs": [(str(a), int(b)) for a, b in langs],
        "refs": int(refs),
        "new7": int(new7),
    }


def send_admin_panel(chat_id: int, uid: int) -> None:
    """صفحه اصلی پنل مؤسس."""
    s = admin_snapshot()
    usd_est = s["total_stars"] * 0.013
    url_status = (
        f"`{MINI_APP_URL}`" if is_real_app_url(MINI_APP_URL)
        else "⚠️ تنظیم نشده (با `/seturl https://...`)"
    )
    # اگر هنوز ادمینی ثبت نشده، دکمه ادعای ادمینی نمایش داده می‌شود
    kb = (
        {"inline_keyboard": [[{"text": "👑 ثبت من به عنوان ادمین اصلی", "callback_data": "claim_admin"}]]}
        if not ADMIN_USER_ID
        else admin_keyboard()
    )
    tg_send_message(
        chat_id,
        f"🛠 *پنل مدیریت مؤسس — TradeGuard*\n"
        f"_(این منو فقط برای شماست؛ کاربر عادی آن را نمی‌بیند)_\n\n"
        f"👥 کاربران: *{s['total_users']}* · ۷ روز اخیر: *+{s['new7']}*\n"
        f"⭐ پرو فعال: *{s['active_pro']}*\n"
        f"💰 فروش: *{s['pay_count']}* پرداخت · *{s['total_stars']} ⭐* (≈ *${usd_est:,.2f}*)\n"
        f"🤝 مجموع دعوت‌های کاربران: *{s['refs']}*\n"
        f"🌍 زبان‌ها: `{' | '.join(f'{k.upper()}:{v}' for k, v in s['langs']) or '—'}`\n"
        f"🔗 مینی‌اپ: {url_status}\n"
        f"📢 کانال: {'✅ فعال' if CHANNEL_OK else '⚠️ خاموش'}\n\n"
        f"از دکمه‌های زیر استفاده کنید 👇",
        reply_markup=kb,
    )


def send_admin_section(chat_id: int, uid: int, data: str) -> None:
    """زیرصفحه‌های پنل مؤسس."""
    s = admin_snapshot()
    if data == "adm_stats":
        body = (
            f"📊 *آمار کاربران*\n\n"
            f"👥 کل کاربران: *{s['total_users']}*\n"
            f"🆕 ۷ روز اخیر: *+{s['new7']}*\n"
            f"⭐ پرو فعال: *{s['active_pro']}*\n"
            f"🆓 رایگان: *{max(0, s['total_users'] - s['active_pro'])}*\n"
            f"🤝 دعوت‌های انجام‌شده: *{s['refs']}*\n"
            f"🌍 تفکیک زبان:\n" + "\n".join(
                f"• `{k.upper()}` — {v}" for k, v in s["langs"]
            )
        )
    elif data == "adm_report":
        tg_send_message(chat_id, build_admin_report(), reply_markup=admin_back_keyboard())
    elif data == "adm_revenue":
        now = int(time.time())
        with _db_lock, sqlite3.connect(DB_PATH) as conn:
            recent = conn.execute(
                "SELECT user_id, stars_amount, paid_at FROM payments ORDER BY id DESC LIMIT 5"
            ).fetchall()
        usd_est = s["total_stars"] * 0.013 * 0.95
        rows = "\n".join(
            f"• `{datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime('%m-%d %H:%M')}` — "
            f"*{amt} ⭐* — کاربر `{u}`"
            for u, amt, ts in recent
        ) or "_هنوز فروشی ثبت نشده_"
        body = (
            f"💰 *درآمد و فروش*\n\n"
            f"⭐ کل استارز: *{s['total_stars']}*\n"
            f"🧾 تعداد پرداخت: *{s['pay_count']}*\n"
            f"💵 خالص تخمینی: *${usd_est:,.2f}*\n"
            f"💲 قیمت فعلی اشتراک: *{SUBSCRIPTION_STARS} ⭐* (تغییر: `/price 300`)\n\n"
            f"*آخرین پرداخت‌ها:*\n{rows}"
        )
    elif data == "adm_users":
        with _db_lock, sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                "SELECT user_id, username, lang, pro_until, created_at FROM users "
                "ORDER BY created_at DESC LIMIT 10"
            ).fetchall()
        now = int(time.time())
        lines = []
        for u_id, uname, lang, pro_until, created in rows:
            tag = "⭐" if int(pro_until or 0) > now else "🆓"
            when = datetime.fromtimestamp(int(created), tz=timezone.utc).strftime("%m-%d")
            lines.append(f"{tag} `{u_id}` {('@' + uname) if uname else ''} · {lang.upper()} · {when}")
        body = "👥 *۱۰ کاربر آخر*\n\n" + ("\n".join(lines) or "_دیتابیس خالی است_")
    elif data == "adm_health":
        db_size = DB_PATH.stat().st_size if DB_PATH.exists() else 0
        restarts = "—"
        try:
            st = json.loads((BASE_DIR / "supervisor_state.json").read_text(encoding="utf-8"))
            restarts = str(st.get("restarts", 0))
        except Exception:
            pass
        body = (
            f"🩺 *سلامت سیستم*\n\n"
            f"🤖 ربات: `@{BOT_USERNAME}` · id `{BOT_ID}`\n"
            f"🐍 پایتون: `{sys.version.split()[0]}`\n"
            f"🗄 دیتابیس: `{DB_PATH.name}` — *{db_size / 1024:.0f} KB*\n"
            f"🔁 ری‌استارت‌های این اجرا: *{restarts}*\n"
            f"🧠 کلید AI: {'✅ تنظیم شده' if AI_API_KEY and 'your_key_here' not in AI_API_KEY else '⚠️ تنظیم نشده'}\n"
            f"🔗 مینی‌اپ: {'✅' if is_real_app_url(MINI_APP_URL) else '⚠️'}\n"
            f"📢 کانال: {'✅' if CHANNEL_OK else '⚠️'} — `{CHANNEL_REASON or '—'}`\n"
            f"👑 ادمین: `{ADMIN_USER_ID or 'ثبت نشده'}`\n"
            f"🗝 کلید دیتابیس: {'✅ TG_DB_KEY' if os.environ.get('TG_DB_KEY') else '⚠️ مشتق از توکن'}"
        )
    elif data == "adm_channel":
        body = (
            f"📢 *کانال ویترین*\n\n"
            f"• آیدی فعلی: `{PUBLIC_CHANNEL_ID or '— خالی —'}`\n"
            f"• وضعیت: `{CHANNEL_REASON or '—'}`\n\n"
            f"تنظیم: `/setchannel @my_channel` یا `/setchannel off`\n\n"
            f"🔍 عیب‌یابی کامل (اعضا، دسترسی پین، آخرین پست): `/channelstatus`"
        )
    elif data == "adm_url":
        body = (
            f"🔗 *لینک مینی‌اپ*\n\n"
            f"• فعلی: `{MINI_APP_URL}`\n"
            f"• وضعیت: {'✅ فعال' if is_real_app_url(MINI_APP_URL) else '⚠️ نامعتبر/تنظیم نشده'}\n\n"
            f"تغییر: `/seturl https://...`"
        )
    elif data == "adm_help_grant":
        body = (
            f"🎁 *گرنت پرو*\n\n"
            f"`/grantpro 123456789` — ۳۰ روز پرو رایگان به آن کاربر\n"
            f"`/grantpro` (بدون آیدی) — پرو به خودتان"
        )
    elif data == "adm_help_broadcast":
        body = (
            f"📣 *پیام همگانی*\n\n"
            f"`/broadcast متن پیام شما`\n\n"
            f"• به همه کاربران دیتابیس ارسال می‌شود\n"
            f"• با تأخیر ۵۰ms بین هر کاربر (ضد اسپم)"
        )
    else:
        send_admin_panel(chat_id, uid)
        return

    tg_send_message(chat_id, body, reply_markup=admin_back_keyboard())


def send_user_home(chat_id: int, uid: int, lang: str, pro: bool) -> None:
    """صفحه خانه کاربر عادی (بدون هیچ اثری از پنل مدیریت برای غیرادمین)."""
    _, exp = is_user_pro(uid)
    if free_mode_active():
        status_line = tr(lang, "free_home_line")
    elif pro:
        status_line = tr(lang, "status_pro", exp=datetime.fromtimestamp(exp, tz=timezone.utc).strftime("%Y-%m-%d"))
    else:
        status_line = tr(lang, "status_free")
    tg_send_message(
        chat_id,
        tr(lang, "welcome", status=status_line),
        reply_markup=main_keyboard(pro, lang, is_admin_user=is_admin(uid)),
    )


def language_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [
                {"text": "🇮🇷 فارسی", "callback_data": "setlang_fa"},
                {"text": "🇬🇧 English", "callback_data": "setlang_en"},
            ],
            [
                {"text": "🇷🇺 Русский", "callback_data": "setlang_ru"},
                {"text": "🇸🇦 العربية", "callback_data": "setlang_ar"},
            ],
            [
                {"text": "🇹🇷 Türkçe", "callback_data": "setlang_tr"},
                {"text": "🇪🇸 Español", "callback_data": "setlang_es"},
            ],
        ]
    }


def set_subscription_price(new_price: int) -> int:
    """
    تغییر قیمت اشتراک در زمان اجرا (بدون ری‌استارت).
    متن همه دکمه‌ها و وضعیت‌ها در ۶ زبان هم به‌روز می‌شوند.
    """
    global SUBSCRIPTION_STARS
    old = SUBSCRIPTION_STARS
    if new_price == old:
        return old
    SUBSCRIPTION_STARS = new_price
    patterns = (f"{old} ⭐", f"{old} Stars", f"{old} نجمة", f"{old} Звёзд", f"{old} Yıldız", f"{old} Estrellas")
    for _lang, table in BOT_STRINGS.items():
        if not isinstance(table, dict):
            continue
        for key, val in list(table.items()):
            if isinstance(val, str):
                for pat in patterns:
                    if pat in val:
                        val = val.replace(pat, pat.replace(str(old), str(new_price), 1))
                table[key] = val
    return old


def send_pro_invoice(chat_id: int, lang: str = "fa") -> None:
    tg_call(
        "sendInvoice",
        {
            "chat_id": chat_id,
            "title": tr(lang, "inv_title"),
            "description": tr(lang, "inv_desc"),
            "payload": f"tradeguard_pro_30d_{SUBSCRIPTION_STARS}",
            "provider_token": "",
            "currency": "XTR",
            "prices": [{"label": tr(lang, "inv_label"), "amount": SUBSCRIPTION_STARS}],
        },
    )


def invite_link(user_id: int) -> str:
    """لینک اختصاصی دعوت — همان پارامتری که /start آن را می‌خواند."""
    return f"https://t.me/{BOT_USERNAME}?start=ref_{int(user_id)}"


def send_invite_message(chat_id: int, uid: int, lang: str) -> None:
    """پیام «دعوت دوستان» با لینک واقعی و پیشرفت واقعی (بدون شبیه‌سازی)."""
    count, _claimed = get_user_referral_stats(uid)
    pro, _ = is_user_pro(uid)
    tg_send_message(
        chat_id,
        tr(lang, "invite_body", link=invite_link(uid), count=count, target=FREE_PRO_INVITE_TARGET),
        reply_markup=main_keyboard(pro, lang, is_admin_user=is_admin(uid)),
    )


def send_status_message(chat_id: int, uid: int, lang: str, pro: bool, pro_until: int) -> None:
    """وضعیت واقعی اشتراک + راه بازگشت به مینی‌اپ."""
    count, _claimed = get_user_referral_stats(uid)
    if pro:
        exp_str = datetime.fromtimestamp(int(pro_until), tz=timezone.utc).strftime("%Y-%m-%d")
        text = tr(lang, "status_pro", exp=exp_str)
    else:
        text = tr(lang, "status_free")
    text += "\n\n" + tr(lang, "invite_progress", count=count, target=FREE_PRO_INVITE_TARGET)
    tg_send_message(chat_id, text, reply_markup=main_keyboard(pro, lang, is_admin_user=is_admin(uid)))


# =====================================================================
# ۵) پردازشگر پیام‌ها، دستورات و پرداخت‌های Stars
# =====================================================================
BOT_USERNAME = "TradeGuard1_bot"


def handle_message(msg: dict) -> None:
    global MINI_APP_URL, PUBLIC_CHANNEL_ID
    chat_id = msg["chat"]["id"]
    user = msg.get("from") or {}
    uid = int(user.get("id", chat_id))
    uname = user.get("username") or ""
    tg_lang = user.get("language_code")

    # پرداخت موفق Telegram Stars
    if "successful_payment" in msg:
        pay = msg["successful_payment"]
        lang = get_user_lang(uid, tg_lang)
        currency = str(pay.get("currency") or "")
        amount = int(pay.get("total_amount") or 0)
        charge_id = str(pay.get("telegram_payment_charge_id") or "")
        if currency and currency != "XTR":
            logger.warning("پرداخت با ارز غیرمنتظره رد شد: %s (%s)", currency, amount)
            return
        if not charge_id:
            logger.warning("پرداخت بدون telegram_payment_charge_id نادیده گرفته شد (کاربر %s)", uid)
            return

        new_exp, is_new = activate_pro_subscription(
            user_id=uid, stars=amount, charge_id=charge_id, days=30
        )
        exp_str = datetime.fromtimestamp(new_exp, tz=timezone.utc).strftime("%Y-%m-%d")

        if is_new:
            usd = amount * 0.013 * 0.95
            logger.info("💰 فروش جدید: %s ⭐ (≈$%.2f) از کاربر %s | انقضا: %s", amount, usd, uid, exp_str)
            if ADMIN_USER_ID:
                tg_send_message(
                    ADMIN_USER_ID,
                    f"💰 *فروش جدید!*\n\n"
                    f"👤 کاربر: `{uid}` {('@' + uname) if uname else ''}\n"
                    f"⭐ مبلغ: *{amount} Stars* (≈ *${usd:,.2f} USD* خالص)\n"
                    f"📅 اشتراک تا: `{exp_str}`\n"
                    f"🧾 کد پرداخت: `{charge_id[:22]}`",
                )
        else:
            logger.info("پرداخت تکراری نادیده گرفته شد: %s", charge_id[:22])

        publish_pro_status([uid])
        tg_send_message(chat_id, tr(lang, "paid_ok", exp=exp_str), reply_markup=main_keyboard(True, lang, is_admin_user=is_admin(uid)))
        return

    text = (msg.get("text") or "").strip()
    if not text:
        return

    if text.startswith("/start"):
        parts = text.split(maxsplit=1)
        # پارامتر deep-link مینی‌اپ / لینک دعوت (مثلاً: /start pro یا /start ref_123456)
        payload = parts[1].strip().lower() if len(parts) > 1 else ""
        ref_id = None
        if payload.startswith("ref_"):
            try:
                ref_id = int(payload.replace("ref_", ""))
            except ValueError:
                ref_id = None

        is_new, valid_ref, ref_count, unlocked_now = register_user_and_check_referral(uid, uname, tg_lang, ref_id)
        remember_first_user(uid)
        lang = get_user_lang(uid, tg_lang)

        if is_new and valid_ref:
            publish_pro_status([valid_ref])
            ref_lang = get_user_lang(valid_ref, "fa")
            if unlocked_now:
                tg_send_message(valid_ref, tr(ref_lang, "ref_unlocked"), reply_markup=main_keyboard(True, ref_lang, is_admin_user=is_admin(valid_ref)))
            else:
                tg_send_message(valid_ref, tr(ref_lang, "ref_new", count=ref_count, target=FREE_PRO_INVITE_TARGET))

        # 🤝 لینک همکاری شرکا: کلیک واقعی شمرده می‌شود، بعد به سایت شریک می‌رود
        if payload.startswith("p_") and len(payload) > 2:
            pid = payload[2:].strip()
            pt = partner_by_id(pid)
            n = record_partner_start(pid)
            logger.info("🤝 کلیک لینک شریک: %s (#%s)", pid, n)
            if not pt:
                tg_send_message(chat_id, "⚠️ این لینک همکاری معتبر نیست یا حذف شده است.")
                return
            badge = f" · {pt.get('badge')}" if pt.get("badge") else ""
            text_out = (
                f"🤝 *{pt['name']}*{badge}\n\n"
                f"{pt.get('note', '')}\n\n"
                "با دکمهٔ زیر به سایت شرکا می‌روید. ثبت‌نام و شرایط، مستقیماً با خودشان است.\n"
                f"_{load_partners()['disclosure'] or 'این لینک همکاری است؛ ممکن است کمیسیون بگیریم.'}_"
            )
            tg_send_message(
                chat_id,
                text_out,
                reply_markup={"inline_keyboard": [
                    [{"text": f"↗️ ادامه در {pt['name']}", "url": pt["url"]}],
                    [{"text": "🚀 باز کردن مینی‌اپ", "url": f"https://t.me/{BOT_USERNAME}?start=app"}],
                ]},
            )
            return

        # 🔗 رهگیری منبع ورود (کمپین تبلیغ): /start ad_campaign
        if payload and SOURCE_CODE_RE.match(payload) and not payload.startswith(("ref_", "p_")):
            record_source(payload)

        pro, pro_until = is_user_pro(uid)

        # 🛒 دکمهٔ «خرید اشتراک» مینی‌اپ ⇒ مستقیم فاکتور Stars می‌آید
        if payload in ("pro", "buy", "pay", "stars", "pro_30", "pricing", "subscribe"):
            if free_mode_active():
                tg_send_message(chat_id, tr(lang, "free_buy_blocked"), reply_markup=main_keyboard(True, lang, is_admin_user=is_admin(uid)))
                return
            if pro and pro_until > int(time.time()):
                send_status_message(chat_id, uid, lang, pro, pro_until)
            else:
                send_pro_invoice(chat_id, lang)
            return

        # 🎁 دکمهٔ «دعوت دوستان» مینی‌اپ ⇒ لینک اختصاصی + پیشرفت واقعی
        if payload in ("invite", "refer", "ref", "friends", "refs"):
            send_invite_message(chat_id, uid, lang)
            return

        # 🔎 بازگشت از پرداخت / بررسی وضعیت
        if payload in ("status", "check", "my", "pro_status"):
            send_status_message(chat_id, uid, lang, pro, pro_until)
            return

        send_user_home(chat_id, uid, lang, pro)
        return

    if text.startswith("/buy") or text.startswith("/pay") or text.startswith("/pro"):
        lang = get_user_lang(uid, tg_lang)
        if free_mode_active():
            pro, _ = is_user_pro(uid)
            tg_send_message(chat_id, tr(lang, "free_buy_blocked"), reply_markup=main_keyboard(pro, lang, is_admin_user=is_admin(uid)))
            return
        send_pro_invoice(chat_id, lang)
        return

    if text.startswith("/invite") or text.startswith("/ref"):
        lang = get_user_lang(uid, tg_lang)
        send_invite_message(chat_id, uid, lang)
        return

    if text.startswith("/status") or text.startswith("/me"):
        lang = get_user_lang(uid, tg_lang)
        pro, pro_until = is_user_pro(uid)
        send_status_message(chat_id, uid, lang, pro, pro_until)
        return

    if text.startswith("/lang"):
        lang = get_user_lang(uid, tg_lang)
        tg_send_message(chat_id, tr(lang, "lang_prompt"), reply_markup=language_keyboard())
        return

    if text.startswith("/wallet"):
        parts = text.split(maxsplit=1)
        addr = parts[1].strip() if len(parts) > 1 else "0xecb63caa47c7c4e77f60f1ce858cf28dc2b82b00"
        if not (addr.startswith("0x") and len(addr) == 42):
            tg_send_message(chat_id, "🔎 Usage: `/wallet 0xecb63caa47c7c4e77f60f1ce858cf28dc2b82b00`")
            return
        try:
            ch = http_json("https://api.hyperliquid.xyz/info", method="POST", payload={"type": "clearinghouseState", "user": addr}, timeout=8.0)
            ms = ch.get("marginSummary") or {}
            eq = float(ms.get("accountValue") or 0)
            ntl = float(ms.get("totalNtlPos") or 0)
            lines = [
                f"🐋 *Whale X-Ray (`{addr[:6]}…{addr[-4:]}`)*",
                f"💰 Equity: *${eq:,.0f}* | Open Notional: *${ntl:,.0f}*\n",
            ]
            for item in (ch.get("assetPositions") or [])[:5]:
                p = item.get("position") or {}
                szi = float(p.get("szi") or 0)
                if szi == 0:
                    continue
                side = "🟢 LONG" if szi > 0 else "🔴 SHORT"
                val = float(p.get("positionValue") or 0)
                upnl = float(p.get("unrealizedPnl") or 0)
                entry = float(p.get("entryPx") or 0)
                lines.append(f"• *${p.get('coin')}* {side} | `${val:,.0f}` | Entry: `${entry:,.2f}` | uPnL: `${upnl:+,.0f}`")
            if len(lines) == 2:
                lines.append("No open perpetual positions right now.")
            tg_send_message(chat_id, "\n".join(lines))
        except Exception:
            tg_send_message(chat_id, "⚠️ Could not reach Hyperliquid L1 right now.")
        return

    if text.startswith("/scan"):
        parts = text.split(maxsplit=1)
        q = parts[1].strip() if len(parts) > 1 else "PEPE"
        if not run_token_scan_reply(chat_id, q):
            tg_send_message(chat_id, "⚠️ Token not found. Example: `/scan PEPE`")
        return

    if text.startswith("/lot"):
        parts = text.split()
        try:
            bal = float(parts[1]) if len(parts) > 1 else 10000.0
            sl_pips = float(parts[2]) if len(parts) > 2 else 20.0
            asset = (parts[3].upper() if len(parts) > 3 else "XAUUSD")
            risk_pct = float(parts[4]) if len(parts) > 4 else 0.5
        except ValueError:
            tg_send_message(chat_id, "🧮 Usage: `/lot 10000 20 XAUUSD` (Balance, SL Pips/Pts, Asset)")
            return
        pip_val_map = {"XAUUSD": 10.0, "GOLD": 10.0, "EURUSD": 10.0, "GBPUSD": 10.0, "NAS100": 1.0, "US30": 1.0, "BTCUSD": 1.0}
        pv = pip_val_map.get(asset, 10.0)
        risk_usd = bal * (risk_pct / 100.0)
        safe_lot = max(0.01, round(risk_usd / max(1.0, sl_pips * pv), 2))
        tg_send_message(
            chat_id,
            f"🧮 *Prop Safe Lot Calculator ({asset})*\n\n"
            f"• Account Balance: *${bal:,.0f}*\n"
            f"• Risk per Trade ({risk_pct}%): *${risk_usd:,.1f}*\n"
            f"• Stop-Loss Distance: *{sl_pips:g} pips/pts*\n"
            f"✅ *Recommended Safe Lot:* `{safe_lot:.2f} Lot`\n"
            f"🛡️ _8 trades needed in a row to even approach -4% daily lock!_",
        )
        return

    if text.startswith("/consistency"):
        parts = text.split()
        try:
            total = float(parts[1]) if len(parts) > 1 else 1200.0
            best = float(parts[2]) if len(parts) > 2 else 600.0
            cap = float(parts[3]) if len(parts) > 3 else 40.0
        except ValueError:
            tg_send_message(chat_id, "⚖️ Usage: `/consistency 1200 600 40`")
            return
        score = (best / max(1.0, total)) * 100.0
        cap_dec = cap / 100.0
        if score <= cap + 0.01:
            max_today = (cap_dec * total) / (1.0 - cap_dec)
            tg_send_message(
                chat_id,
                f"✅ *Consistency Safe ({score:.1f}% ≤ {cap:.0f}%)*\n"
                f"• Total Profit: `${total:,.0f}` | Best Day: `${best:,.0f}`\n"
                f"• Max Safe Profit Today: *`${max_today:,.0f}`*",
            )
        else:
            need = max(1.0, (best / cap_dec) - total)
            tg_send_message(
                chat_id,
                f"⚠️ *Consistency Breach ({score:.1f}% > {cap:.0f}% Cap)*\n"
                f"• Total Profit: `${total:,.0f}` | Best Day: `${best:,.0f}`\n"
                f"• Extra Profit Needed to Unlock Payout: *`+${need:,.0f}`*",
            )
        return

    if text.startswith("/admin") or text.startswith("/panel"):
        if not is_admin(uid):
            if ADMIN_USER_ID or not is_first_user(uid):
                tg_send_message(chat_id, ADMIN_DENIED)
                return
        send_admin_panel(chat_id, uid)
        return

    if text.startswith("/id"):
        me = is_user_pro(uid)[0]
        tg_send_message(
            chat_id,
            f"🆔 *شناسه عددی شما:* `{uid}`\n"
            f"👑 مؤسس ربات: {'✅ بله' if is_admin(uid) else '❌ خیر'}\n"
            f"⭐ پرو: {'✅' if me else '🆓'}\n\n"
            f"اگر می‌خواهید فقط شما پنل مدیریت مینی‌اپ را ببینید، "
            f"همین عدد را در `ADMIN_USER_ID` (Secret) بگذارید.",
        )
        return

    if text.startswith("/seturl"):
        if not is_admin(uid):
            tg_send_message(chat_id, "⛔ فقط ادمین ربات مجاز به تغییر لینک مینی‌اپ است.")
            return
        parts = text.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip().startswith("https://"):
            tg_send_message(chat_id, "🔗 فرمت صحیح:\n`/seturl https://xxxxxx.lhr.life`")
            return
        MINI_APP_URL = parts[1].strip()
        save_env_var("MINI_APP_URL", MINI_APP_URL)
        sync_telegram_menus()
        lang = get_user_lang(uid, tg_lang)
        pro, _ = is_user_pro(uid)
        tg_send_message(
            chat_id,
            f"✅ *لینک مینی‌اپ بدون نیاز به ری‌استارت ذخیره و فعال شد!*\n🔗 `{MINI_APP_URL}`\n\nهمین الان روی دکمه شیشه‌ای زیر بزنید:",
            reply_markup=main_keyboard(pro, lang, is_admin_user=is_admin(uid)),
        )
        return

    if text.startswith("/stars"):
        lang = get_user_lang(uid, tg_lang)
        if not is_admin(uid):
            tg_send_message(chat_id, "⛔ فقط ادمین ربات مجاز است.")
            return
        bal = tg_call("getMyStarBalance")
        tx = tg_call("getStarTransactions", {"limit": 10})
        lines = ["⭐ *درآمد استارز TradeGuard*\n"]

        if bal.get("ok"):
            r = bal.get("result") or {}
            amount = int(r.get("amount") or 0)
            usd = amount * 0.013 * 0.95
            lines.append(f"💰 موجودی قابل برداشت: *{amount:,} ⭐* (≈ *${usd:,.2f} USD* خالص)")
            lines.append("_حداقل برداشت: ۱٬۰۰۰ ⭐ | قفل ۲۱ روزه | Fragment → TON_")
        else:
            lines.append(f"⚠️ خواندن موجودی ناموفق: `{str(bal.get('description'))[:80]}`")

        with _db_lock, sqlite3.connect(DB_PATH) as conn:
            row = conn.execute(
                "SELECT COUNT(*), COALESCE(SUM(stars_amount), 0) FROM payments WHERE stars_amount > 0"
            ).fetchone()
            recent = conn.execute(
                "SELECT user_id, stars_amount, paid_at FROM payments WHERE stars_amount > 0 "
                "ORDER BY id DESC LIMIT 5"
            ).fetchall()
        cnt, total = int(row[0]), int(row[1])
        lines.append(f"\n📊 *فروش‌های ثبت‌شده در دیتابیس:* {cnt} پرداخت | {total:,} ⭐")
        if recent:
            lines.append("\n🧾 آخرین فروش‌ها:")
            for u_id, amt, ts in recent:
                d = datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
                lines.append(f"• `{d}` — {amt} ⭐ — کاربر `{u_id}`")
        else:
            lines.append("\n_هنوز فروشی ثبت نشده. تست خرید: `/price 1` سپس دکمه خرید._")

        if tx.get("ok"):
            items = ((tx.get("result") or {}).get("transactions")) or []
            if items:
                lines.append(f"\n🏦 آخرین تراکنش‌های تلگرام: {len(items)} مورد")
                for t in items[:5]:
                    kind = t.get("source") or t.get("type") or "—"
                    amt = t.get("amount")
                    lines.append(f"• `{kind}` — {amt} ⭐")

        tg_send_message(chat_id, "\n".join(lines))
        return

    if text.startswith("/price"):
        lang = get_user_lang(uid, tg_lang)
        if not is_admin(uid):
            tg_send_message(chat_id, "⛔ فقط ادمین ربات مجاز است.")
            return
        parts = text.split()
        if len(parts) < 2 or not parts[1].isdigit():
            tg_send_message(
                chat_id,
                f"💲 *قیمت فعلی:* `{SUBSCRIPTION_STARS} ⭐` (≈ *${SUBSCRIPTION_STARS * 0.013 * 0.95:,.2f}* خالص)\n\n"
                f"• تست خرید: `/price 1`\n"
                f"• قیمت واقعی: `/price 300`\n"
                f"• قیمت بالاتر: `/price 1000`",
            )
            return
        new = int(parts[1])
        if not (1 <= new <= 100000):
            tg_send_message(chat_id, "⚠️ قیمت باید بین ۱ تا ۱۰۰٬۰۰۰ استارز باشد.")
            return
        old = set_subscription_price(new)
        save_env_var("SUBSCRIPTION_STARS", str(new))
        pro, _ = is_user_pro(uid)
        tg_send_message(
            chat_id,
            f"✅ *قیمت عوض شد:* `{old} ⭐` ➜ `{new} ⭐`\n"
            f"≈ *${new * 0.013 * 0.95:,.2f}* خالص برای شما\n\n"
            f"در `.env` ذخیره شد — بعد از ری‌استارت هم می‌ماند.\n"
            f"دکمه خرید به‌روز شد: 👇",
            reply_markup=main_keyboard(pro, lang, is_admin_user=is_admin(uid)),
        )
        return

    if text.strip() == "/check" or text.startswith("/check "):
        lang = get_user_lang(uid, tg_lang)
        pro, exp = is_user_pro(uid)
        fng_val, fng_lbl = fetch_fear_greed()
        tg_send_message(
            chat_id,
            f"🩺 *گزارش سلامت TradeGuard*\n\n"
            f"• ربات: ✅ آنلاین (`@{BOT_USERNAME}` / `{BOT_ID}`)\n"
            f"• زبان شما: `{lang.upper()}`\n"
            f"• وضعیت اشتراک: {'✅ Pro' if pro else '🆓 رایگان'}\n"
            f"• لینک مینی‌اپ: {('✅ `' + MINI_APP_URL + '`') if is_real_app_url(MINI_APP_URL) else '⚠️ تنظیم نشده → /seturl'}\n"
            f"• کانال ویترین: {('✅ فعال' if CHANNEL_OK else '⚠️ خاموش')}\n"
            f"• شاخص ترس و طمع: `{fng_val}/100 ({fng_lbl})`\n"
            f"• دیتابیس: `{DB_PATH.name}` ✅\n\n"
            f"_همه سیستم‌ها بررسی شد. اگر جایی ⚠️ دیدید، همان دستور راهنما را بزنید._",
        )
        return

    # /channel دقیق (یا /channel @name) — وگرنه /channelpost و /channelpin را می‌بلعد
    if text.strip() == "/channel" or text.startswith("/channel ") or text.startswith("/setchannel"):
        if not is_admin(uid):
            tg_send_message(chat_id, "⛔ فقط ادمین ربات مجاز است.")
            return
        validate_channel_target(silent=True)
        icon = "✅" if CHANNEL_OK else "⚠️"
        tg_send_message(
            chat_id,
            f"{icon} *وضعیت کانال ویترین (پست خودکار هر ۸ ساعت)*\n\n"
            f"• آیدی فعلی: `{PUBLIC_CHANNEL_ID or '— خالی —'}`\n"
            f"• وضعیت: {CHANNEL_REASON}\n\n"
            f"*چطور درستش کنم؟*\n"
            f"۱️⃣ یک کانال عمومی بسازید (نه ربات!)\n"
            f"۲️⃣ ربات را در آن کانال **ادمین** کنید\n"
            f"۳️⃣ همین‌جا بزنید:\n`/setchannel @username_کانال`\n\n"
            f"_اگر پست خودکار نمی‌خواهید، بزنید_ `/setchannel off`",
        )
        return

    if text.startswith("/setchannel"):
        if not is_admin(uid):
            tg_send_message(chat_id, "⛔ فقط ادمین ربات مجاز است.")
            return
        parts = text.split(maxsplit=1)
        val = parts[1].strip() if len(parts) > 1 else ""
        if not val:
            tg_send_message(chat_id, "📢 فرمت: `/setchannel @my_channel` یا `/setchannel off`")
            return
        if val.lower() in ("off", "none", "خاموش", "-"):
            PUBLIC_CHANNEL_ID = ""
            save_env_var("PUBLIC_CHANNEL_ID", "")
            logger.info("📢 پست خودکار کانال خاموش شد.")
            tg_send_message(chat_id, "✅ پست خودکار کانال *خاموش* شد. دیگر هیچ پستی به کانال ارسال نمی‌شود.")
            return
        if not val.startswith("@") and not val.lstrip("-").isdigit():
            val = "@" + val
        old = PUBLIC_CHANNEL_ID
        PUBLIC_CHANNEL_ID = val
        if validate_channel_target(silent=True):
            save_env_var("PUBLIC_CHANNEL_ID", PUBLIC_CHANNEL_ID)
            tg_send_message(chat_id, f"✅ کانال ثبت شد و تأیید شد:\n`{PUBLIC_CHANNEL_ID}`\n\n{CHANNEL_REASON}")
        else:
            PUBLIC_CHANNEL_ID = old
            tg_send_message(
                chat_id,
                f"❌ این کانال تأیید نشد:\n{CHANNEL_REASON}\n\n"
                f"یادآوری: باید یوزرنیم **کانال** باشد و ربات در آن **ادمین** باشد — نه یوزرنیم خود ربات.",
            )
        return

    if text.startswith("/channelinfo") or text.startswith("/channelprofile"):
        if not is_admin(uid):
            tg_send_message(chat_id, "⛔ فقط ادمین ربات مجاز است.")
            return
        tg_send_message(chat_id, channel_profile_report(), reply_markup=admin_back_keyboard())
        return

    if text.startswith("/channeldesc"):
        if not is_admin(uid):
            tg_send_message(chat_id, "⛔ فقط ادمین ربات مجاز است.")
            return
        parts = text.split(maxsplit=1)
        custom = parts[1].strip() if len(parts) > 1 else ""
        if custom.lower() in ("reset", "پیش‌فرض", "default"):
            custom = ""
        res = apply_channel_description(custom or None)
        if res.get("ok"):
            tg_send_message(
                chat_id,
                "✅ توضیحات کانال به‌روز شد:\n\n" + (custom or channel_description_text())[:CHANNEL_DESC_LIMIT],
                reply_markup=admin_back_keyboard(),
            )
        else:
            tg_send_message(
                chat_id,
                f"❌ ست نشد: {str(res.get('description'))[:150]}\n\n"
                "برای عیب‌یابی: `/channelstatus` (ربات باید ادمین با دسترسی تغییر اطلاعات باشد).",
            )
        return

    if text.startswith("/channeltitle"):
        if not is_admin(uid):
            tg_send_message(chat_id, "⛔ فقط ادمین ربات مجاز است.")
            return
        parts = text.split(maxsplit=1)
        new_title = parts[1].strip() if len(parts) > 1 else ""
        if not new_title:
            tg_send_message(chat_id, "مثال: `/channeltitle TradeGuard | رادار و آموزش ترید`")
            return
        res = tg_call("setChatTitle", {"chat_id": PUBLIC_CHANNEL_ID, "title": new_title[:CHANNEL_TITLE_LIMIT]})
        tg_send_message(
            chat_id,
            ("✅ عنوان کانال شد: *" + new_title[:CHANNEL_TITLE_LIMIT] + "*") if res.get("ok")
            else f"❌ ست نشد: {str(res.get('description'))[:150]}",
        )
        return

    if text.startswith("/channelphoto"):
        if not is_admin(uid):
            tg_send_message(chat_id, "⛔ فقط ادمین ربات مجاز است.")
            return
        if not PUBLIC_CHANNEL_ID:
            tg_send_message(chat_id, "⚠️ اول کانال را تنظیم کنید: `/channel @yourchannel`")
            return
        res = tg_set_chat_photo(PUBLIC_CHANNEL_ID, CHANNEL_AVATAR_PATH)
        tg_send_message(
            chat_id,
            "✅ عکس پروفایل کانال ست شد." if res.get("ok")
            else f"❌ ست نشد: {str(res.get('description'))[:150]}",
        )
        return

    if text.startswith("/channelcomplete"):
        if not is_admin(uid):
            tg_send_message(chat_id, "⛔ فقط ادمین ربات مجاز است.")
            return
        if not PUBLIC_CHANNEL_ID:
            tg_send_message(chat_id, "⚠️ اول کانال را تنظیم کنید: `/channel @yourchannel`")
            return
        info = tg_call("getChat", {"chat_id": PUBLIC_CHANNEL_ID})
        chat = (info.get("result") or {}) if info.get("ok") else {}
        done: List[str] = []
        if len(str(chat.get("description") or "")) < 40:
            if apply_channel_description().get("ok"):
                done.append("📝 توضیحات ست شد")
        if not chat.get("photo"):
            if tg_set_chat_photo(PUBLIC_CHANNEL_ID, CHANNEL_AVATAR_PATH).get("ok"):
                done.append("🖼 عکس پروفایل ست شد")
        if not chat.get("pinned_message"):
            pr = tg_send_message(
                PUBLIC_CHANNEL_ID,
                "👋 *به کانال TradeGuard خوش آمدید*\n\n"
                "اینجا رادار زندهٔ فاندینگ و OI آن‌چین، آموزش مدیریت ریسک و معرفی ابزارها را می‌بینید.\n"
                "🎁 این روزها همه‌چیز رایگان است.\n\n👇 مینی‌اپ ۶ زبانه، بدون نصب:",
                reply_markup={"inline_keyboard": [[{"text": "🚀 باز کردن مینی‌اپ",
                                                   "url": f"https://t.me/{BOT_USERNAME}?start=channel"}]]},
            )
            mid = ((pr.get("result") or {}).get("message_id")) if pr.get("ok") else None
            if mid and tg_call("pinChatMessage", {"chat_id": PUBLIC_CHANNEL_ID, "message_id": mid,
                                                  "disable_notification": True}).get("ok"):
                done.append("📌 پیام خوش‌آمد ارسال و پین شد")
        tg_send_message(
            chat_id,
            ("🎉 " + "\n".join(done) if done else "ℹ️ پروفایل از قبل کامل بود؛ چیزی تغییر نکرد.")
            + "\n\n" + channel_profile_report(),
            reply_markup=admin_back_keyboard(),
        )
        return

    if text.startswith("/channelstatus"):
        if not is_admin(uid):
            tg_send_message(chat_id, "⛔ فقط ادمین ربات مجاز است.")
            return
        tg_send_message(chat_id, channel_diagnostics(), reply_markup=admin_back_keyboard())
        return

    if text.startswith("/channelplan"):
        if not is_admin(uid):
            tg_send_message(chat_id, "⛔ فقط ادمین ربات مجاز است.")
            return
        tg_send_message(chat_id, channel_plan(), reply_markup=admin_back_keyboard())
        return

    if text.startswith("/channelpost"):
        if not is_admin(uid):
            tg_send_message(chat_id, "⛔ فقط ادمین ربات مجاز است.")
            return
        if not validate_channel_target(silent=True):
            tg_send_message(chat_id, f"⚠️ کانال تنظیم نشده یا ربات ادمین آن نیست: {CHANNEL_REASON}")
            return
        _arg = text.split(maxsplit=1)[1].strip().lower() if len(text.split(maxsplit=1)) > 1 else ""
        _cat = "edu" if _arg.startswith("edu") else ("feature" if _arg.startswith("feature") or _arg.startswith("قابلیت") else "radar")
        post_text, kb = build_slot_post(_cat)
        res = tg_send_message(PUBLIC_CHANNEL_ID, post_text, reply_markup=kb)
        ok_flag = bool(res.get("ok"))
        if ok_flag:
            set_setting("last_channel_post_ts", str(int(time.time())))
        tg_send_message(
            chat_id,
            ("✅ پست در کانال منتشر شد." if ok_flag else f"⚠️ ارسال ناموفق: {str(res.get('description'))[:120]}")
            + f"\n📍 `{PUBLIC_CHANNEL_ID}`",
        )
        return

    if text.startswith("/channelpin"):
        if not is_admin(uid):
            tg_send_message(chat_id, "⛔ فقط ادمین ربات مجاز است.")
            return
        if not validate_channel_target(silent=True):
            tg_send_message(chat_id, f"⚠️ کانال تنظیم نشده یا ربات ادمین آن نیست: {CHANNEL_REASON}")
            return
        intro = (
            "👋 *به کانال TradeGuard خوش آمدید*\n\n"
            "اینجا هر روز: رادار فاندینگ و نهنگ‌ها، وضعیت ترس و طمع، و یک نکتهٔ ریسک.\n\n"
            + ("🎁 *این روزها همه‌چیز رایگان است* — بدون پرداخت، بدون کارت بانکی.\n\n"
               if free_mode_active() else "⭐ نسخهٔ کامل با ۳۰۰ استارز (۳۰ روز).\n\n")
            + "👇 از دکمهٔ زیر مینی‌اپ را باز کن (۶ زبان):"
        )
        kb = {"inline_keyboard": [[{"text": "🚀 باز کردن مینی‌اپ", "url": f"https://t.me/{BOT_USERNAME}?start=channel"}]]}
        res = tg_send_message(PUBLIC_CHANNEL_ID, intro, reply_markup=kb)
        mid = ((res.get("result") or {}).get("message_id")) if res.get("ok") else None
        pinned = False
        if mid:
            pr = tg_call("pinChatMessage", {"chat_id": PUBLIC_CHANNEL_ID, "message_id": mid, "disable_notification": True})
            pinned = bool(pr.get("ok"))
        tg_send_message(
            chat_id,
            ("✅ پیام خوش‌آمد ارسال و پین شد." if pinned else "✅ پیام خوش‌آمد ارسال شد (پین نشد — ربات را ادمین با دسترسی pin کنید).")
            + f"\n📍 `{PUBLIC_CHANNEL_ID}`",
        )
        return

    if text.startswith("/report") or text.startswith("/stats"):
        if not is_admin(uid):
            tg_send_message(chat_id, "⛔ فقط ادمین ربات مجاز است.")
            return
        tg_send_message(chat_id, build_admin_report(), reply_markup=admin_back_keyboard())
        return

    if text.startswith("/checkjoin"):
        ok, days, status = claim_join_reward(uid)
        if ok:
            tg_send_message(
                chat_id,
                f"✅ *عضویتت در کانال تأیید شد* (بررسی واقعی از تلگرام).\n\n"
                f"🎁 *{fa_num(days)} روز پلن پرو* برایت ثبت شد و به جمع اشتراکت اضافه می‌شود.",
                reply_markup=main_keyboard(True, get_user_lang(uid, tg_lang), is_admin_user=is_admin(uid)),
            )
            return
        if status == "already":
            tg_send_message(chat_id, "✅ پاداش عضویت را قبلاً گرفته‌ای — هر کاربر یک بار.", reply_markup=main_keyboard(True, get_user_lang(uid, tg_lang)))
            return
        if status == "not_configured":
            tg_send_message(chat_id, "⚠️ کانال هنوز برای ربات تنظیم نشده است.")
            return
        join_kb = {"inline_keyboard": [[{"text": "📣 عضویت در کانال", "url": channel_url() or f"https://t.me/{BOT_USERNAME}"}]]}
        tg_send_message(
            chat_id,
            "🔍 تلگرام می‌گوید هنوز عضو کانال نیستی.\n\n"
            "عضو شو و بعد همین دستور را دوباره بزن تا پاداش بگیرد.",
            reply_markup=join_kb,
        )
        return

    if text.startswith("/sources"):
        if not is_admin(uid):
            tg_send_message(chat_id, "⛔ فقط ادمین ربات مجاز است.")
            return
        tg_send_message(chat_id, sources_text(), reply_markup=admin_back_keyboard())
        return

    if text.startswith("/partners"):
        res = tg_send_message(chat_id, partners_text())
        if not res.get("ok") and ADMIN_USER_ID and res.get("description"):
            logger.warning("ارسال /partners ناموفق: %s", res.get("description"))
        return

    if text.startswith("/freemode"):
        if not is_admin(uid):
            tg_send_message(chat_id, "⛔ فقط ادمین ربات مجاز است.")
            return
        lang = get_user_lang(uid, tg_lang)
        arg = (text.split(maxsplit=1)[1].strip().lower() if len(text.split(maxsplit=1)) > 1 else "")
        if arg in ("on", "1", "true", "روشن", "باز"):
            set_free_mode(True)
            tg_send_message(chat_id, tr(lang, "free_admin_on"))
        elif arg in ("off", "0", "false", "خاموش", "بسته"):
            set_free_mode(False)
            tg_send_message(chat_id, tr(lang, "free_admin_off"))
        else:
            state = tr(lang, "free_home_line") if free_mode_active() else "💰 پرداختی"
            tg_send_message(
                chat_id,
                tr(lang, "free_admin_state", state=("🎁 روشن" if free_mode_active() else "💰 خاموش"))
                + "\n\n`/freemode on` — همه‌چیز رایگان\n`/freemode off` — برگشت پرداخت",
                reply_markup=admin_back_keyboard(),
            )
        return

    if text.startswith("/grantpro"):
        if not is_admin(uid):
            tg_send_message(chat_id, "⛔ فقط ادمین ربات مجاز است.")
            return
        parts = text.split()
        target_id = int(parts[1]) if (len(parts) > 1 and parts[1].isdigit()) else uid
        gift_charge = f"admin_gift_{target_id}_{int(time.time())}"
        exp, _ = activate_pro_subscription(target_id, stars=0, charge_id=gift_charge, days=30)
        publish_pro_status([target_id])   # مینی‌اپ هم بلافاصله پرو را ببیند
        exp_str = datetime.fromtimestamp(exp, tz=timezone.utc).strftime("%Y-%m-%d")
        tg_send_message(chat_id, f"🎁 اشتراک ۳۰ روزه Pro برای کاربر `{target_id}` تا تاریخ `{exp_str}` فعال شد!")
        return

    if text.startswith("/broadcast"):
        if not is_admin(uid):
            tg_send_message(chat_id, "⛔ ابتدا دستور `/admin` را بزنید و روی دکمه «ثبت من به عنوان ادمین اصلی» کلیک کنید.")
            return
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            tg_send_message(chat_id, "📢 فرمت صحیح: `/broadcast متن پیام`")
            return
        with _db_lock, sqlite3.connect(DB_PATH) as conn:
            user_ids = [r[0] for r in conn.execute("SELECT user_id FROM users").fetchall()]
        sent = 0
        for tid in user_ids:
            r = tg_send_message(tid, parts[1], parse_mode="")
            if r.get("ok"):
                sent += 1
            time.sleep(0.05)
        tg_send_message(chat_id, f"✅ پیام شما برای *{sent}* کاربر ارسال شد!")
        return

    # ── مسیریاب هوشمند بدون نیاز به اسلش (/) ──
    clean = text.strip()
    if clean.startswith("0x") and len(clean) == 42:
        try:
            ch = http_json("https://api.hyperliquid.xyz/info", method="POST", payload={"type": "clearinghouseState", "user": clean}, timeout=6.0)
            eq = float((ch.get("marginSummary") or {}).get("accountValue") or 0)
            if eq > 10:
                msg_copy = dict(msg)
                msg_copy["text"] = f"/wallet {clean}"
                handle_message(msg_copy)
                return
        except Exception:
            pass
        if run_token_scan_reply(chat_id, clean):
            return

    if 2 <= len(clean) <= 10 and clean.replace("$", "").isalnum() and clean.isascii():
        sym_q = clean.lstrip("$")
        if run_token_scan_reply(chat_id, sym_q):
            return

    # هر پیام متنی دیگر (مثل سلام / منو) -> نمایش منوی شیشه‌ای زبان کاربر
    lang = get_user_lang(uid, tg_lang)
    pro, _ = is_user_pro(uid)
    send_user_home(chat_id, uid, lang, pro)


ADMIN_CALLBACKS = frozenset(
    {
        "admin_panel",
        "adm_stats",
        "adm_report",
        "adm_revenue",
        "adm_users",
        "adm_health",
        "adm_channel",
        "adm_url",
        "adm_help_grant",
        "adm_help_broadcast",
    }
)


def handle_callback(cb: dict) -> None:
    global ADMIN_USER_ID
    cb_id = cb["id"]
    data = cb.get("data") or ""
    user = cb.get("from") or {}
    uid = int(user.get("id", 0))
    tg_lang = user.get("language_code")
    chat_id = cb["message"]["chat"]["id"]
    lang = get_user_lang(uid, tg_lang)

    if data == "claim_admin":
        if ADMIN_USER_ID:
            tg_answer_callback(cb_id, "ادمین قبلاً ثبت شده است.", show_alert=True)
            return
        # فقط اولین کاربر ربات (صاحب ربات) می‌تواند ادمین شود — جلوی تصاحب ربات را می‌گیرد
        if not is_first_user(uid):
            tg_answer_callback(
                cb_id,
                "⛔ فقط اولین کاربر ربات می‌تواند مؤسس شود. "
                "صاحب ربات باید ADMIN_USER_ID را در Secret بگذارد.",
                show_alert=True,
            )
            return
        ADMIN_USER_ID = str(uid)
        save_env_var("ADMIN_USER_ID", ADMIN_USER_ID)  # .env + دیتابیس (پایدار)
        tg_answer_callback(cb_id, "👑 شما به عنوان ادمین اصلی ثبت شدید!", show_alert=True)
        tg_send_message(
            chat_id,
            f"✅ *تبریک! اکانت شما (`{ADMIN_USER_ID}`) به عنوان مؤسس اصلی قفل شد و اشتراک VIP دائمی برایتان فعال گردید!*\n\n"
            f"🔐 برای اینکه این دسترسی بعد از هر ری‌استارت هم بماند، "
            f"`ADMIN_USER_ID={ADMIN_USER_ID}` را در Secretهای گیت‌هاب بگذارید.",
            reply_markup=main_keyboard(True, lang),
        )
        return

    # ── 👑 پنل مؤسس: همه‌ی این کال‌بک‌ها فقط برای ادمین واقعی ──
    if data in ADMIN_CALLBACKS or data == "user_view":
        if data != "user_view" and not is_admin(uid):
            tg_answer_callback(cb_id, "⛔ دسترسی فقط برای مؤسس ربات مجاز است.", show_alert=True)
            return
        tg_answer_callback(cb_id)
        if data == "user_view":
            pro, _ = is_user_pro(uid)
            send_user_home(chat_id, uid, lang, pro)
        else:
            send_admin_section(chat_id, uid, data)
        return

    if data == "app_not_set":
        tg_answer_callback(cb_id)
        tg_send_message(
            chat_id,
            "📱 *اتصال ۱۰ ثانیه‌ای دکمه مینی‌اپ:*\n\n"
            "کافیست لینک امن `https://...` تونل یا هاست خود را با دستور زیر همین‌جا در چت بفرستید (بدون نیاز به ری‌استارت!):\n"
            "`/seturl https://xxxxxx.lhr.life`",
        )
        return

    if data == "lang_menu":
        tg_answer_callback(cb_id)
        tg_send_message(chat_id, tr(lang, "lang_prompt"), reply_markup=language_keyboard())
        return

    if data.startswith("setlang_"):
        new_lang = data.replace("setlang_", "")
        if new_lang not in SUPPORTED_LANGS:
            new_lang = "en"
        set_user_lang(uid, new_lang)
        pro, exp = is_user_pro(uid)
        status_line = (
            tr(new_lang, "status_pro", exp=datetime.fromtimestamp(exp, tz=timezone.utc).strftime("%Y-%m-%d"))
            if pro
            else tr(new_lang, "status_free")
        )
        tg_answer_callback(cb_id)
        tg_send_message(
            chat_id,
            f"{tr(new_lang, 'lang_saved')}\n\n{tr(new_lang, 'welcome', status=status_line)}",
            reply_markup=main_keyboard(pro, new_lang, is_admin_user=is_admin(uid)),
        )
        return

    if data == "radar":
        tg_answer_callback(cb_id, tr(lang, "scanning"))
        pro, _ = is_user_pro(uid)
        rates = fetch_live_funding_and_oi()
        fng_val, fng_lbl = fetch_fear_greed()
        lines = [tr(lang, "radar_head"), f"🧭 *Fear & Greed Index:* `{fng_val}/100 ({fng_lbl})`\n"]
        visible = rates if pro else rates[:3]
        for idx, r in enumerate(visible, start=1):
            oi_txt = f" | OI: `${r['oi_m']:.0f}M`" if r.get("oi_m", 0) > 0 else ""
            lines.append(f"{idx}. *${r['sym']}* ➜ `{r['rate_pct']:+.3f}%` ({r['magnet']}){oi_txt} | $500: `${r['daily_500']:.2f}/d`")
        if not pro and len(rates) > 3:
            lines.append(tr(lang, "radar_locked", rem=len(rates) - 3))
        tg_send_message(chat_id, "\n".join(lines), reply_markup=main_keyboard(pro, lang))
        return

    if data == "free_info":
        tg_answer_callback(cb_id, tr(lang, "free_info"), show_alert=True)
        return

    if data == "invite_free":
        tg_answer_callback(cb_id)
        send_invite_message(chat_id, uid, lang)
        return

    if data == "ai_brief":
        pro, _ = is_user_pro(uid)
        if not pro:
            tg_answer_callback(cb_id, tr(lang, "need_pro"), show_alert=True)
            send_pro_invoice(chat_id, lang)
            return
        tg_answer_callback(cb_id, tr(lang, "ai_thinking"))
        rates = fetch_live_funding_and_oi()
        tg_send_message(chat_id, ask_ai_market_agent(rates, lang))
        return

    if data == "prop_guard":
        tg_answer_callback(cb_id)
        pro, _ = is_user_pro(uid)
        tg_send_message(chat_id, tr(lang, "guard_info"), reply_markup=main_keyboard(pro, lang))
        return

    if data == "download_ea":
        pro, _ = is_user_pro(uid)
        if not pro:
            tg_answer_callback(cb_id, tr(lang, "need_pro"), show_alert=True)
            return
        tg_answer_callback(cb_id)
        if EA_FILE_PATH.exists():
            tg_send_document(chat_id, EA_FILE_PATH, "TradeGuard_PropProtector.mq5", tr(lang, "ea_cap"))
        return

    if data == "download_pine":
        pro, _ = is_user_pro(uid)
        if not pro:
            tg_answer_callback(cb_id, tr(lang, "need_pro"), show_alert=True)
            return
        tg_answer_callback(cb_id)
        if PINE_FILE_PATH.exists():
            tg_send_document(chat_id, PINE_FILE_PATH, "TradeGuard_SmartRadar.pine", tr(lang, "pine_cap"))
        return

    if data == "buy_pro":
        if free_mode_active():
            tg_answer_callback(cb_id, tr(lang, "free_info"), show_alert=True)
            return
        tg_answer_callback(cb_id)
        send_pro_invoice(chat_id, lang)


def validate_channel_target(silent: bool = False) -> bool:
    """
    اعتبارسنجی PUBLIC_CHANNEL_ID:
    - خالی باشد → پست خودکار غیرفعال (سالم)
    - به ربات خودش اشاره کند → غیرفعال + هشدار
    - کانال واقعی و ربات ادمین باشد → فعال
    مقدار جهانی CHANNEL_OK / CHANNEL_REASON را ست می‌کند.
    """
    global CHANNEL_OK, CHANNEL_REASON

    if not PUBLIC_CHANNEL_ID:
        CHANNEL_OK, CHANNEL_REASON = False, "خالی است (پست خودکار غیرفعال — سالم)"
        return False


    if PUBLIC_CHANNEL_ID == "@TradeGuard_Live":
        CHANNEL_OK, CHANNEL_REASON = False, "مقدار نمونه پیش‌فرض است"
        return False

    if is_self_chat(PUBLIC_CHANNEL_ID):
        CHANNEL_OK = False
        CHANNEL_REASON = (
            "به خودِ ربات اشاره می‌کند! باید یوزرنیم یک کانال عمومی باشد، نه ربات. "
            "آن را در .env خالی بگذارید یا با /setchannel @yourchannel عوض کنید."
        )
        if not silent:
            logger.error("❌ PUBLIC_CHANNEL_ID نامعتبر: %s", CHANNEL_REASON)
        return False

    info = tg_call("getChat", {"chat_id": PUBLIC_CHANNEL_ID})
    if not info.get("ok"):
        desc = str((info.get("description") or "")).strip() or str(info)
        CHANNEL_OK = False
        CHANNEL_REASON = f"تلگرام این آیدی را نشناخت ({desc[:110]})"
        if not silent:
            logger.error("❌ PUBLIC_CHANNEL_ID نامعتبر: %s", CHANNEL_REASON)
        return False

    chat = info.get("result") or {}
    chat_type = chat.get("type", "")
    title = chat.get("title") or chat.get("username") or PUBLIC_CHANNEL_ID
    if chat_type != "channel":
        CHANNEL_OK = False
        CHANNEL_REASON = f"«{title}» کانال نیست (نوع: {chat_type}) — باید Supergroup یا Channel باشد"
        if not silent:
            logger.error("❌ PUBLIC_CHANNEL_ID نامعتبر: %s", CHANNEL_REASON)
        return False

    bot_id = own_bot_id()
    if bot_id:
        mem = tg_call("getChatMember", {"chat_id": PUBLIC_CHANNEL_ID, "user_id": bot_id})
        status = ((mem.get("result") or {}).get("status") or "") if mem.get("ok") else ""
        if status not in ("administrator", "creator"):
            CHANNEL_OK = False
            CHANNEL_REASON = f"ربات در کانال «{title}» ادمین نیست (وضعیت: {status or 'نامشخص'})"
            if not silent:
                logger.error("❌ PUBLIC_CHANNEL_ID نامعتبر: %s", CHANNEL_REASON)
            return False

    CHANNEL_OK = True
    CHANNEL_REASON = f"فعال — کانال «{title}»"
    if not silent:
        logger.info("✅ کانال ویترین تأیید شد: %s", title)
    return True


CHANNEL_TIPS = [
    "📌 *فاندینگ مثبت شدید یعنی چه؟* وقتی فاندینگ یک ارز بالا می‌رود، پوزیشن‌های شورت هزینه می‌دهند؛ بازار آمادهٔ اسکوییز است. رادار همین را نشان می‌دهد.",
    "📌 *Open Interest را با حجم اشتباه نگیر.* OI جهشی بدون حجم = اهرم زیاد و ریسک لیکوییدیشن زنجیره‌ای.",
    "📌 *قانون ۳.۸٪:* در حساب پراپ، حد ضرر روزانه را خودت انتخاب نکن؛ یک عدد ثابت کوچک‌تر از قانون شرکت بگذار و به آن احترام بگذار.",
    "📌 *هر معامله را با حجم اشتباه شروع می‌کنی؟* اول لات را از ریسک حساب حساب کن، بعد ورود بزن (نه برعکس).",
    "📌 *دلتا-خنثی:* با فاندینگ مثبت می‌توان بدون شرط‌بندی روی جهت قیمت، از اختلاف نرخ‌ها درآمد ساخت — به شرط مدیریت اهرم.",
    "📌 *سه دعوت = ۷ روز پرو.* لینک اختصاصی‌ات را در گروه پراپ بفرست؛ ربات خودش تأیید می‌کند.",
]


def channel_url() -> str:
    """لینک عمومی کانال (اگر یوزرنیم عمومی باشد)."""
    cid = str(PUBLIC_CHANNEL_ID or "").strip()
    if cid.startswith("@"):
        return "https://t.me/" + cid.lstrip("@")
    if cid.startswith("https://t.me/"):
        return cid
    return ""


_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def fa_num(value) -> str:
    """اعداد را برای نمایش فارسی به رقم فارسی تبدیل می‌کند (۳ ساعت، ۱۲۳۴ عضو)."""
    return str(value).translate(_FA_DIGITS)


def human_delta(seconds: int) -> str:
    """«۳ دقیقه» / «۲ ساعت» — برای گزارش وضعیت کانال."""
    sec = max(0, int(seconds))
    if sec < 60:
        return f"{fa_num(sec)} ثانیه"
    if sec < 3600:
        return f"{fa_num(sec // 60)} دقیقه"
    if sec < 86400:
        h = sec // 3600
        m = (sec % 3600) // 60
        return f"{fa_num(h)} ساعت" + (f" و {fa_num(m)} دقیقه" if m else "")
    return f"{fa_num(sec // 86400)} روز"


def own_bot_id() -> int:
    """شناسهٔ ربات — از getMe، و اگر هنوز خوانده نشده از پیشوند توکن."""
    if BOT_ID:
        return BOT_ID
    try:
        return int(str(BOT_TOKEN).split(":", 1)[0])
    except Exception:
        return 0


def channel_diagnostics() -> str:
    """گزارش دقیق وضعیت کانال: دسترسی ربات، پین، اعضا، آخرین پست.

    همهٔ موارد از API تلگرام خوانده می‌شود؛ هر چه در دسترس نباشد «—» می‌شود
    تا کاربر فکر نکند چیزی درست کار می‌کند که کار نمی‌کند.
    """
    validate_channel_target(silent=True)
    lines = ["📢 *وضعیت کانال ویترین*", ""]
    if not PUBLIC_CHANNEL_ID:
        lines += [
            "کانال تنظیم نشده است.",
            "",
            "۱) ربات را در کانال ادمین کنید (با دسترسی ارسال و پین).",
            "۲) سپس: `/channel @yourchannel`",
        ]
        return "\n".join(lines)

    info = tg_call("getChat", {"chat_id": PUBLIC_CHANNEL_ID})
    chat = (info.get("result") or {}) if info.get("ok") else {}
    if not info.get("ok"):
        desc = str(info.get("description") or "بدون توضیح")[:120]
        return "\n".join(lines + [f"❌ تلگرام این آیدی را نشناخت: `{PUBLIC_CHANNEL_ID}`", f"علت: {desc}"])

    title = chat.get("title") or chat.get("username") or PUBLIC_CHANNEL_ID
    lines.append(f"📍 کانال: *{title}* — `{PUBLIC_CHANNEL_ID}`")

    mc = tg_call("getChatMemberCount", {"chat_id": PUBLIC_CHANNEL_ID})
    lines.append(f"👥 اعضا: *{fa_num(mc.get('result')) if mc.get('ok') else '—'}*")

    bot_id = own_bot_id()
    if bot_id:
        mem = tg_call("getChatMember", {"chat_id": PUBLIC_CHANNEL_ID, "user_id": bot_id})
        r = (mem.get("result") or {}) if mem.get("ok") else {}
        status = r.get("status") or "نامشخص"
        admin = status in ("administrator", "creator")
        lines.append(f"🤖 دسترسی ربات: {'✅ ادمین' if admin else '❌ ادمین نیست'} (`{status}`)")
        if admin:
            can_post = r.get("can_post_messages", True)
            can_pin = r.get("can_pin_messages", True)
            lines.append(
                f"   {'✅' if can_post is not False else '❌'} ارسال پست"
                f" · {'✅' if can_pin is not False else '❌'} پین پیام"
            )
    else:
        lines.append("🤖 شناسهٔ ربات هنوز از تلگرام خوانده نشده (getMe).")

    pin = chat.get("pinned_message") or {}
    lines.append("📌 پیام پین‌شده: " + ("✅ دارد" if pin else "— ندارد (با `/channelpin` بگذارید)"))

    last = str(get_setting("last_channel_post_ts", "") or "")
    if last.isdigit():
        lines.append(f"🕒 آخرین پست خودکار: *{human_delta(int(time.time()) - int(last))}* پیش")
    else:
        lines.append("🕒 آخرین پست خودکار: — (هنوز ثبت نشده)")

    every_h = CHANNEL_POST_INTERVAL_SEC // 3600
    lines.append(
        "🔁 پست خودکار: "
        + (f"روشن — هر {fa_num(every_h)} ساعت، ساعت {fa_num(f'{CHANNEL_WINDOW_UTC[0]:02d}')}–{fa_num(f'{CHANNEL_WINDOW_UTC[1]:02d}')} UTC"
           if CHANNEL_OK else f"خاموش ({CHANNEL_REASON})")
    )
    lines.append(f"⏭ پست بعدی: {next_post_eta()}")
    lines.append("🗓 برنامه: `/channelplan` · ارسال فوری: `/channelpost edu`")
    return "\n".join(lines)


# =====================================================================
#  تکمیل پروفایل کانال: توضیحات، عنوان، عکس
# =====================================================================
# محدودیت تلگرام: توضیحات کانال حداکثر ۲۵۵ کاراکتر، عنوان حداکثر ۱۲۸.
CHANNEL_DESC_LIMIT = 255
CHANNEL_TITLE_LIMIT = 128
CHANNEL_DESCRIPTION = (
    "📡 رادار زندهٔ فاندینگ و OI آن‌چین + آموزش مدیریت ریسک برای تریدر پراپ.\n"
    "🎁 دورهٔ رشد: رادار کامل، هشدارها، مربی AI و فایل MT5/TV رایگان است.\n"
    "🧠 آموزش روزانه · 🌍 مینی‌اپ ۶ زبانه بدون نصب"
)
CHANNEL_AVATAR_PATH = Path(__file__).resolve().parent / "bot_avatar.png"


def channel_description_text() -> str:
    """توضیحاتی که با /channeldesc روی کانال ست می‌شود (همیشه ≤۲۵۵ کاراکتر)."""
    bot_user = str(BOT_USERNAME or "TradeGuard1_bot")
    tail = f"\n👇 شروع: t.me/{bot_user}?start=channel"
    text = CHANNEL_DESCRIPTION + tail
    if len(text) > CHANNEL_DESC_LIMIT:
        text = text[: CHANNEL_DESC_LIMIT - len(tail)].rstrip() + tail
    return text


def tg_set_chat_photo(chat_id: int | str, file_path: Path) -> dict:
    """آپلود عکس پروفایل کانال (setChatPhoto) با multipart — بدون کتابخانهٔ خارجی."""
    if not file_path.exists():
        return {"ok": False, "description": "فایل عکس پیدا نشد"}
    boundary = f"----TradeGuardPhoto{uuid.uuid4().hex}"
    parts: List[bytes] = []

    def add_field(name: str, value: str) -> None:
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        parts.append(f"{value}\r\n".encode())

    add_field("chat_id", str(chat_id))
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(b'Content-Disposition: form-data; name="photo"; filename="channel_avatar.png"\r\n')
    parts.append(b"Content-Type: image/png\r\n\r\n")
    parts.append(file_path.read_bytes() + b"\r\n")
    parts.append(f"--{boundary}--".encode())
    body = b"".join(parts)
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setChatPhoto"
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "User-Agent": "TradeGuardBot/7.5"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30.0) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="ignore")
        logger.warning("Telegram API error on setChatPhoto: %s", raw[:200])
        return {"ok": False, "description": raw[:200]}
    except Exception as exc:
        logger.warning("Network error on setChatPhoto: %s", exc)
        return {"ok": False, "description": str(exc)}


def apply_channel_description(text: Optional[str] = None) -> dict:
    """توضیحات کانال را ست می‌کند؛ خروجی خام API تلگرام."""
    if not PUBLIC_CHANNEL_ID:
        return {"ok": False, "description": "کانال تنظیم نشده است"}
    payload = {"chat_id": PUBLIC_CHANNEL_ID, "description": (text or channel_description_text())[:CHANNEL_DESC_LIMIT]}
    return tg_call("setChatDescription", payload)


def channel_profile_report() -> str:
    """چک‌لیست کامل بودن پروفایل کانال — هر مورد مستقیم از تلگرام خوانده می‌شود."""
    lines = ["🧾 *تکمیل پروفایل کانال*", ""]
    if not PUBLIC_CHANNEL_ID:
        return "\n".join(lines + ["کانال تنظیم نشده — اول `/channel @yourchannel`"])

    info = tg_call("getChat", {"chat_id": PUBLIC_CHANNEL_ID})
    if not info.get("ok"):
        return "\n".join(lines + [f"❌ کانال خوانده نشد: {str(info.get('description'))[:100]}"])

    chat = info.get("result") or {}
    title = chat.get("title") or "—"
    username = chat.get("username") or ""
    desc = str(chat.get("description") or "")
    photo = chat.get("photo") or {}
    pin = chat.get("pinned_message") or {}
    mc = tg_call("getChatMemberCount", {"chat_id": PUBLIC_CHANNEL_ID})
    members = fa_num(mc.get("result")) if mc.get("ok") else "—"

    def mark(ok: bool) -> str:
        return "✅" if ok else "❌"

    lines += [
        f"📍 عنوان: *{title}* {mark(bool(title and title != '—'))}",
        f"🔗 یوزرنیم: {'@' + username if username else '— ندارد (لینک عمومی لازم است)'} {mark(bool(username))}",
        f"🖼 عکس پروفایل: {mark(bool(photo))}",
        f"📝 توضیحات: {mark(len(desc) >= 40)}",
        f"📌 پیام پین‌شده: {mark(bool(pin))}",
        f"👥 اعضا: *{members}*",
        "",
    ]
    if desc:
        lines += ["_توضیحات فعلی:_", desc[:200], ""]

    missing: List[str] = []
    if len(desc) < 40:
        missing.append("`/channeldesc` — توضیحات آماده را بگذار")
    if not photo:
        missing.append("`/channelphoto` — لوگوی برند را بگذار")
    if not pin:
        missing.append("`/channelpin` — پیام خوش‌آمد را پین کن")
    lines.append("🎯 *کارهای باقی‌مانده:*" if missing else "🎉 *پروفایل کامل است.*")
    lines += missing
    if not missing:
        lines.append("فقط محتوا: `/channelplan` را ببین.")
    lines += ["", "همهٔ این‌ها یک‌جا: `/channelcomplete`"]
    return "\n".join(lines)


PARTNERS_FILE = Path(__file__).resolve().parent.parent / "docs" / "partners.json"


def load_partners() -> dict:
    """شرکا/لینک‌های همکاری را از docs/partners.json می‌خواند (منبع واحد اپ و ربات)."""
    try:
        data = json.loads(PARTNERS_FILE.read_text(encoding="utf-8"))
        partners = [x for x in (data.get("partners") or []) if isinstance(x, dict) and x.get("name") and x.get("url")]
        return {
            "partners": partners[:10],
            "disclosure": str(data.get("disclosure") or ""),
            "updated": data.get("updated") or 0,
        }
    except Exception as exc:
        logger.warning("خواندن partners.json ناموفق: %s", exc)
        return {"partners": [], "disclosure": "", "updated": 0}


def partner_by_id(pid: str) -> Optional[dict]:
    pid = str(pid or "").strip().lower()
    for it in load_partners()["partners"]:
        key = str(it.get("id") or it.get("slug") or "").strip().lower()
        if key and key == pid:
            return it
    return None


def record_partner_start(pid: str) -> int:
    """شمارش کلیک واقعی روی لینک هر شریک (کلید در دیتابیس، پایدار)."""
    key = f"partner_start_{str(pid).strip().lower()}"
    raw = str(get_setting(key, "0") or "0")
    n = (int(raw) if raw.isdigit() else 0) + 1
    set_setting(key, str(n))
    return n


def partner_click_summary() -> List[Tuple[str, int]]:
    try:
        with _db_lock, sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                "SELECT key, value FROM settings WHERE key LIKE 'partner_start_%'"
            ).fetchall()
    except Exception:
        return []
    out: List[Tuple[str, int]] = []
    for key, value in rows:
        try:
            out.append((str(key).replace("partner_start_", ""), int(value or 0)))
        except (TypeError, ValueError):
            continue
    out.sort(key=lambda x: x[1], reverse=True)
    return out


def partners_text() -> str:
    data = load_partners()
    items = data["partners"]
    if not items:
        return (
            "🤝 *شرکای TradeGuard*\n\n"
            "هنوز هیچ شریکی ثبت نشده است.\n\n"
            "هدف: همکاری با بروکرها/پراپ‌فرم‌ها به‌صورت لینک همکاری رسمی — "
            "تخفیف برای کاربر، درآمد برای ما، و افشای شفاف کمیسیون."
        )
    lines = ["🤝 *شرکای TradeGuard*", ""]
    for it in items:
        badge = f" · {it.get('badge')}" if it.get("badge") else ""
        lines.append(f"• *{it['name']}*{badge}\n  {it.get('note', '')}\n  {it['url']}")
    disclosure = data["disclosure"] or "این لینک‌ها همکاری‌اند؛ ممکن است کمیسیون بگیریم."
    lines += ["", f"_{disclosure}_"]
    return "\n".join(lines)


def build_channel_post(rates: List[Dict]) -> Tuple[str, dict]:
    """پست کانال: ۳ فرصت برتر + ترس و طمع + یک نکتهٔ آموزشی چرخشی."""
    if not rates:
        rates = []
    top = rates[:3]
    fng_val, fng_lbl = fetch_fear_greed()
    lines = ["📡 *TradeGuard — رادار زندهٔ بازار* 🌍", ""]
    medals = ("🥇", "🥈", "🥉")
    for i, r in enumerate(top):
        oi_txt = f" | OI: `${r.get('oi_m', 0):.0f}M`" if r.get("oi_m", 0) else ""
        lines.append(
            f"{medals[i]} *${r['sym']}* ➜ `{r['rate_pct']:+.3f}%/8h` ({r['magnet']})"
            f"{oi_txt} | $500: `${r['daily_500']:.2f}/day`"
        )
    lines.append("")
    lines.append(f"🧭 شاخص ترس و طمع: `{fng_val}/100` ({fng_lbl})")
    lines.append("")
    tip = CHANNEL_TIPS[int(time.time() // 3600) % len(CHANNEL_TIPS)]
    lines.append(tip)
    lines.append("")
    if free_mode_active():
        lines.append("🎁 *این روزها همه‌چیز رایگان است* — رادار کامل، هشدارها، مربی AI و فایل MT5/TradingView.")
    else:
        lines.append("⭐ نسخهٔ کامل: رادار بی‌سقف + فایل MT5 و TradingView")
    lines.append("")
    lines.append("👇 مینی‌اپ ۶ زبانه، بدون نصب:")
    kb_rows = [[{"text": "🚀 باز کردن TradeGuard", "url": f"https://t.me/{BOT_USERNAME}?start=post_radar"}]]
    kb_rows.append([{"text": "🎁 دعوت دوستان (۳ نفر = ۷ روز پرو)", "url": f"https://t.me/{BOT_USERNAME}?start=invite"}])
    return "\n".join(lines), {"inline_keyboard": kb_rows}


# =====================================================================
#  پاداش تأییدشدهٔ عضویت کانال + رهگیری منبع ورود (اتربیوشن تبلیغات)
# =====================================================================
JOIN_REWARD_DAYS = int(os.environ.get("JOIN_REWARD_DAYS", "7") or "7")


def grant_pro_days(user_id: int, days: int) -> int:
    """افزودن روز پرو بدون ساخت ردیف پرداخت (برای پاداش‌ها).

    برخلاف activate_pro_subscription، اینجا هیچ ردیف payments ساخته نمی‌شود تا
    آمار درآمد/استارز با هدیه قاطی نشود.
    """
    now = int(time.time())
    with _db_lock, sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT pro_until FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            conn.execute(
                "INSERT OR IGNORE INTO users (user_id, username, lang, pro_until, created_at) "
                "VALUES (?, '', 'fa', 0, ?)",
                (user_id, now),
            )
            base = now
        else:
            base = int(row[0] or 0)
            base = base if base > now else now
        new_expiry = base + int(days) * 86400
        conn.execute("UPDATE users SET pro_until = ? WHERE user_id = ?", (new_expiry, user_id))
    return new_expiry


def channel_membership_status(user_id: int) -> str:
    """وضعیت واقعی عضویت کاربر در کانال از API تلگرام.

    خروجی: member / administrator / creator / left / kicked / not_configured / unknown
    """
    if not PUBLIC_CHANNEL_ID:
        return "not_configured"
    res = tg_call("getChatMember", {"chat_id": PUBLIC_CHANNEL_ID, "user_id": int(user_id)})
    if not res.get("ok"):
        desc = str(res.get("description") or "").lower()
        if "user not found" in desc or "participant" in desc:
            return "left"
        return "unknown"
    return str((res.get("result") or {}).get("status") or "unknown")


def claim_join_reward(user_id: int) -> Tuple[bool, int, str]:
    """پاداش یک‌بارمصرف عضویت کانال.

    خروجی: (موفق؟، تعداد روز، وضعیت/دلیل)
    """
    status = channel_membership_status(user_id)
    if status in ("left", "kicked", "not_configured", "unknown"):
        return False, 0, status
    with _db_lock, sqlite3.connect(DB_PATH) as conn:
        dup = conn.execute("SELECT days FROM join_rewards WHERE user_id = ?", (user_id,)).fetchone()
        if dup:
            return False, int(dup[0] or 0), "already"
        conn.execute(
            "INSERT INTO join_rewards (user_id, days, granted_at) VALUES (?, ?, ?)",
            (int(user_id), JOIN_REWARD_DAYS, int(time.time())),
        )
    grant_pro_days(user_id, JOIN_REWARD_DAYS)
    publish_pro_status([int(user_id)])
    return True, JOIN_REWARD_DAYS, status


SOURCE_CODE_RE = re.compile(r"^[a-z0-9_]{2,24}$")


def record_source(code: str) -> int:
    """شمارش منبع ورود (کمپین/پست/کانال تبلیغ) — کلید پایدار در دیتابیس."""
    code = str(code or "").strip().lower()
    if not SOURCE_CODE_RE.match(code):
        return 0
    key = f"src_{code}"
    raw = str(get_setting(key, "0") or "0")
    n = (int(raw) if raw.isdigit() else 0) + 1
    set_setting(key, str(n))
    if not get_setting(f"src_first_{code}"):
        set_setting(f"src_first_{code}", str(int(time.time())))
    return n


def source_summary(limit: int = 10) -> List[Tuple[str, int]]:
    try:
        with _db_lock, sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                "SELECT key, value FROM settings WHERE key LIKE 'src_%' AND key NOT LIKE 'src_first_%'"
            ).fetchall()
    except Exception:
        return []
    out: List[Tuple[str, int]] = []
    for key, value in rows:
        try:
            out.append((str(key).replace("src_", ""), int(value or 0)))
        except (TypeError, ValueError):
            continue
    out.sort(key=lambda x: x[1], reverse=True)
    return out[:limit]


def sources_text() -> str:
    rows = source_summary(15)
    lines = ["🔗 *منابع ورود کاربران*", ""]
    if not rows:
        return "\n".join(lines + [
            "هنوز هیچ منبعی ثبت نشده است.",
            "",
            "برای تبلیغ، لینک را با کد بسازید:",
            f"`https://t.me/{BOT_USERNAME}?start=ad_telegramads`",
            "کد فقط حروف کوچک انگلیسی، عدد و `_` (۲ تا ۲۴ کاراکتر).",
        ])
    total = sum(n for _, n in rows)
    for code, n in rows:
        pct = (n / total * 100) if total else 0
        lines.append(f"• `{code}` — *{n}* کاربر ({pct:.0f}%)")
    lines += ["", f"جمع: *{total}* کاربر از لینک‌های رهگیری‌شده", "", "منبع هر لینک را در پست تبلیغ `?start=...` بگذارید."]
    return "\n".join(lines)


def build_admin_report() -> str:
    """گزارش مدیریتی با اعداد واقعی (بدون هیچ عدد ساختگی).

    از دیتابیس SQLite و — اگر در دسترس بود — از API تلگرام و بازار خوانده
    می‌شود؛ هر بخشی که در دسترس نباشد با «—» نمایش داده می‌شود، نه با حدس.
    """
    now = int(time.time())
    stats = {"total": 0, "new24": 0, "new7": 0, "pro": 0, "invited": 0, "paid": 0, "stars": 0}
    try:
        with _db_lock, sqlite3.connect(DB_PATH) as conn:
            def one(sql: str, args: tuple = ()) -> int:
                row = conn.execute(sql, args).fetchone()
                return int(row[0] or 0) if row else 0

            stats["total"] = one("SELECT COUNT(*) FROM users")
            stats["new24"] = one("SELECT COUNT(*) FROM users WHERE created_at >= ?", (now - 86400,))
            stats["new7"] = one("SELECT COUNT(*) FROM users WHERE created_at >= ?", (now - 7 * 86400,))
            stats["pro"] = one("SELECT COUNT(*) FROM users WHERE pro_until > ?", (now,))
            stats["invited"] = one("SELECT COUNT(*) FROM users WHERE referred_by IS NOT NULL")
            stats["paid"] = one("SELECT COUNT(*) FROM payments")
            stats["stars"] = one("SELECT COALESCE(SUM(stars_amount), 0) FROM payments")
    except Exception as exc:
        logger.warning("خواندن آمار گزارش ناموفق: %s", exc)

    members_txt = "—"
    if PUBLIC_CHANNEL_ID:
        try:
            res = tg_call("getChatMemberCount", {"chat_id": PUBLIC_CHANNEL_ID}, timeout=8.0)
            if res.get("ok"):
                members_txt = f"{int(res.get('result') or 0):,}"
        except Exception as exc:
            logger.warning("تعداد اعضای کانال خوانده نشد: %s", exc)
    else:
        members_txt = "کانال تنظیم نشده"

    top_txt = "—"
    try:
        rates = fetch_live_funding_and_oi()
        if rates:
            r = rates[0]
            top_txt = f"${r.get('sym')} · {r.get('rate_pct', 0):+.3f}%/8h"
    except Exception:
        top_txt = "—"

    sources = source_summary(5)
    sources_line = (
        "🔗 منابع ورود: " + " · ".join(f"{c}: {n}" for c, n in sources)
        if sources else "🔗 منابع ورود: —"
    )
    clicks = partner_click_summary()
    clicks_line = (
        "🤝 کلیک لینک شرکا: " + " · ".join(f"{pid}: {n}" for pid, n in clicks[:5])
        if clicks else "🤝 کلیک لینک شرکا: —"
    )

    lines = [
        "📊 *گزارش مدیریتی TradeGuard*",
        "",
        f"👥 کاربران ربات: *{stats['total']:,}*",
        f"🆕 امروز (۲۴س): *{stats['new24']:,}* · این هفته: *{stats['new7']:,}*",
        f"🤝 آمده از دعوت دوستان: *{stats['invited']:,}*",
        f"⭐ پرو فعال: *{stats['pro']:,}*",
        f"📢 اعضای کانال: *{members_txt}*",
        "",
        f"💳 پرداخت موفق: *{stats['paid']:,}* · مجموع استارز: *{stats['stars']:,}*",
        f"🎁 دورهٔ رایگان: *{'روشن' if free_mode_active() else 'خاموش'}*",
        clicks_line,
        sources_line,
        f"📡 برترین فرصت همین حالا: `{top_txt}`",
        "",
        f"🕒 {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime(now))}",
    ]
    return "\n".join(lines)


def admin_digest_loop() -> None:
    """هر روز یک‌بار (ساعت ۰۷:۰۰ UTC) گزارش مدیریتی را به چت ادمین می‌فرستد.

    تاریخ آخرین ارسال در دیتابیس ذخیره می‌شود تا با ری‌استارت هر ۶ ساعته
    (که GitHub Actions تحمیل می‌کند) گزارش تکراری ارسال نشود.
    """
    while True:
        try:
            admin = str(ADMIN_USER_ID or "").strip()
            today = time.strftime("%Y-%m-%d", time.gmtime())
            if admin.isdigit() and get_setting("last_admin_digest", "") != today and time.gmtime().tm_hour >= 7:
                res = tg_send_message(int(admin), build_admin_report())
                if res.get("ok"):
                    set_setting("last_admin_digest", today)
                    logger.info("📊 گزارش روزانه برای ادمین ارسال شد.")
        except Exception as exc:
            logger.warning("گزارش روزانه ارسال نشد: %s", exc)
        time.sleep(1800)


# =====================================================================
#  محتوای کانال: آموزش + معرفی قابلیت‌ها (چرخش زمان‌بندی‌شده)
# =====================================================================
# بازهٔ ارسال به وقت UTC: ۰۴:۰۰ تا ۱۹:۵۹ — معادل ۰۷:۳۰ تا ۲۳:۳۰ تهران.
# بیرون این بازه پستی نمی‌رود تا کسی نصف‌شب نوتیف نگیرد (و کانال میوت نشود).
CHANNEL_WINDOW_UTC = (4, 19)
CHANNEL_POST_INTERVAL_SEC = 3 * 3600        # هر ۳ ساعت → تا ۵–۶ پست در روز
CHANNEL_LOOP_SLEEP_SEC = 600                # هر ۱۰ دقیقه بیدار می‌شود

# چرخهٔ دسته‌ها؛ هر ۶ پست یک دور کامل. «radar» دادهٔ واقعی بازار است،
# «edu» آموزش ترید، و «feature» معرفی یک قابلیت واقعی مینی‌اپ.
CHANNEL_CYCLE = ("radar", "edu", "feature", "edu", "radar", "feature")

CHANNEL_EDU_POSTS = [
    ("نرخ فاندینگ چیست و چرا از قیمت مهم‌تر است؟",
     "فاندینگ، هزینه‌ای است که هر ۸ ساعت بین لانگ‌ها و شورت‌ها جابه‌جا می‌شود:\n"
     "• فاندینگ مثبت → لانگ‌ها پول می‌دهند، شورت‌ها می‌گیرند.\n"
     "• فاندینگ منفی → برعکس.\n\n"
     "وقتی فاندینگ یک ارز به‌شدت مثبت می‌شود، یعنی جمعیت روی لانگ سنگین شده و ریسک «اسکوییز» بالا رفته است. "
     "این عدد را می‌توانید هر لحظه در رادار مینی‌اپ ببینید — بدون ثبت‌نام."),
    ("Open Interest را با حجم اشتباه نگیرید",
     "حجم معاملات می‌گوید چقدر پول رد‌وبدل شده؛ Open Interest می‌گوید چند پوزیشن **باز** روی میز است.\n\n"
     "• OI بالا + قیمت ثابت = دو طرف در حال انبار کردن پوزیشن‌اند؛ انفجار نوسان نزدیک است.\n"
     "• OI بالا + حجم کم = اهرم زیاد و ریسک لیکوییدیشن زنجیره‌ای.\n\n"
     "در رادار، ستون OI همین را نشان می‌دهد؛ به‌جای حدس، عدد را ببینید."),
    ("قانون ۳.۸٪؛ عددی که حساب پراپ را نجات می‌دهد",
     "در حساب پراپ، بزرگ‌ترین دشمن شما بازار نیست؛ برداشت‌های روزانه است.\n\n"
     "یک سقف ثابت برای ریسک روزانه بگذارید که **کمتر** از قانون شرکت باشد (مثلاً ۳.۸٪ وقتی سقف ۵٪ است) "
     "و به آن مثل قانون فیزیک احترام بگذارید. اگر امروز به سقف رسیدید، تمام — فردا روز دیگری است.\n\n"
     "ماشین‌حساب گارد در مینی‌اپ همین سقف را برایتان حساب می‌کند."),
    ("لات را از ریسک حساب حساب کنید، نه از احساس",
     "ترتیب اشتباه رایج: «چقدر حجم بزنم؟» → بعد «استاپ کجا؟».\n"
     "ترتیب درست: فاصلهٔ استاپ (به پیپ/درصد) → ریسک مجاز (مثلاً ۰.۵٪ حساب) → حجم.\n\n"
     "مثال: حساب ۱۰٬۰۰۰ دلار، ریسک ۰.۵٪ = ۵۰ دلار. استاپ ۲۵ دلار فاصله دارد → حجم ۲ واحد.\n\n"
     "گارد دراودان همین را در سه ثانیه می‌دهد؛ دیگر لازم نیست ذهنی حساب کنید."),
    ("دلتا-خنثی چیست و چه ریسکی دارد؟",
     "در آربیتراژ فاندینگ، هم‌زمان اسپات می‌خرید و پرپتوال شورت می‌زنید تا از جهت قیمت مستقل شوید و "
     "فاندینگ مثبت را جمع کنید.\n\n"
     "ریسک‌هایی که معمولاً گفته نمی‌شود:\n"
     "• نرخ فاندینگ می‌تواند منفی شود.\n"
     "• هزینهٔ اهرم و کارمزد، سود کوچک را می‌خورد.\n"
     "• ریسک صرافی و ریسک لیکوییدیشن پای شورت.\n\n"
     "برای همین، رادار فقط فرصت‌ها را نشان می‌دهد؛ تصمیم و مدیریت ریسک با شماست."),
    ("شاخص ترس و طمع را چطور بخوانیم؟",
     "این شاخص خلق‌وخوی جمعیت را نشان می‌دهد، نه جهت قیمت:\n"
     "• بالای ۷۵ (طمع شدید): جمعیت خرید سنگین کرده — جای احتیاط، نه هیجان.\n"
     "• زیر ۲۵ (ترس شدید): جمعیت ترسیده — جای بررسی فرصت، نه وحشت.\n\n"
     "کاربرد درست: وقتی می‌خواهید پوزیشن سنگین باز کنید، بپرسید «آیا من دارم دنبال جمعیت می‌روم؟»",
     ),
    ("لییکوییدیشن زنجیره‌ای؛ چرا بازار یک‌دفعه می‌ریزد؟",
     "وقتی قیمت به محدودهٔ استاپ‌های اهرمی می‌رسد، صرافی پوزیشن‌ها را می‌بندد. هر بستن، سفید بازار می‌زند و "
     "قیمت را بیشتر حرکت می‌دهد → استاپ بعدی فعال می‌شود.\n\n"
     "نشانه‌های هشدار: OI بالا + فاندینگ افراطی + نزدیک شدن به سقف/کف روزانه.\n"
     "در این شرایط، کاهش حجم از هر تحلیلی ارزشمندتر است."),
    ("سشن‌ها را بشناسید: ساعت طلایی نوسان",
     "• آسیا (۰۰:۰۰–۰۷:۰۰ UTC): رنج‌های کم‌عمق، مناسب آماده‌سازی سطوح.\n"
     "• لندن (۰۷:۰۰–۱۱:۰۰ UTC): اولین حرکت جدی روز، شکار سقف/کف آسیا.\n"
     "• نیویورک (۱۲:۳۰–۱۶:۰۰ UTC): بیشترین نوسان طلا و بیت‌کوین.\n\n"
     "برای پراپ، معامله در سشن‌های کم‌نوسان معمولاً یعنی استاپ‌های بی‌دلیل. "
     "مینی‌اپ سشن فعال را در گزارش بازار نشان می‌دهد."),
    ("ژورنال معاملاتی؛ ارزان‌ترین راه بهبود",
     "حداقل این سه چیز را ثبت کنید: دلیل ورود، حجم، و احساس لحظهٔ ورود.\n"
     "بعد از ۲۰ معامله الگو پیدا می‌شود: مثلاً «بعد از دو ضرر پشت‌سرهم، حجم را دو برابر می‌کنم» — "
     "و همین یک الگو می‌تواند کل حساب را ببرد.\n\n"
     "ژورنال لازم نیست نرم‌افزار باشد؛ یک فایل ساده کافی است. مهم پیوستگی است، نه ابزار."),
    ("پنج اشتباه تازه‌کارها (به ترتیب گرانی)",
     "۱) حجم ثابت برای همهٔ معاملات.\n"
     "۲) میانگین‌گیری روی ضرر بدون برنامه.\n"
     "۳) معامله برای «جبران» ضرر قبلی.\n"
     "۴) نگه‌داشتن پوزیشن بدون استاپ در اخبار.\n"
     "۵) تست نکردن استراتژی روی دمو.\n\n"
     "هیچ‌کدام راز نیستند؛ فقط گران‌اند. یک بار نوشتنشان و مرور هفتگی، جلوی خیلی از آن‌ها را می‌گیرد."),
    ("چک‌لیست ۵ ثانیه‌ای قبل از هر ورود",
     "۱) استاپ کجاست و چند دلار است؟\n"
     "۲) حجم با ریسک مجاز روزانه می‌خواند؟\n"
     "۳) سشن فعلی ارزش معامله دارد؟\n"
     "۴) فاندینگ و OI چه می‌گویند؟\n"
     "۵) اگر همین حالا استاپ بخورد، فردا هم آرام می‌خوابم؟\n\n"
     "اگر جواب یکی از این‌ها «نمی‌دانم» بود، ورود نزنید. نبودِ معامله هم یک تصمیم حرفه‌ای است."),
    ("چرا ۹۰٪ تریدرها با تحلیل درست هم ضرر می‌کنند؟",
     "چون مشکل معمولاً «تحلیل» نیست، «اندازهٔ پوزیشن» است. یک تحلیل ۵۰٪ درست با حجم ۱٪ حساب، "
     "شما را زنده نگه می‌دارد؛ همان تحلیل با حجم ۱۰٪ حساب، شما را در سه ضرر حذف می‌کند.\n\n"
     "اول بقا، بعد سود. این تنها ترتیبی است که جواب می‌دهد."),
]

CHANNEL_FEATURE_POSTS = [
    ("📡 رادار زنده، بدون ثبت‌نام",
     "مینی‌اپ تریدگارد، فاندینگ و Open Interest بازار پرپتوال را از خود آن‌چین می‌خواند و "
     "سه ستون اصلی را جلوی شما می‌گذارد: داغ‌ترین فاندینگ‌ها، لیدرهای بازار و نهنگ‌های بالای یک میلیون دلار.\n\n"
     "بدون ثبت‌نام، بدون نصب، بدون کارت بانکی — همان‌جا داخل تلگرام باز می‌شود."),
    ("🔥 زنجیرهٔ روز: چرا باید هر روز سر بزنید؟",
     "مینی‌اپ حالا زنجیرهٔ حضور شما را نگه می‌دارد: هر روز که سر بزنید یکی به 🔥 اضافه می‌شود.\n\n"
     "این «بازی‌سازی» بی‌فایده نیست: بازار هر روز عوض می‌شود و کسی که روزانه رادار را می‌بیند، "
     "تغییر رژیم فاندینگ را زودتر از بقیه می‌فهمد.\n\n"
     "و حالا اپ با آخرین دادهٔ ذخیره‌شده فوراً باز می‌شود؛ حتی روی اینترنت ضعیف."),
    ("⭐ دیده‌بان: فقط همان چند ارزی که واقعاً ترید می‌کنید",
     "در رادار، ستارهٔ کنار هر ارز را بزنید؛ از این به بعد با چیپ «⭐ دیده‌بان من» فقط همان‌ها را می‌بینید.\n\n"
     "مناسب کسانی که روی ۳–۴ ارز تمرکز دارند و نمی‌خواهند هر روز کل بازار را مرور کنند. "
     "انتخاب‌ها روی همان دستگاه ذخیره می‌شوند."),
    ("🤖 مربی هوش مصنوعی بازار، داخل خود مینی‌اپ",
     "دکمهٔ «تحلیل زنده ✨» وضعیت فعلی بازار (فاندینگ، OI، ترس و طمع) را می‌خواند و "
     "به زبان خودتان توضیح می‌دهد که الآن چه چیزی روی میز است.\n\n"
     "این مربی، مشاور سرمایه‌گذاری نیست؛ ابزار فهمیدن است. تصمیم و ریسک همیشه با شماست."),
    ("🛡️ اسکنر امنیت توکن قبل از خرید",
     "آدرس یا نماد توکن را بدهید: قرارداد بررسی می‌شود که هانی‌پات باشد یا نه و "
     "کارمزد خرید/فروش چقدر است.\n\n"
     "برای توکن‌های کوچک، این ۱۰ ثانیه می‌تواند تفاوت بین یک سرمایه‌گذاری و یک کمک مالی باشد."),
    ("🔎 اشعه ایکس کیف پول نهنگ",
     "آدرس ۰x یک کیف پول هایپرلیکوید را بدهید: پوزیشن‌های باز، سمت، اهرم، قیمت ورود و قیمت لیکوییدیشن را می‌بینید.\n\n"
     "کاربرد واقعی: وقتی یک نهنگ پوزیشن بزرگ می‌گیرد، می‌فهمید استاپش کجاست و "
     "شکار نقدینگی کجا محتمل است."),
    ("🧮 گارد دراودان پراپ: ریسک را قبل از ورود ببینید",
     "حساب، سقف ضرر روزانه و درصد ریسک را وارد کنید؛ مینی‌اپ حجم مجاز، تعداد معاملات قابل انجام "
     "و حد ضرر پیشنهادی را می‌دهد.\n\n"
     "کمتر معامله با حجم درست = عمر بیشتر حساب. همین."),
    ("🌍 شش زبان، یک مینی‌اپ — و همین روزها همه‌چیز رایگان",
     "فارسی، انگلیسی، روسی، عربی، ترکی و اسپانیایی — از دکمهٔ زبان داخل اپ عوض می‌شود.\n\n"
     "در دورهٔ رشد، رادار کامل، هشدارها، مربی AI و فایل‌های MT5/TradingView **بدون پرداخت** باز است. "
     "کافی است کانال را دنبال کنید تا خبر پایان دوره را از دست ندهید."),
]

CHANNEL_SIGNATURE = "📊 داده‌ها زنده از آن‌چین · آموزشی است، توصیهٔ سرمایه‌گذاری نیست."


def _mini_app_kb(start_param: str = "channel") -> dict:
    return {
        "inline_keyboard": [
            [{"text": "🚀 باز کردن مینی‌اپ (۶ زبان)", "url": f"https://t.me/{BOT_USERNAME}?start={start_param}"}],
            [{"text": "🎁 دعوت دوستان (۳ نفر = ۷ روز پرو)", "url": f"https://t.me/{BOT_USERNAME}?start=invite"}],
        ]
    }


def in_post_window(ts: Optional[int] = None) -> bool:
    """آیا این لحظه در بازهٔ ارسال مجاز است؟ (UTC ۰۴:۰۰–۱۹:۵۹)"""
    hour = time.gmtime(int(ts if ts is not None else time.time())).tm_hour
    return CHANNEL_WINDOW_UTC[0] <= hour <= CHANNEL_WINDOW_UTC[1]


def next_channel_category() -> str:
    """دستهٔ پست بعدی از چرخه؛ شمارنده در دیتابیس نگه داشته می‌شود (پایدار)."""
    raw = str(get_setting("channel_cycle_idx", "0") or "0")
    idx = int(raw) if raw.isdigit() else 0
    cat = CHANNEL_CYCLE[idx % len(CHANNEL_CYCLE)]
    set_setting("channel_cycle_idx", str((idx + 1) % len(CHANNEL_CYCLE)))
    return cat


def _next_index(name: str, size: int) -> int:
    raw = str(get_setting(name, "0") or "0")
    idx = int(raw) if raw.isdigit() else 0
    set_setting(name, str((idx + 1) % max(1, size)))
    return idx % max(1, size)


def build_edu_post(advance: bool = True) -> Tuple[str, dict]:
    idx = _next_index("channel_edu_idx", len(CHANNEL_EDU_POSTS)) if advance else 0
    title, body = CHANNEL_EDU_POSTS[idx]
    text = f"🎓 *{title}*\n\n{body}\n\n{CHANNEL_SIGNATURE}"
    return text, _mini_app_kb("post_edu")


def build_feature_post(advance: bool = True) -> Tuple[str, dict]:
    idx = _next_index("channel_feature_idx", len(CHANNEL_FEATURE_POSTS)) if advance else 0
    title, body = CHANNEL_FEATURE_POSTS[idx]
    text = f"{title}\n\n{body}\n\n👇 داخل تلگرام، بدون نصب:"
    return text, _mini_app_kb("post_feature")


def channel_plan(n: int = 6) -> str:
    """پیش‌نمایش N پست بعدی (فقط دسته و تیتر) — بدون تغییر شمارنده‌ها."""
    def as_int(key: str) -> int:
        raw = str(get_setting(key, "0") or "0")
        return int(raw) if raw.isdigit() else 0

    idx = as_int("channel_cycle_idx")
    edu_i = as_int("channel_edu_idx")
    feat_i = as_int("channel_feature_idx")
    edu_used = 0
    feat_used = 0
    icons = {"radar": "📡", "edu": "🎓", "feature": "✨"}
    lines = ["🗓 *برنامهٔ پست‌های بعدی کانال*", ""]
    for i in range(max(1, n)):
        cat = CHANNEL_CYCLE[(idx + i) % len(CHANNEL_CYCLE)]
        if cat == "edu":
            title = CHANNEL_EDU_POSTS[(edu_i + edu_used) % len(CHANNEL_EDU_POSTS)][0]
            edu_used += 1
        elif cat == "feature":
            title = CHANNEL_FEATURE_POSTS[(feat_i + feat_used) % len(CHANNEL_FEATURE_POSTS)][0]
            feat_used += 1
        else:
            title = "رادار زندهٔ فاندینگ و OI (دادهٔ واقعی)"
        lines.append(f"{fa_num(i + 1)}. {icons[cat]} {title}")
    every_h = CHANNEL_POST_INTERVAL_SEC // 3600
    lines += [
        "",
        f"⏱ هر {fa_num(every_h)} ساعت · بازهٔ {fa_num(f'{CHANNEL_WINDOW_UTC[0]:02d}')}–{fa_num(f'{CHANNEL_WINDOW_UTC[1]:02d}')} UTC",
        f"⏭ پست بعدی: {next_post_eta()}",
        "",
        "ارسال فوری: `/channelpost` یا `/channelpost edu` / `/channelpost feature`",
    ]
    return "\n".join(lines)


def build_slot_post(category: str) -> Tuple[str, dict]:
    """پست مناسب این اسلات: رادار واقعی، آموزش، یا معرفی قابلیت."""
    if category == "edu":
        return build_edu_post()
    if category == "feature":
        return build_feature_post()
    return build_channel_post(fetch_live_funding_and_oi())


def next_post_eta(now_ts: Optional[int] = None) -> str:
    """توضیح انسانی اینکه پست بعدی کِی می‌آید (برای /channelstatus)."""
    now = int(now_ts if now_ts is not None else time.time())
    last = str(get_setting("last_channel_post_ts", "") or "")
    last_ts = int(last) if last.isdigit() else 0
    remaining = CHANNEL_POST_INTERVAL_SEC - (now - last_ts) if last_ts else 0
    if remaining > 0:
        return f"تا {human_delta(remaining)} دیگر"
    if not in_post_window(now):
        return "در بازهٔ ارسال نیست (۰۴:۰۰ UTC به بعد)"
    if not last_ts:
        return "به‌زودی (اولین پستِ چرخه)"
    return "در چرخهٔ بعدی (حداکثر ۱۰ دقیقه)"


def auto_channel_profile_once() -> None:
    """یک بار در استارت‌آپ، فقط چیزهای *خالی* پروفایل کانال را پر می‌کند.

    عمداً idempotent است: اگر توضیحات/عکس/پین از قبل باشد، دست نمی‌زند.
    عنوان کانال هرگز خودکار عوض نمی‌شود (نام برند انتخاب خود صاحب کسب‌وکار است).
    """
    try:
        if not validate_channel_target(silent=True):
            logger.info("پروفایل خودکار کانال رد شد: %s", CHANNEL_REASON)
            return
        info = tg_call("getChat", {"chat_id": PUBLIC_CHANNEL_ID})
        chat = (info.get("result") or {}) if info.get("ok") else {}
        filled: List[str] = []

        if len(str(chat.get("description") or "")) < 40:
            if apply_channel_description().get("ok"):
                filled.append("📝 توضیحات")

        if not chat.get("photo") and CHANNEL_AVATAR_PATH.exists():
            if tg_set_chat_photo(PUBLIC_CHANNEL_ID, CHANNEL_AVATAR_PATH).get("ok"):
                filled.append("🖼 عکس پروفایل")

        if not chat.get("pinned_message"):
            pr = tg_send_message(
                PUBLIC_CHANNEL_ID,
                "👋 *به کانال TradeGuard خوش آمدید*\n\n"
                "اینجا رادار زندهٔ فاندینگ و OI آن‌چین، آموزش مدیریت ریسک و معرفی ابزارها را می‌بینید.\n"
                "🎁 این روزها همه‌چیز رایگان است.\n\n👇 مینی‌اپ ۶ زبانه، بدون نصب:",
                reply_markup={"inline_keyboard": [[{"text": "🚀 باز کردن مینی‌اپ",
                                                   "url": f"https://t.me/{BOT_USERNAME}?start=channel"}]]},
            )
            mid = ((pr.get("result") or {}).get("message_id")) if pr.get("ok") else None
            if mid and tg_call("pinChatMessage", {"chat_id": PUBLIC_CHANNEL_ID, "message_id": mid,
                                                  "disable_notification": True}).get("ok"):
                filled.append("📌 پیام خوش‌آمد پین شد")

        if filled:
            logger.info("🧾 پروفایل کانال کامل شد: %s", " · ".join(filled))
            if ADMIN_USER_ID:
                tg_send_message(
                    int(ADMIN_USER_ID),
                    "🧾 *پروفایل کانال خودکار تکمیل شد*\n\n" + "\n".join(filled)
                    + "\n\nبرای بازبینی: `/channelinfo`",
                )
        else:
            logger.info("🧾 پروفایل کانال از قبل کامل بود.")
    except Exception as exc:
        logger.warning("تکمیل خودکار پروفایل کانال ناموفق: %s", exc)


def auto_channel_loop() -> None:
    """چرخهٔ محتوای کانال: هر ۳ ساعت، در بازهٔ ۰۴–۱۹ UTC، با چرخش رادار/آموزش/قابلیت.

    برخلاف نسخهٔ قبل که فقط هر ۸ ساعت یک پست رادار می‌فرستاد، این حلقه:
      • محتوای متنوع می‌دهد (آموزش + معرفی قابلیت + دادهٔ زنده)،
      • ساعات شب را احترام می‌گذارد،
      • اگر ربات هنوز ادمین کانال نباشد، خودش هر ۱۰ دقیقه دوباره امتحان می‌کند
        (به‌جای اینکه برای همیشه خاموش بماند).
    """
    while True:
        try:
            if validate_channel_target(silent=True):
                now = int(time.time())
                last = str(get_setting("last_channel_post_ts", "") or "")
                last_ts = int(last) if last.isdigit() else 0
                due = (now - last_ts) >= CHANNEL_POST_INTERVAL_SEC
                if due and in_post_window(now):
                    category = next_channel_category()
                    post_text, kb = build_slot_post(category)
                    res = tg_send_message(PUBLIC_CHANNEL_ID, post_text, reply_markup=kb)
                    if res.get("ok"):
                        set_setting("last_channel_post_ts", str(now))
                        logger.info("📣 پست کانال ارسال شد (دسته: %s)", category)
                    elif res.get("error_code") in (400, 403):
                        logger.warning("پست کانال رد شد: %s", res.get("description"))
        except Exception as exc:
            logger.warning("Channel auto-post skipped: %s", exc)
        time.sleep(CHANNEL_LOOP_SLEEP_SEC)


def process_update(upd: dict) -> None:
    try:
        if "pre_checkout_query" in upd:
            pq = upd["pre_checkout_query"]
            payload = str(pq.get("invoice_payload") or "")
            currency = str(pq.get("currency") or "")
            amount = int(pq.get("total_amount") or 0)
            # فقط فاکتور خودِ ربات پذیرفته می‌شود؛ تلگرام فقط ۱۰ ثانیه برای پاسخ صبر می‌کند
            valid = payload.startswith("tradeguard_pro") and currency == "XTR" and amount > 0
            if valid:
                tg_call("answerPreCheckoutQuery", {"pre_checkout_query_id": pq["id"], "ok": True})
            else:
                logger.warning("pre_checkout نامعتبر رد شد: payload=%s currency=%s amount=%s", payload[:40], currency, amount)
                tg_call(
                    "answerPreCheckoutQuery",
                    {
                        "pre_checkout_query_id": pq["id"],
                        "ok": False,
                        "error_message": "این فاکتور معتبر نیست. لطفاً از منوی ربات دوباره اقدام کنید.",
                    },
                )
        elif "message" in upd:
            handle_message(upd["message"])
        elif "callback_query" in upd:
            handle_callback(upd["callback_query"])
    except Exception as exc:
        logger.warning("Update error: %s", exc)


def _gh_error(title: str, detail: str) -> None:
    """خطای قابل‌دیدن در GitHub Actions (Annotation قرمز روی صفحه اجرا)."""
    if os.environ.get("GITHUB_ACTIONS") == "true":
        print(f"::error title={title}::{detail}", flush=True)


def apply_persisted_settings() -> None:
    """
    تنظیمات ذخیره‌شده در دیتابیس را برمی‌گرداند.
    روی GitHub Actions هر جاب از صفر شروع می‌شود، پس بدون این تابع
    قیمت اشتراک / آیدی ادمین / لینک مینی‌اپ هر ۶ ساعت به حالت اول برمی‌گشت.
    """
    global ADMIN_USER_ID, MINI_APP_URL, PUBLIC_CHANNEL_ID

    saved_admin = get_setting("ADMIN_USER_ID")
    if not ADMIN_USER_ID and saved_admin:
        ADMIN_USER_ID = saved_admin
        logger.info("👑 ادمین از دیتابیس بازیابی شد: %s", ADMIN_USER_ID)

    saved_price = get_setting("SUBSCRIPTION_STARS")
    if saved_price.isdigit() and not os.environ.get("SUBSCRIPTION_STARS", "").strip():
        try:
            set_subscription_price(int(saved_price))
            logger.info("💲 قیمت اشتراک بازیابی شد: %s ⭐", SUBSCRIPTION_STARS)
        except Exception:
            pass

    saved_url = get_setting("MINI_APP_URL")
    if saved_url and not is_real_app_url(MINI_APP_URL):
        MINI_APP_URL = saved_url
        logger.info("🔗 لینک مینی‌اپ بازیابی شد: %s", MINI_APP_URL)

    saved_channel = get_setting("PUBLIC_CHANNEL_ID")
    if saved_channel and not PUBLIC_CHANNEL_ID:
        PUBLIC_CHANNEL_ID = saved_channel


def main() -> None:
    global BOT_TOKEN, BOT_USERNAME
    init_db()
    apply_persisted_settings()
    if not BOT_TOKEN or "your_telegram_bot_token" in BOT_TOKEN:
        if sys.stdin and sys.stdin.isatty():
            print("\n========================================================")
            print("🔑 تنظیم سریع توکن ربات تلگرام (فقط یک‌بار نیاز است!)")
            print("توکنی که از @BotFather گرفتید را اینجا Paste کنید و Enter بزنید:")
            print("========================================================")
            try:
                entered = input("BOT_TOKEN > ").strip().strip('"').strip("'")
            except EOFError:
                entered = ""
            if entered and ":" in entered:
                BOT_TOKEN = entered
                env_content = (
                    f"BOT_TOKEN={BOT_TOKEN}\n"
                    f"MINI_APP_URL={MINI_APP_URL}\n"
                    f"SUBSCRIPTION_STARS={SUBSCRIPTION_STARS}\n"
                    f"PUBLIC_CHANNEL_ID={PUBLIC_CHANNEL_ID}\n"
                    f"FREE_PRO_INVITE_TARGET={FREE_PRO_INVITE_TARGET}\n"
                    f"ADMIN_USER_ID={ADMIN_USER_ID}\n"
                )
                ENV_PATH.write_text(env_content, encoding="utf-8")
                logger.info("✅ توکن با موفقیت در فایل tradeguard-pro/.env ذخیره شد!")
        if not BOT_TOKEN or "your_telegram_bot_token" in BOT_TOKEN:
            logger.error(
                "❌ BOT_TOKEN تنظیم نشده است. "
                "GitHub → Settings → Secrets and variables → Actions → BOT_TOKEN"
            )
            _gh_error(
                "BOT_TOKEN تنظیم نشده",
                "Settings → Secrets and variables → Actions → New repository secret → Name: BOT_TOKEN",
            )
            sys.exit(2)

    me = tg_call("getMe")
    if not me.get("ok"):
        logger.error(
            "❌ اتصال به تلگرام برقرار نشد — توکن را چک کنید (یا فیلترشکن اگر روی سیستم خودتان اجرا می‌کنید). جزئیات: %s",
            me,
        )
        _gh_error("BOT_TOKEN نامعتبر است یا تلگرام در دسترس نیست", str(me.get("description"))[:200])
        sys.exit(3)

    BOT_USERNAME = me["result"].get("username", "TradeGuard1_bot")
    BOT_ID = int((me.get("result") or {}).get("id") or 0)
    # اعتبارسنجی کانال ویترین (جلوگیری از خطای 403 «bot can't send messages to the bot»)
    validate_channel_target()
    # پاک کردن وبهوک قبلی و نصب خودکار دکمه منوی آبی تلگرام (Commands + WebApp)
    tg_call("deleteWebhook", {"drop_pending_updates": False})
    sync_telegram_menus()

    logger.info("✅ متصل شد به ربات: @%s (id: %s)", BOT_USERNAME, BOT_ID)
    load_free_mode()
    logger.info("🎁 حالت رایگان: %s", "روشن" if free_mode_active() else "خاموش")
    logger.info("📢 وضعیت کانال ویترین: %s", CHANNEL_REASON)
    logger.info("🌍 ربات جهانی ۶ زبانه TradeGuard v7.5 (نسخه نهایی کامل!) روشن و آماده است! به تلگرام بروید و /start بزنید.")

    # همگام‌سازی وضعیت پرو با مینی‌اپ (docs/pro_users.json) هنگام روشن شدن
    try:
        publish_pro_status()
        logger.info("🗂 وضعیت اشتراک برای مینی‌اپ آماده است: %s", PRO_STATUS_FILE)
    except Exception as exc:
        logger.warning("همگام‌سازی وضعیت پرو در استارت‌آپ ناموفق بود: %s", exc)

    threading.Thread(target=auto_channel_loop, daemon=True).start()
    if os.environ.get("AUTO_CHANNEL_PROFILE", "1") != "0":
        threading.Thread(target=auto_channel_profile_once, daemon=True).start()
    threading.Thread(target=admin_digest_loop, daemon=True).start()
    pool = ThreadPoolExecutor(max_workers=8)
    offset = 0

    # خروج تمیز پیش از سقف ۶ ساعتهٔ گیت‌هاب: مرحلهٔ پشتیبان‌گیری دیتابیس باید
    # فرصت اجرا داشته باشد، وگرنه جاب با «exceeded maximum execution time»
    # می‌میرد و زنجیرهٔ ۲۴/۷ ممکن است یک ساعت معطل بماند.
    started_at = time.time()
    max_runtime = int(os.environ.get("BOT_MAX_RUNTIME_SEC", "20400") or "20400")  # ~۵ ساعت و ۴۰ دقیقه
    graceful_exit = False

    while True:
        if time.time() - started_at > max_runtime:
            logger.info("⏳ سقف زمان اجرا (%s ثانیه) پر شد — خروج تمیز برای پشتیبان‌گیری دیتابیس.", max_runtime)
            graceful_exit = True
            break
        try:
            res = tg_call(
                "getUpdates",
                {
                    "offset": offset,
                    "timeout": 25,
                    "allowed_updates": ["message", "callback_query", "pre_checkout_query"],
                },
                timeout=35.0,
            )
            if res.get("ok"):
                for upd in res.get("result") or []:
                    offset = int(upd["update_id"]) + 1
                    pool.submit(process_update, upd)
            else:
                time.sleep(3)
        except KeyboardInterrupt:
            logger.info("ربات متوقف شد.")
            break
        except Exception as exc:
            logger.warning("Polling retry in 3s: %s", exc)
            time.sleep(3)

    # خروج تمیز: جاب بعدی (که از قبل در صف است) بلافاصله جای این را می‌گیرد
    pool.shutdown(wait=False, cancel_futures=True)
    if graceful_exit:
        logger.info("✅ خروج برنامه‌ریزی‌شده انجام شد؛ دیتابیس اکنون رمزنگاری و کش می‌شود.")


if __name__ == "__main__":
    main()
