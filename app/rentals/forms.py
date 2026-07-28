from django import forms

from .settings_store import MAX_RENTAL_DAYS, MIN_RENTAL_DAYS


class RentalCreateForm(forms.Form):
    memo = forms.CharField(
        label='메모',
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={'placeholder': '선택 입력'}),
    )


class ConsumableIssueForm(forms.Form):
    quantity = forms.IntegerField(
        label='지급 수량',
        min_value=1,
        widget=forms.NumberInput(attrs={'min': 1, 'placeholder': '지급 수량'}),
    )
    memo = forms.CharField(
        label='메모',
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={'placeholder': '선택 입력'}),
    )


class RentalPolicyForm(forms.Form):
    default_due_days = forms.IntegerField(
        label='기본 대여 기간',
        min_value=MIN_RENTAL_DAYS,
        max_value=MAX_RENTAL_DAYS,
        widget=forms.NumberInput(attrs={
            'min': MIN_RENTAL_DAYS,
            'max': MAX_RENTAL_DAYS,
            'placeholder': '7',
        }),
    )
