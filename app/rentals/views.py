from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Prefetch, Q, Sum
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from dashboard.google_sheets import schedule_google_sheet_sync
from items.models import Category, EquipmentUnit, Item
from students.models import Student

from .forms import ConsumableIssueForm, RentalCreateForm
from .models import ConsumableIssueRecord, RentalRecord, ReturnRecord
from .settings_store import get_current_policy_snapshot, get_default_rental_days

PAGE_SIZE = 10
PAGE_WINDOW_SIZE = 8
STAT_PERIOD_CHOICES = [
    ('week', '최근 1주'),
    ('month', '최근 1개월'),
    ('winter_first', '상반기 겨울방학'),
    ('semester_1', '1학기'),
    ('summer', '여름방학'),
    ('semester_2', '2학기'),
    ('winter_second', '하반기 겨울방학'),
    ('year', '최근 1년'),
    ('all', '전체 누적'),
]


def _pagination_query_string(request):
    params = request.GET.copy()
    params.pop('page', None)
    return params.urlencode()


def _paginate(request, queryset, page_size=PAGE_SIZE):
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(request.GET.get('page'))
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


def _student_results(query, selected_student=None):
    query = (query or '').strip()
    if not query:
        return [selected_student] if selected_student else []
    students = list(
        Student.objects
        .filter(Q(name__icontains=query) | Q(student_id__icontains=query))
        .order_by('student_id')[:8]
    )
    if selected_student and selected_student.id not in {student.id for student in students}:
        students = [selected_student, *students][:8]
    return students


@login_required
def student_search_api(request):
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'results': []})
    students = (
        Student.objects
        .filter(Q(name__icontains=query) | Q(student_id__icontains=query))
        .order_by('student_id')[:8]
    )
    return JsonResponse({
        'results': [
            {'id': student.id, 'student_id': student.student_id, 'name': student.name}
            for student in students
        ]
    })


def _available_items(query='', category_id=''):
    cart_units = EquipmentUnit.objects.filter(
        status__in=[
            EquipmentUnit.Status.AVAILABLE,
            EquipmentUnit.Status.BORROWED,
            EquipmentUnit.Status.BROKEN,
            EquipmentUnit.Status.LOST,
        ]
    ).order_by('number')
    items = (
        Item.objects.select_related('category')
        .prefetch_related(Prefetch('units', queryset=cart_units, to_attr='cart_units_for_cart'))
        .annotate(
            cart_available_count=Count(
                'units',
                filter=Q(units__status=EquipmentUnit.Status.AVAILABLE),
                distinct=True,
            )
        )
        .order_by('item_type', 'category__name', 'name')
    )
    if query:
        items = items.filter(Q(name__icontains=query) | Q(location__icontains=query))
    if str(category_id).isdigit():
        items = items.filter(category_id=category_id)
    return items


def _return_item_groups(student, query='', category_id=''):
    if not student:
        return []
    records = (
        RentalRecord.objects
        .select_related('item', 'item__category', 'unit')
        .filter(student=student, status=RentalRecord.Status.ACTIVE, item__item_type=Item.ItemType.EQUIPMENT)
        .order_by('item__category__name', 'item__name', 'unit__number')
    )
    if query:
        records = records.filter(Q(item__name__icontains=query) | Q(item__location__icontains=query))
    if str(category_id).isdigit():
        records = records.filter(item__category_id=category_id)

    groups = []
    grouped_by_item = {}
    for record in records:
        item_id = record.item_id
        if item_id not in grouped_by_item:
            group = {
                'item': record.item,
                'category': record.item.category,
                'records': [],
            }
            grouped_by_item[item_id] = group
            groups.append(group)
        grouped_by_item[item_id]['records'].append(record)
    for group in groups:
        group['count'] = len(group['records'])
        group['unit_numbers'] = ', '.join(f"{record.unit.number}번" for record in group['records'])
    return groups


def _selected_objects(request):
    student_id = request.POST.get('student') or request.GET.get('student')
    selected_student = None
    if student_id and str(student_id).isdigit():
        selected_student = Student.objects.filter(pk=student_id).first()
    return selected_student


