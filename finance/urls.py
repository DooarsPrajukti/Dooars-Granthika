"""
finance/urls.py

Mount in project urls.py:
    path("finance/", include("finance.urls", namespace="finance")),
"""

from django.urls import path
from . import views

app_name = "finance"

urlpatterns = [
    path("",                                          views.finance_dashboard,      name="dashboard"),
    path("api/stats/",                                views.finance_stats_api,      name="stats_api"),
    path("api/fine/<int:pk>/pay/",                    views.finance_pay_fine,       name="pay_fine"),
    path("api/fine/<int:pk>/waive/",                  views.finance_waive_fine,     name="waive_fine"),
    path("fines/<int:fine_pk>/pay/create-order/",     views.create_razorpay_order,  name="razorpay_create_order"),
    path("fines/<int:fine_pk>/pay/callback/",         views.razorpay_callback,      name="razorpay_callback"),
    path("razorpay/webhook/",                         views.razorpay_webhook,       name="razorpay_webhook"),
]