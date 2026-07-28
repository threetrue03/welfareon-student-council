from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_shiftrecord'),
    ]

    operations = [
        migrations.AlterField(
            model_name='shiftrecord',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='shift_records', to=settings.AUTH_USER_MODEL, verbose_name='근무자'),
        ),
    ]
