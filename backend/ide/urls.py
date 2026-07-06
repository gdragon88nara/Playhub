from django.urls import path

from . import views

urlpatterns = [
    path("ide/templates", views.TemplateListView.as_view(), name="ide_templates"),
    path("ide/projects", views.ProjectListCreateView.as_view(), name="ide_projects"),
    path("ide/projects/<slug:slug>", views.ProjectDetailView.as_view(), name="ide_project"),
    path("ide/projects/<slug:slug>/files", views.ProjectFilesView.as_view(), name="ide_files"),
    path("ide/projects/<slug:slug>/run", views.RunView.as_view(), name="ide_run"),
    path("ide/projects/<slug:slug>/deploy", views.DeployView.as_view(), name="ide_deploy"),
    path("ide/files/<int:pk>", views.ProjectFileDetailView.as_view(), name="ide_file"),
]
