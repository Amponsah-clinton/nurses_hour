"""
EnsureUserMiddleware — Vercel cold-start resilience.

PROBLEM
-------
Vercel serverless: each function instance gets its own /tmp/db.sqlite3 (copied
from the build bundle, which has no runtime users). When Django reads
_auth_user_id from the signed-cookie session and the user row is missing it
returns AnonymousUser and @login_required redirects to /login/ — even though
the user just logged in moments ago on a different warm instance.

WHY EARLIER APPROACHES FAIL
----------------------------
Storing _nh_email in the Django session and restoring from there fails when:
  1. The user logged in before the fix was deployed (session has no _nh_email).
  2. django.contrib.auth.login() detects a hash mismatch and calls
     session.flush(), which wipes _nh_email from the session.

SOLUTION
--------
Store the user's identity in a SEPARATE signed cookie (_nh_id) that is
completely independent of the Django session.
• Set on every response where request.user is authenticated.
• Read at the start of every request BEFORE any view runs.
• Even if the Django session is flushed, this cookie survives.
• Signed with Django's SECRET_KEY → tamper-proof.
• Works for users who logged in before any session-based fix was deployed.
"""
from django.contrib.auth import (
    get_user_model,
    login as auth_login,
    SESSION_KEY,
    BACKEND_SESSION_KEY,
    HASH_SESSION_KEY,
)
from django.core.signing import Signer, BadSignature
from django.db import OperationalError

User = get_user_model()

_signer = Signer(salt='nursehour_session_v1')
_COOKIE = '_nh_id'
_MAX_AGE = 30 * 24 * 3600   # 30 days


class EnsureUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    # ------------------------------------------------------------------ #
    # Request phase                                                        #
    # ------------------------------------------------------------------ #
    def __call__(self, request):
        if hasattr(request, 'user') and not request.user.is_authenticated:
            email = self._read_email(request)
            if email:
                self._restore(request, email)

        response = self.get_response(request)

        # Response phase: refresh signed cookie whenever user is authenticated.
        if hasattr(request, 'user') and request.user.is_authenticated:
            try:
                signed = _signer.sign(request.user.email)
                response.set_cookie(
                    _COOKIE,
                    signed,
                    max_age=_MAX_AGE,
                    httponly=True,
                    secure=request.is_secure(),
                    samesite='Lax',
                )
            except Exception:
                pass

        return response

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #
    def _read_email(self, request):
        """Return verified email from signed cookie, fall back to session."""
        signed = request.COOKIES.get(_COOKIE)
        if signed:
            try:
                return _signer.unsign(signed)
            except BadSignature:
                pass
        return request.session.get('_nh_email') or None

    def _restore(self, request, email):
        """Re-create the User row (if gone) and log the user in silently."""
        try:
            name = request.session.get('_nh_name') or ''
            program = request.session.get('_nh_program') or ''
            phone = request.session.get('_nh_phone') or ''

            user, created = User.objects.get_or_create(
                email=email,
                defaults={'username': email, 'first_name': name},
            )
            if created:
                user.set_unusable_password()
                user.save(update_fields=['password'])
                from .models import UserProfile
                UserProfile.objects.get_or_create(
                    user=user,
                    defaults={'program': program, 'phone': phone},
                )

            # Pop stale auth session keys so auth_login() calls cycle_key()
            # (preserves session data) instead of flush() (wipes the session).
            # The original password hash no longer matches the unusable-password
            # hash we just set, which would trigger flush() without this step.
            for key in (SESSION_KEY, BACKEND_SESSION_KEY, HASH_SESSION_KEY):
                request.session.pop(key, None)

            auth_login(
                request, user,
                backend='django.contrib.auth.backends.ModelBackend',
            )

            # Re-persist in session (in case cycle_key wiped anything).
            request.session['_nh_email'] = email
            request.session['_nh_name'] = name
            request.session['_nh_program'] = program
            request.session['_nh_phone'] = phone

        except (OperationalError, Exception):
            pass
