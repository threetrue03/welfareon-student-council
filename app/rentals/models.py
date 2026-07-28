from calendar import monthrange

from django.conf import settings
from django.db import models
from django.utils import timezone

from items.models import EquipmentUnit, Item
from students.models import Student


def _add_months(date_value, months):
    month_index = date_value.month - 1 + int(months or 0)
    year = date_value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(date_value.day, monthrange(year, month)[1])
    return date_value.replace(year=year, month=month, day=day)


class RentalRecord(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'active', '대여 중'
        RETURNED = 'returned', '반납 완료'
        NOT_RETURNED = 'not_returned', '반납 안 함'

    student = models.ForeignKey(Student, verbose_name='학생', related_name='rentals', on_delete=models.PROTECT)
    item = models.ForeignKey(Item, verbose_name='물품', related_name='rental_records', on_delete=models.PROTECT)
    unit = models.ForeignKey(EquipmentUnit, verbose_name='비품 번호', related_name='rental_records', on_delete=models.PROTECT)
    borrowed_at = models.DateTimeField('대여일시', default=timezone.now)
    due_date = models.DateField('반납 예정일')
    returned_at = models.DateTimeField('실제 반납일시', null=True, blank=True)
    status = models.CharField('상태', max_length=20, choices=Status.choices, default=Status.ACTIVE)
    rule_rental_days = models.PositiveIntegerField('대여 당시 기본 대여 일수', default=7)
    rule_overdue_limit = models.PositiveIntegerField('대여 당시 연체 기준 횟수', default=3)
    rule_blacklist_months = models.PositiveIntegerField('대여 당시 블랙리스트 금지 기간', default=3)
    worker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='근무자',
        related_name='rental_records',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    memo = models.CharField('메모', max_length=200, blank=True)

    class Meta:
        ordering = ['-borrowed_at']
        verbose_name = '대여 기록'
        verbose_name_plural = '대여 기록'

    def __str__(self):
        return f'{self.student.name} / {self.item.name} {self.unit.number}번'

    @property
    def is_overdue(self):
        return self.status == self.Status.ACTIVE and self.due_date < timezone.localdate()

    @property
    def display_status(self):
        if self.is_overdue:
            return '반납 안 함'
        return self.get_status_display()


class ReturnRecord(models.Model):
    class ReturnStatus(models.TextChoices):
        NORMAL = 'normal', '정상 반납'
        BROKEN = 'broken', '고장'
        LOST = 'lost', '분실'

    rental = models.ForeignKey(RentalRecord, verbose_name='대여 기록', related_name='return_records', on_delete=models.PROTECT)
    student = models.ForeignKey(Student, verbose_name='학생', related_name='return_records', on_delete=models.PROTECT)
    item = models.ForeignKey(Item, verbose_name='물품', related_name='return_records', on_delete=models.PROTECT)
    unit = models.ForeignKey(EquipmentUnit, verbose_name='비품 번호', related_name='return_records', on_delete=models.PROTECT)
    returned_at = models.DateTimeField('반납일시', default=timezone.now)
    return_status = models.CharField('반납 상태', max_length=20, choices=ReturnStatus.choices, default=ReturnStatus.NORMAL)
    worker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='근무자',
        related_name='return_records',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    memo = models.CharField('메모', max_length=200, blank=True)

    class Meta:
        ordering = ['-returned_at']
        verbose_name = '반납 기록'
        verbose_name_plural = '반납 기록'

    def __str__(self):
        return f'{self.student.name} / {self.item.name} {self.unit.number}번 반납'

    def _apply_return_effects(self):
        rental = self.rental
        rental.status = RentalRecord.Status.RETURNED
        rental.returned_at = self.returned_at
        rental.save(update_fields=['status', 'returned_at'])

        if self.return_status == self.ReturnStatus.NORMAL:
            self.unit.status = EquipmentUnit.Status.AVAILABLE
        elif self.return_status == self.ReturnStatus.BROKEN:
            self.unit.status = EquipmentUnit.Status.BROKEN
        elif self.return_status == self.ReturnStatus.LOST:
            self.unit.status = EquipmentUnit.Status.LOST
        self.unit.save(update_fields=['status', 'updated_at'])

        returned_date = timezone.localtime(self.returned_at).date()
        if returned_date <= rental.due_date:
            return

        student = self.student
        student.overdue_count = max(0, int(student.overdue_count or 0)) + 1
        if student.overdue_count >= max(1, int(rental.rule_overdue_limit or 1)):
            student.is_blacklisted = True
            student.blacklist_until = _add_months(returned_date, max(1, int(rental.rule_blacklist_months or 1)))
        student.save(update_fields=['overdue_count', 'is_blacklisted', 'blacklist_until', 'updated_at'])

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and self.rental.return_records.count() == 1:
            self._apply_return_effects()