@login_required
@transaction.atomic
def borrow_view(request):
    student_query = request.GET.get('student_q', '').strip()
    item_query = request.GET.get('item_q', '').strip()
    category_id = request.GET.get('category', '').strip()

    selected_student = _selected_objects(request)
    phone_ready = request.GET.get('phone_ready') == '1' or request.POST.get('phone_ready') == '1'
    can_choose_items = bool(selected_student and selected_student.can_borrow and phone_ready)
    rental_form = RentalCreateForm()
    issue_form = ConsumableIssueForm()
    policy_snapshot = get_current_policy_snapshot()
    default_due_days = policy_snapshot['rental_days']
    default_due_date = timezone.localdate() + timedelta(days=default_due_days)

    if request.method == 'POST':
        action_type = request.POST.get('action_type', '')
        if not selected_student:
            messages.error(request, '학생을 먼저 선택해주세요.')
        elif action_type == 'save_student_phone':
            selected_student.phone = request.POST.get('phone', '').strip()
            selected_student.save(update_fields=['phone', 'updated_at'])
            messages.success(request, '전화번호가 저장되었습니다.')
            schedule_google_sheet_sync('전화번호 수정')
            return redirect(f'{request.path}?student={selected_student.id}&phone_ready=1')
        elif not selected_student.can_borrow:
            messages.error(request, selected_student.borrow_block_reason)
        elif not phone_ready:
            messages.error(request, '전화번호 입력 후 다음 버튼을 눌러주세요.')
        elif action_type == 'borrow_equipment_cart':
            rental_form = RentalCreateForm(request.POST)
            raw_unit_ids = [unit_id for unit_id in request.POST.getlist('equipment_unit_ids') if str(unit_id).isdigit()]
            if not raw_unit_ids:
                raw_unit_ids = [unit_id for unit_id in request.POST.getlist('unit_ids') if str(unit_id).isdigit()]
            unit_ids = list(dict.fromkeys(raw_unit_ids))
            consumable_ids = [item_id for item_id in request.POST.getlist('consumable_item_ids') if str(item_id).isdigit()]
            consumable_qtys = request.POST.getlist('consumable_quantities')

            if not unit_ids and not consumable_ids:
                messages.error(request, '대여 리스트에 물품을 먼저 담아주세요.')
            elif rental_form.is_valid():
                memo = rental_form.cleaned_data.get('memo', '').strip()
                processed_labels = []

                if unit_ids:
                    units = list(
                        EquipmentUnit.objects.select_for_update()
                        .select_related('item')
                        .filter(pk__in=unit_ids, item__item_type=Item.ItemType.EQUIPMENT)
                    )
                    units_by_id = {str(unit.id): unit for unit in units}
                    ordered_units = [units_by_id.get(unit_id) for unit_id in unit_ids]
                    if any(unit is None for unit in ordered_units):
                        messages.error(request, '대여할 수 없는 물품이 포함되어 있습니다.')
                        return redirect(f'{request.path}?student={selected_student.id}')
                    if any(unit.status != EquipmentUnit.Status.AVAILABLE for unit in ordered_units):
                        messages.error(request, '이미 대여 중이거나 사용할 수 없는 물품 번호가 포함되어 있습니다.')
                        return redirect(f'{request.path}?student={selected_student.id}')
                    if RentalRecord.objects.filter(unit__in=ordered_units, status=RentalRecord.Status.ACTIVE).exists():
                        messages.error(request, '이미 대여 중인 물품 번호가 포함되어 있습니다.')
                        return redirect(f'{request.path}?student={selected_student.id}')

                    for unit in ordered_units:
                        RentalRecord.objects.create(
                            student=selected_student,
                            item=unit.item,
                            unit=unit,
                            due_date=default_due_date,
                            rule_rental_days=policy_snapshot['rental_days'],
                            rule_overdue_limit=policy_snapshot['overdue_limit'],
                            rule_blacklist_months=policy_snapshot['blacklist_months'],
                            memo=memo,
                            worker=request.user,
                        )
                        unit.status = EquipmentUnit.Status.BORROWED
                        unit.save(update_fields=['status', 'updated_at'])
                        processed_labels.append(f'{unit.item.name} {unit.number}번')

                if consumable_ids:
                    qty_by_id = {}
                    for item_id, raw_qty in zip(consumable_ids, consumable_qtys):
                        try:
                            quantity = int(raw_qty)
                        except (TypeError, ValueError):
                            quantity = 0
                        if quantity < 1:
                            messages.error(request, '소모품 지급 수량은 1개 이상이어야 합니다.')
                            return redirect(f'{request.path}?student={selected_student.id}')
                        qty_by_id[item_id] = qty_by_id.get(item_id, 0) + quantity

                    consumables = list(
                        Item.objects.select_for_update()
                        .filter(pk__in=qty_by_id.keys(), item_type=Item.ItemType.CONSUMABLE)
                    )
                    consumables_by_id = {str(item.id): item for item in consumables}
                    if len(consumables_by_id) != len(qty_by_id):
                        messages.error(request, '지급할 수 없는 소모품이 포함되어 있습니다.')
                        return redirect(f'{request.path}?student={selected_student.id}')

                    for item_id, quantity in qty_by_id.items():
                        item = consumables_by_id[item_id]
                        if item.current_quantity is None:
                            messages.error(request, f'{item.name} 현재 수량이 설정되어 있지 않습니다.')
                            return redirect(f'{request.path}?student={selected_student.id}')
                        if quantity > item.current_quantity:
                            messages.error(request, f'{item.name} 현재 수량보다 많이 지급할 수 없습니다. 현재 수량: {item.current_quantity}개')
                            return redirect(f'{request.path}?student={selected_student.id}')

                    for item_id, quantity in qty_by_id.items():
                        item = consumables_by_id[item_id]
                        item.current_quantity -= quantity
                        item.save(update_fields=['current_quantity', 'updated_at'])
                        ConsumableIssueRecord.objects.create(
                            student=selected_student,
                            item=item,
                            quantity=quantity,
                            memo=memo,
                            worker=request.user,
                        )
                        processed_labels.append(f'{item.name} {quantity}개')

                messages.success(request, f'{selected_student.name} 학생에게 {len(processed_labels)}개 항목이 처리되었습니다. ({", ".join(processed_labels)})')
                schedule_google_sheet_sync('대여/지급 처리')
                return redirect(f'{request.path}?student={selected_student.id}')
        else:
            messages.error(request, '물품 특성에 맞는 처리 방식이 아닙니다.')

    item_page_obj = _paginate(request, _available_items(item_query, category_id))
    context = {
        'active_tab': 'borrow',
        'student_query': student_query,
        'student_results': _student_results(student_query, selected_student),
        'selected_student': selected_student,
        'phone_ready': phone_ready,
        'can_choose_items': can_choose_items,
        'categories': Category.objects.order_by('name'),
        'items': item_page_obj.object_list,
        'page_obj': item_page_obj,
        'pagination_query_string': _pagination_query_string(request),
        'item_query': item_query,
        'selected_category': category_id,
        'rental_form': rental_form,
        'issue_form': issue_form,
        'today': timezone.localdate(),
        'default_due_days': default_due_days,
        'default_due_date': default_due_date,
    }
    return render(request, 'rentals/borrow.html', context)


