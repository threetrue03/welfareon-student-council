from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.utils import timezone

from .forms import ChangeOwnPasswordForm, LoginForm, PasswordFindForm, PasswordResetByIdentityForm
from .models import ShiftRecord, User
from dashboard.google_sheets import schedule_google_sheet_sync

PASSWORD_RESET_SESSION_KEY = 'password_reset_user_id'


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if not ShiftRecord.objects.filter(user=user, ended_at__isnull=True).exists():
                ShiftRecord.objects.create(user=user)
                schedule_google_sheet_sync('근무 시작')
            messages.success(request, '로그인되었습니다.')
            return redirect('dashboard:home')
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def password_find_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')

    if request.method == 'POST':
        form = PasswordFindForm(request.POST)
        if form.is_valid():
            request.session[PASSWORD_RESET_SESSION_KEY] = form.get_user().pk
            return redirect('accounts:password_reset')
    else:
        form = PasswordFindForm()

    return render(request, 'accounts/password_find.html', {'form': form})


def password_reset_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')

    user_id = request.session.get(PASSWORD_RESET_SESSION_KEY)
    if not user_id:
        messages.error(request, '먼저 이름과 학번으로 계정을 확인해 주세요.')
        return redirect('accounts:password_find')

    user = get_object_or_404(User, pk=user_id)

    if request.method == 'POST':
        form = PasswordResetByIdentityForm(user, request.POST)
        if form.is_valid():
            form.save()
            request.session.pop(PASSWORD_RESET_SESSION_KEY, None)
            messages.success(request, '비밀번호가 변경되었습니다. 새 비밀번호로 로그인해 주세요.')
            return redirect('accounts:login')
    else:
        form = PasswordResetByIdentityForm(user)

    return render(request, 'accounts/password_reset.html', {
        'form': form,
        'target_user': user,
    })


@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, '로그아웃되었습니다.')
    return redirect('accounts:login')


@require_POST
def end_shift_view(request):
    if request.user.is_authenticated:
        open_shift = (
            ShiftRecord.objects
            .filter(user=request.user, ended_at__isnull=True)
            .order_by('-started_at')
            .first()
        )
        if open_shift:
            open_shift.ended_at = timezone.now()
            open_shift.save(update_fields=['ended_at', 'updated_at'])
            schedule_google_sheet_sync('근무 종료')
    logout(request)
    messages.success(request, '근무가 종료되어 자동 로그아웃되었습니다.')
    return redirect('accounts:login')


@require_POST
def change_password_view(request):
    if not request.user.is_authenticated:
        messages.error(request, '로그인이 필요합니다.')
        return redirect('accounts:login')
    form = ChangeOwnPasswordForm(request.user, request.POST)
    if form.is_valid():
        form.save()
        update_session_auth_hash(request, request.user)
        messages.success(request, '비밀번호가 변경되었습니다.')
    else:
        error = form.non_field_errors().as_text()
        if not error:
            for field_errors in form.errors.values():
                if field_errors:
                    error = field_errors[0]
                    break
        messages.error(request, error or '비밀번호를 변경하지 못했습니다.')
    return redirect(request.META.get('HTTP_REFERER') or 'dashboard:home')
