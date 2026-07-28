from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import SetPasswordForm

from .models import User
from .permissions import is_admin_student_id


class LoginForm(forms.Form):
    student_id = forms.CharField(
        label='학번',
        max_length=20,
        widget=forms.TextInput(attrs={'placeholder': '학번을 입력하세요'}),
    )
    password = forms.CharField(
        label='비밀번호',
        widget=forms.PasswordInput(attrs={'placeholder': '비밀번호를 입력하세요'}),
    )

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.user = None

    def clean(self):
        cleaned_data = super().clean()
        student_id = cleaned_data.get('student_id')
        password = cleaned_data.get('password')
        if student_id and password:
            self.user = authenticate(self.request, username=student_id.strip(), password=password)
            if self.user is None:
                raise forms.ValidationError('학번 또는 비밀번호가 올바르지 않습니다.')
            if not self.user.is_active:
                raise forms.ValidationError('비활성화된 계정입니다. 관리자에게 문의하세요.')
        return cleaned_data

    def get_user(self):
        return self.user


class PasswordFindForm(forms.Form):
    name = forms.CharField(
        label='이름',
        max_length=50,
        widget=forms.TextInput(attrs={'placeholder': '가입할 때 입력한 이름'}),
    )
    student_id = forms.CharField(
        label='학번',
        max_length=20,
        widget=forms.TextInput(attrs={'placeholder': '학번을 입력하세요'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        student_id = cleaned_data.get('student_id')
        if student_id and is_admin_student_id(student_id.strip()):
            self.add_error('student_id', '관리자 학번입니다.')
            return cleaned_data
        if name and student_id:
            self.user = User.objects.filter(name=name.strip(), student_id=student_id.strip()).first()
            if self.user is None:
                raise forms.ValidationError('입력한 정보와 일치하는 계정을 찾을 수 없습니다.')
            if not self.user.is_active:
                raise forms.ValidationError('비활성화된 계정입니다. 관리자에게 문의하세요.')
        return cleaned_data

    def get_user(self):
        return self.user


class PasswordResetByIdentityForm(SetPasswordForm):
    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        self.fields['new_password1'].label = '새 비밀번호'
        self.fields['new_password1'].widget.attrs.update({'placeholder': '새 비밀번호를 입력하세요'})
        self.fields['new_password2'].label = '새 비밀번호 확인'
        self.fields['new_password2'].widget.attrs.update({'placeholder': '새 비밀번호를 다시 입력하세요'})

    def save(self, commit=True):
        password = self.cleaned_data.get('new_password1', '')
        self.user.set_password(password)
        self.user.visible_password = password
        if commit:
            self.user.save(update_fields=['password', 'visible_password'])
        return self.user


class ChangeOwnPasswordForm(forms.Form):
    current_password = forms.CharField(
        label='기존 비밀번호',
        widget=forms.PasswordInput(attrs={'placeholder': '기존 비밀번호를 입력하세요'}),
    )
    new_password1 = forms.CharField(
        label='새 비밀번호',
        widget=forms.PasswordInput(attrs={'placeholder': '새 비밀번호를 입력하세요'}),
    )
    new_password2 = forms.CharField(
        label='새 비밀번호 확인',
        widget=forms.PasswordInput(attrs={'placeholder': '새 비밀번호를 다시 입력하세요'}),
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_current_password(self):
        current_password = self.cleaned_data.get('current_password', '')
        if not self.user.check_password(current_password):
            raise forms.ValidationError('기존 비밀번호가 일치하지 않습니다.')
        return current_password

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')
        if password1 and password2 and password1 != password2:
            self.add_error('new_password2', '새 비밀번호 확인이 일치하지 않습니다.')
        return cleaned_data

    def save(self):
        password = self.cleaned_data['new_password1']
        self.user.set_password(password)
        self.user.visible_password = password
        self.user.save(update_fields=['password', 'visible_password'])
        return self.user