@login_required
@transaction.atomic
def return_view(request):
    student_query = request.GET.get('student_q', '').strip()
    item_query = request.GET.get('item_q', '').strip()
    category_id = request.GET.get('category', '').strip()

    selected_student = _selected_objects(request)
    can_choose_items = bool(selected_student)

    if request.method == 'POST':
        action_type = request.POST.get('action_type', '')
        if not selected_student:
            messages.error(request, '학생을 먼저 선택해주세요.')
        elif action_type == 'return_equipment_cart':
            raw_rental_ids = [rental_id for rental_id in request.POST.getlist('return_rental_ids') if str(rental_id).isdigit()]
            return_statuses = request.POST.getlist('return_statuses')
            rental_ids = list(dict.fromkeys(raw_rental_ids))
            valid_statuses = {value for value, _label in ReturnRecord.ReturnStatus.choices}

            if not rental_ids:
                messages.error(request, '반납 리스트에 물품을 먼저 담아주세요.')
            elif len(raw_rental_ids) != len(return_statuses):
                messages.error(request, '반납 물품 정보가 올바르지 않습니다.')
            else:
                status_by_id = {}
                for rental_id, return_status in zip(raw_rental_ids, return_statuses):
                    if return_status not in valid_statuses:
                        messages.error(request, '반납 상태가 올바르지 않습니다.')
                        return redirect(f'{request.path}?student={selected_student.id}')
                    status_by_id[rental_id] = return_status

                records = list(
                    RentalRecord.objects.select_for_update()
                    .select_related('student', 'item', 'unit')
                    .filter(
                        pk__in=rental_ids,
                        student=selected_student,
                        status=RentalRecord.Status.ACTIVE,
                        item__item_type=Item.ItemType.EQUIPMENT,
                    )
                )
                records_by_id = {str(record.id): record for record in records}
                ordered_records = [records_by_id.get(rental_id) for rental_id in rental_ids]

                if any(record is None for record in ordered_records):
                    messages.error(request, '반납할 수 없는 물품이 포함되어 있습니다.')
                    return redirect(f'{request.path}?student={selected_student.id}')

                processed_labels = []
                for record in ordered_records:
                    return_status = status_by_id[str(record.id)]
                    ReturnRecord.objects.create(
                        rental=record,
                        student=record.student,
                        item=record.item,
                        unit=record.unit,
                        return_status=return_status,
                        worker=request.user,
                    )
                    processed_labels.append(f'{record.item.name} {record.unit.number}번')

                messages.success(request, f'{selected_student.name} 학생의 {len(processed_labels)}개 물품이 반납 처리되었습니다. ({", ".join(processed_labels)})')
                schedule_google_sheet_sync('반납 처리')
                return redirect(f'{request.path}?student={selected_student.id}')
        else:
            messages.error(request, '올바르지 않은 반납 처리입니다.')

    return_groups = _return_item_groups(selected_student, item_query, category_id)
    item_page_obj = _paginate(request, return_groups)
    context = {
        'active_tab': 'return',
        'student_query': student_query,
        'student_results': _student_results(student_query, selected_student),
        'selected_student': selected_student,
        'can_choose_items': can_choose_items,
        'categories': Category.objects.order_by('name'),
        'return_groups': item_page_obj.object_list,
        'page_obj': item_page_obj,
        'pagination_query_string': _pagination_query_string(request),
        'item_query': item_query,
        'selected_category': category_id,
        'return_status_choices': ReturnRecord.ReturnStatus.choices,
    }
    return render(request, 'rentals/return.html', context)


