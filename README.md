<p align="center">
  <img src="assets/readme/banner.svg" alt="Zankode VPN" width="100%" />
</p>

<p align="center">
  <strong>Zankode VPN v2.2.0</strong><br/>
  A modular Telegram bot for selling, delivering, and operating VPN configuration services.
</p>

<p align="center">
  <a href="#fa">فارسی</a> ·
  <a href="#en">English</a> ·
  <a href="#project-structure">Project Structure</a> ·
  <a href="#github-actions">GitHub Actions</a>
</p>

---

<a id="fa"></a>
# 🇮🇷 معرفی فارسی

**Zankode VPN** یک ربات تلگرام ماژولار برای **فروش، مدیریت موجودی، پرداخت، تحویل و پشتیبانی سرویس‌های VPN** است. کاربر تمام مراحل خرید را داخل تلگرام انجام می‌دهد و ادمین نیز از پنل مدیریتی داخل خود ربات، سفارش‌ها، کاربران، موجودی، کیف پول، Referral، Gift Code، اکانت تست، گزارش‌ها و عملیات روزانه را مدیریت می‌کند.

> [!IMPORTANT]
> از نسخه **v2.2.0**، Zankode VPN علاوه بر Inventory داخلی، به‌صورت مستقیم به **3X-UI Clients API** متصل می‌شود. برای هر پلن می‌توان حالت تحویل را مستقل روی `Inventory` یا `3X-UI` گذاشت. در حالت 3X-UI، ساخت Client، تمدید، Reset Traffic، حذف، Sync وضعیت، حجم، انقضا و IP Limit از داخل ربات انجام می‌شود.

## ✨ امکانات اصلی

<table>
  <tr>
    <td align="center" width="20%"><img src="assets/readme/icons/user-panel.svg" width="64" alt="User panel"/><br/><b>پنل کاربر</b></td>
    <td align="center" width="20%"><img src="assets/readme/icons/admin-panel.svg" width="64" alt="Admin panel"/><br/><b>پنل ادمین</b></td>
    <td align="center" width="20%"><img src="assets/readme/icons/wallet.svg" width="64" alt="Wallet"/><br/><b>کیف پول</b></td>
    <td align="center" width="20%"><img src="assets/readme/icons/referral.svg" width="64" alt="Referral"/><br/><b>Referral</b></td>
    <td align="center" width="20%"><img src="assets/readme/icons/gift.svg" width="64" alt="Gift"/><br/><b>Gift Code</b></td>
  </tr>
</table>

<p align="center">
  <img src="assets/readme/icons/xui.svg" width="72" alt="3X-UI automation"/><br/>
  <strong>Direct 3X-UI Automation</strong>
</p>

### 🔌 اتصال مستقیم 3X-UI

- اتصال با API Token به Clients API جدید 3X-UI
- سازگار با مدل Client-first و Multi-Inbound نسخه‌های جدید
- ساخت خودکار Client پس از تأیید سفارش
- انتخاب یک یا چند `Inbound ID` برای هر پلن
- تعیین Traffic Quota بر حسب GB برای هر پلن
- تعیین IP Limit برای هر پلن
- تنظیم Expiry بر اساس مدت پلن
- دریافت لینک‌های واقعی Client از خود 3X-UI در صورت نبود Subscription Template
- تمدید همان Client قبلی به‌جای ساخت Client تکراری
- Reset Traffic هنگام تمدید
- نمایش وضعیت زنده، حجم مصرفی/باقی‌مانده و تاریخ انقضا برای کاربر
- Sync و حذف Client از پنل ادمین
- مرکز اتصال 3X-UI و Health Check داخل پنل ادمین
- ثبت نگاشت محلی `Order ↔ User ↔ 3X-UI Client` برای Retry امن
- جلوگیری از ساخت Client تکراری اگر ساخت Remote موفق شود ولی تحویل Telegram موقتاً شکست بخورد
- Legacy mode اختیاری برای پنل‌های قدیمی‌تر

