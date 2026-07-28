from django.urls import path

from . import views

app_name = 'items'

urlpatterns = [
    path('', views.item_list, name='list'),
    path('items/', views.item_list, name='item_list'),
    path('items/new/', views.item_create, name='create'),
    path('items/<int:pk>/edit/', views.item_update, name='update'),
    path('items/<int:pk>/delete/', views.item_delete, name='delete'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/new/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_update, name='category_update'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    path('import/', views.db_import, name='db_import'),
    path('students/', views.student_list, name='student_list'),
    path('students/new/', views.student_create, name='student_create'),
    path('students/<int:pk>/edit/', views.student_update, name='student_update'),
    path('students/<int:pk>/delete/', views.student_delete, name='student_delete'),
    path('student-import/', views.student_db_import, name='student_db_import'),
    path('workers/', views.worker_list, name='worker_list'),
    path('workers/new/', views.worker_create, name='worker_create'),
    path('workers/<int:pk>/edit/', views.worker_update, name='worker_update'),
    path('workers/<int:pk>/delete/', views.worker_delete, name='worker_delete'),
    path('workers/<int:pk>/password/reveal/', views.worker_password_reveal, name='worker_password_reveal'),
    path('worker-import/', views.worker_db_import, name='worker_db_import'),
    path('data-backup/', views.data_backup, name='data_backup'),
]