def _record_date_context(request):
    today = timezone.localdate()
    range_key = request.GET.get('range', '').strip()
    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()

    if range_key == 'today':
        start_date = end_date = today.isoformat()
    elif range_key == 'yesterday':
        yesterday = today - timedelta(days=1)
        start_date = end_date = yesterday.isoformat()
    elif range_key == 'week':
        start_date = (today - timedelta(days=today.weekday())).isoformat()
        end_date = today.isoformat()
    elif range_key == 'month':
        start_date = today.replace(day=1).isoformat()
        end_date = today.isoformat()
    elif not start_date and not end_date:
        range_key = 'all'
    return {'range_key': range_key, 'start_date': start_date, 'end_date': end_date}


def _apply_date_filter(queryset, field_name, date_context):
    start_date = date_context.get('start_date')
    end_date = date_context.get('end_date')
    if start_date:
        queryset = queryset.filter(**{f'{field_name}__date__gte': start_date})
    if end_date:
        queryset = queryset.filter(**{f'{field_name}__date__lte': end_date})
    return queryset


def _statistics_period(request):
    today = timezone.localdate()
    valid_periods = {**dict(STAT_PERIOD_CHOICES), 'custom': '직접 선택'}
    period_key = request.GET.get('period', 'month').strip()
    if period_key not in valid_periods:
        period_key = 'month'

    default_year = today.year + 1 if today.month == 12 else today.year
    try:
        selected_year = int(request.GET.get('year', default_year))
    except (TypeError, ValueError):
        selected_year = default_year
    selected_year = min(max(selected_year, 2000), 2100)

    start_date = None
    end_date = None
    if period_key == 'week':
        start_date = today - timedelta(days=6)
        end_date = today
    elif period_key == 'month':
        start_date = today - timedelta(days=29)
        end_date = today
    elif period_key == 'winter_first':
        start_date = date(selected_year - 1, 12, 1)
        end_date = date(selected_year, 3, 1) - timedelta(days=1)
    elif period_key == 'semester_1':
        start_date = date(selected_year, 3, 1)
        end_date = date(selected_year, 6, 30)
    elif period_key == 'summer':
        start_date = date(selected_year, 7, 1)
        end_date = date(selected_year, 8, 31)
    elif period_key == 'semester_2':
        start_date = date(selected_year, 9, 1)
        end_date = date(selected_year, 11, 30)
    elif period_key == 'winter_second':
        start_date = date(selected_year, 12, 1)
        end_date = date(selected_year + 1, 3, 1) - timedelta(days=1)
    elif period_key == 'year':
        start_date = today - timedelta(days=364)
        end_date = today
    elif period_key == 'custom':
        try:
            start_date = date.fromisoformat(request.GET.get('start_date', '').strip())
            end_date = date.fromisoformat(request.GET.get('end_date', '').strip())
        except (TypeError, ValueError):
            start_date = end_date = today
        if start_date > end_date:
            start_date, end_date = end_date, start_date

    label = valid_periods[period_key]
    if start_date and end_date:
        label = f'{label} · {start_date:%Y-%m-%d} ~ {end_date:%Y-%m-%d}'
    return {
        'period_key': period_key,
        'period_label': label,
        'period_start': start_date,
        'period_end': end_date,
        'custom_start_date': start_date.isoformat() if period_key == 'custom' else '',
        'custom_end_date': end_date.isoformat() if period_key == 'custom' else '',
        'selected_year': selected_year,
        'year_choices': range(max(default_year, selected_year), 2019, -1),
    }


