from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from accounts.models import ShiftRecord
from items.models import EquipmentUnit, Item
from rentals.models import RentalRecord, ReturnRecord

CONFIG_PATH = settings.BASE_DIR / 'auth' / 'google_sheets.json'
LAUNCHER_CONFIG_PATH = settings.BASE_DIR.parent / 'launcher_config.json'
DEFAULT_SERVICE_ACCOUNT_PATH = ''
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SHEET_TITLES = [
    '오늘 요약',
    '근무 기록',
    '대여 기록',
    '대여 현황',
    '반납 기록',
    '반납 예정',
    '미반납_연체',
    '재고 현황',
]


def _default_config() -> dict[str, str]:
    return {
        'spreadsheet_id': '',
        'service_account_path': '',
        'last_synced_at': '',
        'last_synced_date': '',
        'last_error': '',
    }


def _load_json_file(path: Path) -> dict[str, str]:
    try:
        if not path.exists():
            return {}
        saved = json.loads(path.read_text(encoding='utf-8'))
        if isinstance(saved, dict):
            return {key: str(value) for key, value in saved.items() if value is not None}
    except (OSError, json.JSONDecodeError):
        pass
    return {}


def _launcher_config_fallback() -> dict[str, str]:
    # v1.0.10 이하에서 런처에만 저장된 구글 시트 설정을 웹사이트에서도 읽을 수 있게 한다.
    launcher = _load_json_file(LAUNCHER_CONFIG_PATH)
    spreadsheet_id = launcher.get('spreadsheet_id', '').strip()
    service_account_path = launcher.get('service_account_path', '').strip()
    if service_account_path:
        path = Path(service_account_path)
        try:
            if path.is_absolute() and path.exists() and path.resolve() == (settings.BASE_DIR / 'credentials' / 'service-account.json').resolve():
                service_account_path = 'credentials/service-account.json'
        except OSError:
            pass
    if spreadsheet_id or service_account_path:
        return {
            'spreadsheet_id': spreadsheet_id,
            'service_account_path': service_account_path,
        }
    return {}


def load_google_sheet_config() -> dict[str, str]:
    config = _default_config()
    saved = _load_json_file(CONFIG_PATH)
    if saved:
        config.update(saved)
    if not config.get('spreadsheet_id') and not config.get('service_account_path') and LAUNCHER_CONFIG_PATH.exists():
        config.update(_launcher_config_fallback())
    return config


def save_google_sheet_config(**updates: str) -> dict[str, str]:
    config = load_google_sheet_config()
    for key, value in updates.items():
        if value is not None:
            config[key] = str(value).strip()
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
    return config


def save_service_account_file(uploaded_file) -> str:
    target = settings.BASE_DIR / 'credentials' / 'service-account.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('wb') as output:
        for chunk in uploaded_file.chunks():
            output.write(chunk)
    return 'credentials/service-account.json'


def resolve_service_account_path(path_text: str | None = None) -> Path:
    config = load_google_sheet_config()
    raw_path = str(path_text or config.get('service_account_path') or '').strip()
    if not raw_path:
        raise FileNotFoundError('서비스 계정 JSON 파일을 설정해주세요.')
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return settings.BASE_DIR / path


def _build_sheets_service(config: dict[str, str] | None = None):
    config = config or load_google_sheet_config()
    spreadsheet_id = config.get('spreadsheet_id', '').strip()
    if not spreadsheet_id:
        raise ValueError('스프레드시트 ID를 입력해주세요.')

    credential_path = resolve_service_account_path(config.get('service_account_path'))
    if not credential_path.exists():
        raise FileNotFoundError(f'서비스 계정 JSON 파일을 찾을 수 없습니다: {credential_path}')

    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise ImportError('구글 시트 연동 패키지가 설치되지 않았습니다. setup.bat 또는 start.bat을 다시 실행해주세요.') from exc

    credentials = Credentials.from_service_account_file(str(credential_path), scopes=SCOPES)
    service = build('sheets', 'v4', credentials=credentials, cache_discovery=False)
    return service, spreadsheet_id


def _local_datetime(value, *, with_date=True):
    if not value:
        return ''
    fmt = '%Y-%m-%d %H:%M:%S' if with_date else '%H:%M:%S'
    return timezone.localtime(value).strftime(fmt)


def _student_label(student):
    if not student:
        return '삭제됨'
    return f'{student.name}({student.student_id})'


def _worker_label(user):
    if not user:
        return '삭제됨'
    return f'{user.name}({user.student_id})'


def _unit_label(unit):
    if not unit:
        return '-'
    return f'{unit.number}번'


def _return_status_label(return_record: ReturnRecord | None):
    if not return_record:
        return '-'
    if return_record.return_status == ReturnRecord.ReturnStatus.NORMAL:
        return '정상 반납'
    if return_record.return_status == ReturnRecord.ReturnStatus.BROKEN:
        return '고장'
    if return_record.return_status == ReturnRecord.ReturnStatus.LOST:
        return '분실'
    return return_record.get_return_status_display()


