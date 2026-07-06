"""Deploy a Project's files into a playable Game bundle."""

import os
import re
import shutil

from django.utils import timezone

from games.models import Game, GameScene
from .transpile import strip_types, to_js_name

SCENE_RE = re.compile(r"^scene_(\d+)\.html$")


class DeployError(Exception):
    pass


def _write_files(dest_abs, files: dict):
    if os.path.exists(dest_abs):
        shutil.rmtree(dest_abs)
    os.makedirs(dest_abs, exist_ok=True)
    for path, content in files.items():
        target = os.path.abspath(os.path.join(dest_abs, path))
        if os.path.commonpath([dest_abs]) != os.path.commonpath([dest_abs, target]):
            raise DeployError(f"Unsafe file path: {path}")
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as fh:
            fh.write(content)


def _compile_web_assets(files: dict) -> dict:
    """Emit a browser-runnable ``.js`` next to every ``.ts``/``.tsx`` source so a
    deployed game runs in a plain browser (index.html references the .js)."""
    out = dict(files)
    for path, content in files.items():
        js_name = to_js_name(path)
        if js_name != path:
            out.setdefault(js_name, strip_types(content))
    return out


def deploy_project(project) -> Game:
    """Create (or update) the project's deployed Game and write its bundle."""
    files = {f.path: f.content for f in project.files.all()}
    if not files:
        raise DeployError("Project has no files.")
    files = _compile_web_assets(files)

    if project.kind == project.Kind.STORY:
        scenes = sorted(
            ((int(m.group(1)), name) for name in files if (m := SCENE_RE.match(name))),
            key=lambda t: t[0],
        )
        if not scenes:
            raise DeployError("Story projects need scene_0.html, scene_1.html, …")
        entry = scenes[0][1]
        kind = Game.Kind.STORY
    else:
        if "index.html" not in files:
            raise DeployError("Add an index.html to deploy this game.")
        entry = "index.html"
        scenes = []
        kind = Game.Kind.NORMAL

    game = project.deployed_game
    if game is None:
        game = Game(owner=project.owner, title=project.name, engine=Game.Engine.HTML)
    game.kind = kind
    game.entry_file = entry
    game.status = Game.Status.DEPLOYED
    game.deployed_at = timezone.now()
    game.save()

    _write_files(str(game.bundle_abs), files)

    if kind == Game.Kind.STORY:
        game.scenes.all().delete()
        GameScene.objects.bulk_create([
            GameScene(game=game, order=order, entry_file=name, title=f"Scene {order + 1}")
            for order, name in scenes
        ])

    project.deployed_game = game
    project.save(update_fields=["deployed_game", "updated_at"])
    return game
