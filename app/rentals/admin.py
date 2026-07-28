from django.contrib import admin

from .models import RentalRecord, ReturnRecord


@admin.register(RentalRecord)
class RentalRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'item', 'unit', 'borrowed_at', 'due_date', 'status', 'worker')
    list_filter = ('status', 'due_date')
    search_fields = ('student__name', 'student__student_id', 'item__name', 'unit__number')


@admin.register(ReturnRecord)
class ReturnRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'item', 'unit', 'returned_at', 'return_status', 'worker')
    list_filter = ('return_status', 'returned_at')
    search_fields = ('student__name', 'student__student_id', 'item__name', 'unit__number')
