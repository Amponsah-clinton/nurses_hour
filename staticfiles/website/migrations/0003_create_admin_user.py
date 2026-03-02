# Generated manually for hardcoded admin dashboard access.

from django.db import migrations
from django.conf import settings
from django.contrib.auth.hashers import make_password


def create_admin_user(apps, schema_editor):
    User = apps.get_model(*settings.AUTH_USER_MODEL.split('.'))
    admin_email = 'amoasamoahransford17@gmail.com'
    admin_password = 'Nursehub2026@'
    if not User.objects.filter(email=admin_email).exists():
        User.objects.create(
            username=admin_email,
            email=admin_email,
            password=make_password(admin_password),
            is_staff=False,
            is_superuser=False,
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0002_add_visit_model'),
    ]

    operations = [
        migrations.RunPython(create_admin_user, noop),
    ]
