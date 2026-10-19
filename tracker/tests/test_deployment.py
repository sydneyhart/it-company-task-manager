import os
import subprocess
import sys
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import DatabaseError
from django.test import TestCase
from django.urls import reverse


class DeploymentTests(TestCase):
    def test_health_check_is_public(self):
        response = self.client.get(reverse("health-check"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_health_check_reports_database_failure_without_details(self):
        with patch("tracker.health.connection.cursor", side_effect=DatabaseError):
            response = self.client.get(reverse("health-check"))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unavailable"})

    def test_named_public_account_is_seeded_and_not_a_superuser(self):
        call_command(
            "seed_demo", username="user", password="user12345", stdout=StringIO()
        )
        visitor = get_user_model().objects.get(username="user")
        self.assertTrue(visitor.check_password("user12345"))
        self.assertFalse(visitor.is_staff)
        self.assertFalse(visitor.is_superuser)
        self.assertTrue(visitor.tasks.exists())
        call_command("seed_demo", username="user", password="other", stdout=StringIO())
        visitor.refresh_from_db()
        self.assertTrue(visitor.check_password("user12345"))

    def test_shared_visitor_account_cannot_be_deleted_in_demo_mode(self):
        call_command(
            "seed_demo", username="user", password="user12345", stdout=StringIO()
        )
        visitor = get_user_model().objects.get(username="user")
        self.client.force_login(visitor)
        with patch.dict(os.environ, {"TASKLINE_PUBLIC_DEMO": "1"}):
            response = self.client.post(
                reverse("tracker:worker-delete", args=[visitor.pk])
            )
        self.assertContains(response, "shared visitor account cannot be removed")
        self.assertTrue(get_user_model().objects.filter(pk=visitor.pk).exists())

    def test_render_refuses_ephemeral_sqlite_when_database_url_is_missing(self):
        environment = {
            **os.environ,
            "RENDER": "true",
            "DJANGO_SECRET_KEY": "test-key-for-startup-validation",
            "DJANGO_SETTINGS_MODULE": "config.settings",
        }
        environment.pop("DATABASE_URL", None)
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from django.conf import settings; "
                "print(settings.DATABASES['default']['ENGINE'])",
            ],
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DATABASE_URL is required on Render", result.stderr)

    def test_render_configuration_uses_postgres_and_secure_cookies(self):
        environment = {
            **os.environ,
            "RENDER": "true",
            "DJANGO_DEBUG": "0",
            "DJANGO_SECRET_KEY": "test-key-for-startup-validation",
            "DJANGO_SETTINGS_MODULE": "config.settings",
            "DATABASE_URL": "postgresql://test:test@localhost:5432/taskline",
            "RENDER_EXTERNAL_HOSTNAME": "taskline-test.onrender.com",
        }
        code = (
            "from django.conf import settings; "
            "assert settings.DATABASES['default']['ENGINE'] == "
            "'django.db.backends.postgresql'; "
            "assert not settings.DEBUG; "
            "assert settings.SESSION_COOKIE_SECURE; "
            "assert 'taskline-test.onrender.com' in settings.ALLOWED_HOSTS; "
            "assert 'https://taskline-test.onrender.com' in "
            "settings.CSRF_TRUSTED_ORIGINS"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
