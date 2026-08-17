# -*- coding: utf-8 -*-
"""Date/time, formatting, validation, and small utility helpers."""

from .config import *

def iran_now() -> datetime:
    return datetime.now(IRAN_TZ)

def now() -> str:
    return iran_now().strftime("%Y-%m-%d %H:%M:%S")

def parse_db_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=IRAN_TZ)
    except (TypeError, ValueError):
        return None

def db_dt(value: datetime) -> str:
    return value.astimezone(IRAN_TZ).strftime("%Y-%m-%d %H:%M:%S")

def gregorian_to_jalali(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    gdm = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy + 1 if gm > 2 else gy
    days = (
        355666 + 365 * gy + (gy2 + 3) // 4
        - (gy2 + 99) // 100 + (gy2 + 399) // 400
        + gd + gdm[gm - 1]
    )
    jy = -1595 + 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + days // 31
        jd = 1 + days % 31
    else:
        jm = 7 + (days - 186) // 30
        jd = 1 + (days - 186) % 30
    return jy, jm, jd

def jalali_to_gregorian(jy: int, jm: int, jd: int) -> tuple[int, int, int]:
    jy += 1595
    days = -355668 + (365 * jy) + ((jy // 33) * 8) + (((jy % 33) + 3) // 4) + jd
    if jm < 7:
        days += (jm - 1) * 31
    else:
        days += ((jm - 7) * 30) + 186
    gy = 400 * (days // 146097)
    days %= 146097
    if days > 36524:
        gy += 100 * ((days - 1) // 36524)
        days = (days - 1) % 36524
        if days >= 365:
            days += 1
    gy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365
    gd = days + 1
    leap = gy % 4 == 0 and (gy % 100 != 0 or gy % 400 == 0)
    sal_a = [0, 31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    gm = 1
    while gm <= 12 and gd > sal_a[gm]:
        gd -= sal_a[gm]
        gm += 1
    return gy, gm, gd

def jalali_date(value: Optional[str] | datetime) -> str:
    dt = value if isinstance(value, datetime) else parse_db_dt(value)
    if not dt:
        return "—"
    jy, jm, jd = gregorian_to_jalali(dt.year, dt.month, dt.day)
    return f"{jy:04d}/{jm:02d}/{jd:02d}"

def jalali_month_bounds(value: datetime) -> tuple[datetime, datetime, str]:
    jy, jm, _ = gregorian_to_jalali(value.year, value.month, value.day)
    gy, gm, gd = jalali_to_gregorian(jy, jm, 1)
    start = datetime(gy, gm, gd, tzinfo=IRAN_TZ)
    if jm == 12:
        njy, njm = jy + 1, 1
    else:
        njy, njm = jy, jm + 1
    egy, egm, egd = jalali_to_gregorian(njy, njm, 1)
    end = datetime(egy, egm, egd, tzinfo=IRAN_TZ)
    return start, end, f"{jy:04d}-{jm:02d}"

async def time_ir_now() -> tuple[datetime, str]:
    """Return Tehran wall-clock time without an external HTTP dependency.

    Production hosts should keep their system clock synchronized (NTP/systemd-timesyncd).
    The async signature is retained for backward compatibility with existing handlers.
    """
    return iran_now(), "server-tehran"

def ts() -> int:
    return int(time.time())

def esc(v: Any) -> str:
    return html.escape(str(v or ""))

def money(v: int) -> str:
    return f"{int(v):,} تومان"

def normalize_digits(s: str) -> str:
    return s.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))

def to_int(s: str) -> Optional[int]:
    s = normalize_digits(str(s)).replace(",", "").replace("٬", "").replace(" ", "")
    if not re.fullmatch(r"-?\d+", s):
        return None
    try:
        return int(s)
    except ValueError:
        return None

def is_admin(uid: Optional[int]) -> bool:
    return bool(uid and ADMIN_USER_ID and int(uid) == int(ADMIN_USER_ID))

def validate_config():
    if not BOT_TOKEN.strip():
        raise RuntimeError("BOT_TOKEN خالی است.")
    if not isinstance(ADMIN_USER_ID, int) or ADMIN_USER_ID <= 0:
        raise RuntimeError("ADMIN_USER_ID باید آیدی عددی ادمین باشد.")

def divider() -> str:
    return "━━━━━━━━━━━━━━━━━━"

def username_text(username: Optional[str]) -> str:
    return f"@{username}" if username else "ندارد"



def human_bytes(value: int) -> str:
    try:
        n = int(value)
    except (TypeError, ValueError):
        n = 0
    if n < 0:
        return "نامحدود"
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    size = float(max(0, n))
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"
