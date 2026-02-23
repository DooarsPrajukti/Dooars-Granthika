import secrets
import string
import re


# ==========================================================
# 🔐 SECURE RANDOM PASSWORD
# ==========================================================
def generate_random_password(length=10):
    """
    Generate a secure random password.
    Uses cryptographically strong randomness.
    """
    if length < 8:
        length = 8

    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


# ==========================================================
# 👤 AUTO USERNAME GENERATOR
# Example: LIB582193
# ==========================================================
def generate_username(prefix="DG", digits=6):
    """
    Generate a random username.
    NOTE: Must still check uniqueness in view.
    """
    number_part = ''.join(secrets.choice(string.digits) for _ in range(digits))
    return f"{prefix}{number_part}"