### 👤 پنل کاربران

- ثبت خودکار کاربر در اولین ورود
- مشاهده و خرید پلن‌های فعال
- ایجاد سفارش و ارسال فیش پرداخت
- پرداخت با موجودی کیف پول
- شارژ کیف پول و ارسال فیش شارژ
- استفاده از کد تخفیف
- تحویل کانفیگ پس از تأیید سفارش
- مشاهده سرویس‌های خریداری‌شده و جزئیات سفارش‌ها
- مشاهده تاریخ خرید، تاریخ انقضا و وضعیت سرویس
- مشاهده وضعیت لحظه‌ای سرویس‌های 3X-UI شامل مصرف، مانده حجم، انقضا و IP Limit
- درخواست تمدید سرویس
- دریافت مجدد کانفیگ‌های طولانی به‌صورت فایل محافظت‌شده
- خرید سرویس به‌عنوان هدیه
- دریافت هدیه با Gift Code
- دریافت اکانت تست از موجودی تست
- سیستم دعوت دوستان و Referral
- دریافت کمیسیون Referral در کیف پول
- نمایش سطح مشتری و پیشرفت VIP
- ثبت و پیگیری تیکت پشتیبانی

### 👑 پنل ادمین

- مشاهده داشبورد آماری فروش و عملیات، به‌همراه آمار سرویس‌های 3X-UI
- مرکز 3X-UI برای Health Check، Sync و مدیریت سرویس‌های Remote
- بررسی، تأیید و رد فیش‌های سفارش
- مشاهده **نام خریدار + پلن خریداری‌شده** در لیست سفارش‌ها
- مشاهده ریز خریدهای هر کاربر از پروفایل ادمین
- مدیریت کاربران، مسدودسازی و جستجو
- ثبت یادداشت خصوصی برای هر کاربر
- مدیریت پلن‌ها و بایگانی امن پلن‌ها
- مدیریت Inventory کانفیگ‌ها
- مشاهده موجودی آزاد، رزروشده و مصرف‌شده
- جستجوی کانفیگ‌ها و جستجوی سراسری
- مدیریت کیف پول کاربران و درخواست‌های شارژ
- مدیریت Coupon / کد تخفیف
- مدیریت Gift Code و سرویس‌های هدیه
- مدیریت موجودی و درخواست اکانت تست
- بررسی دستی کاربران مشکوک برای اکانت تست
- مدیریت تیکت‌های پشتیبانی
- Broadcast همگانی و پیام هدفمند به Segmentها
- Segmentهای VIP، وفادار، از‌دست‌رفته و مشکوک
- گزارش فروش روزانه/ماهانه
- تاریخچه تحویل سرویس و اکانت تست
- خروجی CSV از داده‌های مدیریتی
- بکاپ دیتابیس
- تنظیمات فروشگاه و Premium Emojiهای منوی کاربر

### ⚙️ عملیات خودکار

<p align="center"><img src="assets/readme/icons/automation.svg" width="72" alt="Automation"/></p>

ربات یک حلقه‌ی نگهداری پس‌زمینه دارد که در کنار Long Polling اجرا می‌شود و کارهای عملیاتی را انجام می‌دهد، از جمله:

- هشدار کمبود موجودی پلن‌ها
- هشدار کمبود اکانت تست
- اعلان نزدیک‌شدن به تاریخ انقضا
- اعلان سرویس منقضی‌شده
- لغو سفارش‌های پرداخت‌نشده‌ی قدیمی طبق تنظیمات
- گزارش‌های دوره‌ای
- پاک‌سازی/کنترل Log
- بازیابی رزروهای نیمه‌کاره پس از Restart
- بازیابی Gift Redemption نیمه‌کاره در صورت Crash

## 🧠 مدل داده و ذخیره‌سازی

