from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='visible_password',
            field=models.CharField(blank=True, default='', max_length=128, verbose_name='표시용 비밀번호'),
            preserve_default=False,
        ),
    ]
