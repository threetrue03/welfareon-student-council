from django.contrib import admin

from .models import Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'name', 'fee_status', 'updated_at')
    list_filter = ('fee_status',)
    search_fields = ('student_id', 'name')
