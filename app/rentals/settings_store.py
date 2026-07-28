import json
from pathlib import Path

from django.conf import settings

DEFAULT_RENTAL_DAYS = 7
MIN_RENTAL_DAYS = 1
MAX_RENTAL_DAYS = 365
DEFAULT_OVERDUE_LIMIT = 3
MIN_OVERDUE_LIMIT = 1
MAX_OVERDUE_LIMIT = 99
DEFAULT_BLACKLIST_MONTHS = 3
MIN_BLACKLIST_MONTHS = 1
MAX_BLACKLIST_MONTHS = 120
_SETTINGS_PATH = Path(settings.BASE_DIR) / 'data' / 'rental_settings.json'


def _normalize_int(value, *, default, minimum, maximum):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    if number < minimum:
        return minimum
    if number > maximum:
        return maximum
    return number


def _normalize_days(value):
    return _normalize_int(value, default=DEFAULT_RENTAL_DAYS, minimum=MIN_RENTAL_DAYS, maximum=MAX_RENTAL_DAYS)


def _normalize_overdue_limit(value):
    return _normalize_int(value, default=DEFAULT_OVERDUE_LIMIT, minimum=MIN_OVERDUE_LIMIT, maximum=MAX_OVERDUE_LIMIT)


def _normalize_blacklist_months(value):
    return _normalize_int(value, default=DEFAULT_BLACKLIST_MONTHS, minimum=MIN_BLACKLIST_MONTHS, maximum=MAX_BLACKLIST_MONTHS)


def _read_settings():
    if not _SETTINGS_PATH.exists():
        return {}
    try:
        return json.loads(_SETTINGS_PATH.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return {}


def _write_settings(data):
    _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _SETTINGS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def get_default_rental_days():
    data = _read_settings()
    return _normalize_days(data.get('default_rental_days', DEFAULT_RENTAL_DAYS))


def set_default_rental_days(days):
    normalized_days = _normalize_days(days)
    data = _read_settings()
    data['default_rental_days'] = normalized_days
    _write_settings(data)
    return normalized_days


def get_overdue_limit():
    data = _read_settings()
    return _normalize_overdue_limit(data.get('overdue_limit', DEFAULT_OVERDUE_LIMIT))


def set_overdue_limit(limit):
    normalized_limit = _normalize_overdue_limit(limit)
    data = _read_settings()
    data['overdue_limit'] = normalized_limit
    _write_settings(data)
    return normalized_limit


def get_blacklist_months():
    data = _read_settings()
    return _normalize_blacklist_months(data.get('blacklist_months', DEFAULT_BLACKLIST_MONTHS))


def set_blacklist_months(months):
    normalized_months = _normalize_blacklist_months(months)
    data = _read_settings()
    data['blacklist_months'] = normalized_months
    _write_settings(data)
    return normalized_months


def get_current_policy_snapshot():
    return {
        'rental_days': get_default_rental_days(),
        'overdue_limit': get_overdue_limit(),
        'blacklist_months': get_blacklist_months(),
    }


def save_policy_settings(*, default_rental_days, overdue_limit, blacklist_months):
    data = _read_settings()
    data['default_rental_days'] = _normalize_days(default_rental_days)
    data['overdue_limit'] = _normalize_overdue_limit(overdue_limit)
    data['blacklist_months'] = _normalize_blacklist_months(blacklist_months)
    _write_settings(data)
    return data


# 이전 패치에서 사용하던 이름과의 호환용 별칭입니다.
def save_default_rental_days(days):
    return set_default_rental_days(days)
