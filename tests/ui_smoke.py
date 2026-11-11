#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست مینی‌اپ در مرورگر واقعی (Playwright) — بر اساس مهارت `webapp-testing`
=======================================================================
روش کار (همان Decision Tree مهارت):
  ۱) سرور استاتیک روی docs/ بالا می‌آید (این تست خودش سرور را می‌سازد)
  ۲) صفحه در Chromium باز می‌شود و «شبکه آرام» می‌شود
  ۳) DOM رندرشده بررسی و اسکرین‌شات گرفته می‌شود
  ۴) هر خطای کنسول/صفحه = شکست تست

اجرا (محلی یا CI):
    pip install playwright && playwright install --with-deps chromium
    python tests/ui_smoke.py            # خروجی در tests/artifacts/

در سندباکس توسعه، دانلود Chromium بلاک است؛ پس اجرای رسمی در
.github/workflows/ui-audit.yml انجام می‌شود.
"""

import json
import os
import sys
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCS = HERE.parent / "docs"
OUT = HERE / "artifacts"
PORT = int(os.environ.get("UI_PORT", "8765"))

FAILS = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(("  ✅ " if cond else "  ❌ ") + name + ("" if cond or not detail else f" — {detail}"))
    if not cond:
        FAILS.append(name)


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):  # سرور بی‌صدا
        pass


def serve() -> ThreadingHTTPServer:
    handler = partial(QuietHandler, directory=str(DOCS))
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


# تلگرام قلابی: همان چیزی که مینی‌اپ از WebApp می‌خواند
FAKE_TG = """
window.Telegram = {
  WebApp: {
    initData: "stub", initDataUnsafe: { user: { id: %d, first_name: "Test", language_code: "fa" }, start_param: "" },
    ready(){}, expand(){}, onEvent(){}, offEvent(){}, enableClosingConfirmation(){},
    openTelegramLink(url){ window.__opened = url; },
    openLink(url){ window.__opened = url; },
    themeParams: {}, colorScheme: "dark", viewportStableHeight: 780,
    HapticFeedback: { impactOccurred(){}, selectionChanged(){}, notificationOccurred(){} },
    MainButton: { hide(){}, show(){}, setText(){}, onClick(){} },
    BackButton: { show(){}, hide(){}, onClick(){} }
  }
};
"""

# پرو_users قلابی تا مسیر «کاربر پرو» هم رندر شود
PRO_STUB = """
window.__proStub = true;
"""


HL_FIXTURE = {
    "universe": [{"name": n} for n in ("BTC", "ETH", "SOL", "SUI", "DOGE", "PEPE")],
}
HL_CTXS = [
    {"funding": "0.000125", "openInterest": "1000", "markPx": "60000", "prevDayPx": "59000", "dayNtlVlm": "900000000"},
    {"funding": "0.0009", "openInterest": "4000", "markPx": "3000", "prevDayPx": "2900", "dayNtlVlm": "500000000"},
    {"funding": "-0.0004", "openInterest": "2000", "markPx": "180", "prevDayPx": "185", "dayNtlVlm": "300000000"},
    {"funding": "0.0031", "openInterest": "900", "markPx": "3.4", "prevDayPx": "3.1", "dayNtlVlm": "120000000"},
    {"funding": "0.0012", "openInterest": "1500", "markPx": "0.19", "prevDayPx": "0.18", "dayNtlVlm": "80000000"},
    {"funding": "0.0019", "openInterest": "700", "markPx": "0.000012", "prevDayPx": "0.000011", "dayNtlVlm": "50000000"},
]


def route_external(route, request):
    """همهٔ درخواست‌های بیرونی با داده‌ی ثابت جواب می‌گیرند (تست قطعی و سریع).

    نکتهٔ مهم: اسکریپت واقعی telegram-web-app.js نسخهٔ قلابی ما را بازنویسی
    می‌کند و initDataUnsafe خالی می‌شود؛ پس همان مسیر را خالی برمی‌گردانیم.
    """
    url = request.url
    if "telegram.org/js/telegram-web-app.js" in url:
        return route.fulfill(status=200, content_type="application/javascript", body="/* stubbed in tests */")
    if "api.hyperliquid.xyz" in url:
        body = (request.post_data or "")
        if "metaAndAssetCtxs" in body:
            return route.fulfill(status=200, content_type="application/json",
                                 body=json.dumps([HL_FIXTURE, HL_CTXS]))
        if "clearinghouseState" in body:
            return route.fulfill(status=200, content_type="application/json", body=json.dumps({
                "marginSummary": {"accountValue": "1250000", "totalNtlPos": "800000"},
                "assetPositions": [{"position": {"coin": "BTC", "szi": "2.5", "positionValue": "150000",
                                                 "unrealizedPnl": "4200", "entryPx": "59000"}}],
            }))
        return route.fulfill(status=200, content_type="application/json", body=json.dumps({"leaderboardRows": []}))
    if "alternative.me" in url:
        return route.fulfill(status=200, content_type="application/json",
                             body=json.dumps({"data": [{"value": "62", "value_classification": "Greed"}]}))
    if "okx.com" in url:
        return route.fulfill(status=200, content_type="application/json", body=json.dumps({"data": [{"fundingRate": "0.00013"}]}))
    if "dexscreener" in url:
        return route.fulfill(status=200, content_type="application/json", body=json.dumps({"pairs": [{
            "chainId": "ethereum", "priceUsd": "0.0000123", "liquidity": {"usd": 320000},
            "baseToken": {"symbol": "PEPE", "address": "0x6982508145454ce325ddbe47a25d4ec3d2311933"}}]}))
    if "gopluslabs" in url:
        return route.fulfill(status=200, content_type="application/json", body=json.dumps({"result": {
            "0x6982508145454ce325ddbe47a25d4ec3d2311933": {"is_honeypot": "0", "buy_tax": "0", "sell_tax": "0.05"}}}))
    if "api.github.com" in url:
        return route.fulfill(status=200, content_type="application/json", body=json.dumps({"workflow_runs": []}))
    if "127.0.0.1" in url or "localhost" in url:
        return route.continue_()
    return route.fulfill(status=204, content_type="text/plain", body="")


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        print("⚠️ playwright نصب نیست — pytest/jsdom کافی است یا در CI اجرا شود.")
        return 0

    OUT.mkdir(exist_ok=True)
    srv = serve()
    base = f"http://127.0.0.1:{PORT}"
    time.sleep(0.4)
    console_errors: list[str] = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(viewport={"width": 390, "height": 844}, locale="fa-IR")
            ctx.route("**/*", route_external)
            ctx.add_init_script(FAKE_TG % 999000111)
            page = ctx.new_page()
            page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: console_errors.append("pageerror: " + str(e)))

            print("\n🧪 TradeGuard — UI smoke (Chromium)\n")
            page.goto(f"{base}/app.html", wait_until="networkidle")
            page.wait_for_timeout(1200)

            check("صفحه بالا آمد", page.title() != "")
            check("رادار رندر شد", page.locator("#radarList .row").count() > 0,
                  str(page.locator("#radarList .row").count()))

            # آنبوردینگ اولین اجرا: باید روی صفحه باشد و با «رد کردن» بسته شود
            onboard = page.locator("#onboard")
            ob_shown = onboard.is_visible()
            check("آنبوردینگ اولین اجرا نمایش داده می‌شود", ob_shown)
            if ob_shown:
                page.screenshot(path=str(OUT / "00-onboarding.png"))
                page.click("#obSkip")
                page.wait_for_timeout(250)
                check("آنبوردینگ با «رد کردن» بسته می‌شود", not onboard.is_visible())
                page.reload(wait_until="networkidle")
                page.wait_for_timeout(700)
                check("اجرای بعدی، آنبوردینگ دوباره نشان داده نمی‌شود",
                      not page.locator("#onboard").is_visible())

            # دیده‌بان: ستاره‌کردن اولین ارز رادار
            first_star = page.locator("#radarList .fav-btn").first
            if first_star.count():
                first_star.click()
                page.wait_for_timeout(200)
                check("ستاره‌کردن ارز، ردیف را در دیده‌بان نگه می‌دارد",
                      page.locator("#radarList .fav-btn >> nth=0").inner_text().strip() == "★")
                page.click("#favFilter")
                page.wait_for_timeout(250)
                check("فیلتر دیده‌بان فقط ارزهای ستاره‌شده را نشان می‌دهد",
                      page.locator("#radarList .row").count() == 1,
                      str(page.locator("#radarList .row").count()))
                page.screenshot(path=str(OUT / "00-watchlist.png"))
                page.click("#favFilter")
                page.wait_for_timeout(200)

            page.screenshot(path=str(OUT / "01-radar.png"), full_page=True)

            # تب اشتراک + شیت پرداخت
            page.click('.tab-btn[data-tab="sub"]')
            page.wait_for_timeout(300)
            check("تب اشتراک فعال شد", page.locator('[data-pane="sub"]').is_visible())
            link_val = page.input_value("#refLink")
            tg_state = page.evaluate("JSON.stringify((window.Telegram && window.Telegram.WebApp && "
                                     "window.Telegram.WebApp.initDataUnsafe) || null)")
            check("لینک دعوت واقعی است", link_val.startswith("https://t.me/") and "start=ref_" in link_val,
                  f"value={link_val!r} | initDataUnsafe={tg_state}")
            page.screenshot(path=str(OUT / "02-subscription.png"), full_page=True)

            # دورهٔ رایگان (freeMode=true در pro_users.json) کارت خرید را عمداً پنهان می‌کند؛
            # در آن حالت باید نشان «رایگان» دیده شود و هیچ مسیر پرداختی باز نباشد.
            if page.locator("#buyBtn").is_visible():
                page.click("#buyBtn")
                page.wait_for_timeout(250)
                check("شیت پرداخت باز شد", page.locator("#invoice").is_visible())
                check("نام ربات درست است", "@TradeGuard1_bot" in page.inner_text("#invBotName"),
                      page.inner_text("#invBotName"))
                check("ادعای موفقیت جعلی وجود ندارد", page.locator("#payBtn").count() == 0)
                page.screenshot(path=str(OUT / "03-invoice.png"))

                page.click("#startBtn")
                page.wait_for_timeout(250)
                opened = page.evaluate("window.__opened || ''")
                check("دکمه پرداخت چت ربات را باز می‌کند", "?start=pro" in str(opened), str(opened))
            else:
                check("دورهٔ رایگان: یادداشت «رایگان» دیده می‌شود",
                      page.locator("#freeNote").is_visible())
                check("دورهٔ رایگان: کارت خرید بسته است (همه‌چیز باز است)",
                      not page.locator("#subIdle").is_visible())
                check("دورهٔ رایگان: نشان پلن «رایگان» است",
                      "رایگان" in page.inner_text("#planChip"), page.inner_text("#planChip"))
                page.screenshot(path=str(OUT / "03-free-mode.png"), full_page=True)

            # گارد + اسکنر
            page.click('.tab-btn[data-tab="guard"]')
            page.wait_for_timeout(250)
            check("محاسبه‌گر گارد خروجی دارد", page.inner_text("#outLot").strip() != "")
            page.screenshot(path=str(OUT / "04-guard.png"), full_page=True)

            page.click('.tab-btn[data-tab="radar"]')
            page.fill("#rugInput", "PEPE")
            page.click("#rugScanBtn")
            page.wait_for_timeout(1500)
            check("اسکنر توکن جواب داد", page.inner_text("#rugOut").strip() != "")
            page.screenshot(path=str(OUT / "05-scanner.png"))

            # صفحه معرفی: داخل تلگرام، index.html عمداً به app.html ریدایرکت می‌شود؛
            # پس لندینگ را در یک کانتکست «مرورگر معمولی» (بدون تلگرام) می‌بینیم.
            page.goto(f"{base}/index.html", wait_until="domcontentloaded")
            page.wait_for_timeout(900)
            check("داخل تلگرام، index.html به مینی‌اپ هدایت می‌شود",
                  page.url.endswith("/app.html") or "app.html" in page.url, page.url)

            ctx2 = browser.new_context(viewport={"width": 1280, "height": 900})
            ctx2.route("**/*", route_external)
            page2 = ctx2.new_page()
            page2.on("pageerror", lambda e: console_errors.append("landing pageerror: " + str(e)))
            page2.goto(f"{base}/index.html", wait_until="domcontentloaded")
            page2.wait_for_timeout(1200)
            model_count = page2.locator("#model").count()
            check("صفحه معرفی رندر شد", model_count == 1, f"count={model_count} url={page2.url}")
            check("بخش شبیه‌ساز درآمد هم هست", page2.locator("#simSection").count() == 1)
            page2.screenshot(path=str(OUT / "06-landing.png"), full_page=True)

            # درخواست‌های بیرونی عمداً خاموش‌اند؛ ERR_FAILED آن‌ها خطای اپ نیست
            noisy = ("favicon", "failed to load resource", "err_failed", "net::")
            real_errors = [e for e in console_errors if not any(n in e.lower() for n in noisy)]
            check("هیچ خطای کنسول/صفحه‌ای نبود", not real_errors, " | ".join(real_errors[:2]))
            (OUT / "console.json").write_text(json.dumps(console_errors, ensure_ascii=False, indent=1), encoding="utf-8")
            browser.close()
    finally:
        srv.shutdown()

    print("\n" + "─" * 46)
    if FAILS:
        print(f"❌ {len(FAILS)} سنجه شکست خورد: {', '.join(FAILS)}")
        return 1
    print(f"✅ همهٔ سنجه‌های مرورگر سبز — اسکرین‌شات‌ها: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
