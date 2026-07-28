from django.db import models


class Category(models.Model):
    name = models.CharField('카테고리 이름', max_length=50, unique=True)
    description = models.CharField('설명', max_length=120, blank=True)
    created_at = models.DateTimeField('생성일', auto_now_add=True)
    updated_at = models.DateTimeField('수정일', auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = '카테고리'
        verbose_name_plural = '카테고리'

    def __str__(self):
        return self.name


class Item(models.Model):
    class ItemType(models.TextChoices):
        EQUIPMENT = 'equipment', '비품'
        CONSUMABLE = 'consumable', '소모품'

    name = models.CharField('물품 이름', max_length=80)
    location = models.CharField('물품 위치', max_length=120, blank=True)
    item_type = models.CharField('물품 유형', max_length=20, choices=ItemType.choices)
    category = models.ForeignKey(
        Category,
        verbose_name='카테고리',
        related_name='items',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    total_quantity = models.PositiveIntegerField('전체 수량', default=0)
    current_quantity = models.PositiveIntegerField('현재 수량', null=True, blank=True)
    created_at = models.DateTimeField('생성일', auto_now_add=True)
    updated_at = models.DateTimeField('수정일', auto_now=True)

    class Meta:
        ordering = ['category__name', 'name', 'id']
        verbose_name = '물품'
        verbose_name_plural = '물품'

    def __str__(self):
        return self.name

    @property
    def is_equipment(self):
        return self.item_type == self.ItemType.EQUIPMENT

    @property
    def is_consumable(self):
        return self.item_type == self.ItemType.CONSUMABLE

    @property
    def available_unit_count(self):
        if not self.is_equipment:
            return 0
        return self.units.filter(status=EquipmentUnit.Status.AVAILABLE).count()

    @property
    def borrowed_unit_count(self):
        if not self.is_equipment:
            return 0
        return self.units.filter(status=EquipmentUnit.Status.BORROWED).count()

    @property
    def broken_unit_count(self):
        if not self.is_equipment:
            return 0
        return self.units.filter(status=EquipmentUnit.Status.BROKEN).count()

    @property
    def lost_unit_count(self):
        if not self.is_equipment:
            return 0
        return self.units.filter(status=EquipmentUnit.Status.LOST).count()


class EquipmentUnit(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = 'available', '대여 가능'
        BORROWED = 'borrowed', '대여 중'
        BROKEN = 'broken', '고장'
        LOST = 'lost', '분실'
        INACTIVE = 'inactive', '비활성'

    item = models.ForeignKey(
        Item,
        verbose_name='물품',
        related_name='units',
        on_delete=models.CASCADE,
    )
    number = models.PositiveIntegerField('번호')
    status = models.CharField('상태', max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    created_at = models.DateTimeField('생성일', auto_now_add=True)
    updated_at = models.DateTimeField('수정일', auto_now=True)

    class Meta:
        ordering = ['item__name', 'number']
        unique_together = [('item', 'number')]
        verbose_name = '비품 개별 번호'
        verbose_name_plural = '비품 개별 번호'

    def __str__(self):
        return f'{self.item.name} {self.number}번'
