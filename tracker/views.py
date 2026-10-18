from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import generic
from django.views.decorators.http import require_POST

from .forms import TaskFilterForm, TaskForm, WorkerCreationForm, WorkerUpdateForm
from .models import Position, Tag, Task, TaskType


@login_required
def dashboard(request):
    tasks = Task.objects.select_related("task_type").prefetch_related("assignees")
    active = tasks.filter(is_completed=False)
    total = tasks.count()
    completed = tasks.filter(is_completed=True).count()
    return render(
        request,
        "tracker/dashboard.html",
        {
            "active_count": active.count(),
            "completed_count": completed,
            "overdue_count": active.filter(deadline__lt=timezone.localdate()).count(),
            "worker_count": get_user_model().objects.count(),
            "completion_percent": round(completed * 100 / total) if total else 0,
            "upcoming_tasks": active.order_by("deadline", "pk")[:5],
            "my_tasks": active.filter(assignees=request.user)[:4],
        },
    )


class QueryContextMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.copy()
        query.pop("page", None)
        context["query_string"] = query.urlencode()
        return context


class TaskListView(LoginRequiredMixin, QueryContextMixin, generic.ListView):
    model = Task
    paginate_by = 8

    def get_queryset(self):
        queryset = Task.objects.select_related("task_type").prefetch_related(
            "assignees", "tags"
        )
        self.filter_form = TaskFilterForm(self.request.GET)
        if not self.filter_form.is_valid():
            return queryset.none()
        data = self.filter_form.cleaned_data
        if data["q"]:
            queryset = queryset.filter(
                Q(name__icontains=data["q"]) | Q(description__icontains=data["q"])
            )
        if data["status"]:
            queryset = queryset.filter(is_completed=data["status"] == "done")
        for field in ("priority", "task_type"):
            if data[field]:
                queryset = queryset.filter(**{field: data[field]})
        if data["tag"]:
            queryset = queryset.filter(tags=data["tag"])
        if data["mine"]:
            queryset = queryset.filter(assignees=self.request.user)
        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = self.filter_form
        return context


class TaskDetailView(LoginRequiredMixin, generic.DetailView):
    queryset = Task.objects.select_related("task_type").prefetch_related(
        "assignees__position", "tags"
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_assigned"] = self.request.user in self.object.assignees.all()
        return context


class TaskCreateView(LoginRequiredMixin, generic.CreateView):
    model = Task
    form_class = TaskForm


class TaskUpdateView(LoginRequiredMixin, generic.UpdateView):
    model = Task
    form_class = TaskForm


class TaskDeleteView(LoginRequiredMixin, generic.DeleteView):
    model = Task
    success_url = reverse_lazy("tracker:task-list")


@login_required
@require_POST
def task_status(request, pk):
    task = get_object_or_404(Task, pk=pk)
    value = request.POST.get("completed")
    if value not in ("0", "1"):
        messages.error(request, "Choose a valid task status.")
    else:
        task.is_completed = value == "1"
        task.save(update_fields=["is_completed"])
        messages.success(request, "Task status updated.")
    return redirect(task)


@login_required
@require_POST
def task_assignment(request, pk):
    task = get_object_or_404(Task, pk=pk)
    action = request.POST.get("action")
    if action == "join":
        task.assignees.add(request.user)
        messages.success(request, "You are now assigned to this task.")
    elif action == "leave":
        task.assignees.remove(request.user)
        messages.success(request, "You have left this task.")
    else:
        messages.error(request, "Choose a valid assignment action.")
    return redirect(task)


class WorkerListView(LoginRequiredMixin, QueryContextMixin, generic.ListView):
    model = get_user_model()
    paginate_by = 8

    def get_queryset(self):
        queryset = (
            get_user_model()
            .objects.select_related("position")
            .annotate(
                active_count=Count("tasks", filter=Q(tasks__is_completed=False)),
                done_count=Count("tasks", filter=Q(tasks__is_completed=True)),
            )
            .order_by("username")
        )
        query = self.request.GET.get("q", "").strip()
        if query:
            queryset = queryset.filter(
                Q(username__icontains=query)
                | Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(email__icontains=query)
            )
        return queryset


class WorkerDetailView(LoginRequiredMixin, generic.DetailView):
    queryset = get_user_model().objects.select_related("position")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tasks = self.object.tasks.select_related("task_type")
        context["active_tasks"] = tasks.filter(is_completed=False)
        context["completed_tasks"] = tasks.filter(is_completed=True)
        return context


class WorkerCreateView(LoginRequiredMixin, generic.CreateView):
    model = get_user_model()
    form_class = WorkerCreationForm


class WorkerUpdateView(LoginRequiredMixin, generic.UpdateView):
    model = get_user_model()
    form_class = WorkerUpdateForm


class WorkerDeleteView(LoginRequiredMixin, generic.DeleteView):
    model = get_user_model()
    success_url = reverse_lazy("tracker:worker-list")


CATALOGS = {
    "positions": (Position, "Positions", "position"),
    "types": (TaskType, "Task types", "task type"),
    "tags": (Tag, "Tags", "tag"),
}


class CatalogMixin:
    def dispatch(self, request, *args, **kwargs):
        self.kind = kwargs["kind"]
        if self.kind not in CATALOGS:
            raise Http404
        self.model, self.catalog_title, self.singular = CATALOGS[self.kind]
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse("tracker:catalog-list", args=[self.kind])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            kind=self.kind,
            catalog_title=self.catalog_title,
            singular=self.singular,
            cancel_url=self.get_success_url(),
        )
        return context


class CatalogListView(
    LoginRequiredMixin, CatalogMixin, QueryContextMixin, generic.ListView
):
    template_name = "tracker/catalog_list.html"
    context_object_name = "items"
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get("q", "").strip()
        if query:
            queryset = queryset.filter(name__icontains=query)
        return queryset


class CatalogCreateView(LoginRequiredMixin, CatalogMixin, generic.CreateView):
    fields = ("name",)
    template_name = "tracker/catalog_form.html"


class CatalogUpdateView(LoginRequiredMixin, CatalogMixin, generic.UpdateView):
    fields = ("name",)
    template_name = "tracker/catalog_form.html"


class CatalogDeleteView(LoginRequiredMixin, CatalogMixin, generic.DeleteView):
    template_name = "tracker/catalog_confirm_delete.html"

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except ProtectedError:
            messages.error(
                self.request,
                "This item is in use. Reassign its workers or tasks before deleting it.",
            )
            return self.render_to_response(self.get_context_data(form=form))
