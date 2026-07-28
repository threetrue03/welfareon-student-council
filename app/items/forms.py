from django import forms

from .models import Category, EquipmentUnit, Item


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': '예: 전자기기, 생활, 잡화/문서'}),
        }


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ['name', 'location', 'category', 'item_type', 'total_quantity', 'current_quantity']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': '예: 보조배터리, 우산, A4용지'}),
            'location': forms.TextInput(attrs={'placeholder': '예: 학생회실 선반 1칸, 창고 A-2'}),
            'item_type': forms.RadioSelect(),
            'total_quantity': forms.NumberInput(attrs={'min': 0, 'placeholder': '전체 수량'}),
            'current_quantity': forms.NumberInput(attrs={'min': 0, 'placeholder': '현재 수량'}),
        }
        labels = {
            'name': '물품 이름',
            'location': '물품 위치',
            'category': '카테고리',
            'item_type': '물품 유형',
            'total_quantity': '전체 수량',
            'current_quantity': '현재 수량',
        }

    def clean(self):
        cleaned_data = super().clean()
        item_type = cleaned_data.get('item_type')
        total_quantity = cleaned_data.get('total_quantity') or 0
        current_quantity = cleaned_data.get('current_quantity')

        if item_type == Item.ItemType.EQUIPMENT:
            if total_quantity < 1:
                self.add_error('total_quantity', '비품은 전체 수량을 1개 이상 입력해야 합니다.')
            cleaned_data['current_quantity'] = None

        if item_type == Item.ItemType.CONSUMABLE:
            if total_quantity < 0:
                self.add_error('total_quantity', '전체 수량은 0 이상이어야 합니다.')
            if current_quantity is None:
                self.add_error('current_quantity', '소모품은 현재 수량을 입력해야 합니다.')
            elif current_quantity > total_quantity:
                self.add_error('current_quantity', '현재 수량은 전체 수량보다 클 수 없습니다.')

        return cleaned_data


class EquipmentUnitStatusForm(forms.Form):
    status = forms.ChoiceField(label='상태', choices=EquipmentUnit.Status.choices)
