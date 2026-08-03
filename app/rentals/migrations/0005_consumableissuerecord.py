from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('items', '0002_item_location'),
        ('students', '0005_student_blacklist_until'),
        ('rentals', '0004_rental_policy_snapshot'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConsumableIssueRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(verbose_name='지급 수량')),
                ('issued_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='지급일시')),
                ('memo', models.CharField(blank=True, max_length=200, verbose_name='메모')),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='issue_records', to='items.item', verbose_name='소모품')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='consumable_issue_records', to='students.student', verbose_name='학생')),
                ('worker', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='consumable_issue_records', to=settings.AUTH_USER_MODEL, verbose_name='처리 근무자')),
            ],
            options={
                'verbose_name': '소모품 지급 기록',
                'verbose_name_plural': '소모품 지급 기록',
                'ordering': ['-issued_at'],
            },
        ),
    ]
