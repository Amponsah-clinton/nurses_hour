"""
EnsureUserMiddleware — Vercel cold-start resilience.

On Vercel each serverless function instance gets its own /tmp/db.sqlite3 copied
from the build bundle (no runtime users). When Django reads _auth_user_id from
the signed-cookie session and the user row is gone it returns AnonymousUser and
@login_required redirects to /login/ — even though the user just logged in on a
previous warm instance.

This middleware reads the email stored in the signed-cookie session (_nh_email).
If the user is anonymous but _nh_email is present it recreates the User row and
logs them in silently.

IMPORTANT — session flush bug:
django.contrib.auth.login() compares the HASH_SESSION_KEY stored in the session
(hash of the original password) with the user's current get_session_auth_hash().
If they differ it calls session.flush() which wipes _nh_email from the session,
so the NEXT cold-start instance can't restore the user either.

Fix: pop the stale auth session keys before calling auth_login() so Django takes
the cycle_key() branch (preserves session data) instead of flush().  Then
re-write _nh_email/name explicitly so they survive even if the session was
somehow modified.
"""
from django.contrib.auth import (
    get_user_model,
    login as auth_login,
    SESSION_KEY,
    BACKEND_SESSION_KEY,
    HASH_SESSION_KEY,
)
from django.db import OperationalError

User = get_user_model()


class EnsureUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if hasattr(request, 'user') and not request.user.is_authenticated:
            email = request.session.get('_nh_email')
            name = request.session.get('_nh_name') or ''
            if email:
                try:
                    user, created = User.objects.get_or_create(
                        email=email,
                        defaults={'username': email, 'first_name': name},
                    )
                    if created:
                        user.set_unusable_password()
                        user.save(update_fields=['password'])
                        from .models import UserProfile
                        program = request.session.get('_nh_program') or ''
                        phone = request.session.get('_nh_phone') or ''
                        UserProfile.objects.get_or_create(
                            user=user,
                            defaults={'program': program, 'phone': phone},
                        )

                    # Remove stale auth keys so auth_login() takes the
                    # cycle_key() branch instead of flush() — the original
                    # password hash no longer matches the unusable-password
                    # hash, which would cause session.flush() and wipe _nh_email.
                    for key in (SESSION_KEY, BACKEND_SESSION_KEY, HASH_SESSION_KEY):
                        request.session.pop(key, None)

                    auth_login(
                        request, user,
                        backend='django.contrib.auth.backends.ModelBackend',
                    )

                    # Always re-persist so future cold-start instances can restore.
                    request.session['_nh_email'] = email
                    request.session['_nh_name'] = name

                except (OperationalError, Exception):
                    pass

        return self.get_response(request)
