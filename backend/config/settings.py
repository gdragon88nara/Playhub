"""
Django settings for the game-platform backend.

Environment-driven: SQLite + in-memory channel layer for local dev,
Postgres + Redis for production (set DATABASE_URL / REDIS_URL).
"""

from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
# Read a .env file next to manage.py if present.
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(str(env_file))

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
SECRET_KEY = env("SECRET_KEY", default="dev-insecure-change-me")
DEBUG = env.bool("DEBUG", default=True)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

AUTH_USER_MODEL = "accounts.User"

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "daphne",  # ASGI server; must precede staticfiles for runserver override
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "channels",
]

LOCAL_APPS = [
    "accounts",
    "games",
    "community",
    "chat",
    "shorts",
    "ide",
    "payments",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Serves collected static files in production (Render) without nginx.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Restricts game bundles to being embedded only by our own frontend.
    "games.middleware.GameEmbedPolicyMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Database  (SQLite by default; DATABASE_URL switches to Postgres)
# ---------------------------------------------------------------------------
if env("DATABASE_URL", default=""):
    DATABASES = {"default": env.db("DATABASE_URL")}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ---------------------------------------------------------------------------
# Channels  (in-memory for dev; Redis for prod)
# ---------------------------------------------------------------------------
if env("REDIS_URL", default=""):
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [env("REDIS_URL")]},
        }
    }
else:
    CHANNEL_LAYERS = {
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
    }

# ---------------------------------------------------------------------------
# Auth / passwords
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# DRF + JWT
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=env.int("ACCESS_TOKEN_LIFETIME_MIN", default=30)
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=env.int("REFRESH_TOKEN_LIFETIME_DAYS", default=7)
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,
    "UPDATE_LAST_LOGIN": True,
}

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
FRONTEND_ORIGIN = env("FRONTEND_ORIGIN", default="http://localhost:3000")
CORS_ALLOWED_ORIGINS = [FRONTEND_ORIGIN]
# Any Render frontend (*.onrender.com) may call the API, so a manual Render
# deploy works without pinning FRONTEND_ORIGIN to the exact suffixed URL.
CORS_ALLOWED_ORIGIN_REGEXES = [r"^https://[a-z0-9-]+\.onrender\.com$"]
CORS_ALLOW_CREDENTIALS = True

# Origins allowed to embed (iframe) game bundles — our own frontend plus any
# Render frontend, so games stay playable only inside the site.
GAME_FRAME_ANCESTORS = env.list(
    "GAME_FRAME_ANCESTORS", default=[FRONTEND_ORIGIN, "https://*.onrender.com"]
)

# ---------------------------------------------------------------------------
# i18n
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static / media
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# Public media (avatars, game thumbnails) — safe to serve directly.
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Protected content is NEVER served as public static files. It is streamed only
# through Django views that enforce visibility/access — this is what keeps games
# and private posts playable/viewable *only inside the site*.
PROTECTED_ROOT = BASE_DIR / "protected"
GAMES_ROOT = PROTECTED_ROOT / "games"
POSTS_ROOT = PROTECTED_ROOT / "posts"
SHORTS_ROOT = PROTECTED_ROOT / "shorts"
DM_ROOT = PROTECTED_ROOT / "dm"

# Signed short-lived access grants (play/view cookies).
PLAY_COOKIE_MAX_AGE = 60 * 60 * 6   # 6 hours

# ---------------------------------------------------------------------------
# Payments (marketplace via Stripe Connect). No keys yet -> "simulation" mode:
# the split math runs and Purchase records are created, but no real charge.
# ---------------------------------------------------------------------------
PLATFORM_COMMISSION_RATE = env.float("PLATFORM_COMMISSION_RATE", default=0.20)
STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY", default="")
STRIPE_PUBLISHABLE_KEY = env("STRIPE_PUBLISHABLE_KEY", default="")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET", default="")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# WhiteNoise compressed, hashed static files in production.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
        if not DEBUG
        else "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}

# Behind Render's proxy, honour the forwarded host and CSRF origins. Any Render
# subdomain is trusted so the admin/login works on the auto-assigned URL.
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS", default=[FRONTEND_ORIGIN, "https://*.onrender.com"]
)
USE_X_FORWARDED_HOST = True

# ---------------------------------------------------------------------------
# Production hardening (only when DEBUG is off)
# ---------------------------------------------------------------------------
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_CONTENT_TYPE_NOSNIFF = True
