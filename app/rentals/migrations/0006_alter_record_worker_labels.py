import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rentals', '0005_consumableissuerecord'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='rentalrecord',
            name='worker',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='rental_records',
                to=settings.AUTH_USER_MODEL,
                verbose_name='근무자',
            ),
        ),
        migrations.AlterField(
            model_name='returnrecord',
            name='worker',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='return_records',
                to=settings.AUTH_USER_MODEL,
                verbose_name='근무자',
            ),
        ),
    ]
