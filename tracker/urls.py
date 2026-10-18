from django.urls import path

from . import views

app_name = "tracker"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("tasks/", views.TaskListView.as_view(), name="task-list"),
    path("tasks/new/", views.TaskCreateView.as_view(), name="task-create"),
    path("tasks/<int:pk>/", views.TaskDetailView.as_view(), name="task-detail"),
    path("tasks/<int:pk>/edit/", views.TaskUpdateView.as_view(), name="task-update"),
    path("tasks/<int:pk>/delete/", views.TaskDeleteView.as_view(), name="task-delete"),
    path("tasks/<int:pk>/status/", views.task_status, name="task-status"),
    path("tasks/<int:pk>/assignment/", views.task_assignment, name="task-assignment"),
    path("people/", views.WorkerListView.as_view(), name="worker-list"),
    path("people/new/", views.WorkerCreateView.as_view(), name="worker-create"),
    path("people/<int:pk>/", views.WorkerDetailView.as_view(), name="worker-detail"),
    path("people/<int:pk>/edit/", views.WorkerUpdateView.as_view(), name="worker-update"),
    path("people/<int:pk>/delete/", views.WorkerDeleteView.as_view(), name="worker-delete"),
    path("settings/<str:kind>/", views.CatalogListView.as_view(), name="catalog-list"),
    path("settings/<str:kind>/new/", views.CatalogCreateView.as_view(), name="catalog-create"),
    path("settings/<str:kind>/<int:pk>/edit/", views.CatalogUpdateView.as_view(),
         name="catalog-update"),
    path("settings/<str:kind>/<int:pk>/delete/", views.CatalogDeleteView.as_view(),
         name="catalog-delete"),
]
