<p align="center">
  <img src="assets/readme/banner.svg" alt="Zankode VPN" width="100%">
</p>

<h1 align="center">Zankode VPN</h1>

<p align="center">
  <strong>Telegram VPN Store & 3X-UI Manager</strong>
</p>

<p align="center">
  A modular Telegram bot for selling, delivering and managing VPN services with direct 3X-UI / Xray integration.
</p>

<p align="center">
  <a href="#-فارسی">🇮🇷 فارسی</a>
  &nbsp;•&nbsp;
  <a href="#-english">🇬🇧 English</a>
  &nbsp;•&nbsp;
  <a href="#-installation">⚙️ Installation</a>
  &nbsp;•&nbsp;
  <a href="#-project-structure">📁 Structure</a>
</p>

---

# 🇮🇷 فارسی

**Zankode VPN** یک ربات تلگرام ماژولار برای فروش و مدیریت سرویس‌های VPN است.

کاربر تمام مراحل خرید، پرداخت، دریافت سرویس، تمدید، کیف پول، هدیه و پشتیبانی را مستقیماً داخل تلگرام انجام می‌دهد و ادمین نیز از پنل مدیریتی داخل ربات، کاربران، سفارش‌ها، موجودی، فروش و سرویس‌های 3X-UI را مدیریت می‌کند.

از نسخه **v2.2.0**، هر پلن می‌تواند از دو روش تحویل استفاده کند:

* `Inventory` — تحویل کانفیگ‌های از قبل ثبت‌شده
* `3X-UI` — ساخت و مدیریت خودکار Client از طریق API

---

<h2>
  <img src="assets/readme/icons/user-panel.svg" width="32" valign="middle">
  پنل کاربران
</h2>

* ثبت خودکار کاربر با `/start`
* مشاهده و خرید پلن‌ها
* ایجاد سفارش
* ارسال فیش پرداخت
* پرداخت با کیف پول
* شارژ کیف پول
* استفاده از Coupon
* دریافت خودکار سرویس
* مشاهده سرویس‌های خریداری‌شده
* مشاهده تاریخ خرید و انقضا
* مشاهده وضعیت لحظه‌ای سرویس
* نمایش حجم مصرف‌شده
* نمایش حجم باقی‌مانده
* نمایش IP Limit
* درخواست تمدید
* دریافت مجدد کانفیگ
* خرید سرویس هدیه
* دریافت Gift Code
* دریافت اکانت تست
* سیستم Referral
* دریافت کمیسیون Referral
* سیستم VIP
* تیکت پشتیبانی

---

<h2>
  <img src="assets/readme/icons/admin-panel.svg" width="32" valign="middle">
  پنل ادمین
</h2>

* داشبورد آماری فروش
* مشاهده کاربران
* مشاهده سفارش‌ها
* مشاهده **خریدار + پلن خریداری‌شده**
* تاریخچه کامل خرید هر کاربر
* جستجوی کاربران
* Block / Unblock
* یادداشت خصوصی ادمین
* مدیریت پلن‌ها
* مدیریت Inventory
* مدیریت فیش‌های پرداخت
* تأیید یا رد سفارش
* مدیریت کیف پول کاربران
* مدیریت درخواست شارژ
* مدیریت Coupon
* مدیریت Gift Code
* مدیریت اکانت تست
* مدیریت تیکت‌ها
* Broadcast
* پیام به Segmentهای مختلف
* گزارش فروش
* CSV Export
* Database Backup
* مدیریت تنظیمات فروشگاه

---

<h2>
  <img src="assets/readme/icons/xui.svg" width="34" valign="middle">
  اتصال مستقیم 3X-UI
</h2>

Zankode می‌تواند به‌صورت مستقیم به **3X-UI** متصل شود و Clientهای VPN را مدیریت کند.

### قابلیت‌ها

* اتصال با API Token
* ساخت Client بعد از تأیید سفارش
* انتخاب `Inbound ID`
* پشتیبانی از چند Inbound
* تعیین Traffic Quota
* تعیین مدت سرویس
* تعیین Expiry
* تعیین IP Limit
* دریافت لینک واقعی Client
* دریافت وضعیت Client
* مشاهده Traffic
* تمدید Client
* Reset Traffic
* Sync Client
* حذف Remote Client
* Health Check پنل
* پشتیبانی اختیاری از Legacy X-UI

Zankode ارتباط زیر را در دیتابیس نگهداری می‌کند:

```text
User
  ↓
Order
  ↓
Plan
  ↓
3X-UI Client
```

بنابراین اگر Client روی 3X-UI ساخته شود ولی ارسال پیام تلگرام موقتاً شکست بخورد، Retry بعدی **Client جدید ایجاد نمی‌کند** و همان سرویس قبلی را تحویل می‌دهد.

---

