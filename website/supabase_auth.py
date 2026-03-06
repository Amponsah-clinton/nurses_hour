"""
Supabase Auth helpers: sign up and sign in.
Returns (user_data, None) on success or (None, error_message) on failure.
user_data is a dict with at least: id, email, user_metadata (full_name, phone, program).
"""
from django.conf import settings


def _client():
    """Create Supabase client with service key (for server-side auth)."""
    from supabase import create_client
    url = getattr(settings, 'SUPABASE_URL', None)
    key = getattr(settings, 'SUPABASE_SERVICE_KEY', None) or getattr(settings, 'SUPABASE_KEY', None)
    if not url or not key:
        raise ValueError('SUPABASE_URL and SUPABASE_SERVICE_KEY (or SUPABASE_KEY) required.')
    return create_client(url.rstrip('/'), key)


def sign_up_supabase(email, password, full_name=None, phone=None, program=None):
    """
    Register a user with Supabase Auth.
    Returns (user_dict, None) or (None, error_message).
    user_dict has .id, .email, .user_metadata.
    """
    try:
        client = _client()
        opts = {}
        if full_name is not None or phone is not None or program is not None:
            opts['data'] = {}
            if full_name is not None:
                opts['data']['full_name'] = full_name
            if phone is not None:
                opts['data']['phone'] = str(phone).strip()
            if program is not None:
                opts['data']['program'] = program
        resp = client.auth.sign_up({
            'email': email.strip().lower(),
            'password': password,
            'options': opts if opts else None,
        })
        user = getattr(resp, 'user', None)
        if user is None:
            return None, getattr(resp, 'message', None) or 'Sign up failed'
        return user, None
    except Exception as e:
        msg = str(e)
        if 'already registered' in msg.lower() or 'already exists' in msg.lower():
            return None, 'An account with this email already exists.'
        return None, msg


def sign_in_supabase(email, password):
    """
    Sign in with Supabase Auth (email + password).
    Returns (user_dict, None) or (None, error_message).
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
        return None, str(e) or 'Invalid email or password.'
