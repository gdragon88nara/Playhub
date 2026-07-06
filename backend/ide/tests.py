import shutil
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from games.models import Game
from .models import Project

User = get_user_model()
STRONG_PW = "Sup3rSecret!pw"
GAMES = Path(tempfile.mkdtemp(prefix="gp-test-ide-games-"))
test_games = override_settings(GAMES_ROOT=GAMES)


def make_user(email, username):
    return User.objects.create_user(email=email, username=username, password=STRONG_PW)


@test_games
class IDETests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(GAMES, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.dev = make_user("dev@t.com", "dev")
        self.client.force_authenticate(self.dev)

    def test_create_project_from_template_has_default_files(self):
        res = self.client.post("/api/ide/projects",
                               {"name": "My Game", "template": "html_game"}, format="json")
        self.assertEqual(res.status_code, 201, res.data)
        paths = {f["path"] for f in res.data["files"]}
        self.assertIn("index.html", paths)
        # Language marks are derived from the extension.
        marks = {f["path"]: f["language"]["label"] for f in res.data["files"]}
        self.assertEqual(marks["index.html"], "HTML")
        self.assertEqual(marks["main.js"], "JavaScript")

    def test_python_template_and_run(self):
        res = self.client.post("/api/ide/projects",
                               {"name": "Runner", "template": "python"}, format="json")
        slug = res.data["slug"]
        paths = {f["path"] for f in res.data["files"]}
        self.assertIn("main.py", paths)
        # Run: python main.py
        run = self.client.post(f"/api/ide/projects/{slug}/run")
        self.assertEqual(run.status_code, 200, run.data)
        self.assertEqual(run.data["command"], "python main.py")
        self.assertEqual(run.data["exit_code"], 0)
        self.assertIn("Hello from your game platform project!", run.data["stdout"])

    def test_new_file_requires_name_dot_ext(self):
        res = self.client.post("/api/ide/projects",
                               {"name": "P", "template": "python"}, format="json")
        slug = res.data["slug"]
        bad = self.client.post(f"/api/ide/projects/{slug}/files", {"path": "noext"}, format="json")
        self.assertEqual(bad.status_code, 400)
        ok = self.client.post(f"/api/ide/projects/{slug}/files",
                              {"path": "util.py", "content": "x = 1"}, format="json")
        self.assertEqual(ok.status_code, 201, ok.data)
        self.assertEqual(ok.data["language"]["label"], "Python")

    def test_deploy_html_game_creates_playable_game(self):
        res = self.client.post("/api/ide/projects",
                               {"name": "Deployable", "template": "html_game"}, format="json")
        slug = res.data["slug"]
        dep = self.client.post(f"/api/ide/projects/{slug}/deploy")
        self.assertEqual(dep.status_code, 200, dep.data)
        self.assertEqual(dep.data["status"], "deployed")
        self.assertEqual(dep.data["entry_file"], "index.html")
        self.assertTrue(Game.objects.filter(slug=dep.data["slug"]).exists())

    def test_deploy_story_game_creates_scenes(self):
        res = self.client.post("/api/ide/projects",
                               {"name": "Tale", "template": "story_game"}, format="json")
        slug = res.data["slug"]
        dep = self.client.post(f"/api/ide/projects/{slug}/deploy")
        self.assertEqual(dep.status_code, 200, dep.data)
        self.assertEqual(dep.data["kind"], "story")
        self.assertEqual(dep.data["entry_file"], "scene_0.html")
        self.assertEqual(len(dep.data["scenes"]), 2)
        self.assertEqual(dep.data["scenes"][0]["entry_file"], "scene_0.html")

    def test_run_html_project_returns_preview_mode(self):
        res = self.client.post("/api/ide/projects",
                               {"name": "Web", "template": "html_game"}, format="json")
        slug = res.data["slug"]
        run = self.client.post(f"/api/ide/projects/{slug}/run")
        self.assertEqual(run.status_code, 200, run.data)
        self.assertEqual(run.data["mode"], "preview")
        self.assertEqual(run.data["entry"], "index.html")

    def test_typescript_deploy_emits_runnable_js(self):
        res = self.client.post("/api/ide/projects",
                               {"name": "TS", "template": "typescript_game"}, format="json")
        slug = res.data["slug"]
        dep = self.client.post(f"/api/ide/projects/{slug}/deploy")
        self.assertEqual(dep.status_code, 200, dep.data)
        game = Game.objects.get(slug=dep.data["slug"])
        js = (Path(game.bundle_abs) / "game.js").read_text()
        # Type syntax is stripped so a plain browser can run it.
        self.assertIn("const canvas", js)
        self.assertNotIn("interface Ball", js)
        self.assertNotIn(": number", js)
        self.assertNotIn(": void", js)      # return-type annotations gone
        self.assertNotIn(" as HTML", js)    # `as` casts gone
        self.assertNotIn(')!', js)          # non-null assertions gone

    def test_file_can_live_in_subfolder(self):
        res = self.client.post("/api/ide/projects",
                               {"name": "P", "template": "html_game"}, format="json")
        slug = res.data["slug"]
        ok = self.client.post(f"/api/ide/projects/{slug}/files",
                              {"path": "src/level.js", "content": "x"}, format="json")
        self.assertEqual(ok.status_code, 201, ok.data)
        bad = self.client.post(f"/api/ide/projects/{slug}/files",
                               {"path": "../escape.js"}, format="json")
        self.assertEqual(bad.status_code, 400)

    def test_projects_are_private_to_owner(self):
        res = self.client.post("/api/ide/projects",
                               {"name": "Mine", "template": "python"}, format="json")
        slug = res.data["slug"]
        other = make_user("o@t.com", "other")
        self.client.force_authenticate(other)
        self.assertEqual(self.client.get(f"/api/ide/projects/{slug}").status_code, 404)
