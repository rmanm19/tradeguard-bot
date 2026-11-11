/* ============================================================================
   TradeGuard — docs/config.js
   ⚠️ این فایل به‌طور خودکار توسط .github/workflows/sync-app-config.yml
      از روی Secretهای گیت‌هاب ساخته می‌شود؛ دستی ویرایش نکنید.

   adminHashes: sha256("tg-admin:" + <telegram_user_id>) ولی فقط ۱۶ کاراکتر اول
   چرا هش؟ چون فایل عمومی است و آیدی عددی مؤسس نباید متن‌باز پخش شود.
   برای اینکه پنل مدیر ظاهر شود: Secret با نام ADMIN_USER_ID را بگذارید و
   workflow «Sync App Config» را اجرا کنید (یا منتظر اجرای خودکارش بمانید).
   ============================================================================ */
window.TG_CONFIG = {
  generatedAt: null,
  repo: "rmanm19/tradeguard-bot",
  botUsername: "TradeGuard1_bot",
  adminHashes: []
};