def _apply_statistics_period(queryset, field_name, period_context):
    start_date = period_context['period_start']
    end_date = period_context['period_end']
    if start_date:
        queryset = queryset.filter(**{f'{field_name}__date__gte': start_date})
    if end_date:
        queryset = queryset.filter(**{f'{field_name}__date__lte': end_date})
    return queryset


def _chart_distributions(rentals, returns):
    weekday_rows = [
        {'label': label, 'rentals': 0, 'returns': 0}
        for label in ['월', '화', '수', '목', '금', '토', '일']
    ]
    hourly_rows = [
        {'label': f'{hour:02d}시', 'rentals': 0, 'returns': 0}
        for hour in range(24)
    ]

    for value in rentals.values_list('borrowed_at', flat=True):
        local_value = timezone.localtime(value)
        weekday_rows[local_value.weekday()]['rentals'] += 1
        hourly_rows[local_value.hour]['rentals'] += 1
    for value in returns.values_list('returned_at', flat=True):
        local_value = timezone.localtime(value)
        weekday_rows[local_value.weekday()]['returns'] += 1
        hourly_rows[local_value.hour]['returns'] += 1

    for rows in (weekday_rows, hourly_rows):
        maximum = max(
            [row['rentals'] for row in rows] + [row['returns'] for row in rows] + [1]
        )
        for row in rows:
            row['rental_percent'] = round(row['rentals'] / maximum * 100)
            row['return_percent'] = round(row['returns'] / maximum * 100)
    return weekday_rows, hourly_rows


def _ranked_rows(queryset, *, aggregate, unit):
    rows = list(
        queryset.values('item_id', 'item__name')
        .annotate(value=aggregate)
        .order_by('-value', 'item__name')
    )
    maximum = max([row['value'] for row in rows] + [1])
    for rank, row in enumerate(rows, start=1):
        row['rank'] = rank
        row['label'] = row['item__name']
        row['unit'] = unit
        row['percent'] = round(row['value'] / maximum * 100)
    return rows


