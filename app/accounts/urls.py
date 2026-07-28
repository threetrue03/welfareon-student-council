from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('password/find/', views.password_find_view, name='password_find'),
    path('password/reset/', views.password_reset_view, name='password_reset'),
    path('logout/', views.logout_view, name='logout'),
    path('end-shift/', views.end_shift_view, name='end_shift'),
    path('change-password/', views.change_password_view, name='change_password'),
]
