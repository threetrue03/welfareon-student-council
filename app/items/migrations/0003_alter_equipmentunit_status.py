from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('items', '0002_item_location'),
    ]

    operations = [
        migrations.AlterField(
            model_name='equipmentunit',
            name='status',
            field=models.CharField(
                choices=[
                    ('available', '대여 가능'),
                    ('borrowed', '대여 중'),
                    ('broken', '고장'),
                    ('lost', '분실'),
                    ('inactive', '비활성'),
                ],
                default='available',
                max_length=20,
                verbose_name='상태',
            ),
        ),
    ]
