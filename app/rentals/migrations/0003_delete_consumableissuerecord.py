from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('rentals', '0002_returnrecord_consumableissuerecord'),
    ]

    operations = [
        migrations.DeleteModel(
            name='ConsumableIssueRecord',
        ),
    ]
