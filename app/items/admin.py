from django.contrib import admin

from .models import Category, EquipmentUnit, Item


class EquipmentUnitInline(admin.TabularInline):
    model = EquipmentUnit
    extra = 0
    fields = ['number', 'status']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at']
    search_fields = ['name', 'description']


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'location', 'item_type', 'category', 'total_quantity', 'current_quantity', 'updated_at']
    list_filter = ['item_type', 'category']
    search_fields = ['name', 'location']
    inlines = [EquipmentUnitInline]


@admin.register(EquipmentUnit)
class EquipmentUnitAdmin(admin.ModelAdmin):
    list_display = ['item', 'number', 'status', 'updated_at']
    list_filter = ['status', 'item']
    search_fields = ['item__name']
