from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("sign_in/",          views.view_signin,              name="signin"),
    path("sign_up/",          views.register_library,         name="signup"),
    path("forget_password/",  views.view_forget_password,     name="forgetpassword"),
    path("admin_dashboard/",  views.admin_dashboard,          name="admin_dashboard"),
    path("sign_out/",         views.view_logout,              name="signout"),
    path("settings/",         views.settings_view,            name="settings"),

    # ── First-time library setup (onboarding) ──────────────────
    path("library_setup/",    views.library_setup_view,       name="library_setup"),

    # ── AJAX: regenerate library code ─────────────────────────
    path("library_setup/regen_code/", views.regenerate_library_code, name="regen_code"),

    # path("staff_dashboard/", views.staff_dashboard, name="staff_dashboard"),
]