<p align="center"><img src="assets/readme/icons/database.svg" width="72" alt="SQLite database"/></p>

پروژه از **SQLite** استفاده می‌کند. اطلاعات اصلی شامل کاربران، پلن‌ها، موجودی، سفارش‌ها، کیف پول، Referral، Gift Code، اکانت تست، تیکت‌ها، تنظیمات، Audit و گزارش‌های تحویل داخل دیتابیس پروژه نگهداری می‌شوند.

چند نکته‌ی مهم در لایه‌ی Storage:

- Foreign Keyها فعال هستند.
- Transactionهای SQLite پس از `with` واقعاً بسته می‌شوند.
- Migrationهای امن برای دیتابیس نسخه‌های قبلی وجود دارد.
- Integrity Check هنگام Startup انجام می‌شود.
- رزروهای قدیمی و Giftهای نیمه‌کاره بازیابی می‌شوند.
- ارتباط دقیق `user_id` با سفارش و `plan_title` حفظ می‌شود.

---

<a id="project-structure"></a>
## 🧱 ساختار پروژه

```text
Zankode-VPN/
├── main.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── CHANGELOG.md
│
├── docs/
│   └── 3xui-setup.md
│
├── assets/
│   └── readme/
│       ├── banner.svg
│       └── icons/
│           ├── admin-panel.svg
│           ├── automation.svg
│           ├── ci.svg
│           ├── database.svg
│           ├── file.svg
│           ├── folder.svg
│           ├── gift.svg
│           ├── referral.svg
│           ├── user-panel.svg
│           ├── wallet.svg
│           ├── workflow.svg
│           └── xui.svg
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── tests/
│   ├── test_admin_purchase_views.py
│   ├── test_services.py
│   ├── test_smoke.py
│   └── test_xui.py
│
└── zankode/
    ├── __init__.py
    ├── __main__.py
    ├── app.py
    ├── config.py
    ├── services.py
    ├── storage.py
    ├── ui.py
    ├── utils.py
    ├── xui.py
    │
    └── handlers/
        ├── __init__.py
        ├── admin.py
        ├── admin_views.py
        ├── commands.py
        ├── messages.py
        ├── router.py
        └── user.py
```

### 📁 وظیفه‌ی فایل‌ها

<table>
  <tr>
    <td align="center"><img src="assets/readme/icons/folder.svg" width="48" alt="Folder"/><br/><b>Folder</b><br/>گروه‌بندی ماژول‌ها و فایل‌ها</td>
    <td align="center"><img src="assets/readme/icons/file.svg" width="48" alt="File"/><br/><b>File</b><br/>هر فایل یک مسئولیت مشخص دارد</td>
    <td align="center"><img src="assets/readme/icons/workflow.svg" width="48" alt="Workflow"/><br/><b>Workflow</b><br/>دستور اجرای خودکار برای GitHub Actions</td>
  </tr>
</table>

