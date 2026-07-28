from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0004_student_phone'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='blacklist_until',
            field=models.DateField(blank=True, null=True, verbose_name='블랙리스트 해제일'),
        ),
    ]
