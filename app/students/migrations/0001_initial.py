from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Student',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='이름')),
                ('student_id', models.CharField(max_length=20, unique=True, verbose_name='학번')),
                ('fee_status', models.CharField(choices=[('paid', '납부'), ('unpaid', '미납'), ('refunded', '환불')], default='paid', max_length=20, verbose_name='학생회비 상태')),
                ('memo', models.CharField(blank=True, max_length=200, verbose_name='메모')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성일')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='수정일')),
            ],
            options={
                'verbose_name': '학생',
                'verbose_name_plural': '학생 목록',
                'ordering': ['student_id'],
            },
        ),
    ]
