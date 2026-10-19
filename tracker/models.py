from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
from django.utils import timezone


class NamedModel(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        abstract = True
        ordering = ("name",)

    def __str__(self):
        return self.name


class Position(NamedModel):
    pass


class TaskType(NamedModel):
    pass


class Tag(NamedModel):
    pass


class Worker(AbstractUser):
    position = models.ForeignKey(
        Position, on_delete=models.PROTECT, related_name="workers"
    )
    REQUIRED_FIELDS = ["email", "position"]

    class Meta:
        ordering = ("username",)

    def __str__(self):
        return self.get_full_name() or self.username

    def get_absolute_url(self):
        return reverse("tracker:worker-detail", args=[self.pk])


class Task(models.Model):
    class Priority(models.TextChoices):
        URGENT = "urgent", "Urgent"
        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"

    name = models.CharField(max_length=200)
    description = models.TextField()
    deadline = models.DateField()
    is_completed = models.BooleanField(default=False)
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.MEDIUM
    )
    task_type = models.ForeignKey(
        TaskType, on_delete=models.PROTECT, related_name="tasks"
    )
    assignees = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="tasks", blank=True
    )
    tags = models.ManyToManyField(Tag, related_name="tasks", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("is_completed", "deadline", "pk")

    def __str__(self):
        return self.name

    @property
    def is_overdue(self):
        return not self.is_completed and self.deadline < timezone.localdate()

    def get_absolute_url(self):
        return reverse("tracker:task-detail", args=[self.pk])
