from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.urls import reverse
from django.utils import timezone


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

        /* ── Warning / Info / Danger / Success Boxes ── */
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
        .success-box strong {{
            font-weight: 700;
            color: #1a3d2b;
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
    return send_basic_email(subject, plain_message, html_message, user.email)


# ==============================
# 4️⃣ Member Registration Confirmation Email
# ==============================
def send_member_confirmation_email(member):
    subject = "Membership Confirmed – Your Member ID | Dooars Granthika"

    plain_message = f"""
Hello {member.full_name},

Congratulations! Your membership at Dooars Granthika has been confirmed.

Your Member ID: {member.member_id}
Registered On:  {member.created_at.strftime('%d %b %Y') if member.created_at else 'N/A'}

Please keep your Member ID safe — you will need it for borrowing books,
visiting the library, and any future correspondence.

Happy Reading!
Dooars Granthika
"""

    phone_row = (
        f'<p><strong>Phone:</strong> <span>{member.phone}</span></p>'
        if getattr(member, 'phone', None) else ''
    )

    body_content = f"""
        <p class="greeting">Membership Confirmed! 🎊</p>
        <p>Hello <span class="highlight">{member.full_name}</span>, congratulations! Your membership at <span class="highlight">Dooars Granthika Library</span> has been officially confirmed.</p>

        <div class="credential-box">
            <p><strong>Member ID:</strong> <span>{member.member_id}</span></p>
            <p><strong>Full Name:</strong> <span>{member.full_name}</span></p>
            <p><strong>Registered On:</strong> <span>{member.created_at.strftime('%d %b %Y') if member.created_at else 'N/A'}</span></p>
            {phone_row}
        </div>

        <div class="success-box">
            ✅ Your membership is now <strong>active</strong>. Please keep your <strong>Member ID</strong> safe — you will need it for borrowing books, library visits, and all future correspondence.
        </div>

        <div class="info-strip">
            <div class="info-strip-item">
                <div class="info-label">Member ID</div>
                <div class="info-value">{member.member_id}</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">Status</div>
                <div class="info-value" style="color: #38a169;">Active ✓</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">Role</div>
                <div class="info-value" style="font-size:13px;">{member.get_role_display()}</div>
            </div>
        </div>

        <hr class="divider"/>

        <p>You can now borrow books from our catalogue, track your borrowing history, and access all member benefits. Simply quote your <span class="highlight">Member ID</span> at the library counter or when contacting us.</p>
        <p style="margin-top: 24px; font-size: 18px;">Welcome to the family — Happy Reading! 📚</p>
    """

    html_message = build_html_email("Membership Confirmation", body_content)
    return send_basic_email(subject, plain_message, html_message, member.email)


# ==============================
# 5️⃣ Member Reactivation Email
# ==============================
def send_member_reactivation_email(member):
    subject = "Your Library Membership Has Been Reactivated | Dooars Granthika"

    plain_message = f"""
Hello {member.full_name},

Great news! Your membership at Dooars Granthika has been reactivated.

Member ID: {member.member_id}
Status: Active

You now have full access to borrow books and use all library services again.

Happy Reading!
Dooars Granthika
"""

    phone_row = (
        f'<p><strong>Phone:</strong> <span>{member.phone}</span></p>'
        if getattr(member, 'phone', None) else ''
    )

    body_content = f"""
        <p class="greeting">Welcome Back! 🎉</p>
        <p>Hello <span class="highlight">{member.full_name}</span>, your membership at <span class="highlight">Dooars Granthika Library</span> has been successfully reactivated.</p>

        <div class="credential-box">
            <p><strong>Member ID:</strong> <span>{member.member_id}</span></p>
            <p><strong>Full Name:</strong> <span>{member.full_name}</span></p>
            {phone_row}
        </div>

        <div class="success-box">
            ✅ Your account is now <strong>active</strong> again. You have full access to borrow books and use all library services.
        </div>

        <div class="info-strip">
            <div class="info-strip-item">
                <div class="info-label">Member ID</div>
                <div class="info-value">{member.member_id}</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">Status</div>
                <div class="info-value" style="color: #38a169;">Active ✓</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">Role</div>
                <div class="info-value" style="font-size:13px;">{member.get_role_display()}</div>
            </div>
        </div>

        <hr class="divider"/>

        <p>If you did not expect this reactivation or have any concerns, please contact our library team immediately.</p>
        <p style="margin-top: 24px; font-size: 18px;">Happy Reading! 📖</p>
    """

    html_message = build_html_email("Membership Reactivated", body_content)
    return send_basic_email(subject, plain_message, html_message, member.email)


# ==============================
# 6️⃣ Clearance Confirmed Email
# ==============================
def send_clearance_confirmation_email(member):
    subject = "Library Clearance Confirmed | Dooars Granthika"

    clearance_date_str = (
        member.clearance_date.strftime('%d %b %Y')
        if member.clearance_date else 'N/A'
    )
    cleared_by_name = 'Library Administration'
    if member.cleared_by:
        cleared_by_name = member.cleared_by.get_full_name() or member.cleared_by.username

    dept_name = member.department.name if member.department else 'N/A'

    plain_message = f"""
Hello {member.full_name},

Your library clearance has been confirmed at Dooars Granthika.

Member ID     : {member.member_id}
Department    : {dept_name}
Clearance Date: {clearance_date_str}
Cleared By    : {cleared_by_name}

You have no outstanding books or dues. You may collect your clearance
certificate from the library if required.

Dooars Granthika
"""

    body_content = f"""
        <p class="greeting">Clearance Confirmed! ✅</p>
        <p>Hello <span class="highlight">{member.full_name}</span>, we are pleased to confirm that your library clearance at <span class="highlight">Dooars Granthika</span> has been completed successfully.</p>

        <div class="credential-box">
            <p><strong>Member ID:</strong> <span>{member.member_id}</span></p>
            <p><strong>Full Name:</strong> <span>{member.full_name}</span></p>
            <p><strong>Department:</strong> <span>{dept_name}</span></p>
            <p><strong>Clearance Date:</strong> <span>{clearance_date_str}</span></p>
            <p><strong>Cleared By:</strong> <span>{cleared_by_name}</span></p>
        </div>

        <div class="success-box">
            ✅ You have <strong>no outstanding books, fines, or dues</strong>. Your library record is fully clear.
        </div>

        <div class="info-strip">
            <div class="info-strip-item">
                <div class="info-label">Books Pending</div>
                <div class="info-value" style="color: #38a169;">0</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">Fines Due</div>
                <div class="info-value" style="color: #38a169;">₹0</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">Clearance</div>
                <div class="info-value" style="color: #38a169;">Cleared ✓</div>
            </div>
        </div>

        <hr class="divider"/>

        <p>You may visit the library to collect your official <strong>Clearance Certificate</strong> if required for institutional purposes.</p>
        <p>Thank you for being a valued member of Dooars Granthika Library. We wish you all the best!</p>
    """

    html_message = build_html_email("Library Clearance Confirmed", body_content)
    return send_basic_email(subject, plain_message, html_message, member.email)


# ==============================
# 7️⃣ Overdue Reminder Email
# ==============================
def send_overdue_reminder_email(member, overdue_transactions):
    """
    Send an overdue reminder to a member.

    Args:
        member               – Member model instance
        overdue_transactions – QuerySet or list of Transaction objects
                               with .book.title, .issue_date, .due_date,
                               .fine_amount populated.
    """
    subject = "⚠️ Overdue Books Notice – Action Required | Dooars Granthika"

    overdue_list = list(overdue_transactions)
    total_fine   = sum(float(t.fine_amount or 0) for t in overdue_list)
    book_count   = len(overdue_list)

    # Plain-text book lines
    book_lines = "\n".join(
        f"  • {t.book.title} — Due: {t.due_date.strftime('%d %b %Y')} | Fine: ₹{t.fine_amount or 0}"
        for t in overdue_list
    )

    plain_message = f"""
Hello {member.full_name},

This is a reminder that you have {book_count} overdue book(s) at Dooars Granthika Library.

Member ID    : {member.member_id}
Overdue Books:
{book_lines}

Total Fine Accrued: ₹{total_fine:.2f}

Please return the books at the earliest to avoid additional fines.
Visit the library or contact us for any assistance.

Dooars Granthika
"""

    # Build HTML table rows for each overdue transaction
    book_rows = ""
    for t in overdue_list:
        due_date = t.due_date
        if hasattr(due_date, 'date'):
            days_overdue = (timezone.now().date() - due_date.date()).days
        else:
            days_overdue = 0

        book_rows += f"""
            <tr>
                <td style="padding:10px 14px; border-bottom:1px solid #e8edf2; font-size:14px; color:#2c3e50;">{t.book.title}</td>
                <td style="padding:10px 14px; border-bottom:1px solid #e8edf2; font-size:14px; color:#666; text-align:center;">{t.issue_date.strftime('%d %b %Y')}</td>
                <td style="padding:10px 14px; border-bottom:1px solid #e8edf2; font-size:14px; color:#e53e3e; text-align:center; font-weight:600;">{t.due_date.strftime('%d %b %Y')}</td>
                <td style="padding:10px 14px; border-bottom:1px solid #e8edf2; font-size:14px; color:#e53e3e; text-align:center;">{days_overdue}d</td>
                <td style="padding:10px 14px; border-bottom:1px solid #e8edf2; font-size:14px; font-weight:700; color:#742a2a; text-align:right;">₹{t.fine_amount or 0}</td>
            </tr>
        """

    body_content = f"""
        <p class="greeting">Overdue Notice ⚠️</p>
        <p>Hello <span class="highlight">{member.full_name}</span>, this is a friendly reminder that you have overdue books at <span class="highlight">Dooars Granthika Library</span>. Please return them as soon as possible to avoid further fines.</p>

        <div class="credential-box">
            <p><strong>Member ID:</strong> <span>{member.member_id}</span></p>
            <p><strong>Overdue Books:</strong> <span>{book_count} book(s)</span></p>
            <p><strong>Total Fine:</strong> <span>₹{total_fine:.2f}</span></p>
        </div>

        <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse; margin:24px 0; border:1px solid #e8edf2; border-radius:10px; overflow:hidden;">
            <thead>
                <tr style="background:linear-gradient(135deg, #1e3a5f, #2c3e50);">
                    <th style="padding:12px 14px; text-align:left; font-size:12px; color:#a8c4e0; text-transform:uppercase; letter-spacing:1px; font-weight:600;">Book Title</th>
                    <th style="padding:12px 14px; text-align:center; font-size:12px; color:#a8c4e0; text-transform:uppercase; letter-spacing:1px; font-weight:600;">Issued</th>
                    <th style="padding:12px 14px; text-align:center; font-size:12px; color:#a8c4e0; text-transform:uppercase; letter-spacing:1px; font-weight:600;">Due Date</th>
                    <th style="padding:12px 14px; text-align:center; font-size:12px; color:#a8c4e0; text-transform:uppercase; letter-spacing:1px; font-weight:600;">Overdue</th>
                    <th style="padding:12px 14px; text-align:right; font-size:12px; color:#a8c4e0; text-transform:uppercase; letter-spacing:1px; font-weight:600;">Fine</th>
                </tr>
            </thead>
            <tbody>
                {book_rows}
                <tr style="background:#f7f9fc;">
                    <td colspan="4" style="padding:12px 14px; font-size:14px; font-weight:700; color:#1e3a5f; text-align:right;">Total Fine:</td>
                    <td style="padding:12px 14px; font-size:15px; font-weight:700; color:#742a2a; text-align:right;">₹{total_fine:.2f}</td>
                </tr>
            </tbody>
        </table>

        <div class="danger-box">
            ⏰ <strong>Please return all overdue books immediately.</strong> Fines continue to accrue daily until the books are returned. Failure to return books may result in membership suspension.
        </div>

        <div class="info-strip">
            <div class="info-strip-item">
                <div class="info-label">Books Overdue</div>
                <div class="info-value" style="color:#e53e3e;">{book_count}</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">Total Fine</div>
                <div class="info-value" style="color:#e53e3e;">₹{total_fine:.2f}</div>
            </div>
            <div class="info-strip-item">
                <div class="info-label">Action</div>
                <div class="info-value" style="font-size:12px; color:#e53e3e;">Return ASAP</div>
            </div>
        </div>

        <hr class="divider"/>
        <p>If you have already returned the books, please ignore this notice or contact us so we can update your record. We're always here to help!</p>
    """

    html_message = build_html_email("Overdue Books Notice", body_content)
    return send_basic_email(subject, plain_message, html_message, member.email)


# ==============================
# 8️⃣ Member Account Closed Email
# ==============================
def send_member_deletion_email(member_name, member_id, member_email):
    """
    Send a farewell / account-closed notice.

    Accepts raw values (not the model instance) because the member will
    already be deleted from the DB when this is called.
    IMPORTANT: Call this BEFORE member.delete() in the view.
    """
    subject = "Your Library Membership Has Been Closed | Dooars Granthika"

    plain_message = f"""
Hello {member_name},

Your membership at Dooars Granthika Library has been closed.

Member ID: {member_id}

All your borrowing records have been archived. If you believe this was
done in error, please contact our library team immediately.

Thank you for being a member of Dooars Granthika.
"""

    body_content = f"""
        <p class="greeting">Membership Closed</p>
        <p>Hello <span class="highlight">{member_name}</span>, we are writing to inform you that your membership at <span class="highlight">Dooars Granthika Library</span> has been closed.</p>

        <div class="credential-box">
            <p><strong>Member ID:</strong> <span>{member_id}</span></p>
            <p><strong>Full Name:</strong> <span>{member_name}</span></p>
            <p><strong>Status:</strong> <span>Closed</span></p>
        </div>

        <div class="warning-box">
            ⚠️ <strong>Your membership is no longer active.</strong> All borrowing privileges have been revoked and your records have been archived.
        </div>

        <div class="danger-box">
            🛡️ <strong>Not expecting this?</strong> If you did not request account closure or believe this was done in error, please contact our library support team immediately.
        </div>

        <hr class="divider"/>
        <p>Thank you for being a valued member of Dooars Granthika Library. We hope to welcome you back in the future.</p>
        <p style="margin-top: 16px;">Goodbye and best wishes! 👋</p>
    """

    html_message = build_html_email("Membership Closed", body_content)
    return send_basic_email(subject, plain_message, html_message, member_email)