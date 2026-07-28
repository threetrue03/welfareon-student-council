import calendar
from collections import defaultdict
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import ShiftRecord
from accounts.permissions import admin_required
from items.models import Category, Item
from rentals.models import RentalRecord, ReturnRecord
from rentals.settings_store import get_blacklist_months, get_default_rental_days, get_overdue_limit, save_policy_settings
from .google_sheets import (
    load_google_sheet_config,
    save_google_sheet_config,
    save_service_account_file,
    sync_today_to_google_sheet,
    test_google_sheet_connection,
)
from students.models import Student

PAGE_SIZE = 10
PAGE_WINDOW_SIZE = 8


def _paginate_queryset(request, queryset, *, page_param='page', page_size=PAGE_SIZE):
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(request.GET.get(page_param))
    total_pages = page_obj.paginator.num_pages
    if total_pages <= PAGE_WINDOW_SIZE:
        start_page = 1
        end_page = total_pages
    else:
        start_page = page_obj.number - (PAGE_WINDOW_SIZE // 2) + 1
        end_page = start_page + PAGE_WINDOW_SIZE - 1
        if start_page < 1:
            start_page = 1
            end_page = PAGE_WINDOW_SIZE
        if end_page > total_pages:
            end_page = total_pages
            start_page = total_pages - PAGE_WINDOW_SIZE + 1
    page_obj.page_window = range(start_page, end_page + 1)
    return page_obj


def _query_string_without(request, *keys):
    params = request.GET.copy()
    for key in keys:
        params.pop(key, None)
    return params.urlencode()


def _record_json(record, *, date_key):
    return {
        'date': date_key,
        'borrowed_at': timezone.localtime(record.borrowed_at).strftime('%Y-%m-%d %H:%M:%S'),
        'student': f'{record.student.student_id} {record.student.name}',
        'student_name': record.student.name,
        'student_id': record.student.student_id,
        'item': f'{record.item.name} {record.unit.number}번',
        'due_date': record.due_date.strftime('%Y-%m-%d'),
        'worker': record.worker.name if record.worker else '삭제됨',
        'memo': record.memo or '-',
        'status': record.display_status,
    }


def _latest_return(record):
    cached = getattr(record, 'lookup_returns', None)
    if cached is not None:
        return cached[0] if cached else None
    return record.return_records.select_related('worker').order_by('-returned_at').first()


def _return_status_label(return_record):
    if not return_record:
        return '-'
    if return_record.return_status == ReturnRecord.ReturnStatus.NORMAL:
        return '완료'
    if return_record.return_status == ReturnRecord.ReturnStatus.BROKEN:
        return '고장'
    if return_record.return_status == ReturnRecord.ReturnStatus.LOST:
        return '분실'
    return return_record.get_return_status_display()


def _d_day_label(due_date):
    days = (due_date - timezone.localdate()).days
    if days == 0:
        return 'D-day'
    if days > 0:
        return f'D-{days}'
    return f'D+{abs(days)}'


def _due_date_display(record):
    base = record.due_date.strftime('%Y-%m-%d')
    if record.status == RentalRecord.Status.ACTIVE:
        return f'{base} ({_d_day_label(record.due_date)})'
    return base


def _worker_display(worker, *, empty='삭제됨'):
    return worker.name if worker else empty


def _parse_date_param(value, default):
    try:
        return datetime.strptime(str(value or ''), '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return default



def _overdue_label(record, return_record):
    if return_record:
        end_date = timezone.localtime(return_record.returned_at).date()
    elif record.status == RentalRecord.Status.ACTIVE:
        end_date = timezone.localdate()
    else:
        return '-'
    days = (end_date - record.due_date).days
    return f'{days}일' if days > 0 else '-'


def _history_row(record, *, include_student=False, include_item=False):
    return_record = _latest_return(record)
    if return_record:
        return_worker = _worker_display(return_record.worker)
    else:
        return_worker = '-'
    row = {
        'borrowed_at': timezone.localtime(record.borrowed_at).strftime('%Y-%m-%d %H:%M:%S'),
        'borrow_worker': _worker_display(record.worker),
        'due_date': _due_date_display(record),
        'returned_at': timezone.localtime(return_record.returned_at).strftime('%Y-%m-%d %H:%M:%S') if return_record else '-',
        'return_status': _return_status_label(return_record),
        'overdue': _overdue_label(record, return_record),
        'return_worker': return_worker,
        'memo': record.memo or (return_record.memo if return_record else '') or '-',
    }
    if include_student:
        row['student'] = f'{record.student.student_id} {record.student.name}'
    if include_item:
        row['item'] = f'{record.item.name} {record.unit.number}번'
    return row


def _record_in_shift_range(queryset, time_field, shift):
    end_at = shift.ended_at or timezone.now()
    return queryset.filter(**{f'{time_field}__gte': shift.started_at, f'{time_field}__lte': end_at})


def _shift_time(value):
    if not value:
        return '근무 중'
    return timezone.localtime(value).strftime('%H:%M:%S')


def _date_filter_records(request, records):
    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()
    if start_date:
        records = records.filter(borrowed_at__date__gte=start_date)
    if end_date:
        records = records.filter(borrowed_at__date__lte=end_date)
    return records, start_date, end_date


@login_required
def dashboard_view(request):
    today = timezone.localdate()
    try:
        selected_year = int(request.GET.get('year', today.year))
        selected_month = int(request.GET.get('month', today.month))
        if not 1 <= selected_month <= 12:
            raise ValueError
    except (TypeError, ValueError):
        selected_year = today.year
        selected_month = today.month

    prev_year, prev_month = (selected_year - 1, 12) if selected_month == 1 else (selected_year, selected_month - 1)
    next_year, next_month = (selected_year + 1, 1) if selected_month == 12 else (selected_year, selected_month + 1)

    active_records = (
        RentalRecord.objects.filter(status=RentalRecord.Status.ACTIVE)
        .select_related('student', 'item', 'unit', 'worker')
        .order_by('due_date', 'student__name')
    )
    month_start = timezone.datetime(selected_year, selected_month, 1).date()
    month_end = timezone.datetime(selected_year, selected_month, calendar.monthrange(selected_year, selected_month)[1]).date()
    borrowed_records = (
        RentalRecord.objects.filter(borrowed_at__date__gte=month_start, borrowed_at__date__lte=month_end)
        .select_related('student', 'item', 'unit', 'worker')
        .order_by('-borrowed_at')
    )

    due_items_json = []
    due_by_date = defaultdict(list)
    for record in active_records:
        item = _record_json(record, date_key=record.due_date.isoformat())
        due_items_json.append(item)
        due_by_date[item['date']].append(item)

    borrowed_items_json = []
    borrowed_by_date = defaultdict(list)
    for record in borrowed_records:
        key = timezone.localtime(record.borrowed_at).date().isoformat()
        item = _record_json(record, date_key=key)
        borrowed_items_json.append(item)
        borrowed_by_date[key].append(item)

    month_calendar = []
    for week in calendar.Calendar(firstweekday=6).monthdatescalendar(selected_year, selected_month):
        week_data = []
        for day in week:
            day_key = day.isoformat()
            day_items = due_by_date.get(day_key, [])
            overdue_count = sum(1 for item in day_items if item['status'] == '반납 안 함')
            week_data.append({
                'date': day_key,
                'day': day.day,
                'is_current_month': day.month == selected_month,
                'is_today': day == today,
                'due_count': len(day_items),
                'borrowed_count': len(borrowed_by_date.get(day_key, [])),
                'overdue_count': overdue_count,
                'has_due': bool(day_items),
                'has_activity': bool(day_items) or bool(borrowed_by_date.get(day_key, [])),
            })
        month_calendar.append(week_data)

    today_key = today.isoformat()
    today_due_items = due_by_date.get(today_key, [])
    not_returned_count = active_records.filter(due_date__lt=today).count()
    recent_records = RentalRecord.objects.select_related('student', 'item', 'unit', 'worker').order_by('-borrowed_at')[:5]

    return render(request, 'dashboard/dashboard.html', {
        'active_tab': 'dashboard',
        'today': today,
        'selected_year': selected_year,
        'selected_month': selected_month,
        'month_label': f'{selected_year}년 {selected_month}월',
        'prev_month_url': f'?year={prev_year}&month={prev_month}',
        'next_month_url': f'?year={next_year}&month={next_month}',
        'today_month_url': f'?year={today.year}&month={today.month}',
        'is_current_month_view': selected_year == today.year and selected_month == today.month,
        'weekdays': ['일', '월', '화', '수', '목', '금', '토'],
        'month_calendar': month_calendar,
        'due_items_json': due_items_json,
        'borrowed_items_json': borrowed_items_json,
        'today_due_items': today_due_items,
        'recent_records': recent_records,
        'summary': {
            'active_rentals': active_records.count(),
            'today_due': len(today_due_items),
            'not_returned': not_returned_count,
        },
    })


@login_required
def coming_soon_view(request, page_title):
    route_to_tab = {
        '물품 반납': 'return',
    }
    return render(request, 'dashboard/coming_soon.html', {
        'page_title': page_title,
        'active_tab': route_to_tab.get(page_title, ''),
    })


@login_required
def student_lookup_view(request):
    query = request.GET.get('q', '').strip()
    students = Student.objects.order_by('student_id')
    if query:
        students = students.filter(Q(name__icontains=query) | Q(student_id__icontains=query))
    page_obj = _paginate_queryset(request, students, page_param='page')

    selected_student = None
    record_page_obj = None
    record_rows = []
    if request.GET.get('student'):
        selected_student = get_object_or_404(Student, pk=request.GET.get('student'))
        records = RentalRecord.objects.filter(student=selected_student).select_related('item', 'unit', 'worker').prefetch_related(
            Prefetch('return_records', queryset=ReturnRecord.objects.select_related('worker').order_by('-returned_at'), to_attr='lookup_returns')
        ).order_by('-borrowed_at')
        records, start_date, end_date = _date_filter_records(request, records)
        record_page_obj = _paginate_queryset(request, records, page_param='record_page')
        record_rows = [_history_row(record, include_item=True) for record in record_page_obj.object_list]
    else:
        start_date = request.GET.get('start_date', '').strip()
        end_date = request.GET.get('end_date', '').strip()

    return render(request, 'dashboard/student_lookup.html', {
        'active_tab': 'lookup',
        'lookup_sub_tab': 'students',
        'students': page_obj.object_list,
        'page_obj': page_obj,
        'pagination_query_string': _query_string_without(request, 'page'),
        'query': query,
        'selected_student': selected_student,
        'record_page_obj': record_page_obj,
        'record_pagination_query_string': _query_string_without(request, 'record_page'),
        'record_rows': record_rows,
        'start_date': start_date,
        'end_date': end_date,
    })


@login_required
def item_lookup_view(request):
    query = request.GET.get('q', '').strip()
    item_type = request.GET.get('type', '').strip()
    category_id = request.GET.get('category', '').strip()
    categories = Category.objects.order_by('name')
    items = Item.objects.select_related('category').order_by('item_type', 'category__name', 'name')
    if query:
        items = items.filter(Q(name__icontains=query) | Q(location__icontains=query) | Q(category__name__icontains=query))
    if item_type in dict(Item.ItemType.choices):
        items = items.filter(item_type=item_type)
    if category_id.isdigit():
        items = items.filter(category_id=category_id)
    page_obj = _paginate_queryset(request, items, page_param='page')

    selected_item = None
    record_page_obj = None
    record_rows = []
    if request.GET.get('item'):
        selected_item = get_object_or_404(Item, pk=request.GET.get('item'))
        records = RentalRecord.objects.filter(item=selected_item).select_related('student', 'unit', 'worker').prefetch_related(
            Prefetch('return_records', queryset=ReturnRecord.objects.select_related('worker').order_by('-returned_at'), to_attr='lookup_returns')
        ).order_by('-borrowed_at')
        records, start_date, end_date = _date_filter_records(request, records)
        record_page_obj = _paginate_queryset(request, records, page_param='record_page')
        record_rows = [_history_row(record, include_student=True) for record in record_page_obj.object_list]
    else:
        start_date = request.GET.get('start_date', '').strip()
        end_date = request.GET.get('end_date', '').strip()

    return render(request, 'dashboard/item_lookup.html', {
        'active_tab': 'lookup',
        'lookup_sub_tab': 'items',
        'categories': categories,
        'item_type_choices': Item.ItemType.choices,
        'items': page_obj.object_list,
        'page_obj': page_obj,
        'pagination_query_string': _query_string_without(request, 'page'),
        'query': query,
        'selected_type': item_type,
        'selected_category': category_id,
        'selected_item': selected_item,
        'record_page_obj': record_page_obj,
        'record_pagination_query_string': _query_string_without(request, 'record_page'),
        'record_rows': record_rows,
        'start_date': start_date,
        'end_date': end_date,
    })



@login_required
@admin_required
def shift_records_view(request):
    today = timezone.localdate()
    query = request.GET.get('q', '').strip()
    selected_date = request.GET.get('date', '').strip() or today.isoformat()

    shifts = ShiftRecord.objects.select_related('user').order_by('-started_at')
    if query:
        deleted_query = '삭제됨'.find(query) >= 0 or query in {'삭제', 'deleted'}
        worker_filter = Q(user__name__icontains=query) | Q(user__student_id__icontains=query)
        if deleted_query:
            worker_filter |= Q(user__isnull=True)
        shifts = shifts.filter(worker_filter)
    if selected_date:
        shifts = shifts.filter(started_at__date=selected_date)

    page_obj = _paginate_queryset(request, shifts, page_param='page')

    selected_shift = None
    rental_rows = []
    return_rows = []
    shift_id = request.GET.get('shift', '').strip()
    if shift_id.isdigit():
        selected_shift = get_object_or_404(ShiftRecord.objects.select_related('user'), pk=shift_id)
        if selected_shift.user:
            rental_records = (
                RentalRecord.objects.select_related('student', 'item', 'unit', 'worker')
                .filter(worker=selected_shift.user)
                .order_by('-borrowed_at')
            )
            rental_records = _record_in_shift_range(rental_records, 'borrowed_at', selected_shift)
            return_records = (
                ReturnRecord.objects.select_related('student', 'item', 'unit', 'worker')
                .filter(worker=selected_shift.user)
                .order_by('-returned_at')
            )
            return_records = _record_in_shift_range(return_records, 'returned_at', selected_shift)
        else:
            rental_records = RentalRecord.objects.none()
            return_records = ReturnRecord.objects.none()
        rental_rows = [
            {
                'borrowed_at': timezone.localtime(record.borrowed_at).strftime('%Y-%m-%d %H:%M:%S'),
                'student': f'{record.student.student_id} {record.student.name}',
                'item': f'{record.item.name} {record.unit.number}번',
                'due_date': record.due_date.strftime('%Y-%m-%d'),
                'memo': record.memo or '-',
            }
            for record in rental_records
        ]
        return_rows = [
            {
                'returned_at': timezone.localtime(record.returned_at).strftime('%Y-%m-%d %H:%M:%S'),
                'student': f'{record.student.student_id} {record.student.name}',
                'item': f'{record.item.name} {record.unit.number}번',
                'return_status': _return_status_label(record),
                'overdue': _overdue_label(record.rental, record),
            }
            for record in return_records
        ]

    return render(request, 'dashboard/shift_records.html', {
        'active_tab': 'admin',
        'settings_sub_tab': 'shifts',
        'query': query,
        'selected_date': selected_date,
        'shifts': page_obj.object_list,
        'page_obj': page_obj,
        'pagination_query_string': _query_string_without(request, 'page'),
        'selected_shift': selected_shift,
        'rental_rows': rental_rows,
        'return_rows': return_rows,
        'today': today,
    })


@login_required
@admin_required
def google_sheets_view(request):
    config = load_google_sheet_config()

    if request.method == 'POST':
        action = request.POST.get('action', '').strip()
        spreadsheet_id = request.POST.get('spreadsheet_id', '').strip()
        service_account_path = request.POST.get('service_account_path', '').strip()

        if action == 'save':
            uploaded_file = request.FILES.get('service_account_file')
            if uploaded_file:
                service_account_path = save_service_account_file(uploaded_file)
            if not spreadsheet_id and not service_account_path:
                # 연동하지 않는 경우 테스트값/기본값을 남기지 않는다.
                save_google_sheet_config(spreadsheet_id='', service_account_path='', last_error='')
                messages.success(request, '구글 시트 연동 설정을 비웠습니다.')
            else:
                save_google_sheet_config(
                    spreadsheet_id=spreadsheet_id,
                    service_account_path=service_account_path,
                    last_error='',
                )
                messages.success(request, '구글 시트 연동 설정이 저장되었습니다.')
            return redirect('dashboard:google_sheets')

        if action in {'test', 'sync'}:
            if spreadsheet_id or service_account_path:
                save_google_sheet_config(
                    spreadsheet_id=spreadsheet_id or config.get('spreadsheet_id', ''),
                    service_account_path=service_account_path or config.get('service_account_path', ''),
                )
            uploaded_file = request.FILES.get('service_account_file')
            if uploaded_file:
                saved_path = save_service_account_file(uploaded_file)
                save_google_sheet_config(service_account_path=saved_path)
            try:
                if action == 'test':
                    result = test_google_sheet_connection()
                    save_google_sheet_config(last_error='')
                    messages.success(request, f"구글 시트 연결 확인 완료: {result.get('title') or result.get('spreadsheet_id')}")
                else:
                    result = sync_today_to_google_sheet()
                    messages.success(request, f"오늘 데이터 동기화 완료: {result['sheet_count']}개 시트 / {result['synced_at']}")
            except Exception as exc:  # noqa: BLE001
                save_google_sheet_config(last_error=str(exc))
                messages.error(request, f'구글 시트 연동 실패: {exc}')
            return redirect('dashboard:google_sheets')

    config = load_google_sheet_config()
    return render(request, 'dashboard/google_sheets.html', {
        'active_tab': 'admin',
        'settings_sub_tab': 'google_sheets',
        'config': config,
    })


@login_required
@admin_required
def settings_view(request):
    return redirect('dashboard:rental_settings')


@login_required
@admin_required
def rental_settings_view(request):
    current_days = get_default_rental_days()
    overdue_limit = get_overdue_limit()
    blacklist_months = get_blacklist_months()

    if request.method == 'POST':
        try:
            days = int(request.POST.get('default_rental_days', current_days))
        except (TypeError, ValueError):
            days = current_days

        if days < 1:
            messages.error(request, '기본 대여 기간은 1일 이상이어야 합니다.')
        else:
            saved = save_policy_settings(
                default_rental_days=days,
                overdue_limit=overdue_limit,
                blacklist_months=blacklist_months,
            )
            current_days = saved['default_rental_days']
            messages.success(request, '대여 설정이 저장되었습니다.')
            return redirect('dashboard:rental_settings')

    return render(request, 'dashboard/settings_rental.html', {
        'active_tab': 'admin',
        'settings_sub_tab': 'rental',
        'default_rental_days': current_days,
        'example_due_date': timezone.localdate() + timedelta(days=current_days),
    })


@login_required
@admin_required
def blacklist_settings_view(request):
    current_days = get_default_rental_days()
    overdue_limit = get_overdue_limit()
    blacklist_months = get_blacklist_months()

    if request.method == 'POST':
        try:
            submitted_overdue_limit = int(request.POST.get('overdue_limit', overdue_limit))
        except (TypeError, ValueError):
            submitted_overdue_limit = overdue_limit
        try:
            submitted_blacklist_months = int(request.POST.get('blacklist_months', blacklist_months))
        except (TypeError, ValueError):
            submitted_blacklist_months = blacklist_months

        if submitted_overdue_limit < 1:
            messages.error(request, '연체 기준 횟수는 1회 이상이어야 합니다.')
        elif submitted_blacklist_months < 1:
            messages.error(request, '블랙리스트 대여 금지 기간은 1개월 이상이어야 합니다.')
        else:
            saved = save_policy_settings(
                default_rental_days=current_days,
                overdue_limit=submitted_overdue_limit,
                blacklist_months=submitted_blacklist_months,
            )
            overdue_limit = saved['overdue_limit']
            blacklist_months = saved['blacklist_months']
            messages.success(request, '블랙리스트 설정이 저장되었습니다.')
            return redirect('dashboard:blacklist_settings')

    return render(request, 'dashboard/settings_blacklist.html', {
        'active_tab': 'admin',
        'settings_sub_tab': 'blacklist',
        'overdue_limit': overdue_limit,
        'blacklist_months': blacklist_months,
    })
