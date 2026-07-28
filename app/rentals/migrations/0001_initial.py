import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('items', '0001_initial'),
        ('students', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='RentalRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('borrowed_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='대여일시')),
                ('due_date', models.DateField(verbose_name='반납 예정일')),
                ('returned_at', models.DateTimeField(blank=True, null=True, verbose_name='실제 반납일시')),
                ('status', models.CharField(choices=[('active', '대여 중'), ('returned', '반납 완료'), ('not_returned', '반납 안 함')], default='active', max_length=20, verbose_name='상태')),
                ('memo', models.CharField(blank=True, max_length=200, verbose_name='메모')),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='rental_records', to='items.item', verbose_name='물품')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='rentals', to='students.student', verbose_name='학생')),
                ('unit', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='rental_records', to='items.equipmentunit', verbose_name='비품 번호')),
                ('worker', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='rental_records', to=settings.AUTH_USER_MODEL, verbose_name='처리 근무자')),
            ],
            options={
                'verbose_name': '대여 기록',
                'verbose_name_plural': '대여 기록',
                'ordering': ['-borrowed_at'],
            },
        ),
    ]