| مسیر | وظیفه |
|---|---|
| `main.py` | Entry Point ساده برای اجرای پروژه با `python main.py` |
| `requirements.txt` | Dependencyهای Python پروژه |
| `.env.example` | الگوی متغیرهای محرمانه و تنظیمات محیطی |
| `.gitignore` | جلوگیری از Commit شدن `.env`، دیتابیس، Log و فایل‌های Runtime |
| `CHANGELOG.md` | تاریخچه تغییرات نسخه‌ها |
| `assets/readme/` | تمام تصاویر و آیکون‌های README؛ فقط SVG |
| `zankode/app.py` | ساخت Telegram Application، ثبت Handlerها، Startup و Long Polling |
| `zankode/config.py` | تنظیمات اصلی، متغیرهای محیطی، ثابت‌ها، Logging و Premium Emoji |
| `zankode/storage.py` | Schema، Migration، Queryها، Transactionها و منطق دیتابیس SQLite |
| `zankode/services.py` | تحویل کانفیگ، Gift، Provision/Sync سرویس 3X-UI، هشدارها، Backup و عملیات دوره‌ای |
| `zankode/xui.py` | Adapter مستقل برای Clients API جدید 3X-UI و Legacy X-UI |
| `zankode/ui.py` | متن‌ها، Keyboardها، Buttonها و View helperهای رابط تلگرام |
| `zankode/utils.py` | توابع کمکی، زمان ایران، فرمت پول، اعتبارسنجی و ابزارهای عمومی |
| `handlers/commands.py` | Commandهایی مانند `/start`، `/admin`، `/account` و ... |
| `handlers/router.py` | Router مرکزی Callback Queryهای دکمه‌های Inline |
| `handlers/user.py` | جریان‌ها و عملیات سمت کاربر |
| `handlers/admin.py` | Actionها و Callbackهای مدیریتی |
| `handlers/admin_views.py` | صفحات مدیریتی، لیست‌ها، گزارش‌ها، Export CSV و Viewهای ادمین |
| `handlers/messages.py` | دریافت فیش، پیام متنی، Broadcast و Actionهای وابسته به Message |
| `tests/` | تست‌های خودکار دیتابیس، سرویس‌ها، نمایش خریدها و اتصال شبیه‌سازی‌شده 3X-UI |
| `docs/3xui-setup.md` | راهنمای تنظیم API Token، Inbound و متغیرهای محیطی 3X-UI |

---

<a id="github-actions"></a>
## 🔁 GitHub Actions / CI

<p align="center"><img src="assets/readme/icons/ci.svg" width="72" alt="Continuous Integration"/></p>

فایل زیر:

```text
.github/workflows/ci.yml
```

یک **Workflow خودکار GitHub Actions** است. هر بار که روی Repository `push` انجام شود یا Pull Request ساخته شود، GitHub روی یک ماشین Ubuntu تمیز پروژه را بررسی می‌کند.

Workflow فعلی پروژه این مراحل را انجام می‌دهد:

1. دریافت سورس با `actions/checkout@v4`
2. اجرای جداگانه روی Python `3.10`، `3.11` و `3.12`
3. نصب `requirements.txt`
4. Compile کردن تمام فایل‌های Python
5. اجرای تمام Unit Testهای پوشه `tests/`

در نتیجه اگر تغییری باعث Syntax Error یا شکست تست‌ها شود، قبل از Merge شدن روی GitHub با علامت ❌ مشخص می‌شود.

> [!NOTE]
> پوشه `.github/workflows` بخشی از خود برنامه‌ی Telegram نیست و روی سرور Bot اجرا نمی‌شود. این پوشه فقط به **GitHub** می‌گوید هنگام Push/PR چه تست‌های خودکاری اجرا کند.

---

## ⚙️ پیش‌نیازها

- Python **3.10+**
- Telegram Bot Token
- Telegram numeric Admin User ID
- SQLite 3

Dependencyهای اصلی:

```text
python-telegram-bot==22.8
httpx>=0.27,<1
python-dotenv>=1.0,<2
```

## 🚀 نصب و اجرا

### 1. Clone

```bash
git clone https://github.com/YOUR_USERNAME/Zankode-VPN.git
cd Zankode-VPN
```

### 2. ساخت Virtual Environment

Linux / macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. نصب Dependencyها

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. ساخت `.env`

Linux / macOS:

```bash
cp .env.example .env
```

Windows:

```powershell
copy .env.example .env
```

محتوای نمونه:

```env
BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
ADMIN_USER_ID=123456789
DB_FILE=config_shop.db

XUI_PANEL_URL=https://panel.example.com/secret-path
XUI_API_TOKEN=YOUR_3XUI_API_TOKEN
XUI_API_MODE=modern
XUI_VERIFY_TLS=1
XUI_TIMEOUT=15
# Optional: if empty, Zankode can fall back to 3X-UI generated client links
XUI_SUB_URL_TEMPLATE=https://sub.example.com/sub/{sub_id}
```

