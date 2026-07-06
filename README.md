# Game Platform

A community platform for uploading and playing browser games (Unity WebGL +
HTML/JS/Three.js), with an Instagram-style social layer, realtime chat/voice,
an in-browser game IDE, and a marketplace for paid games.

> **Status:** Phase 0–1 complete — project foundation + accounts + follow graph.
> See the [Roadmap](#roadmap) for what's next.

---

## Architecture

| Concern            | Choice                                                        |
| ------------------ | ------------------------------------------------------------- |
| Backend API        | Django 5 + Django REST Framework                              |
| Auth               | JWT (SimpleJWT); email is the login identity, `username` is the public @handle |
| Realtime           | Django Channels (WebSocket) + Redis — DM, open chat, notifications, WebRTC signalling |
| Voice (planned)    | WebRTC + SFU (LiveKit/mediasoup) for group calls that survive navigation |
| Frontend           | Next.js (React) SPA calling the Django API                    |
| DB                 | SQLite for local dev · PostgreSQL in production               |
| Payments (planned) | **Marketplace model** via Stripe Connect / PortOne            |
| Code execution     | Phase 1: browser-run games only · Phase 2: sandboxed server runtimes |

### Payments security model (why we're safe by design)

The platform **never touches raw financial data**. We do not store card numbers,
bank accounts, or national IDs. Instead:

- Sellers complete the payment provider's **hosted onboarding** (Stripe Connect
  / PortOne). We keep only an opaque `provider_account_id` reference.
- At checkout, the provider connects **buyer → seller** directly and splits the
  payment, routing the platform's **20% commission** to our account
  automatically (`SellerProfile.commission_rate`, default `0.20`).
- This delegates PCI/KYC liability to the provider — so a breach of our DB
  exposes no financial secrets. This directly satisfies the requirement to
  "never ask for information that would be a legal/hacking liability."

---

## Repository layout

```
game platform/
├── backend/            Django + DRF + Channels API
│   ├── config/         project settings, urls, asgi
│   ├── accounts/       User, SellerProfile, Follow, FollowRequest
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/           Next.js app (scaffolded next)
├── docs/
├── docker-compose.yml  Postgres + Redis + backend + frontend (for later)
└── README.md
```

---

## Running the backend (local dev, no Docker needed)

```bash
cd backend
# venv already created at backend/.venv
.venv/Scripts/python.exe manage.py migrate          # Windows
# source .venv/bin/activate && python manage.py migrate   # macOS/Linux

# create an admin user
.venv/Scripts/python.exe manage.py createsuperuser

# run the ASGI dev server
.venv/Scripts/python.exe manage.py runserver
```

API is at `http://localhost:8000/api/`. Admin at `/admin/`.

Copy `backend/.env.example` → `backend/.env` to override defaults (SECRET_KEY,
`DATABASE_URL` for Postgres, `REDIS_URL` for Redis, JWT lifetimes).

Run the tests:

```bash
cd backend && .venv/Scripts/python.exe manage.py test
```

### Production stack

```bash
docker compose up --build   # Postgres + Redis + Daphne ASGI + Next.js
```

---

## API (Phase 1)

