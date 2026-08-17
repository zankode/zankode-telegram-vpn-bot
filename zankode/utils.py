# -*- coding: utf-8 -*-
"""Date/time, formatting, validation, and small utility helpers."""

from .config import *

_TIME_IR_CACHE_DT = None
_TIME_IR_CACHE_MONO = 0.0

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
    """Reference purchase time from time.ir; cached + safe Tehran fallback."""
    global _TIME_IR_CACHE_DT, _TIME_IR_CACHE_MONO

    mono = time.monotonic()
    if _TIME_IR_CACHE_DT is not None and mono - _TIME_IR_CACHE_MONO < TIME_IR_CACHE_SECONDS:
        elapsed = max(0.0, mono - _TIME_IR_CACHE_MONO)
        return _TIME_IR_CACHE_DT + timedelta(seconds=elapsed), "time.ir-cache"

    try:
        async with httpx.AsyncClient(
            timeout=8.0,
            follow_redirects=True,
            headers={"User-Agent": "ZankodeVPNBot/1.0"},
        ) as client:
            response = await client.get(TIME_IR_URL)
            response.raise_for_status()
            header = response.headers.get("date")
            if not header:
                raise ValueError("time.ir Date header missing")
            dt = parsedate_to_datetime(header)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            dt = dt.astimezone(IRAN_TZ)
            if abs((dt - iran_now()).total_seconds()) > 48 * 3600:
                raise ValueError("time.ir Date header looks stale")

            _TIME_IR_CACHE_DT = dt
            _TIME_IR_CACHE_MONO = time.monotonic()
            return dt, "time.ir"
    except Exception as exc:
        log.warning("time.ir unavailable; Tehran fallback used: %s", exc)
        return iran_now(), "tehran-fallback"

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