<h2>
  <img src="assets/readme/icons/wallet.svg" width="32" valign="middle">
  کیف پول
</h2>

* موجودی مستقل برای هر کاربر
* پرداخت سفارش با Wallet
* درخواست افزایش موجودی
* تأیید شارژ توسط ادمین
* ثبت تراکنش‌ها
* پاداش Referral
* پاداش‌های فروشگاهی

---

<h2>
  <img src="assets/readme/icons/referral.svg" width="32" valign="middle">
  Referral System
</h2>

* لینک اختصاصی دعوت
* ثبت Referrer
* محاسبه پاداش
* واریز کمیسیون
* مشاهده Referralها
* سیستم سطح و وفاداری مشتری

---

<h2>
  <img src="assets/readme/icons/gift.svg" width="32" valign="middle">
  Gift System
</h2>

* خرید سرویس برای دیگران
* تولید Gift Code
* دریافت Gift Code
* بازیابی Gift نیمه‌کاره بعد از Crash
* جلوگیری از استفاده مجدد هدیه

---

<h2>
  <img src="assets/readme/icons/automation.svg" width="32" valign="middle">
  عملیات خودکار
</h2>

Zankode یک Background Operations Loop دارد که در کنار Telegram Long Polling اجرا می‌شود.

از جمله:

* هشدار کمبود موجودی
* هشدار کمبود اکانت تست
* اعلان نزدیک شدن به انقضا
* اعلان سرویس منقضی‌شده
* پاک‌سازی سفارش‌های قدیمی
* گزارش‌های دوره‌ای
* کنترل Logها
* بازیابی Reservationهای نیمه‌کاره
* بازیابی Gift Redemption بعد از Crash

---

<h2>
  <img src="assets/readme/icons/database.svg" width="32" valign="middle">
  Database
</h2>

Zankode از **SQLite** استفاده می‌کند.

اطلاعات زیر داخل دیتابیس مدیریت می‌شوند:

* Users
* Plans
* Orders
* Inventory
* Wallet
* Wallet Transactions
* Coupons
* Referral
* Gift Codes
* Test Accounts
* Tickets
* Settings
* Delivery History
* Audit Data
* 3X-UI Client Mapping

یکی از بخش‌های مهم ساختار دیتابیس ارتباط دقیق:

```text
User ↔ Order ↔ Plan
```

است؛ بنابراین ادمین می‌تواند دقیقاً ببیند **هر کاربر چه پلنی خریداری کرده است**.

---

# 📁 Project Structure

```text
zankode-telegram-vpn-bot/
│
├── .github/
│   └── workflows/
│       └── ci.yml
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
├── docs/
│   └── 3xui-setup.md
│
├── tests/
│   ├── test_admin_purchase_views.py
│   ├── test_services.py
│   ├── test_smoke.py
│   └── test_xui.py
│
├── zankode/
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── admin_views.py
│   │   ├── commands.py
│   │   ├── messages.py
│   │   ├── router.py
│   │   └── user.py
│   │
│   ├── __init__.py
│   ├── __main__.py
│   ├── app.py
│   ├── config.py
│   ├── services.py
│   ├── storage.py
│   ├── ui.py
│   ├── utils.py
│   └── xui.py
│
├── .env.example
├── .gitignore
├── CHANGELOG.md
├── main.py
├── README.md
└── requirements.txt
```

---

<h2>
  <img src="assets/readme/icons/folder.svg" width="30" valign="middle">
  پوشه‌های پروژه
</h2>

| Path                 | Description                  |
| -------------------- | ---------------------------- |
| `zankode/`           | هسته اصلی Zankode VPN        |
| `zankode/handlers/`  | منطق پنل کاربر و ادمین       |
| `tests/`             | تست‌های خودکار               |
| `docs/`              | مستندات پروژه                |
| `assets/readme/`     | فایل‌های SVG مربوط به README |
| `.github/workflows/` | GitHub Actions               |

---

<h2>
  <img src="assets/readme/icons/file.svg" width="30" valign="middle">
  فایل‌های اصلی
</h2>

| File                  | Description                      |
| --------------------- | -------------------------------- |
| `main.py`             | Entry Point پروژه                |
| `zankode/app.py`      | اجرای Telegram Application       |
| `zankode/config.py`   | تنظیمات پروژه                    |
| `zankode/storage.py`  | SQLite و Queryها                 |
| `zankode/services.py` | عملیات سرویس و Background Jobs   |
| `zankode/xui.py`      | ارتباط با 3X-UI                  |
| `zankode/ui.py`       | رابط Telegram                    |
| `zankode/utils.py`    | توابع کمکی                       |
| `.env.example`        | نمونه Environment Variables      |
| `.gitignore`          | جلوگیری از Commit فایل‌های خصوصی |
| `CHANGELOG.md`        | تاریخچه نسخه‌ها                  |
| `requirements.txt`    | Python Dependencies              |

