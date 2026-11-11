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
            page.screenshot(path=str(OUT / "01-radar.png"), full_page=True)

            # تب اشتراک + شیت پرداخت
            page.click('.tab-btn[data-tab="sub"]')
            page.wait_for_timeout(300)
            check("تب اشتراک فعال شد", page.locator('[data-pane="sub"]').is_visible())
            link_val = page.input_value("#refLink")
            check("لینک دعوت واقعی است", link_val.startswith("https://t.me/") and "start=ref_" in link_val, link_val)
            page.screenshot(path=str(OUT / "02-subscription.png"), full_page=True)

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

            # صفحه معرفی
            page.goto(f"{base}/index.html", wait_until="networkidle")
            page.wait_for_timeout(800)
            check("صفحه معرفی رندر شد", page.locator("#model").count() == 1)
            page.screenshot(path=str(OUT / "06-landing.png"), full_page=True)

            real_errors = [e for e in console_errors if "favicon" not in e.lower()]
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