| متغیر | توضیح |
|---|---|
| `BOT_TOKEN` | توکن دریافتی از BotFather |
| `ADMIN_USER_ID` | ID عددی ادمین اصلی |
| `DB_FILE` | مسیر یا نام فایل SQLite |
| `XUI_PANEL_URL` | آدرس پنل 3X-UI همراه Base Path در صورت وجود |
| `XUI_API_TOKEN` | API Token پنل برای Clients API |
| `XUI_API_MODE` | حالت `modern`، `legacy` یا `auto` |
| `XUI_VERIFY_TLS` | بررسی معتبر بودن TLS؛ در Production روشن بماند |
| `XUI_SUB_URL_TEMPLATE` | اختیاری؛ قالب لینک Subscription با `{sub_id}` |

### 5. اجرا

```bash
python main.py
```

یا:

```bash
python -m zankode
```

پس از اجرا، Bot با **Long Polling** شروع به کار می‌کند و کاربر از `/start` وارد منوی اصلی می‌شود.

## 🧪 اجرای تست‌ها

```bash
python -m unittest discover -s tests -v
```

بررسی Compile:

```bash
python -m compileall -q .
```

## 🔐 نکات امنیتی قبل از انتشار

- فایل `.env` را هرگز Commit نکنید.
- Bot Token واقعی را داخل README، Issue، Screenshot یا Log قرار ندهید.
- API Token، آدرس خصوصی پنل و Credentialهای 3X-UI را هم هرگز Commit نکنید.
- فایل دیتابیس واقعی مشتریان را روی GitHub قرار ندهید.
- قبل از Public کردن Repository، یک بار `git status` و `.gitignore` را بررسی کنید.
- برای Bot Production از یک سرور با Backup منظم استفاده کنید.
- دسترسی Admin را فقط به Telegram User ID مورد اعتماد بدهید.
- اگر پروژه را عمومی می‌کنید، قبل از انتشار نوع License را آگاهانه انتخاب کنید.

## 🧩 تست‌شده در v2.2.0

- Database initialization & integrity checks
- Buyer ↔ Order ↔ Plan mapping
- Admin purchase views
- Retry behavior for stock/expiry notifications
- Long configuration delivery & failed-delivery safety
- Legacy brand migration & Gift crash recovery
- 3X-UI modern API Bearer authentication contract
- 3X-UI Client creation + read-back
- Server-generated credential model for modern 3X-UI
- 3X-UI direct client-link fallback
- Live traffic/status parsing
- Renewal + quota/IP update + traffic reset
- Idempotent retry after Telegram delivery failure

در بسته‌ی Release، تست‌های شبکه‌ای 3X-UI با `httpx.MockTransport` اجرا می‌شوند تا بدون نیاز به سرور واقعی، Request/Response contract و سناریوهای خطا قابل تکرار باشند. تست واقعی شبکه به آدرس و Token محیط Production وابسته است.

---

<a id="en"></a>
# 🇬🇧 English Overview

**Zankode VPN** is a modular Telegram bot for **selling, tracking, delivering, and operating VPN configuration services**. Users complete the purchase flow directly inside Telegram, while administrators manage orders, buyers, inventory, wallets, referrals, gift codes, test accounts, reports, support tickets, and routine operations from an in-bot admin panel.

> [!IMPORTANT]
> Starting with **v2.2.0**, Zankode VPN supports both internal inventory delivery and direct **3X-UI Clients API** provisioning. Each plan can independently use `Inventory` or `3X-UI` mode. In 3X-UI mode the bot can create, renew, reset traffic, delete and synchronize client state without touching the panel database directly.

## ✨ Features

### 🔌 Direct 3X-UI Automation

