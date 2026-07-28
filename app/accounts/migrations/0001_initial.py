# Generated manually for the initial custom user model.

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('student_id', models.CharField(max_length=20, unique=True, verbose_name='학번')),
                ('name', models.CharField(max_length=50, verbose_name='이름')),
                ('role', models.CharField(choices=[('worker', '근무자'), ('admin', '관리자')], default='worker', max_length=20, verbose_name='권한')),
                ('is_active', models.BooleanField(default=True, verbose_name='활성 상태')),
                ('is_staff', models.BooleanField(default=False, verbose_name='관리자 페이지 접근')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='가입일')),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': '사용자',
                'verbose_name_plural': '사용자 목록',
                'ordering': ['-date_joined'],
            },
        ),
    ]
