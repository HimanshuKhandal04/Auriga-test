import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from math import ceil
from pathlib import Path
from typing import Any, Optional

from app.core.config import settings


class RateCardError(ValueError):
    pass


@dataclass(frozen=True)
class RateCardCleaningRules:
    strip_whitespace: bool = True
    normalize_field_names: bool = True
    decimal_separator: str = "."


@dataclass(frozen=True)
class RateCard:
    first_hour_rate: Decimal
    additional_hour_rate: Decimal
    daily_cap: Decimal



def import_rate_card(
    source: str | bytes,
    file_format: Optional[str] = None,
    cleaning_rules: Optional[RateCardCleaningRules] = None,
) -> RateCard:
    """Import one rate-card record from CSV or JSON without supplying defaults."""
    rules = cleaning_rules or RateCardCleaningRules()
    text = source.decode() if isinstance(source, bytes) else source
    resolved_format = (file_format or _detect_format(text)).strip().lower()

    if resolved_format == "json":
        record = _parse_json_record(text)
    elif resolved_format == "csv":
        record = _parse_csv_record(text)
    else:
        raise RateCardError("Rate-card format must be CSV or JSON")

    values = _clean_record(record, rules)
    required = ("first_hour_rate", "additional_hour_rate", "daily_cap")
    missing = [field for field in required if field not in values or values[field] == ""]
    if missing:
        raise RateCardError(f"Rate card is missing required fields: {', '.join(missing)}")

    try:
        rate_card = RateCard(
            first_hour_rate=_decimal_value(values["first_hour_rate"], rules),
            additional_hour_rate=_decimal_value(values["additional_hour_rate"], rules),
            daily_cap=_decimal_value(values["daily_cap"], rules),
        )
    except (ArithmeticError, TypeError, ValueError) as exc:
        raise RateCardError("Rate-card rates must be valid decimal values") from exc

    if any(value < 0 for value in (rate_card.first_hour_rate, rate_card.additional_hour_rate, rate_card.daily_cap)):
        raise RateCardError("Rate-card rates cannot be negative")
    return rate_card


def load_configured_rate_card() -> RateCard:
    if not settings.parking_rate_card_path:
        return RateCard(
            first_hour_rate=Decimal(str(settings.parking_first_hour_rate)),
            additional_hour_rate=Decimal(str(settings.parking_additional_hour_rate)),
            daily_cap=Decimal(str(settings.parking_daily_cap)),
        )

    path = Path(settings.parking_rate_card_path)
    try:
        source = path.read_bytes()
    except OSError as exc:
        raise RateCardError(f"Unable to read rate card: {path}") from exc
    return import_rate_card(source, settings.parking_rate_card_format)


def _detect_format(source: str) -> str:
    stripped = source.lstrip()
    return "json" if stripped.startswith("{") or stripped.startswith("[") else "csv"


def _parse_json_record(source: str) -> dict[str, Any]:
    try:
        payload = json.loads(source)
    except json.JSONDecodeError as exc:
        raise RateCardError("Rate card contains invalid JSON") from exc
    if isinstance(payload, list):
        if len(payload) != 1 or not isinstance(payload[0], dict):
            raise RateCardError("JSON rate card must contain one object")
        return payload[0]
    if not isinstance(payload, dict):
        raise RateCardError("JSON rate card must be an object")
    return payload


def _parse_csv_record(source: str) -> dict[str, Any]:
    rows = list(csv.DictReader(source.splitlines()))
    if len(rows) != 1:
        raise RateCardError("CSV rate card must contain one data row")
    return rows[0]


def _clean_record(record: dict[str, Any], rules: RateCardCleaningRules) -> dict[str, Any]:
    cleaned = {}
    for key, value in record.items():
        field = (
            str(key).strip().lower().replace(" ", "_").replace("-", "_")
            if rules.normalize_field_names
            else str(key)
        )
        cleaned[field] = value.strip() if rules.strip_whitespace and isinstance(value, str) else value
    return cleaned


def _decimal_value(value: Any, rules: RateCardCleaningRules) -> Decimal:
    text = str(value).strip() if rules.strip_whitespace else str(value)
    if rules.decimal_separator != ".":
        text = text.replace(rules.decimal_separator, ".")
    return Decimal(text)


def calculate_fee(
    check_in: datetime,
    check_out: datetime,
    rate_card: RateCard,
) -> tuple[int, Decimal]:
    start = as_utc(check_in)
    end = as_utc(check_out)
    elapsed_seconds = max(0, (end - start).total_seconds())
    billable_hours = max(1, ceil(elapsed_seconds / 3600))

    fee = rate_card.first_hour_rate + (
        max(0, billable_hours - 1) * rate_card.additional_hour_rate
    )
    return billable_hours, min(fee, rate_card.daily_cap)


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)