- API-token authentication against the modern 3X-UI Clients API
- Automatic client provisioning after payment approval
- Per-plan inbound IDs, traffic quota, expiry and IP limit
- Safe renewal of the existing remote client
- Traffic reset during renewal
- Live user status with usage, remaining traffic and expiry
- Admin health check, sync and remote-client deletion
- Local `Order ↔ User ↔ Client` mapping for crash-safe/idempotent retries
- Delivery using an explicit subscription template or panel-generated client links
- Optional legacy X-UI compatibility mode

### 👤 User Panel

- Automatic registration on first interaction
- Browse and purchase active plans
- Receipt-based order flow
- Wallet payments and wallet top-ups
- Coupon support
- Automatic or admin-approved config delivery
- Purchased services and order history
- Live 3X-UI service status and usage refresh
- Purchase and expiry information
- Renewal requests
- Safe re-delivery of long configurations as protected files
- Gift purchases and Gift Code redemption
- Test-account inventory
- Referral links and referral commissions
- Buyer bonus and wallet rewards
- VIP/customer-level progress
- Support tickets

### 👑 Admin Panel

- Operational dashboard with 3X-UI service metrics
- 3X-UI connection center, health check, sync and deletion controls
- Approve/reject payment receipts
- See **buyer name + purchased plan** in order lists
- Open the complete purchase history of a specific user
- User search, blocking, notes, and account management
- Plan management and safe plan archiving
- Config inventory management
- Available/reserved/used stock visibility
- Config search and global search
- Wallet adjustments and top-up approval
- Coupon management
- Gift management
- Test-account inventory and suspicious-request review
- Support-ticket management
- Global and segmented broadcasts
- VIP / loyal / lost / suspicious user segments
- Sales reports and delivery history
- CSV exports
- Database backups
- Store settings and Telegram Premium Emoji configuration

## ⚙️ Background Operations

The bot runs an operations loop alongside Telegram long polling. It handles low-stock warnings, test-stock warnings, expiry notifications, old unpaid-order cleanup, scheduled reports, log maintenance, stale reservation recovery, and crash-safe gift redemption recovery.

## 🧱 Architecture

```text
Telegram
   │
   ▼
Zankode Application
   ├── Commands
   ├── Callback Router
   ├── User Flows
   ├── Admin Flows
   ├── Message / Receipt Flows
   │
   ├── UI Layer
   ├── Services Layer
   ├── Storage Layer ─────► SQLite
   │
   └── 3X-UI Adapter ─────► 3X-UI Clients API ─────► Xray
```

The application uses **long polling**, so a public webhook endpoint or web dashboard is not required for the Telegram bot itself.

## 🚀 Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/Zankode-VPN.git
cd Zankode-VPN
python -m venv .venv
```

Linux / macOS:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Create `.env` from `.env.example`:

```env
BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
ADMIN_USER_ID=123456789
DB_FILE=config_shop.db
XUI_PANEL_URL=https://panel.example.com/secret-path
XUI_API_TOKEN=YOUR_3XUI_API_TOKEN
XUI_API_MODE=modern
XUI_VERIFY_TLS=1
# Optional; when omitted, Zankode can deliver panel-generated client links
XUI_SUB_URL_TEMPLATE=https://sub.example.com/sub/{sub_id}
```

Run:

```bash
python main.py
```

or:

```bash
python -m zankode
```

## 🧪 Tests

```bash
python -m unittest discover -s tests -v
python -m compileall -q .
```

## 🔁 Continuous Integration

The repository contains `.github/workflows/ci.yml`. On every push and pull request, GitHub Actions runs the project on Ubuntu with Python **3.10, 3.11, and 3.12**, installs dependencies, compiles the source, and executes the test suite.

## 🔐 Security

Never commit `.env`, a production database, Telegram/3X-UI API tokens, panel credentials, customer data, runtime logs, or exported private CSV files. Review the repository state before making it public.

---

<p align="center">
  Built for a clean, maintainable Telegram-based VPN sales workflow.<br/>
  <strong>Zankode VPN • v2.2.0</strong>
</p>
