# arXiver

A web application for browsing, searching, and subscribing to arXiv papers. Users can create custom feeds based on keywords and authors, with full-text search powered by PostgreSQL tsvector.

## Tech Stack

- **Runtime**: Python 3.11
- **Framework**: Flask 2.2 with SQLAlchemy 1.4
- **Database**: PostgreSQL 15 (full-text search with tsvector)
- **Auth**: Passwordless magic links (same flow as puzzle-parlor), Flask-Login sessions
- **Container**: Docker with docker compose
- **Port**: 7854 (localhost) -> 5000 (container)

## Development

```bash
# Start all services
docker compose up --build

# Start in background
docker compose up -d --build

# View logs
docker compose logs -f app

# Rebuild after code changes
docker compose restart app

# Database shell
docker compose exec db psql -U arxiver arxiver

# Harvest articles from the arXiv OAI-PMH API (own process, see below)
docker compose exec -d cron python /app/harvest.py
```

## Project Structure

```
arxiver/
├── arxiver/                  # Main Flask application package
│   ├── __init__.py          # App factory, extensions setup
│   ├── models.py            # SQLAlchemy models (Article, Author, Feed, User, etc.)
│   ├── views.py             # Route handlers
│   ├── forms.py             # WTForms form classes
│   ├── apis.py              # REST API (currently disabled)
│   ├── updater.py           # arXiv OAI-PMH paper fetcher
│   ├── harvest_state.py     # Harvest claim/status (flock + JSON state)
│   ├── magiclink.py         # Magic-link tokens, rate limits, sign-in email
│   ├── mail.py              # Email delivery (console / Resend backends)
│   ├── templates/           # Jinja2 templates
│   └── static/              # CSS, JS, fonts, images
├── config.py                # App configuration (DB URI, mail + auth settings)
├── docker compose.yml       # Docker services (app + postgres)
├── Dockerfile               # Python 3.11 container
├── requirements.txt         # Python dependencies
├── runp.py                  # Production entry point (port 5000)
├── run.py                   # Development entry point (debug mode)
├── manage.py                # Flask-Script manager
├── db_create.py             # Database creation script
├── db_migrate.py            # Database migration script
├── db_upgrade.py            # Database upgrade script
└── start-arxiver.sh         # tmux session launcher
```

## Authentication

Passwordless magic links, ported from puzzle-parlor's `apps/server/src/auth`
so both apps behave the same and send through the same verified Resend
domain (`send.lazybrains.com`).

```
GET  /login          form asking for an email address
POST /login          issues a token, mails the link, always answers
                     "check your email" (no account-enumeration signal)
GET  /auth/verify    redeems the token, creates the account if new,
                     signs the user in, redirects to ?next or /
GET  /logout         clears the session
GET  /login2         legacy Google path, now redirects to /login
```

Properties worth preserving if you touch this:

- The raw token exists only in the emailed URL. `auth_token` stores its
  SHA-256 hash, so a database leak yields no usable links.
- Links live 15 minutes and are single-use. `magiclink.consume` redeems
  them in one `UPDATE ... WHERE used_at IS NULL ... RETURNING`, so two
  simultaneous clicks can't both mint a session.
- `?next=` is confined to relative same-site paths (`//evil.com` is a
  protocol-relative URL and is rejected).
- Rate limits live in the database (5 per IP, 3 per address, per 10
  minutes) rather than process memory, because gunicorn runs 2 workers
  and a per-process bucket would hand out double the allowance.

Environment (`.env`):

| Var | Meaning |
| --- | --- |
| `APP_URL` | Public origin used to build the emailed link |
| `EMAIL_BACKEND` | `console` logs the mail (dev), `resend` delivers it |
| `RESEND_API_KEY` | Shared with puzzle-parlor |
| `EMAIL_FROM` | `arXiver <arxiver@send.lazybrains.com>` |
| `SIGNIN_ALLOWLIST` | Comma-separated emails/domains; empty = anyone |
| `COOKIE_SECURE` | `1` by default; set `0` only for plain-http local runs |

`docker compose restart app` does **not** re-read `.env` — use
`docker compose up -d app` after changing it.

### Legacy Google accounts

