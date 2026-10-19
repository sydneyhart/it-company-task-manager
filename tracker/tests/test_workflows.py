from datetime import timedelta
from io import StringIO
from urllib.parse import parse_qs

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape

from tracker.forms import TaskForm, WorkerCreationForm, WorkerUpdateForm
from tracker.models import Position, Tag, Task, TaskType


class WorkspaceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.position = Position.objects.create(name="Developer")
        cls.kind = TaskType.objects.create(name="Feature")
        cls.tag = Tag.objects.create(name="backend")
        cls.worker = get_user_model().objects.create_user(
            username="alex",
            first_name="Alex",
            last_name="Morgan",
            email="alex@example.com",
            position=cls.position,
            password="Unique-password-4729",
        )
        cls.other = get_user_model().objects.create_user(
            username="maya",
            first_name="Maya",
            last_name="Chen",
            email="maya@example.com",
            position=cls.position,
        )
        cls.task = Task.objects.create(
            name="Ship dashboard",
            description="Build useful charts",
            deadline=timezone.localdate() + timedelta(days=2),
            task_type=cls.kind,
            priority="high",
        )
        cls.task.assignees.add(cls.worker, cls.other)
        cls.task.tags.add(cls.tag)

    def setUp(self):
        self.client.force_login(self.worker)

    def url(self, name, *args):
        return reverse(f"tracker:{name}", args=args)

    def task_data(self, **overrides):
        return {
            "name": "Search redesign",
            "description": "Improve findability",
            "deadline": timezone.localdate().isoformat(),
            "priority": "medium",
            "task_type": self.kind.pk,
            "assignees": [self.other.pk],
            "tags": [self.tag.pk],
            **overrides,
        }

    def test_all_custom_pages_render(self):
        pages = [
            ("dashboard", []),
            ("task-list", []),
            ("task-detail", [self.task.pk]),
            ("task-create", []),
            ("task-update", [self.task.pk]),
            ("task-delete", [self.task.pk]),
            ("worker-list", []),
            ("worker-detail", [self.worker.pk]),
            ("worker-create", []),
            ("worker-update", [self.worker.pk]),
            ("worker-delete", [self.other.pk]),
        ]
        for kind, item in (
            ("positions", self.position),
            ("types", self.kind),
            ("tags", self.tag),
        ):
            pages.extend(
                [
                    ("catalog-list", [kind]),
                    ("catalog-create", [kind]),
                    ("catalog-update", [kind, item.pk]),
                    ("catalog-delete", [kind, item.pk]),
                ]
            )
        for name, args in pages:
            with self.subTest(name=name, args=args):
                self.assertEqual(
                    self.client.get(self.url(name, *args)).status_code, 200
                )

    def test_custom_pages_and_mutations_require_login(self):
        self.client.logout()
        for name, args in [
            ("dashboard", []),
            ("task-list", []),
            ("task-create", []),
            ("task-detail", [self.task.pk]),
            ("task-update", [self.task.pk]),
            ("task-delete", [self.task.pk]),
            ("task-status", [self.task.pk]),
            ("task-assignment", [self.task.pk]),
            ("worker-list", []),
            ("worker-create", []),
            ("worker-detail", [self.worker.pk]),
            ("worker-update", [self.worker.pk]),
            ("worker-delete", [self.worker.pk]),
            ("catalog-list", ["tags"]),
            ("catalog-create", ["tags"]),
            ("catalog-update", ["tags", self.tag.pk]),
            ("catalog-delete", ["tags", self.tag.pk]),
        ]:
            for method in (self.client.get, self.client.post):
                with self.subTest(name=name, method=method.__name__):
                    response = method(self.url(name, *args))
                    self.assertEqual(response.status_code, 302)
                    self.assertTrue(response.url.startswith(reverse("login")))

    def test_task_create_and_update_many_to_many_assignments(self):
        response = self.client.post(self.url("task-create"), self.task_data())
        task = Task.objects.get(name="Search redesign")
        self.assertRedirects(response, task.get_absolute_url())
        self.assertEqual(list(task.assignees.all()), [self.other])
        self.assertEqual(list(task.tags.all()), [self.tag])
        self.client.post(
            self.url("task-update", task.pk),
            self.task_data(name="Updated task", assignees=[self.worker.pk], tags=[]),
        )
        task.refresh_from_db()
        self.assertEqual(task.name, "Updated task")
        self.assertEqual(list(task.assignees.all()), [self.worker])
        self.assertFalse(task.tags.exists())

    def test_invalid_task_does_not_save(self):
        for overrides in (
            {"name": ""},
            {"deadline": "not-a-date"},
            {"priority": "unknown"},
            {"assignees": [999]},
            {"tags": [999]},
            {"task_type": 999},
        ):
            with self.subTest(overrides=overrides):
                form = TaskForm(data=self.task_data(**overrides))
                self.assertFalse(form.is_valid())
        self.client.post(self.url("task-create"), self.task_data(name=""))
        self.assertEqual(Task.objects.count(), 1)

    def test_task_can_have_no_assignees_or_tags(self):
        self.assertTrue(TaskForm(data=self.task_data(assignees=[], tags=[])).is_valid())

    def test_task_completion_and_reopening_are_idempotent(self):
        url = self.url("task-status", self.task.pk)
        self.assertEqual(self.client.get(url).status_code, 405)
        for value, expected in (("1", True), ("1", True), ("0", False)):
            self.assertRedirects(
                self.client.post(url, {"completed": value}),
                self.task.get_absolute_url(),
            )
            self.task.refresh_from_db()
            self.assertEqual(self.task.is_completed, expected)
        self.client.post(url, {"completed": "invalid"})
        self.task.refresh_from_db()
        self.assertFalse(self.task.is_completed)

    def test_self_assignment_never_modifies_another_worker(self):
        url = self.url("task-assignment", self.task.pk)
        self.assertEqual(self.client.get(url).status_code, 405)
        for action in ("leave", "leave"):
            self.client.post(url, {"action": action, "worker": self.other.pk})
        self.assertEqual(list(self.task.assignees.all()), [self.other])
        for action in ("join", "join"):
            self.client.post(url, {"action": action})
        self.assertEqual(set(self.task.assignees.all()), {self.worker, self.other})
        self.client.post(url, {"action": "invalid"})
        self.assertEqual(self.task.assignees.count(), 2)

    def test_task_mutations_require_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.worker)
        for action in ("task-status", "task-assignment", "task-delete"):
            self.assertEqual(
                client.post(self.url(action, self.task.pk)).status_code, 403
            )

    def test_task_delete_get_only_confirms(self):
        url = self.url("task-delete", self.task.pk)
        self.assertContains(self.client.get(url), "Cancel")
        self.assertTrue(Task.objects.filter(pk=self.task.pk).exists())
        self.assertRedirects(self.client.post(url), self.url("task-list"))
        self.assertFalse(Task.objects.filter(pk=self.task.pk).exists())
        self.assertEqual(get_user_model().objects.count(), 2)

    def test_worker_creation_hashes_password_and_ignores_privileges(self):
        response = self.client.post(
            self.url("worker-create"),
            {
                "username": "new.worker",
                "first_name": "New",
                "last_name": "Worker",
                "email": "new@example.com",
                "position": self.position.pk,
                "password1": "Unique-password-4729",
                "password2": "Unique-password-4729",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        worker = get_user_model().objects.get(username="new.worker")
        self.assertRedirects(response, worker.get_absolute_url())
        self.assertTrue(worker.check_password("Unique-password-4729"))
        self.assertFalse(worker.is_staff)
        self.assertFalse(worker.is_superuser)

    def test_worker_update_cannot_escalate_privileges(self):
        self.client.post(
            self.url("worker-update", self.other.pk),
            {
                "first_name": "Edited",
                "last_name": "Name",
                "email": "edit@example.com",
                "position": self.position.pk,
                "is_staff": True,
                "is_superuser": True,
                "username": "hacked",
                "password": "raw",
            },
        )
        self.other.refresh_from_db()
        self.assertEqual(self.other.first_name, "Edited")
        self.assertEqual(self.other.username, "maya")
        self.assertFalse(self.other.is_staff)
        self.assertFalse(self.other.is_superuser)
        self.assertNotEqual(self.other.password, "raw")
        self.assertNotIn("password", WorkerUpdateForm().fields)

    def test_creation_form_uses_custom_user_and_rejects_bad_passwords(self):
        self.assertEqual(WorkerCreationForm._meta.model, get_user_model())
        form = WorkerCreationForm(
            data={
                "username": "new",
                "email": "valid@example.com",
                "position": self.position.pk,
                "password1": "first",
                "password2": "second",
            }
        )
        self.assertFalse(form.is_valid())

    def test_worker_removal_preserves_tasks(self):
        url = self.url("worker-delete", self.other.pk)
        response = self.client.get(url)
        self.assertContains(response, f'href="{self.other.get_absolute_url()}"')
        self.assertTrue(get_user_model().objects.filter(pk=self.other.pk).exists())
        self.assertRedirects(self.client.post(url), self.url("worker-list"))
        self.assertTrue(Task.objects.filter(pk=self.task.pk).exists())
        self.assertEqual(list(self.task.assignees.all()), [self.worker])

    def test_worker_detail_separates_active_and_completed_tasks(self):
        done = Task.objects.create(
            name="Finished",
            description="Done",
            deadline=timezone.localdate(),
            task_type=self.kind,
            is_completed=True,
        )
        done.assignees.add(self.worker)
        response = self.client.get(self.worker.get_absolute_url())
        self.assertEqual(list(response.context["active_tasks"]), [self.task])
        self.assertEqual(list(response.context["completed_tasks"]), [done])

    def test_dashboard_counts_and_overdue_definition(self):
        self.task.deadline = timezone.localdate() - timedelta(days=1)
        self.task.save()
        self.assertTrue(self.task.is_overdue)
        response = self.client.get(self.url("dashboard"))
        self.assertEqual(response.context["active_count"], 1)
        self.assertEqual(response.context["overdue_count"], 1)
        self.assertEqual(response.context["worker_count"], 2)
        self.task.is_completed = True
        self.task.save()
        self.assertFalse(self.task.is_overdue)
        response = self.client.get(self.url("dashboard"))
        self.assertEqual(response.context["completion_percent"], 100)
        self.assertEqual(response.context["overdue_count"], 0)

    def test_dashboard_handles_empty_workspace(self):
        Task.objects.all().delete()
        response = self.client.get(self.url("dashboard"))
        self.assertEqual(response.context["completion_percent"], 0)

    def test_search_and_combined_task_filters(self):
        other = Task.objects.create(
            name="Other task",
            description="No matching brief",
            deadline=timezone.localdate(),
            task_type=self.kind,
            is_completed=True,
        )
        for params in (
            {"q": "DASH"},
            {"q": "  useful  "},
            {"status": "active"},
            {
                "priority": "high",
                "task_type": self.kind.pk,
                "tag": self.tag.pk,
                "mine": "on",
                "status": "active",
            },
        ):
            with self.subTest(params=params):
                response = self.client.get(self.url("task-list"), params)
                self.assertEqual(list(response.context["task_list"]), [self.task])
        response = self.client.get(self.url("task-list"), {"status": "done"})
        self.assertEqual(list(response.context["task_list"]), [other])

    def test_invalid_filters_and_no_match_show_empty_results(self):
        for params in ({"q": "unknown"}, {"priority": "fake"}, {"tag": 999}):
            response = self.client.get(self.url("task-list"), params)
            self.assertFalse(response.context["task_list"])

    def test_pagination_retains_encoded_filters(self):
        for index in range(10):
            Task.objects.create(
                name=f"API & Search {index}",
                description="Brief",
                deadline=timezone.localdate(),
                task_type=self.kind,
            )
        params = {"q": "API & Search", "status": "active"}
        first = self.client.get(self.url("task-list"), params)
        self.assertEqual(len(first.context["task_list"]), 8)
        query = first.context["query_string"]
        self.assertEqual(parse_qs(query), {key: [val] for key, val in params.items()})
        self.assertContains(first, escape(f"?{query}&page=2"))
        second = self.client.get(self.url("task-list"), {**params, "page": 2})
        self.assertEqual(len(second.context["task_list"]), 2)
        self.assertNotIn("page", parse_qs(second.context["query_string"]))

    def test_worker_search_and_counts(self):
        response = self.client.get(self.url("worker-list"), {"q": "MAYA"})
        self.assertEqual(list(response.context["worker_list"]), [self.other])
        self.assertEqual(response.context["worker_list"][0].active_count, 1)

    def test_catalog_crud_search_and_duplicate_validation(self):
        for kind, model in (
            ("positions", Position),
            ("types", TaskType),
            ("tags", Tag),
        ):
            with self.subTest(kind=kind):
                response = self.client.post(
                    self.url("catalog-create", kind), {"name": "New"}
                )
                self.assertRedirects(response, self.url("catalog-list", kind))
                item = model.objects.get(name="New")
                response = self.client.get(self.url("catalog-list", kind), {"q": "NEW"})
                self.assertEqual(list(response.context["items"]), [item])
                self.client.post(
                    self.url("catalog-update", kind, item.pk), {"name": "Updated"}
                )
                item.refresh_from_db()
                self.assertEqual(item.name, "Updated")
                duplicate = self.client.post(
                    self.url("catalog-create", kind), {"name": "Updated"}
                )
                self.assertEqual(duplicate.status_code, 200)
                self.assertIn("name", duplicate.context["form"].errors)
                self.assertRedirects(
                    self.client.post(self.url("catalog-delete", kind, item.pk)),
                    self.url("catalog-list", kind),
                )

    def test_protected_catalog_records_cannot_be_deleted(self):
        for kind, item in (("positions", self.position), ("types", self.kind)):
            response = self.client.post(self.url("catalog-delete", kind, item.pk))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "This item is in use")
            self.assertTrue(type(item).objects.filter(pk=item.pk).exists())

    def test_tag_deletion_keeps_tasks(self):
        self.client.post(self.url("catalog-delete", "tags", self.tag.pk))
        self.assertTrue(Task.objects.filter(pk=self.task.pk).exists())
        self.assertFalse(self.task.tags.exists())

    def test_missing_records_and_invalid_catalog_return_404(self):
        for name, args in (
            ("task-detail", [999]),
            ("task-status", [999]),
            ("task-assignment", [999]),
            ("worker-detail", [999]),
            ("catalog-list", ["invalid"]),
        ):
            response = (
                self.client.post(self.url(name, *args))
                if name in ("task-status", "task-assignment")
                else self.client.get(self.url(name, *args))
            )
            self.assertEqual(response.status_code, 404)

    def test_text_is_escaped_in_templates(self):
        self.task.name = "<script>alert(1)</script>"
        self.task.description = "<img src=x onerror=alert(1)>"
        self.task.save()
        response = self.client.get(self.task.get_absolute_url())
        self.assertContains(response, "&lt;script&gt;")
        self.assertNotContains(response, "<script>alert(1)</script>")

    def test_demo_seed_is_idempotent_and_preserves_password(self):
        output = StringIO()
        call_command("seed_demo", password="First-demo-password-839", stdout=output)
        counts = (Task.objects.count(), get_user_model().objects.count())
        call_command("seed_demo", password="Different-password-273", stdout=output)
        self.assertEqual(
            counts, (Task.objects.count(), get_user_model().objects.count())
        )
        demo = get_user_model().objects.get(username="demo.user")
        self.assertTrue(demo.check_password("First-demo-password-839"))