def _overdue_days(rental: RentalRecord, return_record: ReturnRecord | None = None) -> int:
    if return_record:
        end_date = timezone.localtime(return_record.returned_at).date()
    elif rental.status == RentalRecord.Status.ACTIVE:
        end_date = timezone.localdate()
    else:
        return 0
    return max(0, (end_date - rental.due_date).days)


def _record_in_shift_range(queryset, time_field: str, shift: ShiftRecord):
    end_at = shift.ended_at or timezone.now()
    return queryset.filter(**{f'{time_field}__gte': shift.started_at, f'{time_field}__lte': end_at})


def build_today_sheet_payload(today=None) -> dict[str, list[list[Any]]]:
    today = today or timezone.localdate()

    today_rentals = (
        RentalRecord.objects.filter(borrowed_at__date=today)
        .select_related('student', 'item', 'unit', 'worker')
        .order_by('borrowed_at', 'id')
    )
    today_returns = (
        ReturnRecord.objects.filter(returned_at__date=today)
        .select_related('rental', 'student', 'item', 'unit', 'worker')
        .order_by('returned_at', 'id')
    )
    active_rentals = (
        RentalRecord.objects.filter(status=RentalRecord.Status.ACTIVE)
        .select_related('student', 'item', 'unit', 'worker')
        .order_by('due_date', 'borrowed_at')
    )
    today_due = active_rentals.filter(due_date=today)
    overdue = active_rentals.filter(due_date__lt=today)
    today_shifts = ShiftRecord.objects.filter(started_at__date=today).select_related('user').order_by('started_at', 'id')

    payload: dict[str, list[list[Any]]] = {}

    payload['오늘 요약'] = [
        ['항목', '값'],
        ['날짜', today.strftime('%Y-%m-%d')],
        ['근무자 수', today_shifts.count()],
        ['대여 건수', today_rentals.count()],
        ['반납 건수', today_returns.count()],
        ['현재 대여 중', active_rentals.count()],
        ['오늘 반납 예정', today_due.count()],
        ['연체 건수', overdue.count()],
        ['동기화 시각', _local_datetime(timezone.now())],
    ]

    shift_rows = [['근무자 이름', '근무자 학번', '출근 시간', '퇴근 시간', '대여 처리 수', '반납 처리 수']]
    for shift in today_shifts:
        user = shift.user
        shift_rentals = RentalRecord.objects.filter(worker=user) if user else RentalRecord.objects.none()
        shift_returns = ReturnRecord.objects.filter(worker=user) if user else ReturnRecord.objects.none()
        if user:
            shift_rentals = _record_in_shift_range(shift_rentals, 'borrowed_at', shift)
            shift_returns = _record_in_shift_range(shift_returns, 'returned_at', shift)
        shift_rows.append([
            user.name if user else '삭제됨',
            user.student_id if user else '삭제됨',
            _local_datetime(shift.started_at, with_date=False),
            _local_datetime(shift.ended_at, with_date=False) if shift.ended_at else '근무 중',
            shift_rentals.count(),
            shift_returns.count(),
        ])
    payload['근무 기록'] = shift_rows

    rental_rows = [['대여 일시', '대여 근무자', '학생', '전화번호', '물품', '물품 번호', '반납 예정일', '메모']]
    for record in today_rentals:
        rental_rows.append([
            _local_datetime(record.borrowed_at, with_date=False),
            _worker_label(record.worker),
            _student_label(record.student),
            record.student.phone or '',
            record.item.name,
            _unit_label(record.unit),
            record.due_date.strftime('%Y-%m-%d'),
            record.memo or '',
        ])
    payload['대여 기록'] = rental_rows

    active_rental_rows = [['이름', '학번', '물품', '물품번호', '반납예정일']]
    for record in active_rentals:
        active_rental_rows.append([
            record.student.name,
            record.student.student_id,
            record.item.name,
            record.unit.number,
            record.due_date.strftime('%Y-%m-%d'),
        ])
    payload['대여 현황'] = active_rental_rows

    return_rows = [['반납 일시', '반납 근무자', '학생', '물품', '물품 번호', '반납 상태', '연체']]
    for record in today_returns:
        days = _overdue_days(record.rental, record)
        return_rows.append([
            _local_datetime(record.returned_at, with_date=False),
            _worker_label(record.worker),
            _student_label(record.student),
            record.item.name,
            _unit_label(record.unit),
            _return_status_label(record),
            f'{days}일' if days else '-',
        ])
    payload['반납 기록'] = return_rows

    due_rows = [['대여 일시', '학생', '전화번호', '물품', '물품 번호', '반납 예정일', '대여 근무자']]
    for record in today_due:
        due_rows.append([
            _local_datetime(record.borrowed_at),
            _student_label(record.student),
            record.student.phone or '',
            record.item.name,
            _unit_label(record.unit),
            record.due_date.strftime('%Y-%m-%d'),
            _worker_label(record.worker),
        ])
    payload['반납 예정'] = due_rows

    overdue_rows = [['학생', '전화번호', '물품', '물품 번호', '대여 일시', '반납 예정일', '연체 일수', '대여 근무자']]
    for record in overdue:
        days = _overdue_days(record)
        overdue_rows.append([
            _student_label(record.student),
            record.student.phone or '',
            record.item.name,
            _unit_label(record.unit),
            _local_datetime(record.borrowed_at),
            record.due_date.strftime('%Y-%m-%d'),
            f'{days}일' if days else '-',
            _worker_label(record.worker),
        ])
    payload['미반납_연체'] = overdue_rows

    inventory_rows = [['물품명', '물품 위치', '유형', '카테고리', '전체 수량', '대여 가능', '대여 중', '고장', '분실']]
    items = Item.objects.select_related('category').prefetch_related('units').order_by('item_type', 'category__name', 'name')
    for item in items:
        category_name = item.category.name if item.category else '-'
        if item.item_type == Item.ItemType.EQUIPMENT:
            inventory_rows.append([
                item.name,
                item.location or '-',
                item.get_item_type_display(),
                category_name,
                item.units.count(),
                item.units.filter(status=EquipmentUnit.Status.AVAILABLE).count(),
                item.units.filter(status=EquipmentUnit.Status.BORROWED).count(),
                item.units.filter(status=EquipmentUnit.Status.BROKEN).count(),
                item.units.filter(status=EquipmentUnit.Status.LOST).count(),
            ])
        else:
            inventory_rows.append([
                item.name,
                item.location or '-',
                item.get_item_type_display(),
                category_name,
                item.total_quantity,
                item.current_quantity if item.current_quantity is not None else item.total_quantity,
                '-',
                '-',
                '-',
            ])
    payload['재고 현황'] = inventory_rows

    return payload


