from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import ShiftRecord, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ['-date_joined']
    list_display = ['student_id', 'name', 'role', 'is_active', 'is_staff', 'date_joined']
    list_filter = ['role', 'is_active', 'is_staff', 'date_joined']
    search_fields = ['student_id', 'name']

    fieldsets = (
        ('기본 정보', {'fields': ('student_id', 'name', 'password')}),
        ('권한', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('날짜 정보', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        ('사용자 생성', {
            'classes': ('wide',),
            'fields': ('student_id', 'name', 'password1', 'password2', 'role', 'is_active', 'is_staff'),
        }),
    )
    readonly_fields = ['last_login', 'date_joined']


@admin.register(ShiftRecord)
class ShiftRecordAdmin(admin.ModelAdmin):
    list_display = ['user', 'started_at', 'ended_at']
    list_filter = ['started_at', 'ended_at']
    search_fields = ['user__student_id', 'user__name']
    readonly_fields = ['created_at', 'updated_at']
