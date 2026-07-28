# Generated manually for the welfare program item management app.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True, verbose_name='카테고리 이름')),
                ('description', models.CharField(blank=True, max_length=120, verbose_name='설명')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성일')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='수정일')),
            ],
            options={
                'verbose_name': '카테고리',
                'verbose_name_plural': '카테고리',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Item',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=80, verbose_name='물품 이름')),
                ('item_type', models.CharField(choices=[('equipment', '비품'), ('consumable', '소모품')], max_length=20, verbose_name='물품 유형')),
                ('total_quantity', models.PositiveIntegerField(default=0, verbose_name='전체 수량')),
                ('current_quantity', models.PositiveIntegerField(blank=True, null=True, verbose_name='현재 수량')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성일')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='수정일')),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='items', to='items.category', verbose_name='카테고리')),
            ],
            options={
                'verbose_name': '물품',
                'verbose_name_plural': '물품',
                'ordering': ['category__name', 'name', 'id'],
            },
        ),
        migrations.CreateModel(
            name='EquipmentUnit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.PositiveIntegerField(verbose_name='번호')),
                ('status', models.CharField(choices=[('available', '대여 가능'), ('borrowed', '대여 중'), ('broken', '고장'), ('lost', '분실')], default='available', max_length=20, verbose_name='상태')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='생성일')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='수정일')),
                ('item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='units', to='items.item', verbose_name='물품')),
            ],
            options={
                'verbose_name': '비품 개별 번호',
                'verbose_name_plural': '비품 개별 번호',
                'ordering': ['item__name', 'number'],
                'unique_together': {('item', 'number')},
            },
        ),
    ]
