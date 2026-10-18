from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Tag, Task, TaskType


class WorkerCreationForm(UserCreationForm):
    email = forms.EmailField()

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = UserCreationForm.Meta.fields + (
            "first_name", "last_name", "email", "position",
        )


class WorkerUpdateForm(forms.ModelForm):
    email = forms.EmailField()

    class Meta:
        model = get_user_model()
        fields = ("first_name", "last_name", "email", "position")


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = (
            "name", "description", "deadline", "priority",
            "task_type", "assignees", "tags", "is_completed",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "deadline": forms.DateInput(attrs={"type": "date"}),
            "assignees": forms.CheckboxSelectMultiple,
            "tags": forms.CheckboxSelectMultiple,
        }


class TaskFilterForm(forms.Form):
    q = forms.CharField(
        required=False, label="Search tasks",
        widget=forms.TextInput(attrs={"placeholder": "Name or description"}),
    )
    status = forms.ChoiceField(
        required=False, choices=(
            ("", "All statuses"), ("active", "Active"), ("done", "Completed"),
        ),
    )
    priority = forms.ChoiceField(
        required=False,
        choices=[("", "All priorities")] + list(Task.Priority.choices),
    )
    task_type = forms.ModelChoiceField(
        queryset=TaskType.objects.all(), required=False, empty_label="All types"
    )
    tag = forms.ModelChoiceField(
        queryset=Tag.objects.all(), required=False, empty_label="All tags"
    )
    mine = forms.BooleanField(required=False, label="Assigned to me")


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"
            else:
                field.widget.attrs["class"] = "form-control"
