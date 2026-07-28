from django.db import models
from django.utils import timezone


class Student(models.Model):
    class FeeStatus(models.TextChoices):
        PAID = 'paid', '납부'
        UNPAID = 'unpaid', '미납'
        REFUNDED = 'refunded', '환불'

    name = models.CharField('이름', max_length=50)
    student_id = models.CharField('학번', max_length=20, unique=True)
    phone = models.CharField('전화번호', max_length=30, blank=True)
    fee_status = models.CharField('학생회비 상태', max_length=20, choices=FeeStatus.choices, default=FeeStatus.PAID)
    memo = models.CharField('메모', max_length=200, blank=True)
    overdue_count = models.PositiveIntegerField('연체 횟수', default=0)
    is_blacklisted = models.BooleanField('블랙리스트 여부', default=False)
    blacklist_until = models.DateField('블랙리스트 해제일', null=True, blank=True)
    created_at = models.DateTimeField('생성일', auto_now_add=True)
    updated_at = models.DateTimeField('수정일', auto_now=True)

    class Meta:
        ordering = ['student_id']
        verbose_name = '학생'
        verbose_name_plural = '학생 목록'

    def __str__(self):
        return f'{self.name} ({self.student_id})'

    @property
    def blacklist_active(self):
        if not self.is_blacklisted:
            return False
        if self.blacklist_until is None:
            return True
        return self.blacklist_until >= timezone.localdate()

    @property
    def can_borrow(self):
        return self.fee_status == self.FeeStatus.PAID and not self.blacklist_active

    @property
    def borrow_block_reason(self):
        if self.can_borrow:
            return ''
        if self.blacklist_active:
            if self.blacklist_until:
                return f'블랙리스트 학생은 {self.blacklist_until:%Y-%m-%d}까지 물품 대여가 불가능합니다.'
            return '블랙리스트 학생은 물품 대여가 불가능합니다.'
        if self.fee_status == self.FeeStatus.UNPAID:
            return '학생회비 미납 학생은 물품 대여가 불가능합니다.'
        if self.fee_status == self.FeeStatus.REFUNDED:
            return '학생회비 환불 학생은 물품 대여가 불가능합니다.'
        return '물품 대여가 불가능한 학생입니다.'