The old OAuth flow stored the Google subject id in `user.username` and
never recorded an email, so pre-existing accounts (and the feeds they
own) can't be matched by address. Signing in with a magic link therefore
creates a fresh account. `merge_user.py` folds an old account's feeds,
subscriptions and likes into the new one (dry-run unless `--commit`):

```bash
docker compose exec app python merge_user.py --list
docker compose exec app python merge_user.py --from 2 --to 1 --commit
```

Dave's own accounts (2 → 1) are already merged; the other 21 legacy rows
still have no email and will strand their feeds until someone maps an
address to each.

Note that rows created before this switch had `active IS NULL`, which
Flask-Login reads as falsy and refuses to sign in without explanation.
The column is backfilled and `User.is_active` now treats only an
explicit `False` as deactivated.

## Harvesting

Harvests run in **their own process**, in the `cron` container -- same image
and code as the app, serving no traffic:

```bash
# scheduled: daily at HARVEST_AT (default 08:15 UTC), by ops/harvest-loop.sh
docker compose logs -f cron

# manually, detached
docker compose exec -d cron python /app/harvest.py
docker compose exec -d cron python /app/harvest.py --all   # full archive walk

# status (needs UPDATE_TOKEN)
curl -H "X-Update-Token: $UPDATE_TOKEN" http://localhost:7854/update/status
```

This is not a stylistic choice. The harvest used to run as a thread spawned
inside a gunicorn worker by `GET /update`. With two sync workers, a harvest
holding the GIL made every request routed to its worker crawl: during the
46-day catch-up in Oct 2026 the home page took 56s and `/about` -- which
touches no database at all -- timed out entirely, so the site served white
pages. `/update` now returns 410 and tells you to use the CLI; only
`/update/status` still answers. Measured during a harvest after the move:
home page 0.65-1.3s, `/about` a few milliseconds.

Two harvests can't overlap: `claim_slot()` takes an flock around
`tmp/update_state.json`. A claim records the pid **and hostname** of its
holder, so a claim whose process died is taken over rather than blocking
forever -- without that, a killed harvest left `running: true` and every
later attempt was refused, which stranded the database 46 days behind while
the scheduler collected 41 consecutive refusals. The hostname matters now
that the claimer is in a different container from the status reader: pids are
per-namespace, so a claim from another host falls back to a 12-hour
wall-clock backstop instead of a meaningless `os.kill` check.

Note that `Synchronization` is only written **after** a full walk completes,
so an interrupted harvest redoes its whole range. Re-running is otherwise
harmless -- articles upsert.

Two things that will mislead you while debugging a harvest:

- **The image has no `ps`** (`python:3.11-slim` ships without procps), so
  `ps ax | grep harvest` reports nothing whether or not the harvest is
  running. Check `/proc/<pid>/cmdline` instead.
- **A slow harvest looks like a dead one.** arXiv throttles OAI-PMH with
  `Retry-After`, so minutes can pass with the article count unchanged. Watch
  `last_seen`-style progress over several minutes before concluding anything.
- `/update/status` read from the **app** container can only report
  `stale: false` for a claim held by the **cron** container until the 12-hour
  backstop, because it can't check another namespace's pid. A new harvest
  still takes the claim over correctly, since that runs in the same container
  as the holder -- so this is a display wart, not an outage. If it ever needs
  to be exact, a Postgres advisory lock (released automatically when the
  holding connection dies, and visible from any container) is the right fix,
  not a heartbeat -- a heartbeat would false-positive during throttling and
  start a second harvest.

## Key Models

- **Article**: arXiv papers with title, abstract, full-text search vectors
- **Author**: Paper authors with collaboration tracking
- **Feed**: User-created feeds combining keywords and authors
- **Subscription**: User subscriptions to feeds
- **Category**: arXiv categories (e.g., quant-ph, cond-mat)

## Database

PostgreSQL with full-text search (tsvector). The database contains ~8,300 articles, ~5,600 authors, and ~44,000 article-author associations. Search vectors are maintained by database triggers.

Connection: `postgresql://arxiver:arxiver@db/arxiver` (within Docker network)

## External Access

Intended to be served via Cloudflare Zero Trust tunnel at arxiver.lazybrains.com.

## Origin

Ported from lithium.lazybrains.com where it ran under Apache/mod_wsgi with Python 3.6. Source repo: https://github.com/circuitqed/arXiver.git
