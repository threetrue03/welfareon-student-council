from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from accounts.permissions import _clear_admin_cache, get_admin_ids, write_admin_ids
from items.models import EquipmentUnit, Item
from rentals.models import RentalRecord, ReturnRecord
from students.models import Student

from .google_sheets import build_today_sheet_payload


class ActiveRentalSheetTests(TestCase):
    def setUp(self):
        self.student = Student.objects.create(
            name='테스트 학생',
            student_id='20250000',
        )
        self.item = Item.objects.create(
            name='테스트 물품',
            item_type=Item.ItemType.EQUIPMENT,
            total_quantity=1,
        )
        self.unit = EquipmentUnit.objects.create(
            item=self.item,
            number=1,
            status=EquipmentUnit.Status.BORROWED,
        )
        self.due_date = timezone.localdate() + timedelta(days=7)
        self.rental = RentalRecord.objects.create(
            student=self.student,
            item=self.item,
            unit=self.unit,
            due_date=self.due_date,
        )

    def test_active_rental_is_listed_and_removed_after_return(self):
        header = ['이름', '학번', '물품', '물품번호', '반납예정일']
        expected_row = [
            self.student.name,
            self.student.student_id,
            self.item.name,
            self.unit.number,
            self.due_date.strftime('%Y-%m-%d'),
        ]

        payload = build_today_sheet_payload()
        self.assertEqual(payload['대여 현황'], [header, expected_row])

        ReturnRecord.objects.create(
            rental=self.rental,
            student=self.student,
            item=self.item,
            unit=self.unit,
        )

        payload = build_today_sheet_payload()
        self.assertEqual(payload['대여 현황'], [header])


class AdminStudentIdManagementTests(TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.settings_override = override_settings(BASE_DIR=Path(self.temp_dir.name))
        self.settings_override.enable()
        self.admin = User.objects.create_user(
            student_id='20250001',
            name='기본 관리자',
            password='test-password',
            role=User.Role.ADMIN,
            is_staff=True,
        )
        write_admin_ids({self.admin.student_id})
        self.client.login(student_id=self.admin.student_id, password='test-password')

    def tearDown(self):
        _clear_admin_cache()
        self.settings_override.disable()
        self.temp_dir.cleanup()

    def create_worker(self, student_id, name='테스트 근무자'):
        return User.objects.create_user(
            student_id=student_id,
            name=name,
            password='test-password',
        )

    def test_admin_can_open_management_page_and_add_existing_worker(self):
        worker = self.create_worker('20250002')

        page_response = self.client.get(reverse('dashboard:admin_student_ids'))
        add_response = self.client.post(reverse('dashboard:admin_student_ids'), {
            'action': 'add',
            'student_id': worker.student_id,
        })

        self.assertEqual(page_response.status_code, 200)
        self.assertContains(page_response, '관리자 학번 관리')
        self.assertRedirects(add_response, reverse('dashboard:admin_student_ids'))
        self.assertEqual(get_admin_ids(), {self.admin.student_id, worker.student_id})
        worker.refresh_from_db()
        self.assertEqual(worker.role, User.Role.ADMIN)
        self.assertTrue(worker.is_staff)

    def test_admin_id_can_be_changed_to_another_existing_worker(self):
        old_admin = self.create_worker('20250002', '변경 전 관리자')
        new_admin = self.create_worker('20250003', '변경 후 관리자')
        old_admin.role = User.Role.ADMIN
        old_admin.is_staff = True
        old_admin.save(update_fields=['role', 'is_staff'])
        write_admin_ids({self.admin.student_id, old_admin.student_id})

        response = self.client.post(reverse('dashboard:admin_student_ids'), {
            'action': 'update',
            'old_student_id': old_admin.student_id,
            'student_id': new_admin.student_id,
        })

        self.assertRedirects(response, reverse('dashboard:admin_student_ids'))
        self.assertEqual(get_admin_ids(), {self.admin.student_id, new_admin.student_id})
        old_admin.refresh_from_db()
        new_admin.refresh_from_db()
        self.assertEqual(old_admin.role, User.Role.WORKER)
        self.assertFalse(old_admin.is_staff)
        self.assertEqual(new_admin.role, User.Role.ADMIN)
        self.assertTrue(new_admin.is_staff)

    def test_other_admin_can_be_deleted_and_is_demoted(self):
        target = self.create_worker('20250002', '삭제 대상 관리자')
        target.role = User.Role.ADMIN
        target.is_staff = True
        target.save(update_fields=['role', 'is_staff'])
        write_admin_ids({self.admin.student_id, target.student_id})

        response = self.client.post(reverse('dashboard:admin_student_ids'), {
            'action': 'delete',
            'old_student_id': target.student_id,
        })

        self.assertRedirects(response, reverse('dashboard:admin_student_ids'))
        self.assertEqual(get_admin_ids(), {self.admin.student_id})
        target.refresh_from_db()
        self.assertEqual(target.role, User.Role.WORKER)
        self.assertFalse(target.is_staff)

    def test_current_admin_cannot_modify_or_delete_own_membership(self):
        response = self.client.post(reverse('dashboard:admin_student_ids'), {
            'action': 'delete',
            'old_student_id': self.admin.student_id,
        })

        self.assertRedirects(response, reverse('dashboard:admin_student_ids'))
        self.assertEqual(get_admin_ids(), {self.admin.student_id})
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.role, User.Role.ADMIN)
        self.assertTrue(self.admin.is_staff)

    def test_unknown_worker_id_cannot_be_added(self):
        response = self.client.post(reverse('dashboard:admin_student_ids'), {
            'action': 'add',
            'student_id': '20999999',
        })

        self.assertRedirects(response, reverse('dashboard:admin_student_ids'))
        self.assertEqual(get_admin_ids(), {self.admin.student_id})