def _overdue_ranking(period_context):
    today = timezone.localdate()
    rentals = RentalRecord.objects.select_related('student')
    start_date = period_context['period_start']
    end_date = period_context['period_end']
    if start_date:
        rentals = rentals.filter(due_date__gte=start_date)
    if end_date:
        rentals = rentals.filter(due_date__lte=end_date)

    ranking = {}
    for record in rentals:
        is_currently_overdue = record.returned_at is None and record.due_date < today
        was_returned_late = bool(
            record.returned_at
            and timezone.localtime(record.returned_at).date() > record.due_date
        )
        if not (is_currently_overdue or was_returned_late):
            continue
        row = ranking.setdefault(record.student_id, {
            'student': record.student,
            'value': 0,
            'active_overdue': 0,
        })
        row['value'] += 1
        if is_currently_overdue:
            row['active_overdue'] += 1

    rows = sorted(
        ranking.values(),
        key=lambda row: (-row['value'], row['student'].student_id),
    )
    maximum = max([row['value'] for row in rows] + [1])
    for rank, row in enumerate(rows, start=1):
        row['rank'] = rank
        row['percent'] = round(row['value'] / maximum * 100)
    return rows


@login_required
def rental_records_view(request):
    date_context = _record_date_context(request)
    records = RentalRecord.objects.select_related('student', 'item', 'unit', 'worker')
    records = _apply_date_filter(records, 'borrowed_at', date_context).order_by('-borrowed_at')[:300]
    return render(request, 'rentals/rental_records.html', {
        'active_tab': 'records',
        'record_sub_tab': 'rentals',
        'records': records,
        **date_context,
    })


@login_required
def return_records_view(request):
    date_context = _record_date_context(request)
    records = ReturnRecord.objects.select_related('student', 'item', 'unit', 'worker')
    records = _apply_date_filter(records, 'returned_at', date_context).order_by('-returned_at')[:300]
    return render(request, 'rentals/return_records.html', {
        'active_tab': 'records',
        'record_sub_tab': 'returns',
        'records': records,
        **date_context,
    })


@login_required
def consumable_records_view(request):
    date_context = _record_date_context(request)
    records = ConsumableIssueRecord.objects.select_related('student', 'item', 'worker')
    records = _apply_date_filter(records, 'issued_at', date_context).order_by('-issued_at')[:300]
    return render(request, 'rentals/consumable_records.html', {
        'active_tab': 'records',
        'record_sub_tab': 'consumables',
        'records': records,
        **date_context,
    })


@login_required
def statistics_view(request):
    period_context = _statistics_period(request)
    equipment_rentals = RentalRecord.objects.filter(item__item_type=Item.ItemType.EQUIPMENT)
    equipment_returns = ReturnRecord.objects.filter(item__item_type=Item.ItemType.EQUIPMENT)
    consumable_issues = ConsumableIssueRecord.objects.all()

    equipment_rentals = _apply_statistics_period(equipment_rentals, 'borrowed_at', period_context)
    equipment_returns = _apply_statistics_period(equipment_returns, 'returned_at', period_context)
    consumable_issues = _apply_statistics_period(consumable_issues, 'issued_at', period_context)

    weekday_rows, hourly_rows = _chart_distributions(equipment_rentals, equipment_returns)
    equipment_rows = _ranked_rows(
        equipment_rentals,
        aggregate=Count('id'),
        unit='건',
    )
    consumable_rows = _ranked_rows(
        consumable_issues,
        aggregate=Sum('quantity'),
        unit='개',
    )
    overdue_rows = _overdue_ranking(period_context)
    consumable_total = consumable_issues.aggregate(total=Sum('quantity'))['total'] or 0

    return render(request, 'rentals/statistics.html', {
        'active_tab': 'records',
        'record_sub_tab': 'statistics',
        'period_choices': STAT_PERIOD_CHOICES,
        'weekday_rows': weekday_rows,
        'hourly_rows': hourly_rows,
        'equipment_rows': equipment_rows,
        'consumable_rows': consumable_rows,
        'overdue_rows': overdue_rows,
        'summary': {
            'rentals': equipment_rentals.count(),
            'returns': equipment_returns.count(),
            'consumable_quantity': consumable_total,
            'overdue': sum(row['value'] for row in overdue_rows),
        },
        **period_context,
    })
