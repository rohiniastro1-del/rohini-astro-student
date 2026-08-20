from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from vedic_app.data import DASHA_NAMES_BG, DASHA_SEQUENCE, DASHA_YEARS, NAKSHATRA_NAMES_BG


NAKSHATRA_ARCSECONDS = Decimal("48000")
TROPICAL_YEAR_DAYS = Decimal("365.24219")
SECONDS_PER_YEAR = TROPICAL_YEAR_DAYS * Decimal("86400")
TOTAL_YEARS = Decimal("120")


def _rotate_from(lord: str) -> list[str]:
    start_index = DASHA_SEQUENCE.index(lord)
    return DASHA_SEQUENCE[start_index:] + DASHA_SEQUENCE[:start_index]


def _years_to_timedelta(years: Decimal) -> timedelta:
    seconds = int((years * SECONDS_PER_YEAR).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return timedelta(seconds=seconds)


def _format_dasha_duration(years: Decimal) -> str:
    rounded_years = years.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP).normalize()
    years_label = format(rounded_years, "f")
    if "." in years_label:
        years_label = years_label.rstrip("0").rstrip(".")
    return f"{years_label} г."


def _format_dt(value: datetime) -> str:
    return value.strftime("%d.%m.%Y %H:%M:%S")


def _build_pratyantardashas(
    md_lord: str,
    ad_lord: str,
    start: datetime,
    ad_length_years: Decimal,
    birth_dt: datetime,
) -> list[dict[str, object]]:
    periods: list[dict[str, object]] = []
    cursor = start
    order = _rotate_from(ad_lord)
    for index, pd_lord in enumerate(order):
        pd_years = ad_length_years * DASHA_YEARS[pd_lord] / TOTAL_YEARS
        end = cursor + _years_to_timedelta(pd_years)
        periods.append(
            {
                "key": f"{md_lord}-{ad_lord}-{pd_lord}-{index}",
                "lord": pd_lord,
                "label": DASHA_NAMES_BG[pd_lord],
                "start": cursor,
                "end": end,
                "start_label": _format_dt(cursor),
                "end_label": _format_dt(end),
                "duration_label": _format_dasha_duration(pd_years),
                "active": cursor <= birth_dt < end,
                "visible": end > birth_dt,
            }
        )
        cursor = end
    return [period for period in periods if period["visible"]]


def _build_antardashas(
    md_lord: str,
    start: datetime,
    birth_dt: datetime,
) -> list[dict[str, object]]:
    periods: list[dict[str, object]] = []
    cursor = start
    md_years = DASHA_YEARS[md_lord]
    order = _rotate_from(md_lord)
    for index, ad_lord in enumerate(order):
        ad_years = md_years * DASHA_YEARS[ad_lord] / TOTAL_YEARS
        end = cursor + _years_to_timedelta(ad_years)
        pd_periods = _build_pratyantardashas(md_lord, ad_lord, cursor, ad_years, birth_dt)
        periods.append(
            {
                "key": f"{md_lord}-{ad_lord}-{index}",
                "lord": ad_lord,
                "label": DASHA_NAMES_BG[ad_lord],
                "start": cursor,
                "end": end,
                "start_label": _format_dt(cursor),
                "end_label": _format_dt(end),
                "duration_label": _format_dasha_duration(ad_years),
                "active": cursor <= birth_dt < end,
                "visible": end > birth_dt,
                "pd_periods": pd_periods,
            }
        )
        cursor = end
    return [period for period in periods if period["visible"]]


def build_vimshottari_dasha(moon_longitude: float, birth_dt: datetime) -> dict[str, object]:
    moon_arcseconds = Decimal(str(moon_longitude)) * Decimal("3600")
    moon_arcseconds = moon_arcseconds % (Decimal("360") * Decimal("3600"))
    nak_index = int(moon_arcseconds // NAKSHATRA_ARCSECONDS)
    offset_in_nak = moon_arcseconds % NAKSHATRA_ARCSECONDS
    elapsed_fraction = offset_in_nak / NAKSHATRA_ARCSECONDS

    md_lord = DASHA_SEQUENCE[nak_index % len(DASHA_SEQUENCE)]
    full_md_years = DASHA_YEARS[md_lord]
    elapsed_md_years = full_md_years * elapsed_fraction
    balance_md_years = full_md_years - elapsed_md_years

    md_start = birth_dt - _years_to_timedelta(elapsed_md_years)

    md_periods: list[dict[str, object]] = []
    cursor = md_start
    current_lord = md_lord
    horizon = birth_dt + _years_to_timedelta(Decimal("120"))
    loop_guard = 0
    while cursor < horizon and loop_guard < 18:
        md_years = DASHA_YEARS[current_lord]
        md_end = cursor + _years_to_timedelta(md_years)
        ad_periods = _build_antardashas(current_lord, cursor, birth_dt)
        md_periods.append(
            {
                "key": f"{current_lord}-{loop_guard}",
                "lord": current_lord,
                "label": DASHA_NAMES_BG[current_lord],
                "start": cursor,
                "end": md_end,
                "start_label": _format_dt(cursor),
                "end_label": _format_dt(md_end),
                "duration_label": _format_dasha_duration(md_years),
                "active": cursor <= birth_dt < md_end,
                "visible": md_end > birth_dt,
                "ad_periods": ad_periods,
            }
        )
        cursor = md_end
        current_lord = DASHA_SEQUENCE[(DASHA_SEQUENCE.index(current_lord) + 1) % len(DASHA_SEQUENCE)]
        loop_guard += 1

    md_periods = [period for period in md_periods if period["visible"]]

    current_md = next(period for period in md_periods if period["active"])
    current_ad = next(period for period in current_md["ad_periods"] if period["active"])
    current_pd = next(period for period in current_ad["pd_periods"] if period["active"])

    return {
        "janma_nakshatra": NAKSHATRA_NAMES_BG[nak_index],
        "current_md_lord": DASHA_NAMES_BG[current_md["lord"]],
        "current_ad_lord": DASHA_NAMES_BG[current_ad["lord"]],
        "current_pd_lord": DASHA_NAMES_BG[current_pd["lord"]],
        "balance_md_label": _format_dasha_duration(balance_md_years),
        "current_md_end_label": current_md["end_label"],
        "current_ad_end_label": current_ad["end_label"],
        "current_pd_end_label": current_pd["end_label"],
        "md_periods": md_periods,
        "calendar_note": "Датите са изчислени по средна тропическа соларна година = 365.24219 дни.",
    }
