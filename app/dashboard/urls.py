from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_view, name='home'),
    path('rentals/return/', RedirectView.as_view(pattern_name='rentals:return', permanent=False), name='return'),
    path('lookup/students/', views.student_lookup_view, name='student_lookup'),
    path('lookup/items/', views.item_lookup_view, name='item_lookup'),
    path('settings/', views.settings_view, name='settings'),
    path('settings/rental/', views.rental_settings_view, name='rental_settings'),
    path('settings/blacklist/', views.blacklist_settings_view, name='blacklist_settings'),
    path('admin/shifts/', views.shift_records_view, name='shift_records'),
    path('admin/google-sheets/', views.google_sheets_view, name='google_sheets'),
]
