from django.core.mail import send_mail
from django.conf import settings


def send_account_credentials(email, password):
    """
    Send login credentials to new account creator
    """

    subject = "Your Library Account Credentials"

    message = f"""
Welcome to Dooars Granthika!

Your account has been created successfully.

Login Email: {email}
Password: {password}

Please login and change your password immediately.
"""

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        return True

    except Exception as e:
        print("Email sending failed:", e)
        return False
