from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0002_more_demo_students'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='overdue_count',
            field=models.PositiveIntegerField(default=0, verbose_name='연체 횟수'),
        ),
        migrations.AddField(
            model_name='student',
            name='is_blacklisted',
            field=models.BooleanField(default=False, verbose_name='블랙리스트 여부'),
        ),
    ]
