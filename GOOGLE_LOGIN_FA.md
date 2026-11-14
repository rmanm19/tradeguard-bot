# 🔐 راه‌اندازی «ورود با گوگل» (۵ دقیقه، یک‌بار)

این صفحه دقیقاً همان کاری را می‌گوید که باید در **Google Cloud Console** انجام شود تا
`/login` در ربات کار کند. تا وقتی این کار انجام نشده، ربات صادقانه می‌گوید
«ورود با گوگل هنوز تنظیم نشده» و هیچ چیز دیگری نمی‌شکند.

> **رمز گوگل هیچ‌وقت از ربات عبور نمی‌کند.** ما از *Device Flow* استفاده می‌کنیم:
> ربات فقط یک «کد» از گوگل می‌گیرد، تو خودت آن کد را در `google.com/device` وارد
> می‌کنی و تأیید می‌کنی؛ بعد ربات فقط «آیا تأیید شد؟» را می‌پرسد.

---

## ۱) ساختن پروژه و صفحهٔ رضایت

1. برو به <https://console.cloud.google.com/> و بالا سمت چپ یک **پروژهٔ تازه** بساز
   (اسمش هرچه باشد، مثلاً `TradeGuard`).
2. از منو: **APIs & Services → OAuth consent screen**
   - User type: **External** → `CREATE`
   - App name: `TradeGuard` · User support email: ایمیل خودت · Developer contact: همان ایمیل → `SAVE AND CONTINUE`
3. مرحلهٔ **Scopes** → `ADD OR REMOVE SCOPES` → این سه را تیک بزن و تأیید کن:
   - `openid`
   - `.../auth/userinfo.email`
   - `.../auth/userinfo.profile`
4. مرحلهٔ **Test users**: اگر وضعیت انتشار (Publishing status) روی **Testing** است،
   ایمیل گوگل خودت را به‌عنوان Test user اضافه کن — وگرنه خودت هم نمی‌توانی تأیید کنی.
   (این اسکوپ‌ها «حساس» نیستند، پس نیازی به Review گوگل نداری.)
5. `BACK TO DASHBOARD`.

## ۲) ساختن کلاینت از نوع درست

**APIs & Services → Credentials → + CREATE CREDENTIALS → OAuth client ID**

| فیلد | مقدار |
|---|---|
| Application type | **TVs and Limited Input devices** ← این مهم‌ترین انتخاب کل این صفحه است |
| Name | `TradeGuard bot` |

بعد از `CREATE`، دو مقدار نمایش داده می‌شود:

- **Client ID** — چیزی شبیه `123456789012-abc123def456.apps.googleusercontent.com`
- **Client secret** — چیزی شبیه `GOCSPX-xxxxxxxxxxxxxxxxxxxx`

> اگر نوع کلاینت را `Web application` یا `Desktop app` بگذاری، ورود کار **نمی‌کند**:
> گوگل برای Device Flow فقط به کلاینت نوع «TVs and Limited Input devices» کد می‌دهد.

## ۳) کجا بگذاریمش (دو راه، هر دو درست)

### راه A — GitHub Secrets (توصیه‌شده)
`Settings → Secrets and variables → Actions → New repository secret`

| Name | Secret |
|---|---|
| `GOOGLE_CLIENT_ID` | همان Client ID |
| `GOOGLE_CLIENT_SECRET` | همان Client secret |

ورک‌فلو این دو را به env ربات می‌دهد (`.github/workflows/bot.yml`). بعد از ذخیره،
خودِ ربات در ≤۵ دقیقه با کد جدید بالا می‌آید و کلیدها را می‌بیند.

### راه B — مستقیم در تلگرام (سریع‌تر، بدون دست‌زدن به گیت‌هاب)
فقط ادمین ربات:

```
/google id 123456789012-abc123def456.apps.googleusercontent.com
/google secret GOCSPX-xxxxxxxxxxxxxxxxxxxx
```

پیامِ حاوی Secret بلافاصله از چت **پاک می‌شود**. مقدارها در دیتابیس ذخیره می‌شوند و
`/google` منبعشان را نشان می‌دهد (`Secrets` یا `دیتابیس`).

> **اولویت:** اگر هر دو جا ست شده باشند، **Secret گیت‌هاب** برنده است.

## ۴) تست کن — بدون اینکه منتظر کسی بمانی

در چت با ربات (به‌عنوان ادمین):

```
/google test
```

این دستور یک تماس **واقعی** با گوگل می‌زند و دقیقاً می‌گوید چه خبر است:

| پاسخ | معنی | کار |
|---|---|---|
| `✅ کلیدها درست‌اند` | گوگل کد دستگاه داد؛ نوع کلاینت و کلیدها درست است | برو سراغ `/login` |
| `invalid_client` | ID و Secret با هم نمی‌خوانند، یا نوع کلاینت اشتباه است | مرحلهٔ ۲ را چک کن |
| `unauthorized_client` | این کلاینت اجازهٔ Device Flow ندارد | باید نوعش «TVs and Limited Input devices» باشد |
| `invalid_scope` | اسکوپ‌ها در consent screen تأیید نشده‌اند | مرحلهٔ ۱ بند ۳ |
| `network: …` | سرور ربات به گوگل دسترسی نداشت | چند دقیقه بعد دوباره |

بعد:

```
/google          → وضعیت: کلید ست شده؟ چند نفر تأیید کرده‌اند؟
/login           → همان چیزی که کاربر عادی می‌بیند (کد + لینک google.com/device)
```

## ۵) چه چیزی ذخیره می‌شود (و چه چیزی نه)

| ذخیره می‌شود | ذخیره نمی‌شود |
|---|---|
| شناسهٔ پایدار گوگل (`sub`) | رمز گوگل |
| ۱۶ کاراکتر اول `sha256(ایمیل)` | ایمیل خام |
| زمان تأیید + روزهای پاداش | توکن دسترسی/رفرش |

- `/logout` دسترسی را در سمت ما باطل می‌کند (`revoked = 1`).
- پاداش تأیید پیش‌فرض **۳۰ روز پرو** است و با `/google days N` عوض می‌شود (`0` = بدون پاداش).
- اسکوپ درخواستی فقط `openid email` است؛ **هیچ** دسترسی به جیمیل، درایو یا تقویم
  درخواست نمی‌شود (همین در تست‌ها هم قفل شده است).

## ۶) اگر بعداً کلید را عوض کردی

`/google id …` و `/google secret …` با مقدار تازه، یا Secret گیت‌هاب را به‌روز کن و
یک‌بار `workflow_dispatch` بزن. تأییدهای قبلیِ کاربران معتبر می‌مانند (کلیدِ جدید فقط
برای *تأییدهای تازه* استفاده می‌شود).

---

**جمع‌بندی برای کسی که عجله دارد:** پروژه → OAuth consent screen (External + سه اسکوپ
+ Test user) → Credentials → OAuth client ID از نوع **TVs and Limited Input devices** →
دو مقدار را در Secrets بگذار → `/google test` → `/login`. تمام.
