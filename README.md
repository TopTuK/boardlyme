# Boardly

A no-nonsense **personal Kanban board** — on the web and inside a **Telegram Mini App**, with a
bot that sends you **daily reminders** about active tasks and deadlines.

**Production URL:** <https://taskboard.s-sidorov.ru>

Contexts (one board = one context), custom stages with optional WIP limits, active/done
sub-stages, tasks with deadlines, a hidden Done stage, and live-shared boards where
collaborators assign tasks to themselves. Minimalist industrial UI, no passwords: your Telegram
identity is the account.

```
Vue 3 (Vite, Pinia, Tailwind, vuedraggable)  ·  FastAPI (SQLAlchemy 2 async, aiogram)  ·  PostgreSQL 16  ·  Docker
```

## Screenshots

![Landing](docs/screenshots/landing.jpg)

![Contexts](docs/screenshots/projects.jpg)

![Board](docs/screenshots/board.jpg)

## Contents

- [Screenshots](#screenshots)
- [Features](#features)
- [1. Quick start with Docker (no Telegram needed)](#1-quick-start-with-docker-no-telegram-needed)
- [2. Local development](#2-local-development)
- [3. Telegram artifacts — what to create in BotFather](#3-telegram-artifacts--what-to-create-in-botfather)
- [4. Testing the Telegram flows locally](#4-testing-the-telegram-flows-locally)
- [5. Production deployment](#5-production-deployment)
- [6. Configuration reference](#6-configuration-reference)
- [7. Architecture](#7-architecture)
- [8. API overview](#8-api-overview)
- [9. Troubleshooting](#9-troubleshooting)
- [10. Notes & limitations](#10-notes--limitations)

## Features

| # | Capability | Details |
|---|------------|---------|
| 1 | **Contexts** | One board per context, created in a click. |
| 2 | **Stages** | New boards start with `Backlog` (predefined, always first, cannot be deleted), `ToDo` and `Active`; owners add, rename, delete and reorder stages — `Backlog` is pinned first and `Done` is pinned last, any column in between can be dragged around. Any regular stage can carry a **WIP limit** and can be **split into active/done sub-stages**. |
| 3 | **Tasks** | Title + description + optional deadline date. Drag & drop between stages and sub-stages. WIP limits are enforced server-side (409 on overflow). |
| 4 | **Done, hidden** | Completing a task moves it to the `Done` stage, which is hidden by default — toggle **Show done** in the board header. |
| 5 | **Share & assign** | Owners invite users by Telegram username; every member can assign tasks (to themselves or others). All changes sync live over WebSocket. |
| 6 | **Reminders** | The bot sends each user one daily digest: active tasks grouped by context + upcoming/overdue deadlines. |

## 1. Quick start with Docker (no Telegram needed)

Requirements: Docker with Compose v2. Nothing else.

```bash
git clone <your-repo> boardly
cd boardly
docker compose up --build
```

Open **http://localhost:8080**.

Out of the box the stack runs in **dev mode** (`DEV_FAKE_AUTH=1`): the login page offers
**Alice** / **Bob** buttons (or any custom username), so you can exercise the entire product —
including sharing a board between two users — without touching Telegram. Use a normal window
plus an incognito window to play both roles.

What is running:

| Service | Where | Notes |
|---|---|---|
| `frontend` | http://localhost:8080 | nginx serving the built SPA, proxies `/api` and `/api/ws/` to the backend |
| `backend` | internal `:8000` | FastAPI + uvicorn; runs Alembic migrations on boot; reminder scheduler included |
| `db` | internal `:5432` | PostgreSQL 16 with a named volume `pgdata` |

Useful commands:

```bash
docker compose logs -f backend        # tail backend logs (also shows reminder-loop status)
docker compose up -d --build backend  # rebuild just the backend after changes
docker compose down                   # stop (data survives in the pgdata volume)
docker compose down -v                # stop and WIPE the database
```

The interactive API docs (Swagger UI) are served by the backend at `http://localhost:8000/docs`
when you run it natively (see below); inside the plain compose stack the backend port is not
published.

## 2. Local development

There are two comfortable loops, depending on what you're changing. Both share one database
strategy: Postgres in Docker, application processes on your host for hot reload.

| You are changing… | Recommended loop |
|---|---|
| Frontend only | 2.A (native Vite) + Docker backend, or 2.B full native |
| Backend only | 2.B full native (`uvicorn --reload`) |
| Docker/compose/infra | 2.A rebuild loop |
| Telegram-related flows | Section 4 (ngrok recipe) |

### 2.A Docker iteration loop

Edit files, then:

```bash
docker compose up -d --build backend    # or frontend, or both
docker compose logs -f backend
```

To reach Postgres from your host tools (psql, DBeaver, etc.) use the dev override — it is
**not** auto-loaded, so the normal stack stays sealed:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d db
# Postgres is now on localhost:5432 (boardly / boardly / boardly)
```

### 2.B Full native loop (hot reload everywhere)

Prerequisites: Python 3.11+, Node 18+.

**Step 1 — Postgres in Docker** (skip if you run your own):

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d db
```

**Step 2 — backend** (PowerShell on Windows):

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
copy .env.example .env              # DATABASE_URL already points at localhost:5432
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

macOS/Linux:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

`backend/.env` is read automatically (it is gitignored and excluded from the Docker image).
Dev login (`DEV_FAKE_AUTH=1`) is on by default there. Swagger UI: http://localhost:8000/docs

**Step 3 — frontend** (second terminal):

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. The Vite dev server proxies `/api` (including WebSocket
upgrades) to `http://localhost:8000`, so no CORS or URL configuration is needed. Tailwind,
Pinia stores, and Vue SFCs hot-reload on save.

**Step 4 — run the tests** (whenever you like; no Postgres needed — tests use throwaway SQLite):

```bash
cd backend
python -m pytest                       # 77 tests: auth, stages, WIP, WS, reminders, …
```

### 2.C Creating a database migration

After changing `backend/app/models.py`:

```bash
cd backend
alembic revision --autogenerate -m "describe the change"
# review/edit backend/alembic/versions/<new>_describe_the_change.py
alembic upgrade head
```

Autogenerate diffs the models against the live database, so keep it migrated first. In Docker
the migration runs automatically on container start (`alembic upgrade head && uvicorn …`).

### 2.D Resetting your local data

- Native dev: drop and recreate the database, then `alembic upgrade head` — or simply
  `docker compose -f docker-compose.yml -f docker-compose.dev.yml down -v` (wipes the volume).
- Docker stack: `docker compose down -v`. This is also the fix when Postgres credentials were
  changed after the volume was created (the old password lives on in the volume).

## 3. Telegram artifacts — what to create in BotFather

Everything Telegram-related is created by talking to [@BotFather](https://t.me/BotFather).
There are exactly **three artifacts**. You can develop the whole app without any of them
(dev login), and add them when you need real Telegram auth, the Mini App, or reminders.

| # | Artifact | Created with | Feeds config | Enables |
|---|----------|--------------|--------------|---------|
| 1 | **The bot** (token + username) | `/newbot` | `BOT_TOKEN`, `BOT_USERNAME` | Signature verification for both auth flows; sending reminder messages |
| 2 | **The web domain** | `/setdomain` | must match `APP_URL` | Telegram Login Widget on the website |
| 3 | **The Mini App** (menu button / web app link) | `/newapp` or *Bot Settings → Menu Button* | entry URL is your `APP_URL` | The Mini App inside Telegram |

### 3.1 Artifact 1 — the bot (`/newbot`)

1. Open [@BotFather](https://t.me/BotFather) → `/newbot`.
2. Choose a display name (e.g. `Boardly`).
3. Choose a username ending in `bot` (e.g. `boardly_bot`).
4. BotFather replies with the **token** (`123456789:AAF...`).

Where it goes:

```
BOT_TOKEN=123456789:AAF...     # backend: verifies Login Widget payloads and initData,
                               #          signs nothing itself — used as the HMAC key
BOT_USERNAME=boardly_bot     # backend exposes it via /api/meta; the frontend renders
                               # the Login Widget with it (no leading @)
```

Security notes:

- The token is a secret — treat it like a password. If it leaks, regenerate it in BotFather
  (`/revoke` under *API Token*) and update `BOT_TOKEN`.
- No webhook or polling setup is ever needed: **the bot only sends messages** (daily
  reminders). It does not receive or process commands.

### 3.2 Artifact 2 — the web domain (`/setdomain`)

The Login Widget only works on the exact HTTPS domain registered with the bot.

1. In BotFather: `/setdomain` → pick your bot.
2. Send the bare domain, e.g. `boardly.example.com` (no `https://`, no path).
3. Set the same origin in your deployment: `APP_URL=https://boardly.example.com`.

A bot has **one** registered domain at a time. Pointing it at an ngrok tunnel for local
testing (section 4) temporarily disables the widget on the production domain — switch it back
afterwards. Changing it later does not affect tokens or sessions.

### 3.3 Artifact 3 — the Mini App (`/newapp` or the menu button)

The Mini App is just your website loaded in Telegram's webview — no separate build. You only
register an entry point:

- **Via `/newapp`**: BotFather asks for a short name (letters/digits, used in the direct link
  `https://t.me/<bot_username>/<short_name>`), the web app URL (your `APP_URL`), and
  optionally a description and icon.
- **Via the menu button**: */mybots → your bot → Bot Settings → Menu Button → Edit* → set the
  URL to `APP_URL`. This puts a permanent launch button in the bot's chat header.

Users can then open Boardly from the bot chat (▶ button) or the direct link. The app
detects the Telegram context automatically, signs the user in via `initData`, and wires the
native BackButton.

### 3.4 Optional polish

- `/setuserpic` — avatar (e.g. the Boardly logotype)
- `/setdescription` — what people see before pressing *Start*
- `/setabouttext` — the "What can this bot do?" line

### 3.5 What each artifact enables (auth & reminder flows)

```
Website login   browser → Telegram Login Widget (needs BOT_USERNAME + registered domain)
                → redirect to /login with a signed payload
                → POST /api/auth/telegram/widget → verified against BOT_TOKEN → JWT

Mini App        user opens the app from the bot (needs artifact 3)
                → webview loads your site → window.Telegram.WebApp.initData
                → POST /api/auth/telegram/miniapp → verified against BOT_TOKEN → JWT

Reminders       scheduler (backend) → aiogram sendMessage via BOT_TOKEN → user's Telegram chat
                (only users who have interacted with the bot at least once)
```

## 4. Testing the Telegram flows locally

Constraints: the Login Widget needs the bot's registered domain (artifact 2) and browsers
need HTTPS for a "real" context; the Mini App must be loaded from an HTTPS URL. The standard
local solution is an HTTPS tunnel.

### 4.1 Login Widget + Mini App through ngrok

1. **Start the tunnel** against the site port:

   ```bash
   ngrok http 8080        # or: npx ngrok http 8080
   ```

   Copy the HTTPS URL, e.g. `https://ab12-cd34.ngrok-free.app`.

2. **Point the stack at it** — create `.env` next to `docker-compose.yml`:

   ```env
   BOT_TOKEN=123456789:AAF...            # artifact 1
   BOT_USERNAME=boardly_bot            # artifact 1
   APP_URL=https://ab12-cd34.ngrok-free.app
   DEV_FAKE_AUTH=1                       # keep dev login as a fallback
   ```

3. Restart: `docker compose up -d --build`.

4. **Register the domain** (artifact 2): BotFather → `/setdomain` → your bot → send
   `ab12-cd34.ngrok-free.app`.

5. **Register the Mini App** (artifact 3): `/newapp` → same URL — or set it later and just
   test the website login first.

6. Open `https://ab12-cd34.ngrok-free.app` → *Log in with Telegram* — the widget appears,
   you authenticate with your real Telegram account, and a real user row is created.

Gotchas:

- Free ngrok URLs change on every restart → re-run `/setdomain` (and the Mini App URL) each time.
- The single-domain rule: while the tunnel domain is registered, the production widget won't work.
- Recent Telegram Desktop builds have an experimental setting to open `http://localhost`
  links as Mini Apps — if you have it, you can skip the tunnel for mini-app-only testing,
  but the tunnel path works everywhere.
- If the WebSocket can't connect through your network, the board automatically falls back
  to HTTP polling (`POLL` indicator in the board header) — expected behavior, not a bug.

### 4.2 Testing reminders locally

Reminders only reach **real Telegram users** (dev users like Alice/Bob have negative ids and
are never messaged), so first log in with your Telegram account as in 4.1, and make sure
you have *started* the bot (open `t.me/<bot_username>` and press Start, or open the Mini App).

Then make the schedule trigger on demand:

```env
# .env (docker compose) or backend/.env (native)
REMINDERS_CHECK_INTERVAL_MIN=1      # check every minute
REMINDERS_DAILY_TIME=00:01         # any time already passed today -> fires on the first tick
REMINDERS_TIMEZONE=Europe/Berlin   # your zone, so "already passed" is predictable
```

Restart (`docker compose up -d --build backend`, or restart uvicorn), create one task in a
work stage and one with tomorrow's deadline, and watch:

```bash
docker compose logs -f backend      # "Reminder loop started: daily digest at ..." on boot,
                                    # then the send attempt for your chat id
```

The digest should arrive within ~1 minute; a second run the same day will not duplicate it.
Afterwards restore the production values.

Without any bot you can still develop the reminder logic: `python -m pytest tests/test_reminders.py`
runs the whole pipeline against SQLite with a fake Telegram sender.

## 5. Production deployment

1. **Create the Telegram artifacts** 1–3 (section 3) for your public domain.
2. Put the stack behind HTTPS (Caddy / Traefik / nginx + certbot — anything that terminates
   TLS and forwards to the `frontend` container).
3. Configure `.env`:

   ```env
   BOT_TOKEN=123456789:AAF...
   BOT_USERNAME=boardly_bot
   APP_URL=https://boardly.example.com
   JWT_SECRET=<openssl rand -hex 32>
   DEV_FAKE_AUTH=0
   REMINDERS_TIMEZONE=Europe/Berlin
   REMINDERS_DAILY_TIME=09:00
   ```

4. `docker compose up -d --build`
5. In BotFather, `/setdomain` → `boardly.example.com`, and set the Mini App URL to
   `https://boardly.example.com`.
6. Verify: health (`GET /api/health` through nginx), website login, mini app launch, and the
   backend log line `Reminder loop started`.

Backups: everything lives in the `pgdata` volume — back it up
(`docker run --rm -v boardly_pgdata:/data -v $PWD:/backup alpine tar czf /backup/pgdata.tgz /data`).

## 6. Configuration reference

All values can be set in `.env` (compose) or `backend/.env` (native) — compose environment
always wins over the file.

| Variable | Default | Purpose |
|----------|---------|---------|
| `BOT_TOKEN` | *(empty)* | Telegram bot token (artifact 1). Required for real auth and reminders; empty = dev mode. |
| `BOT_USERNAME` | *(empty)* | Bot username without `@` — renders the Login Widget. |
| `APP_URL` | `http://localhost:8080` | Public site URL; must match the BotFather domain (artifact 2) in production. |
| `JWT_SECRET` | `dev-secret-change-me` | JWT signing secret. **Change in production.** |
| `DEV_FAKE_AUTH` | `1` | `1` enables the no-Telegram dev login (Alice/Bob). **Set `0` in production.** |
| `DATABASE_URL` | compose-internal | Postgres DSN. Native dev: `postgresql+asyncpg://boardly:boardly@localhost:5432/boardly`. |
| `APP_PORT` | `8080` | Host port for the website. |
| `REMINDERS_ENABLED` | `1` | Master switch for the daily digest. |
| `REMINDERS_DAILY_TIME` | `09:00` | Local time (HH:MM) the digest is sent. |
| `REMINDERS_DEADLINE_DAYS` | `2` | Remind N days before a deadline; overdue always included. |
| `REMINDERS_CHECK_INTERVAL_MIN` | `30` | Scheduler tick interval in minutes. |
| `REMINDERS_TIMEZONE` | `UTC` | IANA timezone for the daily time. |

## 7. Architecture

```
boardly/
├── docker-compose.yml           # db + backend + frontend (nginx)
├── docker-compose.dev.yml       # opt-in: publish Postgres to the host
├── frontend/                    # Vue 3 SPA — website AND Telegram Mini App
│   ├── nginx.conf               # static files + /api proxy + WebSocket upgrade
│   └── src/
│       ├── views/               # Landing, Login, Guide (how to use), About, Boards (context list), Board (kanban)
│       ├── components/          # StageColumn, TaskCard, TaskModal, ShareModal, …
│       ├── stores/              # Pinia: auth, projects, board (+ WS sync + polling fallback)
│       ├── composables/         # Telegram BackButton wiring
│       └── lib/                 # axios client w/ auto-refresh, Telegram bridge, formatting
└── backend/                     # FastAPI application
    ├── app/
    │   ├── routers/             # auth, projects, stages, tasks, members, ws
    │   ├── models.py            # users, projects, stages, tasks, project_members, reminder_runs
    │   ├── telegram.py          # Telegram signature verification (widget + initData)
    │   ├── telegram_bot.py      # shared aiogram Bot client (outgoing messages)
    │   ├── security.py          # JWT issue/verify
    │   ├── reminders.py         # daily digest scheduler + Telegram sendMessage
    │   ├── ws.py                # per-project WebSocket rooms
    │   └── config.py            # env settings
    ├── alembic/                 # migrations (run automatically at container start)
    └── tests/                   # pytest suite + optional E2E smoke script
```

**One SPA, two hosts.** The Mini App is the same Vue bundle: on load it detects
`window.Telegram.WebApp`, auto-authenticates via `initData`, applies Telegram viewport
behavior, and routes straight to the boards.

### Data model

- `users` — Telegram identity (`telegram_id`, username, names, photo). Dev users have negative ids.
- `projects` — a *context* in the UI; owned by a user, sharing happens through `project_members`
  (roles: `owner`, `editor`).
- `stages` — ordered columns per project. `Backlog` is flagged `is_backlog` (undeletable,
  always first); `Done` is flagged `is_done` (undeletable, always last) and `is_hidden` by
  default. Regular stages may carry a `wip_limit` and an `is_split` flag dividing them into
  active/done sub-stages.
- `tasks` — title, description, optional deadline, optional assignee (must be a context
  member), position within the (stage, sub-stage) lane, `stage_done` flag, `completed_at`.
- `reminder_runs` — dedup ledger for the daily digest: one row per (kind, user, day).

### Live sync

Every mutation broadcasts an event (`task.updated`, `tasks.reordered`, `members.changed`, …)
to all WebSocket subscribers of that board (`WS /api/ws/projects/{id}?token=…`). The frontend
applies events into the Pinia store; drag & drop lists are store-backed, so remote changes
render instantly.

**Polling fallback.** If the WebSocket cannot connect or drops (tunnels, strict proxies), the
frontend automatically switches to HTTP polling every 4 s (only while the tab is visible) and
shows a `POLL` indicator; polling stops when the socket reconnects.

### Telegram reminders

`app/reminders.py` runs an asyncio loop inside the backend: once per day per user (at
`REMINDERS_DAILY_TIME` in `REMINDERS_TIMEZONE`) it builds a digest — active tasks grouped by
context, plus deadlines within `REMINDERS_DEADLINE_DAYS` (overdue always) — and sends it via
the Bot API. Deduplication via `reminder_runs`; failed deliveries are retried on the next
tick; users who never interacted with the bot cannot be messaged (Telegram's rule).

## 8. API overview

| Method & Path | Purpose |
|---------------|---------|
| `POST /api/auth/telegram/widget` · `/miniapp` · `/dev-login` · `/refresh` | Auth |
| `GET /api/meta`, `GET /api/health` | Public info |
| `GET/POST /api/projects`, `GET/PATCH/DELETE /api/projects/{id}`, `POST …/leave` | Contexts (the UI term; the resource is called *project* in the API) |
| `POST /api/projects/{id}/stages`, `PATCH/DELETE /api/stages/{id}`, `PUT …/stages/reorder` | Stages (incl. `wip_limit`, `is_split`) |
| `POST /api/projects/{id}/tasks`, `PATCH/DELETE /api/tasks/{id}`, `POST …/move` · `/complete` | Tasks (`move` accepts `stage_done` for sub-stages) |
| `GET/POST /api/projects/{id}/members`, `DELETE …/members/{user_id}`, `GET …/members/search` | Sharing |
| `WS /api/ws/projects/{id}?token=…` | Live board events |

Interactive docs (native run): http://localhost:8000/docs

## 9. Troubleshooting

| Symptom | Likely cause & fix |
|---|---|
| "Telegram login is inactive: set BOT_USERNAME" on `/login` | `BOT_USERNAME`/`BOT_TOKEN` not set, or the stack wasn't rebuilt after editing `.env`. |
| Login Widget doesn't render | Domain not registered in BotFather (`/setdomain`), or the page isn't served on that exact domain. |
| `401 Invalid Telegram signature` | `BOT_TOKEN` doesn't match the bot that signed the payload — token regenerated? Update it everywhere. |
| Mini App opens but stays logged out | `APP_URL`/tunnel changed but the Mini App URL in BotFather still points elsewhere; or the bot domain mismatch. Check backend logs for the miniapp-auth error. |
| Board shows `OFFLINE` / `POLL` forever | WebSocket blocked by the network — the polling fallback keeps the board usable; fix the proxy/tunnel if you need instant sync. |
| Reminders never arrive | `BOT_TOKEN` empty (backend logs "Reminders are inactive"), time not reached in `REMINDERS_TIMEZONE`, the user never started the bot, or the account logged in only via dev login (negative id). See 4.2. |
| `port is already allocated` / site unreachable | Another process owns the port — change `APP_PORT`. |
| Postgres `password authentication failed` after changing credentials | The old volume remembers the old password: `docker compose down -v` (wipes data). |
| Migration errors on boot | Check `docker compose logs backend`; worst case reset with `down -v` (dev only). |
| PowerShell blocks `Activate.ps1` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, or call `.\.venv\Scripts\python.exe` directly. |

## 10. Notes & limitations

- Users are discoverable for sharing by Telegram **username** — someone who never opened
  Boardly cannot be found yet (an invite-link flow is a natural next step).
- Signature freshness (`auth_date`) is not strictly enforced; JWTs are the session boundary.
- The UI ships a fixed light "industrial" theme by design, including inside the Mini App.
- One digest per day per user; per-task intermediate reminders (e.g. hourly) are future work.

## License

Released under the [MIT License](LICENSE).
