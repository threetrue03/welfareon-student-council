from datetime import date, timedelta
from unittest.mock import patch

from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from items.models import EquipmentUnit, Item
from students.models import Student

from .models import ConsumableIssueRecord, RentalRecord, ReturnRecord
from .views import _statistics_period


class ConsumableIssueTests(TestCase):
    def setUp(self):
        self.worker = User.objects.create_user(
            student_id='20250001',
            name='테스트 근무자',
            password='test-password',
        )
        self.student = Student.objects.create(
            student_id='20250002',
            name='테스트 학생',
        )
        self.item = Item.objects.create(
            name='물티슈',
            item_type=Item.ItemType.CONSUMABLE,
            total_quantity=100,
            current_quantity=40,
        )
        self.client.login(student_id=self.worker.student_id, password='test-password')

    @patch('rentals.views.schedule_google_sheet_sync')
    def test_consumable_issue_is_recorded_when_stock_is_reduced(self, sync_mock):
        response = self.client.post(reverse('rentals:borrow'), {
            'student': self.student.pk,
            'phone_ready': '1',
            'action_type': 'borrow_equipment_cart',
            'consumable_item_ids': [str(self.item.pk)],
            'consumable_quantities': ['3'],
            'memo': '행사 지급',
        })

        self.assertRedirects(response, f"{reverse('rentals:borrow')}?student={self.student.pk}")
        self.item.refresh_from_db()
        self.assertEqual(self.item.current_quantity, 37)
        record = ConsumableIssueRecord.objects.get()
        self.assertEqual(record.student, self.student)
        self.assertEqual(record.item, self.item)
        self.assertEqual(record.quantity, 3)
        self.assertEqual(record.worker, self.worker)
        self.assertEqual(record.memo, '행사 지급')
        sync_mock.assert_called_once_with('대여/지급 처리')

    def test_consumable_record_page_uses_record_layout(self):
        ConsumableIssueRecord.objects.create(
            student=self.student,
            item=self.item,
            quantity=2,
            worker=self.worker,
        )

        response = self.client.get(reverse('rentals:consumable_records'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'rentals/consumable_records.html')
        self.assertContains(response, '물티슈')
        self.assertContains(response, '2개')


class StatisticsPeriodTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def period(self, key, **params):
        query = {
            'period': key,
            'year': '2026',
        }
        query.update(params)
        request = self.factory.get('/rentals/records/statistics/', query)
        return _statistics_period(request)

    def test_academic_period_boundaries(self):
        winter_first = self.period('winter_first')
        semester_1 = self.period('semester_1')
        summer = self.period('summer')
        semester_2 = self.period('semester_2')
        winter_second = self.period('winter_second')

        self.assertEqual((winter_first['period_start'], winter_first['period_end']), (date(2025, 12, 1), date(2026, 2, 28)))
        self.assertEqual((semester_1['period_start'], semester_1['period_end']), (date(2026, 3, 1), date(2026, 6, 30)))
        self.assertEqual((summer['period_start'], summer['period_end']), (date(2026, 7, 1), date(2026, 8, 31)))
        self.assertEqual((semester_2['period_start'], semester_2['period_end']), (date(2026, 9, 1), date(2026, 11, 30)))
        self.assertEqual((winter_second['period_start'], winter_second['period_end']), (date(2026, 12, 1), date(2027, 2, 28)))

    def test_custom_period_uses_selected_dates_and_normalizes_order(self):
        custom = self.period(
            'custom',
            start_date='2026-05-31',
            end_date='2026-05-01',
        )

        self.assertEqual((custom['period_start'], custom['period_end']), (date(2026, 5, 1), date(2026, 5, 31)))
        self.assertEqual(custom['custom_start_date'], '2026-05-01')
        self.assertEqual(custom['custom_end_date'], '2026-05-31')

    def test_winter_period_handles_leap_year(self):
        request = self.factory.get('/rentals/records/statistics/', {
            'period': 'winter_first',
            'year': '2028',
        })

        winter = _statistics_period(request)

        self.assertEqual(winter['period_end'], date(2028, 2, 29))


class StatisticsViewTests(TestCase):
    def setUp(self):
        self.worker = User.objects.create_user(
            student_id='20250011',
            name='통계 근무자',
            password='test-password',
        )
        self.student = Student.objects.create(
            student_id='20250012',
            name='연체 학생',
        )
        self.client.login(student_id=self.worker.student_id, password='test-password')
        self.equipment = Item.objects.create(
            name='우산',
            item_type=Item.ItemType.EQUIPMENT,
            total_quantity=2,
        )
        self.consumable = Item.objects.create(
            name='물티슈',
            item_type=Item.ItemType.CONSUMABLE,
            total_quantity=100,
            current_quantity=90,
        )
        due_date = timezone.localdate() - timedelta(days=1)

        returned_unit = EquipmentUnit.objects.create(
            item=self.equipment,
            number=1,
            status=EquipmentUnit.Status.BORROWED,
        )
        returned_rental = RentalRecord.objects.create(
            student=self.student,
            item=self.equipment,
            unit=returned_unit,
            due_date=due_date,
            worker=self.worker,
        )
        ReturnRecord.objects.create(
            rental=returned_rental,
            student=self.student,
            item=self.equipment,
            unit=returned_unit,
            worker=self.worker,
        )

        active_unit = EquipmentUnit.objects.create(
            item=self.equipment,
            number=2,
            status=EquipmentUnit.Status.BORROWED,
        )
        RentalRecord.objects.create(
            student=self.student,
            item=self.equipment,
            unit=active_unit,
            due_date=due_date,
            worker=self.worker,
        )
        ConsumableIssueRecord.objects.create(
            student=self.student,
            item=self.consumable,
            quantity=5,
            worker=self.worker,
        )

    def test_statistics_include_equipment_consumables_and_all_overdue_types(self):
        response = self.client.get(reverse('rentals:statistics'), {'period': 'all'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['summary']['rentals'], 2)
        self.assertEqual(response.context['summary']['returns'], 1)
        self.assertEqual(response.context['summary']['consumable_quantity'], 5)
        self.assertEqual(response.context['summary']['overdue'], 2)
        self.assertEqual(response.context['equipment_rows'][0]['label'], '우산')
        self.assertEqual(response.context['equipment_rows'][0]['value'], 2)
        self.assertEqual(response.context['consumable_rows'][0]['label'], '물티슈')
        self.assertEqual(response.context['consumable_rows'][0]['value'], 5)
        self.assertEqual(response.context['overdue_rows'][0]['value'], 2)
        self.assertEqual(response.context['overdue_rows'][0]['active_overdue'], 1)

    def test_custom_date_range_filters_all_statistics(self):
        today = timezone.localdate().isoformat()

        response = self.client.get(reverse('rentals:statistics'), {
            'period': 'custom',
            'start_date': today,
            'end_date': today,
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['period_key'], 'custom')
        self.assertEqual(response.context['summary']['rentals'], 2)
        self.assertEqual(response.context['summary']['returns'], 1)
        self.assertEqual(response.context['summary']['consumable_quantity'], 5)
        self.assertContains(response, '직접 날짜 지정')