def ensure_sheet_tabs(service, spreadsheet_id: str):
    spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    existing_titles = {sheet['properties']['title'] for sheet in spreadsheet.get('sheets', [])}
    requests = []
    for title in SHEET_TITLES:
        if title not in existing_titles:
            requests.append({'addSheet': {'properties': {'title': title}}})
    if requests:
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'requests': requests},
        ).execute()


def _quote_sheet_name(title: str) -> str:
    return "'" + title.replace("'", "''") + "'"


def sync_today_to_google_sheet(today=None) -> dict[str, Any]:
    config = load_google_sheet_config()
    service, spreadsheet_id = _build_sheets_service(config)
    payload = build_today_sheet_payload(today=today)
    ensure_sheet_tabs(service, spreadsheet_id)

    clear_ranges = [f'{_quote_sheet_name(title)}!A:Z' for title in SHEET_TITLES]
    service.spreadsheets().values().batchClear(
        spreadsheetId=spreadsheet_id,
        body={'ranges': clear_ranges},
    ).execute()

    data = []
    for title in SHEET_TITLES:
        rows = payload.get(title, [[]])
        data.append({
            'range': f'{_quote_sheet_name(title)}!A1',
            'values': rows,
        })
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={'valueInputOption': 'USER_ENTERED', 'data': data},
    ).execute()

    now = timezone.localtime(timezone.now())
    save_google_sheet_config(
        last_synced_at=now.strftime('%Y-%m-%d %H:%M:%S'),
        last_synced_date=(today or timezone.localdate()).strftime('%Y-%m-%d'),
        last_error='',
    )
    return {
        'spreadsheet_id': spreadsheet_id,
        'sheet_count': len(SHEET_TITLES),
        'synced_at': now.strftime('%Y-%m-%d %H:%M:%S'),
    }


def google_sheet_is_configured(config: dict[str, str] | None = None) -> bool:
    """자동 동기화가 가능한 최소 설정이 들어있는지 확인한다."""
    config = config or load_google_sheet_config()
    spreadsheet_id = config.get('spreadsheet_id', '').strip()
    if not spreadsheet_id:
        return False
    credential_path = resolve_service_account_path(config.get('service_account_path'))
    return credential_path.exists()


def sync_today_to_google_sheet_safely(reason: str = '') -> bool:
    """업무 처리 흐름을 막지 않도록 구글 시트 동기화를 조용히 시도한다."""
    config = load_google_sheet_config()
    if not google_sheet_is_configured(config):
        return False
    try:
        sync_today_to_google_sheet()
    except Exception as exc:  # noqa: BLE001
        prefix = f'자동 동기화 실패({reason})' if reason else '자동 동기화 실패'
        save_google_sheet_config(last_error=f'{prefix}: {exc}')
        return False
    return True


def schedule_google_sheet_sync(reason: str = '') -> None:
    """DB 변경이 확정된 뒤 오늘자 구글 시트 출력본을 갱신한다."""
    transaction.on_commit(lambda: sync_today_to_google_sheet_safely(reason))


def test_google_sheet_connection() -> dict[str, Any]:
    service, spreadsheet_id = _build_sheets_service()
    spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    return {
        'title': spreadsheet.get('properties', {}).get('title', ''),
        'spreadsheet_id': spreadsheet_id,
        'sheet_count': len(spreadsheet.get('sheets', [])),
    }
