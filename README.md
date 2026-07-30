# Hearth & Bean

A Django coffee shop web app — browse the menu, register/log in, add items
to a cart, and check out. Built on Django 6.0.7.

## Features

- Coffee menu with categories (espresso, cold brew, pastries, beans,
  special offers), pagination, and per-category filtering.
- Accounts: registration, login/logout, per-user profile.
- Cart: add/remove/delete/clear, with atomic stock reservation (no
  overselling under concurrent requests).
- Checkout: places a real `Order`, snapshotting item name/price so order
  history stays correct even if a menu item is later renamed or repriced.
- Staff management (Django admin, gated by role — Barista/Manager/
  Owner-Admin): order fulfillment status, low-stock indicators + restock,
  and a sales dashboard (totals, best-sellers, revenue by day).

## Tech stack

Django 6.0.7 · `django-environ` for config · SQLite in dev / Postgres in
production (`DATABASE_URL`-driven) · `whitenoise` for static files ·
`gunicorn` for serving · `django-debug-toolbar` in dev only.

## Getting started

```bash
git clone https://github.com/vongvannsue/coffeeShop.git
cd coffeeShop
python -m venv venv
source venv/bin/activate        # or venv\Scripts\activate on Windows
pip install -r requirements.txt

cp .env.example .env
# then edit .env: set DJANGO_SECRET_KEY to a real generated value
# (python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")

python manage.py migrate
python manage.py createsuperuser   # to access /admin/
python manage.py runserver
```

Visit `http://127.0.0.1:8000/`. Admin is at `/admin/`.

## Common commands

Run all commands from the repository root (where `manage.py` lives).

```bash
python manage.py runserver              # start dev server
python manage.py makemigrations         # generate migrations after model changes
python manage.py migrate                # apply migrations
python manage.py createsuperuser        # create an admin user
python manage.py test                   # run the full test suite
python manage.py test coffeeapp.tests   # run tests for a single app
python manage.py check --deploy         # security checklist for production settings
```

## Project structure

- `coffee/` — Django project package: settings, root URLs, WSGI/ASGI.
  Reads `DJANGO_SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, and `DATABASE_URL`
  from environment variables (see `.env.example`).
- `coffeeapp/` — the main app: `Coffee`/`Biography`/`Cart`/`CartItem`/
  `Order`/`OrderItem` models, views, templates, and the customized Django
  admin (staff roles, order status, inventory, sales dashboard).
- `users/` — authentication (login/register/logout) and the `Profile`
  model.
- `static/css/style.css` — the site-wide "Hearth & Bean" design system.
- `Note/` — issue-level backlogs (`BACKLOG.md`, `MANAGEMENT_BACKLOG.md`)
  behind the roadmap docs below.

## Roadmap & project history

This repo tracks its own planning in-tree rather than only in issues:

- [`TODO.md`](./TODO.md) — customer-facing production-readiness roadmap
  (security hardening, data model, cart, testing, deployment, polish). ✅ complete.
- [`MANAGEMENT_TODO.md`](./MANAGEMENT_TODO.md) — staff-facing management
  layer (roles/permissions, order fulfillment status, inventory, sales
  dashboard, admin polish), built on Django admin. ✅ complete.
- [`PAYMENT_TODO.md`](./PAYMENT_TODO.md) — real Stripe payment processing
  for checkout. 🚧 planned, not yet started.

## Testing

```bash
python manage.py test
```

Covers auth, models, cart concurrency/stock guards, checkout, staff role
permission boundaries, order status management, inventory, and the sales
dashboard. Runs in CI (`.github/workflows/tests.yml`) on every pull request.

## Deployment

Configured for Heroku-style platforms out of the box:

- `Procfile`: `gunicorn` for the web process, `migrate` on release.
- Static files served via `whitenoise` (`collectstatic` required).
- `DATABASE_URL` switches from SQLite (dev default) to Postgres in
  production — no code changes needed, only the env var.
- Run `python manage.py check --deploy` with `DEBUG=False` and a real
  `ALLOWED_HOSTS` before going live; see `TODO.md` Phase 1 for what each
  warning means and how this project resolves it.
