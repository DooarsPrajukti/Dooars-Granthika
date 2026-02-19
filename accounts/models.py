from django.db import models
from django.contrib.auth.models import User

class Library(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    library_name = models.CharField(max_length=255)
    institute_name = models.CharField(max_length=255)
    institute_email = models.EmailField()
    address = models.TextField()
    district = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)

    late_fine = models.DecimalField(max_digits=8, decimal_places=2)
    borrowing_period = models.IntegerField()
    allotted_books = models.IntegerField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.library_name
