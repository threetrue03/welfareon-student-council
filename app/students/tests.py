from django.test import TestCase

from .models import Student


class StudentModelTests(TestCase):
    def test_paid_student_can_borrow(self):
        student = Student.objects.create(name='테스트', student_id='20990001', fee_status=Student.FeeStatus.PAID)
        self.assertTrue(student.can_borrow)
