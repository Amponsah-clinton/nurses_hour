"""
EnsureUserMiddleware — Vercel cold-start resilience.

On Vercel, each serverless function instance gets its own /tmp/db.sqlite3 copied
from the build bundle (which has no runtime users). When a user was logged in on
a previous instance, Django tries User.objects.get(pk=X) on the new instance's
empty DB and gets DoesNotExist, making request.user anonymous and causing
@login_required to redirect to /login/.

This middleware stores the user's email (and name) in the signed-cookie session.
If the user is anonymous but session has that email, it recreates the User row
in the new instance's DB and logs them back in transparently.
"""
from django.contrib.auth import get_user_model, login as auth_login
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
                        defaults={
                            'username': email,
                            'first_name': name,
                        },
                    )
                    if created:
                        user.set_unusable_password()
                        user.save(update_fields=['password'])
                    auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                except (OperationalError, Exception):
                    pass
        return self.get_response(request)
