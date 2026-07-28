from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('items', '0001_initial'),
        ('students', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('rentals', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReturnRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('returned_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='반납일시')),
                ('return_status', models.CharField(choices=[('normal', '정상 반납'), ('broken', '고장'), ('lost', '분실')], default='normal', max_length=20, verbose_name='반납 상태')),
                ('memo', models.CharField(blank=True, max_length=200, verbose_name='메모')),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='return_records', to='items.item', verbose_name='물품')),
                ('rental', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='return_records', to='rentals.rentalrecord', verbose_name='대여 기록')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='return_records', to='students.student', verbose_name='학생')),
                ('unit', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='return_records', to='items.equipmentunit', verbose_name='비품 번호')),
                ('worker', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='return_records', to=settings.AUTH_USER_MODEL, verbose_name='처리 근무자')),
            ],
            options={
                'verbose_name': '반납 기록',
                'verbose_name_plural': '반납 기록',
                'ordering': ['-returned_at'],
            },
        ),
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
