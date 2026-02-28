
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('authentication/', include('accounts.urls')),
    path("books/", include("books.urls")),
    path("members/", include("members.urls")),
    path("transactions/", include("transactions.urls")),
]