| Method       | Path                                        | Purpose                              |
| ------------ | ------------------------------------------- | ------------------------------------ |
| `GET`        | `/api/health`                               | health check                         |
| `POST`       | `/api/auth/register`                        | create account (`become_seller` opt) |
| `POST`       | `/api/auth/login`                           | email + password → JWT pair          |
| `POST`       | `/api/auth/refresh`                         | refresh access token                 |
| `GET/PATCH`  | `/api/me`                                   | read/update own profile              |
| `GET`        | `/api/users/<username>`                     | public profile                       |
| `POST/DELETE`| `/api/users/<username>/follow`              | follow / unfollow (or request)       |
| `GET`        | `/api/users/<username>/followers`           | followers (privacy-gated)            |
| `GET`        | `/api/users/<username>/following`           | following (privacy-gated)            |
| `GET`        | `/api/follow-requests`                      | incoming pending requests            |
| `POST`       | `/api/follow-requests/<id>/accept`          | accept → **auto mutual follow**      |
| `POST`       | `/api/follow-requests/<id>/reject`          | reject                               |
| `GET`        | `/api/games`                                | feed (`?owner=`, `?mine=1`), visibility-gated |
| `POST`       | `/api/games`                                | create + (with `bundle` ZIP) **deploy** |
| `GET/PATCH/DELETE` | `/api/games/<slug>`                   | game detail / edit / delete          |
| `POST`       | `/api/games/<slug>/bundle`                  | (re)upload bundle & deploy           |
| `POST`       | `/api/games/<slug>/play`                    | register play → returns play URL     |
| `POST/DELETE`| `/api/games/<slug>/like`                    | like / unlike                        |
| `POST/DELETE`| `/api/games/<slug>/save`                    | save / unsave to library             |
| `GET/POST`   | `/api/games/<slug>/comments`                | list / add comments                  |
| `GET`        | `/api/me/saved`                             | your saved-game library              |
| `GET`        | `/api/posts`                                | timeline (`?user=`, `?feed=explore`) |
| `POST`       | `/api/posts`                                | create post (text + image/video media) |
| `GET/DELETE` | `/api/posts/<id>`                           | post detail / delete                 |
| `POST/DELETE`| `/api/posts/<id>/like`                      | like / unlike                        |
| `GET/POST`   | `/api/posts/<id>/comments`                  | list / add comments                  |
| `GET`        | `/api/dm/threads`                           | my DM conversations                  |
| `POST`       | `/api/dm/with/<username>`                    | get/create a DM thread               |
| `GET`        | `/api/dm/threads/<id>/messages`             | DM history (participants only)       |
| `GET`        | `/api/rooms`                                | open realtime rooms (auto-seeded)    |
| `GET`        | `/api/rooms/<slug>/messages`                | room history                         |
| `GET/POST`   | `/api/shorts`                               | shorts feed / upload short video     |
| `POST/DELETE`| `/api/shorts/<id>/like`                     | like / unlike a short                |
| WS           | `/ws/dm/<thread_id>/?token=<jwt>`           | realtime 1:1 DM                      |
| WS           | `/ws/room/<slug>/?token=<jwt>`              | realtime open chat room              |
| WS           | `/ws/voice/<room>/?token=<jwt>`             | WebRTC voice signalling              |
| `GET/POST`   | `/api/ide/projects`                         | list / create IDE project (template) |
| `GET/DELETE` | `/api/ide/projects/<slug>`                  | project detail / delete              |
| `POST`       | `/api/ide/projects/<slug>/files`            | add file (named `name.ext`)          |
| `PATCH/DELETE`| `/api/ide/files/<id>`                       | save / delete file                   |
| `POST`       | `/api/ide/projects/<slug>/run`              | terminal: `python main.py`           |
| `POST`       | `/api/ide/projects/<slug>/deploy`           | build a playable Game (+story scenes)|
| `POST`       | `/api/payments/checkout/<slug>`             | buy paid game (20% split)            |
| `POST`       | `/api/payments/confirm/<id>`                | simulation: confirm (stands in for webhook) |
| `GET`        | `/api/payments/purchases`                   | my purchases                         |

### In-site-only content serving

Games and private post media are **never public files**. They live under a
protected root (`backend/protected/`) and are streamed only by authenticated
Django views:

- **Games** (`/media/games/<id>/…`) require a short-lived **signed play cookie**
  issued by `POST /api/games/<slug>/play` after a visibility check. A middleware
  attaches `Content-Security-Policy: frame-ancestors <our frontend>` so a game
  can only be embedded by our own site — never hotlinked or iframed elsewhere.
- **Post media** (`/media/posts/<id>/…`) uses per-URL **signed tokens** minted by
  the serializer only for viewers allowed to see the post.

Public media (avatars, game thumbnails) is served normally from `media/`.

**Follow semantics:** following a public account is instant and one-directional.
Following a private account creates a pending request; when the target accepts,
both directions are created automatically (mutual follow) — even for private
accounts, with no separate request from the target.

---

## Roadmap

- [x] **Phase 0** — Foundation: Django + DRF + Channels + env settings + Docker
- [x] **Phase 1** — Accounts: normal/seller signup, public/private, follow + auto mutual-follow
- [x] **Phase 2** — Games: Unity WebGL folder + HTML/JS upload & one-click deploy, sandboxed play, likes, comments, saved library, story-scene model
- [x] **Phase 3** — Community: Instagram-style feed, image/video upload, likes, comments, follow-based timeline + explore; in-site-only serving for games & private media
- [x] **Phase 4** — Realtime: 1:1 DM + open realtime chat rooms over WebSocket (Channels, JWT-authed); short-form vertical video (Shorts); dark theme, zero emoji
- [x] **Phase 5** — Web IDE: templates named `name.ext` with per-language marks, default config code pre-placed, terminal `python main.py`, one-click Deploy; story-game scene auto-advance
- [x] **Phase 6 (baseline)** — Discord-style voice: WebRTC P2P signalling over Channels + app-shell `CallProvider` so calls persist across navigation/gameplay. *SFU (LiveKit/mediasoup) + TURN needed for large rooms/production — next.*
- [x] **Phase 7 (structure)** — Marketplace: Stripe Connect gateway with **20% commission split**, Purchase records; runs in simulation until API keys are set.
- [~] **Phase 8** — Python runs in the IDE terminal now (dev executor). **Remaining:** secure sandbox (Docker + gVisor / Judge0) for untrusted C/C++/Python, and realtime battle-royale netcode.

## Deploy to Render

`render.yaml` is a Render Blueprint provisioning Postgres + Redis (Key Value) +
the Django/Channels ASGI backend (Daphne) + the Next.js frontend. Redis makes
realtime low-latency and horizontally scalable in production. Push to GitHub,
then in Render pick **New → Blueprint** and select the repo. Set `STRIPE_SECRET_KEY`
in the dashboard to switch payments from simulation to live.
