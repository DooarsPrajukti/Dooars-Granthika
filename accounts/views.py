from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
# Create your views here.

def view_signin(request):
    return render(request, 'accounts/sign_in.html')

def view_signup(request):
    return render(request, 'accounts/sign_up.html')

def view_forget_password(request):
    return render(request, 'accounts/forget_password.html')