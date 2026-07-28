from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from .models import Category, EquipmentUnit, Item


class ItemManagementTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(student_id='20252731', name='조세진', password='1')
        self.client.login(student_id='20252731', password='1')

    def test_create_equipment_creates_units(self):
        category = Category.objects.create(name='전자기기')
        response = self.client.post(reverse('items:create'), {
            'name': '보조배터리',
            'category': category.id,
            'item_type': Item.ItemType.EQUIPMENT,
            'total_quantity': 3,
            'current_quantity': '',
        })
        self.assertRedirects(response, reverse('items:item_list'))
        item = Item.objects.get(name='보조배터리')
        self.assertEqual(item.units.count(), 3)
        self.assertEqual(list(item.units.values_list('number', flat=True)), [1, 2, 3])

    def test_create_consumable_saves_quantities(self):
        response = self.client.post(reverse('items:create'), {
            'name': 'A4용지',
            'category': '',
            'item_type': Item.ItemType.CONSUMABLE,
            'total_quantity': 500,
            'current_quantity': 320,
        })
        self.assertRedirects(response, reverse('items:item_list'))
        item = Item.objects.get(name='A4용지')
        self.assertEqual(item.current_quantity, 320)
        self.assertEqual(item.total_quantity, 500)

    def test_delete_category_keeps_item_uncategorized(self):
        category = Category.objects.create(name='생활')
        item = Item.objects.create(name='우산', item_type=Item.ItemType.EQUIPMENT, category=category, total_quantity=1)
        EquipmentUnit.objects.create(item=item, number=1)
        response = self.client.post(reverse('items:category_delete', args=[category.pk]))
        self.assertRedirects(response, reverse('items:category_list'))
        item.refresh_from_db()
        self.assertIsNone(item.category)
