from functools import wraps
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect

_ADMIN_CACHE = {'mtime': None, 'ids': set()}
_ADMIN_HEADER = '관리자 학번'


class AdminCsvWriteError(RuntimeError):
    """Raised when auth/admin.csv cannot be updated safely."""


def _admin_csv_path():
    return Path(settings.BASE_DIR) / 'auth' / 'admin.csv'


def _clear_admin_cache():
    _ADMIN_CACHE['mtime'] = None
    _ADMIN_CACHE['ids'] = set()


def _load_admin_ids():
    path = _admin_csv_path()
    if not path.exists():
        return set()
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return set()
    if _ADMIN_CACHE['mtime'] == mtime:
        return _ADMIN_CACHE['ids']

    admin_ids = set()
    try:
        with path.open('r', encoding='utf-8-sig') as file:
            for index, line in enumerate(file):
                value = line.strip().split(',')[0].strip()
                if not value:
                    continue
                if index == 0 and value in {_ADMIN_HEADER, 'student_id', 'admin_student_id'}:
                    continue
                admin_ids.add(str(value))
    except OSError:
        admin_ids = set()

    _ADMIN_CACHE['mtime'] = mtime
    _ADMIN_CACHE['ids'] = admin_ids
    return admin_ids


def get_admin_ids():
    return set(_load_admin_ids())


def _format_admin_csv_error(path):
    return f'{path} 파일을 수정할 수 없습니다. 파일이 엑셀에서 열려 있으면 닫고, 읽기 전용이 아닌지 확인한 뒤 다시 시도해주세요.'


def write_admin_ids(admin_ids):
    path = _admin_csv_path()
    cleaned_ids = sorted({str(student_id).strip() for student_id in admin_ids if str(student_id).strip()})
    content = '\n'.join([_ADMIN_HEADER, *cleaned_ids]) + '\n'
    tmp_path = path.with_name(f'.{path.name}.tmp')

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path.write_text(content, encoding='utf-8-sig')
        tmp_path.replace(path)
    except PermissionError as exc:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass
        raise AdminCsvWriteError(_format_admin_csv_error(path)) from exc
    except OSError as exc:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass
        raise AdminCsvWriteError(_format_admin_csv_error(path)) from exc

    _clear_admin_cache()
    return set(cleaned_ids)


def set_admin_membership(student_id, should_be_admin, *, old_student_id=None):
    admin_ids = get_admin_ids()
    next_admin_ids = set(admin_ids)
    if old_student_id and str(old_student_id).strip() != str(student_id).strip():
        next_admin_ids.discard(str(old_student_id).strip())
    student_id = str(student_id).strip()
    if student_id:
        if should_be_admin:
            next_admin_ids.add(student_id)
        else:
            next_admin_ids.discard(student_id)
    if next_admin_ids == admin_ids:
        return admin_ids
    return write_admin_ids(next_admin_ids)


def is_admin_student_id(student_id):
    return str(student_id or '').strip() in _load_admin_ids()


def is_admin_user(user):
    if not getattr(user, 'is_authenticated', False):
        return False
    return is_admin_student_id(getattr(user, 'student_id', ''))


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_admin_user(request.user):
            messages.error(request, '관리자만 접근할 수 있습니다.')
            return redirect('dashboard:home')
        return view_func(request, *args, **kwargs)
    return wrapper