---

<h2>
  <img src="assets/readme/icons/workflow.svg" width="30" valign="middle">
  GitHub Workflow
</h2>

فایل:

```text
.github/workflows/ci.yml
```

مخصوص **GitHub Actions** است.

این Workflow بعد از `push` یا `pull_request`:

1. سورس پروژه را دریافت می‌کند
2. Python را نصب می‌کند
3. Dependencyها را نصب می‌کند
4. کل پروژه را Compile می‌کند
5. Unit Testها را اجرا می‌کند

---

<h2>
  <img src="assets/readme/icons/ci.svg" width="30" valign="middle">
  Continuous Integration
</h2>

CI پروژه روی نسخه‌های:

```text
Python 3.10
Python 3.11
Python 3.12
```

اجرا می‌شود.

تست‌ها:

```bash
python -m unittest discover -s tests -v
```

Compile check:

```bash
python -m compileall -q .
```

---

# ⚙️ Installation

## 1. Clone

```bash
git clone https://github.com/zankode/zankode-telegram-vpn-bot.git
cd zankode-telegram-vpn-bot
```

## 2. Virtual Environment

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Windows

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

## 3. Install Dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 4. Create `.env`

Linux:

```bash
cp .env.example .env
```

Windows:

```powershell
copy .env.example .env
```

Example:

```env
BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
ADMIN_USER_ID=123456789
DB_FILE=config_shop.db

XUI_PANEL_URL=https://panel.example.com
XUI_API_TOKEN=YOUR_3XUI_API_TOKEN
XUI_API_MODE=modern
XUI_VERIFY_TLS=1
XUI_TIMEOUT=15
```

## 5. Run

```bash
python main.py
```

یا:

```bash
python -m zankode
```

---

# 🔐 Security

هرگز موارد زیر را داخل GitHub قرار ندهید:

* `.env`
* Telegram Bot Token
* 3X-UI API Token
* Password
* Production Database
* Customer Data
* Runtime Logs
* Private CSV Exports

فقط فایل:

```text
.env.example
```

باید داخل Repository قرار بگیرد.

---

# 🧪 Tests

Zankode شامل تست‌های خودکار برای بخش‌های مهم پروژه است:

* Database initialization
* Buyer / Order / Plan mapping
* Admin purchase history
* Notification retry
* Gift recovery
* Long config delivery
* 3X-UI authentication
* Client creation
* Client status
* Client links
* Traffic
* Renewal
* Reset Traffic
* Delete Client
* Safe Retry

---

# 🇬🇧 English

**Zankode VPN** is a modular Telegram-based VPN sales and management system with optional direct **3X-UI / Xray** integration.

Users can purchase, receive, renew and manage their VPN services directly inside Telegram.

Administrators can manage:

* Users
* Orders
* Plans
* Inventory
* Wallets
* Coupons
* Gift Codes
* Referrals
* Test Accounts
* Support Tickets
* Sales Reports
* Backups
* 3X-UI Clients

---

<h2>
  <img src="assets/readme/icons/xui.svg" width="32" valign="middle">
  3X-UI Integration
</h2>

Zankode can automatically:

* Create clients
* Set traffic quota
* Set expiry
* Set IP limits
* Retrieve client links
* Read live usage
* Renew services
* Reset traffic
* Synchronize client state
* Delete remote clients
* Perform health checks

---

<h2>
  <img src="assets/readme/icons/admin-panel.svg" width="32" valign="middle">
  Admin Panel
</h2>

The Telegram-based admin panel provides:

* Sales dashboard
* User management
* Order management
* Buyer purchase history
* Inventory management
* Wallet management
* Coupon management
* Gift management
* Support tickets
* Broadcasts
* Reports
* CSV exports
* Database backups
* 3X-UI management

---

<h2>
  <img src="assets/readme/icons/user-panel.svg" width="32" valign="middle">
  User Panel
</h2>

Users can:

* Browse plans
* Purchase VPN services
* Upload payment receipts
* Pay with wallet balance
* View purchased services
* Check live traffic
* Check expiry
* Request renewal
* Redeem gifts
* Invite friends
* Earn referral rewards
* Open support tickets

---

# 🚀 Quick Start

```bash
git clone https://github.com/zankode/zankode-telegram-vpn-bot.git
cd zankode-telegram-vpn-bot

python -m venv .venv
python -m pip install -r requirements.txt
python main.py
```

---

# 📜 Version

Current release:

```text
Zankode VPN v2.2.0
```

---

<p align="center">
  <strong>Zankode VPN</strong><br>
  Telegram VPN Store & 3X-UI Manager
</p>

<p align="center">
  If you find this project useful, consider giving it a ⭐ on GitHub.
</p>
