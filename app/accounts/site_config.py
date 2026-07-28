# -*- coding: utf-8 -*-
import json
from pathlib import Path

from django.conf import settings

DEFAULT_CONFIG = {
    'organization_name': '학과(부)명 학생회',
    'contact_email': 'threetrue03@gmail.com',
    'instagram': '추후 공개 예정',
    'copyright_owner': '조세진',
    'copyright_year': '2026',
}


def site_config_path() -> Path:
    return Path(settings.BASE_DIR) / 'config' / 'welfare_site.json'


def load_site_config() -> dict:
    path = site_config_path()
    data = DEFAULT_CONFIG.copy()
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding='utf-8'))
            if isinstance(loaded, dict):
                for key, value in loaded.items():
                    if value is not None and str(value).strip() != '':
                        data[key] = value
        except Exception:
            pass
    return data


def strip_student_council_suffix(value: str) -> str:
    value = str(value or '').strip()
    return value[:-3].strip() if value.endswith('학생회') else value


def normalize_organization_name(value: str) -> str:
    value = strip_student_council_suffix(value)
    if not value:
        return '학과(부)명 학생회'
    return f'{value} 학생회'


def save_site_config(**kwargs) -> dict:
    path = site_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = load_site_config()
    for key, value in kwargs.items():
        if value is not None:
            if key == 'organization_name':
                data[key] = normalize_organization_name(value)
            else:
                data[key] = str(value).strip()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return data
