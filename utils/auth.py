import hashlib
import hmac
import random
import re
from typing import Optional, Dict, Any
import streamlit as st
from utils.db import get_supabase


def hash_password(password: str) -> str:
    # MVP hash. For production, use passlib/bcrypt/argon2 with salt.
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hmac.compare_digest(hash_password(password), password_hash)


def valid_university_email(email: str) -> bool:
    domain = st.secrets.get("ALLOWED_EMAIL_DOMAIN", "mahindrauniversity.edu.in")
    pattern = rf"^[A-Za-z0-9._%+-]+@{re.escape(domain)}$"
    return re.match(pattern, email.strip()) is not None


def generate_otp() -> str:
    return str(random.randint(100000, 999999))


def signup_user(name: str, email: str, password: str, course: str, year: str) -> Optional[str]:
    sb = get_supabase()
    email = email.strip().lower()
    exists = sb.table("profiles").select("id").eq("email", email).execute().data
    if exists:
        return "An account with this email already exists."
    sb.table("profiles").insert({
        "name": name.strip(),
        "email": email,
        "password_hash": hash_password(password),
        "course": course.strip(),
        "year": year,
        "is_verified": True,
        "is_admin": False,
    }).execute()
    return None


def login_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    sb = get_supabase()
    email = email.strip().lower()
    rows = sb.table("profiles").select("*").eq("email", email).limit(1).execute().data
    if not rows:
        return None
    user = rows[0]
    if not verify_password(password, user.get("password_hash", "")):
        return None
    return user


def require_login():
    if "user" not in st.session_state or not st.session_state.user:
        st.warning("Please log in first.")
        st.stop()


def logout():
    for key in ["user", "otp", "pending_signup"]:
        st.session_state.pop(key, None)
