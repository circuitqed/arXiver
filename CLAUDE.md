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

# Update articles from arXiv OAI-PMH API
docker compose exec app python -c "from arxiver.updater import do_update; do_update()"
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
