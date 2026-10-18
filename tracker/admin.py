from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Position, Tag, Task, TaskType, Worker


@admin.register(Worker)
class WorkerAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Work", {"fields": ("position",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Work", {"fields": ("position", "first_name", "last_name", "email")}),
    )
    list_display = ("username", "first_name", "last_name", "position", "is_staff")
    list_filter = UserAdmin.list_filter + ("position",)
    list_select_related = ("position",)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("name", "priority", "deadline", "is_completed", "task_type")
    list_filter = ("is_completed", "priority", "task_type", "tags")
    search_fields = ("name", "description", "assignees__username")
    filter_horizontal = ("assignees", "tags")
    list_select_related = ("task_type",)


@admin.register(Position, TaskType, Tag)
class NamedAdmin(admin.ModelAdmin):
    search_fields = ("name",)
