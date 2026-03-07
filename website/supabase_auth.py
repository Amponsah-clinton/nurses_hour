"""
Supabase Auth helpers: sign up, sign in, and admin user management.
Returns (user_data, None) on success or (None, error_message) on failure.
user_data has attributes: .id, .email, .user_metadata (dict with full_name, phone, program).
"""
from django.conf import settings


def _client():
    """Supabase client using the service_role key (server-side only)."""
    from supabase import create_client
    url = getattr(settings, 'SUPABASE_URL', None)
    key = getattr(settings, 'SUPABASE_SERVICE_KEY', None) or getattr(settings, 'SUPABASE_KEY', None)
    if not url or not key:
        raise ValueError('SUPABASE_URL and SUPABASE_SERVICE_KEY are required.')
    return create_client(url.rstrip('/'), key)


def sign_up_supabase(email, password, full_name=None, phone=None, program=None):
    """
    Register a new user via Supabase Auth admin API (email_confirm=True so login works immediately).
    Returns (user_obj, None) or (None, error_message).
    """
    try:
        client = _client()
        data = {}
        if full_name:
            data['full_name'] = full_name
        if phone:
            data['phone'] = str(phone).strip()
        if program:
            data['program'] = program
        resp = client.auth.admin.create_user({
            'email': email.strip().lower(),
            'password': password,
            'email_confirm': True,
            'user_metadata': data,
        })
        user = getattr(resp, 'user', None)
        if user is None:
            return None, 'Sign up failed — please try again.'
        return user, None
    except Exception as e:
        msg = str(e)
        if 'already registered' in msg.lower() or 'already exists' in msg.lower() or 'duplicate' in msg.lower():
            return None, 'An account with this email already exists.'
        return None, msg


def sign_in_supabase(email, password):
    """
    Sign in an existing user via Supabase Auth (email + password).
    Returns (user_obj, None) or (None, error_message).
    error_message is the real Supabase message when possible (e.g. "Email not confirmed").
    """
    try:
        client = _client()
        resp = client.auth.sign_in_with_password({
            'email': email.strip().lower(),
            'password': password,
        })
        user = getattr(resp, 'user', None)
        if user is None:
            return None, getattr(resp, 'message', None) or 'Invalid email or password.'
        return user, None
    except Exception as e:
        msg = str(e)
        # Surface real message for "Email not confirmed" etc.
        if 'email_not_confirmed' in msg.lower() or 'not confirmed' in msg.lower():
            return None, 'Email not confirmed. Check your inbox or use Forgot password to reset.'
        if 'invalid' in msg.lower() or 'credentials' in msg.lower() or 'password' in msg.lower():
            return None, msg if len(msg) < 120 else 'Invalid email or password.'
        return None, msg or 'Sign in failed — please try again.'


def ensure_user_in_supabase_auth(email, password, full_name='', email_confirm=True):
    """
    Ensure a user exists in Supabase Auth. Creates them if they don't exist yet.
    Uses the admin API (service_role key). email_confirm=True skips email verification.
    Returns (user_obj, None) or (None, error_message).
    """
    try:
        client = _client()
        data = {}
        if full_name:
            data['full_name'] = full_name
        resp = client.auth.admin.create_user({
            'email': email.strip().lower(),
            'password': password,
            'email_confirm': email_confirm,
            'user_metadata': data,
        })
        user = getattr(resp, 'user', None)
        return user, None
    except Exception as e:
        msg = str(e)
        if 'already registered' in msg.lower() or 'already exists' in msg.lower() or 'duplicate' in msg.lower():
            return True, None  # Already there — that's fine
        return None, msg


def ensure_admin_in_supabase():
    """
    Create the admin account in Supabase Auth if it doesn't exist yet.
    Uses ADMIN_EMAIL and ADMIN_INITIAL_PASSWORD from settings.
    Called automatically on admin login attempt.
    """
    email = getattr(settings, 'ADMIN_EMAIL', None)
    password = getattr(settings, 'ADMIN_INITIAL_PASSWORD', None)
    if not email or not password:
        return
    ensure_user_in_supabase_auth(email, password, full_name='Admin', email_confirm=True)
