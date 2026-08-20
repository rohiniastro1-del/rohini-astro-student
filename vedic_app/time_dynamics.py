from __future__ import annotations

import calendar
from datetime import datetime, timedelta


VALID_UNITS = {"second", "minute", "hour", "day", "week", "month", "year"}


class TimeDynamicsError(ValueError):
    pass


def _parse_civil_datetime(date_text: str, time_text: str) -> datetime:
    try:
        return datetime.fromisoformat(f"{date_text}T{time_text}")
    except (TypeError, ValueError) as exc:
        raise TimeDynamicsError("Невалидни дата или час.") from exc


def _shift_months(value: datetime, months: int) -> datetime:
    month_index = value.year * 12 + value.month - 1 + months
    year, month_zero = divmod(month_index, 12)
    if not 1 <= year <= 9999:
        raise TimeDynamicsError("Новата година е извън поддържания диапазон 1–9999.")
    month = month_zero + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def shift_civil_datetime(
    date_text: str,
    time_text: str,
    amount: int,
    unit: str,
    *,
    forward: bool = True,
) -> tuple[str, str]:
    """Move wall-clock fields without applying or guessing a timezone.

    Timezone resolution deliberately remains in ``astro._resolve_timezone``:
    automatic mode re-evaluates historical zone rules for the new date, while
    manual mode keeps the user's fixed UTC offset.
    """
    try:
        amount = int(amount)
    except (TypeError, ValueError) as exc:
        raise TimeDynamicsError("Стъпката трябва да бъде положително цяло число.") from exc
    if amount <= 0:
        raise TimeDynamicsError("Стъпката трябва да бъде положително цяло число.")
    if unit not in VALID_UNITS:
        raise TimeDynamicsError("Непозната единица за движение във времето.")

    value = _parse_civil_datetime(date_text, time_text)
    direction = 1 if forward else -1
    signed_amount = direction * amount

    if unit == "month":
        value = _shift_months(value, signed_amount)
    elif unit == "year":
        value = _shift_months(value, signed_amount * 12)
    else:
        multipliers = {
            "second": timedelta(seconds=1),
            "minute": timedelta(minutes=1),
            "hour": timedelta(hours=1),
            "day": timedelta(days=1),
            "week": timedelta(weeks=1),
        }
        try:
            value += multipliers[unit] * signed_amount
        except OverflowError as exc:
            raise TimeDynamicsError("Новият момент е извън поддържания диапазон.") from exc

    return value.strftime("%Y-%m-%d"), value.strftime("%H:%M:%S")
