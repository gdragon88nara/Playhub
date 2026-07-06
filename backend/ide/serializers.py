from rest_framework import serializers

from .languages import language_for
from .models import Project, ProjectFile
from .templates import TEMPLATES


class ProjectFileSerializer(serializers.ModelSerializer):
    language = serializers.SerializerMethodField()

    class Meta:
        model = ProjectFile
        fields = ["id", "path", "content", "order", "language", "updated_at"]

    def get_language(self, obj):
        return language_for(obj.path)


class ProjectListSerializer(serializers.ModelSerializer):
    deployed_slug = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ["id", "slug", "name", "kind", "deployed_slug", "updated_at", "created_at"]

    def get_deployed_slug(self, obj):
        return obj.deployed_game.slug if obj.deployed_game_id else None


class ProjectDetailSerializer(ProjectListSerializer):
    files = ProjectFileSerializer(many=True, read_only=True)

    class Meta(ProjectListSerializer.Meta):
        fields = ProjectListSerializer.Meta.fields + ["files"]


class CreateProjectSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    template = serializers.ChoiceField(choices=list(TEMPLATES.keys()), default="html_game")

    def create(self, validated):
        tpl = TEMPLATES[validated["template"]]
        owner = self.context["request"].user
        project = Project.objects.create(name=validated["name"], kind=tpl["kind"], owner=owner)
        ProjectFile.objects.bulk_create([
            ProjectFile(project=project, path=path, content=content, order=i)
            for i, (path, content) in enumerate(tpl["files"])
        ])
        return project


class NewFileSerializer(serializers.Serializer):
    """A file is named ``name.ext`` and may live in a subfolder (``src/main.js``).
    The extension drives its language mark."""

    # Allow nested folders; each segment is name(.ext optional for dirs) but the
    # final segment must have an extension. No traversal, no absolute paths.
    path = serializers.RegexField(
        r"^(?:[A-Za-z0-9_\-]+/)*[A-Za-z0-9_\-]+\.[A-Za-z0-9]+$",
        error_messages={"invalid": "Use name.ext, optionally in a folder (e.g. src/level.js)."},
    )
    content = serializers.CharField(allow_blank=True, default="")

    def validate_path(self, value):
        if ".." in value.split("/") or value.startswith("/"):
            raise serializers.ValidationError("Path may not escape the project.")
        return value
