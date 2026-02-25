from django.urls import path
from . import views

app_name = 'staff'

urlpatterns = [
    path('',                         views.staff_list,          name='staff_list'),
    path('add/',                     views.staff_add,           name='staff_add'),
    path('<int:pk>/',                views.staff_detail,        name='staff_detail'),
    path('<int:pk>/edit/',           views.staff_edit,          name='staff_edit'),
    path('<int:pk>/delete/',         views.staff_delete,        name='staff_delete'),
    path('<int:pk>/toggle-access/',  views.staff_toggle_access, name='staff_toggle_access'),
]