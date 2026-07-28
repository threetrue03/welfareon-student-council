from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rentals', '0003_delete_consumableissuerecord'),
    ]

    operations = [
        migrations.AddField(
            model_name='rentalrecord',
            name='rule_rental_days',
            field=models.PositiveIntegerField(default=7, verbose_name='대여 당시 기본 대여 일수'),
        ),
        migrations.AddField(
            model_name='rentalrecord',
            name='rule_overdue_limit',
            field=models.PositiveIntegerField(default=3, verbose_name='대여 당시 연체 기준 횟수'),
        ),
        migrations.AddField(
            model_name='rentalrecord',
            name='rule_blacklist_months',
            field=models.PositiveIntegerField(default=3, verbose_name='대여 당시 블랙리스트 금지 기간'),
        ),
    ]
