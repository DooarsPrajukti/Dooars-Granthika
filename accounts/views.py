from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import transaction

from django.contrib.auth import authenticate, login, logout
from django.conf import settings
from datetime import timedelta
from .models import Library
from .utils import generate_random_password
from core.email_service import send_account_credentials


def view_signin(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        remember_me = request.POST.get("remember_me")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            # 🔐 Remember Me Logic
            if not remember_me:
                request.session.set_expiry(0)  # Session expires when browser closes
            else:
                request.session.set_expiry(timedelta(days=7))  # 7 days login

            messages.success(request, "Login Successful! Welcome back.")
            return redirect("accounts:admin_dashboard")  # change to your dashboard url name

        else:
            messages.error(request, "Invalid User ID or Password.")

    return render(request, "accounts/sign_in.html")


def view_logout(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect("accounts:signin")


def register_library(request):

    if request.method == "POST":

        library_name = request.POST.get("library_name")
        institute_name = request.POST.get("institute_name")
        institute_email = request.POST.get("institute_email")
        address = request.POST.get("address")
        district = request.POST.get("district")
        state = request.POST.get("state")
        country = request.POST.get("country")
        late_fine = request.POST.get("late_fine")
        borrowing_period = request.POST.get("borrowing_period")
        allotted_books = request.POST.get("allotted_books")

        # Check duplicate
        if User.objects.filter(username=institute_email).exists():
            messages.error(request, "Account already exists with this email.")
            return redirect("accounts:signup")

        try:
            with transaction.atomic():

                # Generate password
                raw_password = generate_random_password()

                # Create user (password auto hashed by Django)
                user = User.objects.create_user(
                    username=institute_email,
                    email=institute_email,
                    password=raw_password
                )

                # Create library profile
                Library.objects.create(
                    user=user,
                    library_name=library_name,
                    institute_name=institute_name,
                    institute_email=institute_email,
                    address=address,
                    district=district,
                    state=state,
                    country=country,
                    late_fine=late_fine,
                    borrowing_period=borrowing_period,
                    allotted_books=allotted_books
                )

            # Send email AFTER DB success
            email_sent = send_account_credentials(
                email=institute_email,
                password=raw_password
            )

            if email_sent:
                messages.success(request, "Account created! Check your email.")
            else:
                messages.warning(
                    request,
                    "Account created but email could not be sent."
                )

            return redirect("accounts:signin")

        except Exception as e:
            print("Registration error:", e)
            messages.error(request, "Something went wrong.")
            return redirect("accounts:signup")

    return render(request, "accounts/sign_up.html")


# def view_signup(request):
#     return render(request, 'accounts/sign_up.html')


# ==========================================================
# 🔑 FORGOT PASSWORD
# Auto-generate new password & email it
# ==========================================================
def view_forget_password(request):

    if request.method == "POST":
        email = request.POST.get("email")

        try:
            user = User.objects.get(email=email)

            # Generate new password
            new_password = generate_random_password()

            # Set new password (auto hashed)
            user.set_password(new_password)
            user.save()

            # Send email with new password
            email_sent = send_account_credentials(
                email=email,
                password=new_password
            )

            if email_sent:
                messages.success(
                    request,
                    "A new password has been sent to your email."
                )
            else:
                messages.warning(
                    request,
                    "Password updated but email could not be sent."
                )

        except User.DoesNotExist:
            # Do not reveal if email exists (security best practice)
            messages.success(
                request,
                "If this email exists, a new password has been sent."
            )

    return render(request, "accounts/forget_password.html")

def admin(request):
    return render(request, 'dashboards/admin_dashboard.html')