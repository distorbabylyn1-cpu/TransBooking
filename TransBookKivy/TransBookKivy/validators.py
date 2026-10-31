"""Input validation. Every function raises ValueError with a friendly message."""
import re

EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")


def clean_phone(text):
    phone = re.sub(r"[\s\-]", "", text or "")
    if phone and not re.fullmatch(r"\+?\d{10,15}", phone):
        raise ValueError("Phone number must have 10 to 15 digits.")
    return phone or None


def check_password(password):
    if len(password) < 8 or not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise ValueError("Password must be 8+ characters with letters and numbers.")


def validate_login(identifier, password):
    identifier = identifier.strip()
    if not identifier or not password:
        raise ValueError("Enter your phone number or email and your password.")
    return identifier, password


def validate_signup(name, email, phone, password):
    name, email = " ".join(name.split()), email.strip().lower()
    if len(name) < 3:
        raise ValueError("Please enter your full name.")
    if not EMAIL_RE.match(email):
        raise ValueError("Please enter a valid email address.")
    phone = clean_phone(phone)
    check_password(password)
    return name, email, phone, password


def validate_profile(name, phone):
    name = " ".join(name.split())
    if len(name) < 3:
        raise ValueError("Please enter your full name.")
    return name, clean_phone(phone)
