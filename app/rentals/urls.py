from django.urls import path

from . import views

app_name = 'rentals'

urlpatterns = [
    path('borrow/', views.borrow_view, name='borrow'),
    path('return/', views.return_view, name='return'),
    path('api/students/search/', views.student_search_api, name='student_search_api'),
    path('records/rentals/', views.rental_records_view, name='rental_records'),
    path('records/returns/', views.return_records_view, name='return_records'),
]
