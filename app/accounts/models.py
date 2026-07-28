from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, student_id, name, password=None, **extra_fields):
        if not student_id:
            raise ValueError('학번은 필수입니다.')
        if not name:
            raise ValueError('이름은 필수입니다.')

        raw_password = '' if password is None else str(password)
        user = self.model(
            student_id=str(student_id).strip(),
            name=name.strip(),
            visible_password=raw_password,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, student_id, name, password=None, **extra_fields):
        extra_fields.setdefault('role', User.Role.ADMIN)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('관리자 계정은 is_staff=True 여야 합니다.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('관리자 계정은 is_superuser=True 여야 합니다.')

        return self.create_user(student_id, name, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        WORKER = 'worker', '근무자'
        ADMIN = 'admin', '관리자'

    student_id = models.CharField('학번', max_length=20, unique=True)
    name = models.CharField('이름', max_length=50)
    role = models.CharField('권한', max_length=20, choices=Role.choices, default=Role.WORKER)
    visible_password = models.CharField('표시용 비밀번호', max_length=128, blank=True)
    is_active = models.BooleanField('활성 상태', default=True)
    is_staff = models.BooleanField('관리자 페이지 접근', default=False)
    date_joined = models.DateTimeField('가입일', default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = 'student_id'
    REQUIRED_FIELDS = ['name']

    class Meta:
        verbose_name = '사용자'
        verbose_name_plural = '사용자 목록'
        ordering = ['-date_joined']

    def __str__(self):
        return f'{self.name} ({self.student_id})'


class ShiftRecord(models.Model):
    user = models.ForeignKey(User, verbose_name='근무자', related_name='shift_records', null=True, blank=True, on_delete=models.SET_NULL)
    started_at = models.DateTimeField('출근 시간', default=timezone.now)
    ended_at = models.DateTimeField('퇴근 시간', null=True, blank=True)
    created_at = models.DateTimeField('생성일', auto_now_add=True)
    updated_at = models.DateTimeField('수정일', auto_now=True)

    class Meta:
        ordering = ['-started_at']
        verbose_name = '근무 기록'
        verbose_name_plural = '근무 기록'

    def __str__(self):
        if self.user:
            return f'{self.user.name} ({self.user.student_id}) {self.started_at:%Y-%m-%d %H:%M:%S}'
        return f'삭제됨 {self.started_at:%Y-%m-%d %H:%M:%S}'

    @property
    def is_open(self):
        return self.ended_at is None
