from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.db import transaction
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from datetime import timedelta

from .models import Library
from .utils import generate_random_password
import core.email_service


# ==========================================================
# 🔐 SIGN IN
# ==========================================================
def view_signin(request):

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        remember_me = request.POST.get("remember_me")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            # Remember Me Logic
            if not remember_me:
                request.session.set_expiry(0)
            else:
                request.session.set_expiry(timedelta(days=7))

            messages.success(request, "Login Successful! Welcome back.")
            return redirect("accounts:admin_dashboard")

        else:
            messages.error(request, "Invalid User ID or Password.")

    return render(request, "accounts/sign_in.html")


# ==========================================================
# 🚪 LOGOUT
# ==========================================================
def view_logout(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect("accounts:signin")


# ==========================================================
# 📝 REGISTER LIBRARY
# ==========================================================
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

        if User.objects.filter(username=institute_email).exists():
            messages.error(request, "Account already exists with this email.")
            return redirect("accounts:signup")

        try:
            with transaction.atomic():

                raw_password = generate_random_password()

                user = User.objects.create_user(
                    username=institute_email,
                    email=institute_email,
                    password=raw_password
                )

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

            # Send credentials email
            email_sent = core.email_service.send_account_credentials(
                institute_email,
                raw_password
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


# ==========================================================
# 🔑 FORGOT PASSWORD
# Auto-generate new password & email it
# ==========================================================
def view_forget_password(request):

    if request.method == "POST":
        email = request.POST.get("email")

        user = User.objects.filter(email=email).first()

        if user:
            new_password = generate_random_password()

            user.set_password(new_password)
            user.save()

            # ✅ FIXED CALL (Correct parameters)
            email_sent = core.email_service.send_password_reset_email(
                user,
                new_password
            )

            if email_sent:
                messages.success(
                    request,
                    "A new password has been sent to your email."
                )
                return redirect("accounts:signin")
            else:
                messages.warning(
                    request,
                    "Password updated but email could not be sent."
                )

        else:
            # Security best practice
            messages.success(
                request,
                "If this email exists, a new password has been sent."
            )

    return render(request, "accounts/forget_password.html")


# ==========================================================
# 🖥 ADMIN DASHBOARD
# ==========================================================
@login_required
def admin(request):
    return render(request, "dashboards/admin_dashboard.html")