from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from games.serializers import GameDetailSerializer
from .deploy import DeployError, deploy_project
from .models import Project, ProjectFile
from .runner import run_project
from .serializers import (
    CreateProjectSerializer,
    NewFileSerializer,
    ProjectDetailSerializer,
    ProjectFileSerializer,
    ProjectListSerializer,
)
from .templates import TEMPLATES


class TemplateListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response([
            {"id": k, "label": v["label"], "kind": v["kind"]} for k, v in TEMPLATES.items()
        ])


class ProjectListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Project.objects.filter(owner=self.request.user)

    def get_serializer_class(self):
        return CreateProjectSerializer if self.request.method == "POST" else ProjectListSerializer

    def create(self, request, *args, **kwargs):
        ser = CreateProjectSerializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        project = ser.save()
        return Response(
            ProjectDetailSerializer(project, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ProjectDetailView(generics.RetrieveDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProjectDetailSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return Project.objects.filter(owner=self.request.user).prefetch_related("files")


def _own_project(request, slug) -> Project:
    project = get_object_or_404(Project, slug=slug)
    if project.owner_id != request.user.id:
        raise PermissionDenied("Not your project.")
    return project


class ProjectFilesView(APIView):
    """POST /api/ide/projects/<slug>/files — add a file named name.ext."""

    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        project = _own_project(request, slug)
        ser = NewFileSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        if project.files.filter(path=ser.validated_data["path"]).exists():
            raise ValidationError({"path": "A file with that name already exists."})
        f = ProjectFile.objects.create(
            project=project,
            path=ser.validated_data["path"],
            content=ser.validated_data["content"],
            order=project.files.count(),
        )
        return Response(ProjectFileSerializer(f).data, status=status.HTTP_201_CREATED)


class ProjectFileDetailView(APIView):
    """PATCH/DELETE /api/ide/files/<id> — save content or delete a file."""

    permission_classes = [IsAuthenticated]

    def _get(self, request, pk):
        f = get_object_or_404(ProjectFile.objects.select_related("project"), pk=pk)
        if f.project.owner_id != request.user.id:
            raise PermissionDenied("Not your file.")
        return f

    def patch(self, request, pk):
        f = self._get(request, pk)
        f.content = request.data.get("content", f.content)
        f.save(update_fields=["content", "updated_at"])
        return Response(ProjectFileSerializer(f).data)

    def delete(self, request, pk):
        f = self._get(request, pk)
        f.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RunView(APIView):
    """POST /api/ide/projects/<slug>/run — language-aware run.

    Web projects run live in the browser webview (mode=preview); Python runs in
    the server terminal (mode=terminal). The frontend keys off ``mode``."""

    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        project = _own_project(request, slug)
        files = {f.path: f.content for f in project.files.all()}
        return Response(run_project(files))


class DeployView(APIView):
    """POST /api/ide/projects/<slug>/deploy — build a playable Game bundle."""

    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        project = _own_project(request, slug)
        try:
            game = deploy_project(project)
        except DeployError as exc:
            raise ValidationError({"detail": str(exc)})
        return Response(
            GameDetailSerializer(game, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )
