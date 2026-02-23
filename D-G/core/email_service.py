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
        /* ── Reset & Base ── */
        *, *::before, *::after {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            background-color: #eef1f5;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            color: #333333;
            padding: 48px 20px;
            -webkit-text-size-adjust: 100%;
            -ms-text-size-adjust: 100%;
        }}

        /* ── Outer Wrapper ── */
        .email-wrapper {{
            max-width: 620px;
            margin: 0 auto;
            background-color: #ffffff;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 8px 40px rgba(0, 0, 0, 0.10), 0 2px 8px rgba(0,0,0,0.06);
        }}

        /* ── Header ── */
        .email-header {{
            background: linear-gradient(135deg, #1e3a5f 0%, #2c3e50 40%, #4a6fa5 100%);
            padding: 44px 48px 40px;
            text-align: center;
            position: relative;
            overflow: hidden;
        }}
        .email-header::before {{
            content: '';
            position: absolute;
            top: -60px;
            right: -60px;
            width: 200px;
            height: 200px;
            background: rgba(255,255,255,0.04);
            border-radius: 50%;
        }}
        .email-header::after {{
            content: '';
            position: absolute;
            bottom: -80px;
            left: -40px;
            width: 240px;
            height: 240px;
            background: rgba(255,255,255,0.03);
            border-radius: 50%;
        }}
        .email-header h1 {{
            color: #ffffff;
            font-size: 28px;
            font-weight: 700;
            letter-spacing: 0.6px;
            text-shadow: 0 1px 4px rgba(0,0,0,0.2);
            position: relative;
            z-index: 1;
        }}
        .email-header p {{
            color: #a8c4e0;
            font-size: 11px;
            margin-top: 8px;
            letter-spacing: 2.5px;
            text-transform: uppercase;
            font-weight: 500;
            position: relative;
            z-index: 1;
        }}
        .header-badge {{
            display: inline-block;
            margin-top: 14px;
            background: rgba(255,255,255,0.12);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 20px;
            padding: 4px 14px;
            font-size: 11px;
            color: #c8ddf0;
            letter-spacing: 0.5px;
            position: relative;
            z-index: 1;
        }}

        /* ── Body ── */
        .email-body {{
            padding: 44px 48px;
        }}
        .email-body p {{
            font-size: 15px;
            line-height: 1.75;
            color: #4a4a4a;
            margin-bottom: 18px;
        }}
        .email-body p:last-child {{
            margin-bottom: 0;
        }}

        /* ── Greeting ── */
        .greeting {{
            font-size: 22px !important;
            font-weight: 700;
            color: #1e3a5f !important;
            margin-bottom: 10px !important;
            letter-spacing: -0.3px;
        }}

        /* ── Credential Box ── */
        .credential-box {{
            background: linear-gradient(135deg, #f0f5ff 0%, #e8f0fe 100%);
            border-left: 5px solid #4a6fa5;
            border-radius: 10px;
            padding: 22px 26px;
            margin: 26px 0;
            box-shadow: 0 2px 12px rgba(74, 111, 165, 0.10);
        }}
        .credential-box p {{
            font-size: 14px;
            color: #2c3e50;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .credential-box p:last-child {{
            margin-bottom: 0;
        }}
        .credential-box strong {{
            color: #1e3a5f;
            font-weight: 700;
            min-width: 110px;
            display: inline-block;
        }}
        .credential-box span {{
            font-family: 'Courier New', 'Lucida Console', monospace;
            background-color: #ffffff;
            border: 1px solid #c5d5f0;
            padding: 4px 12px;
            border-radius: 6px;
            font-size: 14px;
            color: #1a3a5c;
            font-weight: 600;
            letter-spacing: 0.3px;
            box-shadow: inset 0 1px 3px rgba(0,0,0,0.06);
            word-break: break-all;
        }}

        /* ── Warning / Info Box ── */
        .warning-box {{
            background: linear-gradient(135deg, #fffbf0 0%, #fff8e1 100%);
            border-left: 5px solid #e5a000;
            border-radius: 10px;
            padding: 16px 22px;
            margin: 22px 0;
            font-size: 14px;
            color: #6b4f00;
            line-height: 1.6;
            box-shadow: 0 2px 8px rgba(229, 160, 0, 0.10);
        }}
        .warning-box strong {{
            font-weight: 700;
            color: #5a4000;
        }}

        .danger-box {{
            background: linear-gradient(135deg, #fff5f5 0%, #fee8e8 100%);
            border-left: 5px solid #e53e3e;
            border-radius: 10px;
            padding: 16px 22px;
            margin: 22px 0;
            font-size: 14px;
            color: #742a2a;
            line-height: 1.6;
            box-shadow: 0 2px 8px rgba(229, 62, 62, 0.10);
        }}
        .danger-box strong {{
            font-weight: 700;
            color: #63171b;
        }}

        .success-box {{
            background: linear-gradient(135deg, #f0faf5 0%, #e6f7ee 100%);
            border-left: 5px solid #38a169;
            border-radius: 10px;
            padding: 16px 22px;
            margin: 22px 0;
            font-size: 14px;
            color: #1d4731;
            line-height: 1.6;
            box-shadow: 0 2px 8px rgba(56, 161, 105, 0.10);
        }}

        /* ── CTA Button ── */
        .btn-container {{
            text-align: center;
            margin: 36px 0 28px;
        }}
        .btn {{
            display: inline-block;
            background: linear-gradient(135deg, #4a6fa5, #2c3e50);
            color: #ffffff !important;
            text-decoration: none;
            padding: 15px 42px;
            border-radius: 50px;
            font-size: 15px;
            font-weight: 700;
            letter-spacing: 0.5px;
            box-shadow: 0 6px 20px rgba(44, 62, 80, 0.30), 0 2px 6px rgba(74, 111, 165, 0.25);
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }}
        .btn:hover {{
            box-shadow: 0 10px 28px rgba(44, 62, 80, 0.38), 0 4px 10px rgba(74, 111, 165, 0.30);
            transform: translateY(-1px);
        }}
        .fallback-link {{
            font-size: 12px;
            color: #999;
            word-break: break-all;
            text-align: center;
            margin-top: 14px;
        }}
        .fallback-link a {{
            color: #4a6fa5;
            text-decoration: underline;
        }}

        /* ── Divider ── */
        .divider {{
            border: none;
            border-top: 1px solid #e8edf2;
            margin: 32px 0;
        }}

        /* ── Stats / Info Strip ── */
        .info-strip {{
            display: flex;
            gap: 12px;
            margin: 24px 0;
        }}
        .info-strip-item {{
            flex: 1;
            background: #f7f9fc;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 14px 16px;
            text-align: center;
        }}
        .info-strip-item .info-label {{
            font-size: 11px;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 4px;
        }}
        .info-strip-item .info-value {{
            font-size: 15px;
            font-weight: 700;
            color: #2c3e50;
        }}

        /* ── Footer ── */
        .email-footer {{
            background: linear-gradient(180deg, #f4f7fb 0%, #eef1f5 100%);
            padding: 28px 48px;
            text-align: center;
            border-top: 1px solid #e2e8f0;
        }}
        .email-footer p {{
            font-size: 12px;
            color: #9aa5b4;
            line-height: 1.8;
        }}
        .email-footer a {{
            color: #4a6fa5;
            text-decoration: none;
            font-weight: 500;
        }}
        .email-footer a:hover {{
            text-decoration: underline;
        }}
        .footer-logo {{
            font-size: 14px;
            font-weight: 700;
            color: #4a6fa5;
            margin-bottom: 8px;
            letter-spacing: 0.3px;
        }}

        /* ── Utilities ── */
        .highlight {{
            color: #4a6fa5;
            font-weight: 700;
        }}
        .muted {{
            color: #888;
            font-size: 13px;
        }}

        /* ── Responsive ── */
        @media only screen and (max-width: 640px) {{
            body {{
                padding: 20px 12px;
            }}
            .email-header {{
                padding: 32px 28px;
            }}
            .email-header h1 {{
                font-size: 22px;
            }}
            .email-body {{
                padding: 32px 28px;
            }}
            .email-footer {{
                padding: 22px 28px;
            }}
            .credential-box {{
                padding: 18px 18px;
            }}
            .credential-box p {{
                flex-direction: column;
                align-items: flex-start;
                gap: 4px;
            }}
            .btn {{
                padding: 14px 32px;
                font-size: 14px;
                display: block;
                width: 100%;
                text-align: center;
            }}
            .info-strip {{
                flex-direction: column;
            }}
        }}
    </style>
</head>
<body>
    <div class="email-wrapper">
        <div class="email-header">
            <h1>📚 Dooars Granthika</h1>
            <p>Library Management System</p>
            <span class="header-badge">✦ Official Notification</span>
        </div>
        <div class="email-body">
            {body_content}
        </div>
        <div class="email-footer">
            <div class="footer-logo">Dooars Granthika</div>
            <p>
                &copy; 2025 Dooars Granthika. All rights reserved.<br/>
                This is an automated message — please do not reply directly.<br/>
                <a href="#">Unsubscribe</a> &nbsp;&middot;&nbsp; <a href="#">Privacy Policy</a> &nbsp;&middot;&nbsp; <a href="#">Support</a>
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
def send_account_credentials(email, password, Username):
    subject = "Your Library Account Credentials"

    plain_message = f"""
Welcome to Dooars Granthika!
Your account has been created successfully.
Login Username: {Username}
Password: {password}
Please login and change your password immediately.
"""

    body_content = f"""
        <p class="greeting">Welcome aboard! 🎉</p>
        <p>Your account at <span class="highlight">Dooars Granthika</span> has been created successfully. Here are your login credentials to get started:</p>

        <div class="credential-box">
            <p><strong>Login Username:</strong> <span>{Username}</span></p>
            <p><strong>Password:</strong> <span>{password}</span></p>
        </div>

        <div class="warning-box">
            ⚠️ <strong>Action Required:</strong> Please log in and change your password immediately to secure your account.
        </div>

        <hr class="divider"/>

        <p>Once logged in, you'll have access to our full library catalogue, borrowing history, and member resources.</p>
        <p>Happy reading and enjoy exploring our collection! 📖</p>
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
        <p class="greeting">Hello, {user.username}! 👋</p>
        <p>Welcome to the <span class="highlight">Dooars Granthika Library System</span>. We're thrilled to have you as a member!</p>

        <div class="success-box">
            ✅ Your membership is now <strong>active</strong>. You have full access to our library collection and services.
        </div>

        <hr class="divider"/>

        <p>You can now browse our growing catalogue of books and resources, manage your borrowing history, and take advantage of all member benefits.</p>

        <p>If you ever have questions or need assistance, our library team is always happy to help.</p>

        <p style="margin-top: 24px; font-size: 18px;">Happy Reading! 🌟</p>
    """

    html_message = build_html_email("Welcome", body_content)
    return send_basic_email(subject, plain_message, html_message, user.email)

# ==============================
# 3️⃣ Password Reset Email
# ==============================
def send_password_reset_email(user, new_password, lib_name, username):
    subject = "Your New Password - Dooars Granthika"

    plain_message = f"""
Hello {lib_name},

Your password has been reset successfully.

Your username is: {username}
Your new temporary password is: {new_password}

Please log in and change your password immediately.

If you did not request this, please contact support.
"""

    body_content = f"""
        <p class="greeting">Password Reset</p>
        <p>Hello <span class="highlight">{lib_name}</span>, your password has been reset successfully. Use the temporary password below to log in:</p>

        <div class="credential-box">
            <p><strong>Username:</strong> <span>{username}</span></p>
            <p><strong>New Password:</strong> <span>{new_password}</span></p>
        </div>

        <div class="warning-box">
            ⚠️ <strong>Action Required:</strong> Please log in using this password and change it immediately for security reasons.
        </div>

        <div class="danger-box">
            🛡️ <strong>Didn't request this?</strong> If you did not initiate a password reset, please contact our support team immediately as your account may be at risk.
        </div>
    """

    html_message = build_html_email("Password Reset", body_content)

    # ✅ ALWAYS send to email
    return send_basic_email(subject, plain_message, html_message, user.email)