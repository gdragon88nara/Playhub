"""
Games domain.

A Game is a playable bundle uploaded by a user:
* ``engine=html``        — an HTML/JS/Three.js game; the entry file is an HTML
  document opened in a sandboxed iframe.
* ``engine=unity_webgl`` — a Unity WebGL export folder (index.html + Build/…).

The uploaded ZIP is extracted to ``MEDIA_ROOT/games/<id>/`` and served as static
files. Visibility is layered on top of account privacy:
* ``public``    — anyone can see/play (unless the owner is a private account).
* ``followers`` — only accepted followers (and the owner).
* ``private``   — only the owner.

Monetisation is a marketplace: the platform never charges directly. ``is_paid``
+ ``price`` describe the listing; actual payment (buyer→seller split with the
platform's commission) is handled by the payments app in a later phase.
"""

from django.conf import settings
from django.db import models
from django.utils.text import slugify
from django.utils.crypto import get_random_string


class Game(models.Model):
    class Engine(models.TextChoices):
        HTML = "html", "HTML / JS / Three.js"
        UNITY_WEBGL = "unity_webgl", "Unity WebGL"

    class Kind(models.TextChoices):
        NORMAL = "normal", "Normal game"
        STORY = "story", "Story game (scene-based)"

    class Genre(models.TextChoices):
        ACTION = "action", "Action"
        ADVENTURE = "adventure", "Adventure"
        RPG = "rpg", "RPG"
        SHOOTER = "shooter", "Shooter"
        PLATFORMER = "platformer", "Platformer"
        PUZZLE = "puzzle", "Puzzle"
        ARCADE = "arcade", "Arcade"
        STRATEGY = "strategy", "Strategy"
        SIMULATION = "simulation", "Simulation"
        SPORTS = "sports", "Sports"
        RACING = "racing", "Racing"
        HORROR = "horror", "Horror"
        CASUAL = "casual", "Casual"
        OTHER = "other", "Other"

    class Visibility(models.TextChoices):
        PUBLIC = "public", "Public"
        FOLLOWERS = "followers", "Followers only"
        PRIVATE = "private", "Private (only me)"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        DEPLOYED = "deployed", "Deployed"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="games"
    )
    title = models.CharField(max_length=120)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    description = models.TextField(blank=True)

    engine = models.CharField(max_length=16, choices=Engine.choices, default=Engine.HTML)
    kind = models.CharField(max_length=8, choices=Kind.choices, default=Kind.NORMAL)
    genre = models.CharField(max_length=16, choices=Genre.choices, default=Genre.OTHER)
    visibility = models.CharField(
        max_length=10, choices=Visibility.choices, default=Visibility.PUBLIC
    )
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.DRAFT)

    # Path to the entry document inside the extracted bundle.
    entry_file = models.CharField(max_length=255, default="index.html")
    thumbnail = models.ImageField(upload_to="game_thumbs/", blank=True, null=True)

    # Marketplace listing (payment handled later by the payments app).
    is_paid = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="USD")

    play_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deployed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["visibility", "status"]),
            models.Index(fields=["owner"]),
            models.Index(fields=["genre", "status"]),
        ]

    def __str__(self):
        return f"{self.title} (@{self.owner.username})"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title) or "game"
            self.slug = f"{base}-{get_random_string(6).lower()}"
        super().save(*args, **kwargs)

    @property
    def bundle_abs(self):
        """Absolute dir (under the protected root) holding the extracted bundle.
        NOT publicly served — reachable only via the authenticated serve view."""
        return settings.GAMES_ROOT / str(self.pk)

    @property
    def play_url(self) -> str:
        # Routed to the authenticated Django serve view, not static files.
        return f"{settings.MEDIA_URL}games/{self.pk}/{self.entry_file}"

    @property
    def likes_count(self) -> int:
        return self.likes.count()

    def visible_to(self, viewer) -> bool:
        """Combine per-game visibility with the owner's account privacy."""
        is_owner = bool(viewer and viewer.is_authenticated and viewer.pk == self.owner_id)
        if self.status != self.Status.DEPLOYED and not is_owner:
            return False  # drafts are owner-only
        if is_owner:
            return True
        if self.visibility == self.Visibility.PRIVATE:
            return False
        if self.visibility == self.Visibility.FOLLOWERS or self.owner.is_private:
            if viewer is None or not viewer.is_authenticated:
                return False
            from accounts.models import Follow
            return Follow.objects.filter(follower=viewer, following=self.owner).exists()
        return True  # public game, public owner


class GameScene(models.Model):
    """A single scene of a story game. On deploy, scenes chain in ``order``:
    finishing one advances to the next automatically on the client."""

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="scenes")
    order = models.PositiveIntegerField(default=0)
    title = models.CharField(max_length=120, blank=True)
    # Entry file for this scene within the bundle.
    entry_file = models.CharField(max_length=255)

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(fields=["game", "order"], name="uniq_scene_order")
        ]

    def __str__(self):
        return f"{self.game.title} · scene {self.order}"


class Like(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "game"], name="uniq_like")
        ]


class Comment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="comments")
    body = models.CharField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class SavedGame(models.Model):
    """A user's saved/bookmarked game (their personal library)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_games"
    )
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="saved_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "game"], name="uniq_saved_game")
        ]
