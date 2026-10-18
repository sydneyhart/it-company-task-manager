from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from tracker.models import Position, Tag, Task, TaskType


class Command(BaseCommand):
    help = "Create local demo records without duplicating or overwriting existing data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password", default="Taskline-demo-2026!",
            help="Password for a newly created demo.user account.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        positions = {
            name: Position.objects.get_or_create(name=name)[0]
            for name in ("Developer", "Designer", "Project Manager", "QA Engineer")
        }
        types = {
            name: TaskType.objects.get_or_create(name=name)[0]
            for name in ("Feature", "Bug fix", "Design", "Research", "Testing")
        }
        tags = {
            name: Tag.objects.get_or_create(name=name)[0]
            for name in ("frontend", "backend", "launch", "accessibility", "quality")
        }
        people = [
            ("demo.user", "Alex", "Morgan", "Project Manager"),
            ("maya.chen", "Maya", "Chen", "Designer"),
            ("jordan.lee", "Jordan", "Lee", "Developer"),
            ("sam.patel", "Sam", "Patel", "Developer"),
            ("olivia.reed", "Olivia", "Reed", "QA Engineer"),
            ("noah.brooks", "Noah", "Brooks", "Developer"),
        ]
        workers = []
        for username, first, last, position in people:
            worker, created = get_user_model().objects.get_or_create(
                username=username,
                defaults={
                    "first_name": first, "last_name": last,
                    "email": f"{username}@example.com",
                    "position": positions[position],
                },
            )
            if created:
                if username == "demo.user":
                    worker.set_password(options["password"])
                else:
                    worker.set_unusable_password()
                worker.save()
            workers.append(worker)
        briefs = [
            ("Refine the onboarding experience", "Design", "high", 2,
             "Map the first-run flow and simplify the welcome screens. "
             "Share a clickable prototype and review it with the team.",
             "frontend", False, [0, 1]),
            ("Ship the new analytics dashboard", "Feature", "urgent", -1,
             "Build the overview metrics, add useful empty states, and "
             "verify the dashboard on mobile before the release.",
             "launch", False, [0, 2]),
            ("Improve API response times", "Bug fix", "high", 4,
             "Profile the busiest endpoints, remove redundant queries, "
             "and document the before-and-after results.",
             "backend", False, [3]),
            ("Audit keyboard navigation", "Testing", "medium", 1,
             "Test navigation, form focus, and task actions with a keyboard. "
             "Log any accessibility gaps with reproduction steps.",
             "accessibility", False, [4, 1]),
            ("Prepare the release checklist", "Research", "medium", 5,
             "Agree on release criteria, test ownership, and a rollback plan. "
             "Share the final checklist with the project team.",
             "launch", False, [0, 4]),
            ("Refresh the design system", "Design", "low", 8,
             "Consolidate button, form, and status badge styles. "
             "Document reusable components and usage examples.",
             "frontend", False, [1]),
            ("Add search regression coverage", "Testing", "high", 3,
             "Cover query escaping, empty results, and pagination. "
             "Confirm that filters continue to work together.",
             "quality", False, [4, 5]),
            ("Simplify account settings", "Feature", "medium", 7,
             "Make profile details easier to find and edit. "
             "Keep security-sensitive settings out of the general profile form.",
             "frontend", False, [2]),
            ("Review task model indexes", "Research", "low", 10,
             "Review common filtering and sorting patterns using realistic data. "
             "Propose indexes only where measurements show a benefit.",
             "backend", False, [3, 5]),
            ("Resolve mobile layout overflow", "Bug fix", "high", -2,
             "Correct the task table overflow on narrow screens and "
             "verify the layout on a range of mobile widths.",
             "frontend", True, [0, 2]),
            ("Write the quality playbook", "Testing", "medium", -3,
             "Document test setup, release checks, and how to report "
             "a useful bug. Include examples from this sprint.",
             "quality", True, [4]),
            ("Define the product milestones", "Research", "medium", -5,
             "Turn the product goals into a clear set of milestones "
             "with measurable acceptance criteria.",
             "launch", True, [0]),
        ]
        today = timezone.localdate()
        for name, kind, priority, offset, description, tag, done, assignees in briefs:
            task, created = Task.objects.get_or_create(
                name=name, defaults={
                    "description": description, "task_type": types[kind],
                    "priority": priority, "deadline": today + timedelta(days=offset),
                    "is_completed": done,
                },
            )
            if created:
                task.tags.add(tags[tag])
                task.assignees.set(workers[index] for index in assignees)
        self.stdout.write(self.style.SUCCESS(
            "Demo workspace ready. New demo.user accounts use the supplied password."
        ))
