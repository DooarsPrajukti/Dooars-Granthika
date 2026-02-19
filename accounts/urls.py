from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path('sign_in/', views.view_signin, name='signin'),
    path('sign_up/', views.register_library, name='signup'),
    path('forget_password/', views.view_forget_password, name='forgetpassword'),
    path('admin_dashboard/', views.admin, name='admin_dashboard'),
]
