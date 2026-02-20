from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.urls import reverse

# ==============================
# Shared HTML Email Base
# ==============================
def build_html_email(title, body_content):
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <title>{title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background-color: #f4f6f8;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            color: #333333;
            padding: 40px 20px;
        }}
        .email-wrapper {{
            max-width: 600px;
            margin: 0 auto;
            background-color: #ffffff;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        }}
        .email-header {{
            background: linear-gradient(135deg, #2c3e50, #4a6fa5);
            padding: 36px 40px;
            text-align: center;
        }}
        .email-header h1 {{
            color: #ffffff;
            font-size: 26px;
            font-weight: 700;
            letter-spacing: 0.5px;
        }}
        .email-header p {{
            color: #c8d6e5;
            font-size: 13px;
            margin-top: 6px;
            letter-spacing: 1px;
            text-transform: uppercase;
        }}
        .email-body {{
            padding: 40px;
        }}
        .email-body p {{
            font-size: 15px;
            line-height: 1.7;
            color: #555555;
            margin-bottom: 16px;
        }}
        .credential-box {{
            background-color: #f0f4ff;
            border-left: 4px solid #4a6fa5;
            border-radius: 8px;
            padding: 20px 24px;
            margin: 24px 0;
        }}
        .credential-box p {{
            font-size: 14px;
            color: #333;
            margin-bottom: 8px;
        }}
        .credential-box p:last-child {{ margin-bottom: 0; }}
        .credential-box strong {{
            color: #2c3e50;
            font-weight: 600;
        }}
        .credential-box span {{
            font-family: 'Courier New', monospace;
            background-color: #dce6f5;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 14px;
            color: #1a3a5c;
        }}
        .warning-box {{
            background-color: #fff8e1;
            border-left: 4px solid #f0a500;
            border-radius: 8px;
            padding: 14px 20px;
            margin: 20px 0;
            font-size: 14px;
            color: #7a5c00;
        }}
        .btn-container {{
            text-align: center;
            margin: 32px 0;
        }}
        .btn {{
            display: inline-block;
            background: linear-gradient(135deg, #4a6fa5, #2c3e50);
            color: #ffffff !important;
            text-decoration: none;
            padding: 14px 36px;
            border-radius: 50px;
            font-size: 15px;
            font-weight: 600;
            letter-spacing: 0.4px;
            box-shadow: 0 4px 12px rgba(74, 111, 165, 0.35);
        }}
        .fallback-link {{
            font-size: 13px;
            color: #888;
            word-break: break-all;
            text-align: center;
            margin-top: 12px;
        }}
        .fallback-link a {{
            color: #4a6fa5;
            text-decoration: none;
        }}
        .divider {{
            border: none;
            border-top: 1px solid #eaeaea;
            margin: 30px 0;
        }}
        .email-footer {{
            background-color: #f9fafb;
            padding: 24px 40px;
            text-align: center;
            border-top: 1px solid #eaeaea;
        }}
        .email-footer p {{
            font-size: 12px;
            color: #aaaaaa;
            line-height: 1.6;
        }}
        .email-footer a {{
            color: #4a6fa5;
            text-decoration: none;
        }}
        .highlight {{
            color: #4a6fa5;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="email-wrapper">
        <div class="email-header">
            <h1>📚 Dooars Granthika</h1>
            <p>Library Management System</p>
        </div>
        <div class="email-body">
            {body_content}
        </div>
        <div class="email-footer">
            <p>
                &copy; 2025 Dooars Granthika. All rights reserved.<br/>
                This is an automated message — please do not reply directly.<br/>
                <a href="#">Unsubscribe</a> &nbsp;|&nbsp; <a href="#">Privacy Policy</a>
            </p>
        </div>
    </div>
</body>
</html>
"""

# ==============================
# Basic Email Sender Function
# ==============================
def send_basic_email(subject, plain_message, html_message, recipient):
    try:
        email = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient],
        )
        email.attach_alternative(html_message, "text/html")
        email.send(fail_silently=False)
        return True
    except Exception as e:
        print("Email sending failed:", e)
        return False

# ==============================
# 1️⃣ Account Credentials Email
# ==============================
def send_account_credentials(email, password):
    subject = "Your Library Account Credentials"

    plain_message = f"""
Welcome to Dooars Granthika!
Your account has been created successfully.
Login Email: {email}
Password: {password}
Please login and change your password immediately.
"""

    body_content = f"""
        <p>Welcome to <span class="highlight">Dooars Granthika</span>! 🎉</p>
        <p>Your account has been created successfully. Below are your login credentials:</p>

        <div class="credential-box">
            <p><strong>Login Email:</strong> <span>{email}</span></p>
            <p><strong>Password:</strong> <span>{password}</span></p>
        </div>

        <div class="warning-box">
            ⚠️ <strong>Important:</strong> Please log in and change your password immediately for security.
        </div>

        <p>Happy reading and enjoy exploring our library collection!</p>
    """

    html_message = build_html_email("Account Credentials", body_content)
    return send_basic_email(subject, plain_message, html_message, email)

# ==============================
# 2️⃣ Welcome Email
# ==============================
def send_welcome_email(user):
    subject = "Welcome to Dooars Granthika"

    plain_message = f"""
Hello {user.username},
Welcome to Dooars Granthika Library System.
We are happy to have you with us.
Happy Reading!
"""

    body_content = f"""
        <p>Hello <span class="highlight">{user.username}</span>,</p>
        <p>Welcome to the <strong>Dooars Granthika Library System</strong>! 📖</p>
        <p>We're thrilled to have you as a member. You now have access to our growing collection of books, resources, and library services.</p>

        <hr class="divider"/>

        <p>Start exploring today and make the most of your membership. If you have any questions, feel free to reach out to our library team.</p>
        <p style="margin-top: 20px;">Happy Reading! 🌟</p>
    """

    html_message = build_html_email("Welcome", body_content)
    return send_basic_email(subject, plain_message, html_message, user.email)

# ==============================
# 3️⃣ Password Reset Email
# ==============================
def send_password_reset_email(request, user):
    subject = "Reset Your Password - Dooars Granthika"

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    reset_link = request.build_absolute_uri(
        reverse("password_reset_confirm", kwargs={
            "uidb64": uid,
            "token": token
        })
    )

    plain_message = f"""
Hello {user.username},
Click the link below to reset your password:
{reset_link}
If you did not request this, please ignore this email.
"""

    body_content = f"""
        <p>Hello <span class="highlight">{user.username}</span>,</p>
        <p>We received a request to reset the password for your Dooars Granthika account.</p>
        <p>Click the button below to set a new password. This link is valid for a limited time.</p>

        <div class="btn-container">
            <a href="{reset_link}" class="btn">🔐 Reset My Password</a>
        </div>

        <p class="fallback-link">
            If the button doesn't work, copy and paste this link into your browser:<br/>
            <a href="{reset_link}">{reset_link}</a>
        </p>

        <hr class="divider"/>

        <div class="warning-box">
            🛡️ If you did not request a password reset, please ignore this email. Your account remains secure.
        </div>
    """

    html_message = build_html_email("Password Reset", body_content)
    return send_basic_email(subject, plain_message, html_message, user.email)