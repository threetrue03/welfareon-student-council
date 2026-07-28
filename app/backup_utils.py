from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

from django.conf import settings
from django.utils import timezone


BACKUP_DIR_NAME = 'backups'


def _safe_reason(value: str) -> str:
    text = re.sub(r'[^0-9A-Za-z가-힣_-]+', '-', str(value or '').strip())
    text = text.strip('-_')
    return text or 'manual'


def backup_dir() -> Path:
    target = Path(settings.BASE_DIR) / BACKUP_DIR_NAME
    target.mkdir(parents=True, exist_ok=True)
    return target


def create_backup_archive(reason: str = 'manual') -> Path:
    """현재 운영 데이터와 설정 파일을 ZIP으로 백업한다.

    DB 가져오기/초기화처럼 데이터가 크게 바뀌는 작업 직전에 호출하기 위한 공통 유틸이다.
    파일이 존재하지 않는 항목은 건너뛰고, 어떤 파일이 들어갔는지 manifest에 남긴다.
    """
    app_dir = Path(settings.BASE_DIR)
    project_root = app_dir.parent
    timestamp = timezone.localtime().strftime('%Y%m%d_%H%M%S')
    reason_slug = _safe_reason(reason)
    archive_path = backup_dir() / f'WelfareON_backup_{timestamp}_{reason_slug}.zip'

    candidates = [
        (app_dir / 'db.sqlite3', 'app/db.sqlite3'),
        (app_dir / 'auth' / 'admin.csv', 'app/auth/admin.csv'),
        (app_dir / 'auth' / 'google_sheets.json', 'app/auth/google_sheets.json'),
        (app_dir / 'auth' / 'google_service_account.json', 'app/auth/google_service_account.json'),
        (app_dir / 'credentials' / 'service-account.json', 'app/credentials/service-account.json'),
        (app_dir / 'config' / 'welfare_site.json', 'app/config/welfare_site.json'),
        (project_root / 'launcher_config.json', 'launcher_config.json'),
    ]

    included = []
    with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for source, arcname in candidates:
            try:
                if source.exists() and source.is_file():
                    archive.write(source, arcname)
                    included.append(arcname)
            except OSError:
                continue
        manifest = {
            'service': 'WelfareON',
            'created_at': timezone.localtime().isoformat(),
            'reason': reason,
            'included_files': included,
        }
        archive.writestr('backup_manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))

    return archive_path


def recent_backup_archives(limit: int = 10) -> list[Path]:
    files = sorted(backup_dir().glob('WelfareON_backup_*.zip'), key=lambda path: path.stat().st_mtime, reverse=True)
    return files[:limit]
