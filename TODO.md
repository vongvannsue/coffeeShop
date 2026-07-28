# Coffee Shop — Production Readiness Roadmap

Baseline verified 2026-07-29 via `venv/bin/python manage.py check`, `check --deploy`, and `test` (Django 6.0.7, installed in `venv/`, not yet pinned anywhere).

- `manage.py check`: 0 issues.
- `manage.py check --deploy`: **7 warnings** (listed in Phase 1).
- `manage.py test`: **0 tests exist.**

**Phase 0 complete (2026-07-29)**: `requirements.txt` pinned, `SECRET_KEY`/`DEBUG`/`ALLOWED_HOSTS`/`DATABASE_URL` moved to env vars via `django-environ`, Django version decision made (pin to installed 6.0.7, docs updated). Re-running `check --deploy` now shows **5 warnings**, down from 7 — `W009` (weak secret key) and `W020` (empty `ALLOWED_HOSTS`) are resolved; the remaining 5 need `DEBUG=False` + HTTPS in a real deployment and are Phase 1's job.

Work top-to-bottom — later phases assume earlier ones are done. Each item is independent enough to be its own commit/PR.

---

## Phase 0 — Stop the bleeding (do first, low effort/high risk reduction) ✅ done 2026-07-29

- [x] Move `SECRET_KEY` out of `coffee/settings.py` into an environment variable, loaded via `django-environ`. Generated a fresh key (old one is in git history, treated as burned) — lives in gitignored `.env`, with `.env.example` committed as the template.
- [x] Pin dependencies: `requirements.txt` written from `venv/bin/pip freeze` (`Django==6.0.7`, `asgiref==3.12.1`, `django-environ==0.14.0`, `sqlparse==0.5.5`).
- [x] Django version decision: **pinned to installed 6.0.7** (not downgraded to 5.2). Updated `settings.py` docstring/doc links and `CLAUDE.md` to match.
- [x] Split settings by environment: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, and `DATABASES` (via `env.db('DATABASE_URL', default='sqlite:///...')`) now all read from env vars, with a fail-fast error (not a silent insecure fallback) if `.env`/env vars are missing. Verified both the happy path and the missing-`.env` failure path with `manage.py check`.

## Phase 1 — Security hardening (from `manage.py check --deploy`)

All 7 are real, currently-firing warnings — not hypothetical:

- [ ] `security.W009` — replace the `django-insecure-...` `SECRET_KEY` (see Phase 0).
- [ ] `security.W018` — `DEBUG = True` must be `False` in production (env-var gated).
- [ ] `security.W020` — `ALLOWED_HOSTS = []` must list the real domain(s) in production.
- [ ] `security.W012` — set `SESSION_COOKIE_SECURE = True` (HTTPS-only sessions).
- [ ] `security.W016` — set `CSRF_COOKIE_SECURE = True`.
- [ ] `security.W008` — set `SECURE_SSL_REDIRECT = True` once TLS is in place.
- [ ] `security.W004` — set `SECURE_HSTS_SECONDS` (start small, e.g. `3600`, ramp up once confirmed safe).
- [ ] Re-run `manage.py check --deploy` after each change until it reports zero issues.

## Phase 2 — Data model correctness

- [ ] `coffeeapp/models.py`: rename `coffee`/`biography` classes to `Coffee`/`Biography` (PEP 8 + Django convention — every import site touches this, do it once while the codebase is still small).
- [ ] `coffee.image`: change from `CharField(max_length=2083)` to `URLField()` (or `ImageField` + `MEDIA_ROOT`/`MEDIA_URL` if you want real uploads instead of external links) — currently anything can be stored with zero validation.
- [ ] `biography.mobile`: change from `IntegerField()` to `CharField` with a validator (phone numbers need leading zeros, `+country`, and formatting — an int is the wrong type categorically).
- [ ] `biography.data_birth`: rename to `date_birth` (typo) and change `DateTimeField` → `DateField` (it's a birthdate, not a timestamp).
- [ ] Add `__str__` to `Coffee` (biography already has one).
- [ ] Decide on a `users` profile model now, before real user data accumulates: does this app need more than Django's built-in `auth.User` (e.g. address, phone, order history)? If yes, add a `Profile` model with a `OneToOneField(User)` — retrofitting this after users exist means a data migration, not just a schema migration.
- [ ] Run `makemigrations`/`migrate` for any of the above once decided.

## Phase 3 — Finish the cart feature (currently a template with nothing behind it)

`cart_detail.html` references `add_to_cart`, `remove_from_cart`, `delete_from_cart`, `clear_cart` — none of these exist as views, URLs, or models today.

- [ ] **Architecture decision**: session-based cart (works anonymously, lost on logout/device change) vs. DB-backed `Cart`/`CartItem` tied to `request.user` (persists, requires login). Given `users` auth now works end-to-end, a DB-backed cart tied to the logged-in user is the more defensible choice for a shop that already has accounts — but confirm before building.
- [ ] Add `Cart`/`CartItem` models (or session dict schema) accordingly, with a migration.
- [ ] Add `add_to_cart`, `remove_from_cart`, `delete_from_cart`, `clear_cart`, `cart_detail` views + URL names in `coffeeapp/urls.py`.
- [ ] **Security**: all four mutating actions must be POST forms with `{% csrf_token %}`, not `<a href>` GET links as currently templated — GET must stay idempotent (no crawler/prefetch should ever be able to empty someone's cart).
- [ ] Add a "Cart" link to the `base.html` nav once the URL names exist (left out deliberately until now — a `{% url 'cart_detail' %}` reference to a non-existent name would 500 every page on the site).
- [ ] Guard against overselling: cart add/checkout must check `coffee.quantity` and decrement atomically (`F() expressions` or `select_for_update()` inside a transaction) — a naive read-then-write race is a real double-sell bug under concurrent requests.

## Phase 4 — Testing (currently zero coverage)

- [ ] `coffeeapp/tests.py` and add a `users/tests.py` (doesn't exist yet).
- [ ] Cover, in priority order: (1) login/register/logout flow, (2) cart add/remove/checkout including the stock-race case above, (3) model `__str__`/validation, (4) view permissions (e.g. can an anonymous user reach checkout?).
- [ ] Use Django's `TestCase` + `Client()`; no need for a separate test framework at this scale.
- [ ] Wire `manage.py test` into a CI workflow (GitHub Actions) so it runs on every PR — currently nothing runs tests automatically because there's no CI config in the repo at all.

## Phase 5 — Static/media & deployment shape

- [ ] Set `STATIC_ROOT` and run `collectstatic` — not configured yet, needed for any real deployment (dev server serving static files via `APP_DIRS` doesn't work in production).
- [ ] Add `whitenoise` (or a CDN/object storage) to actually serve static files in production; Django's dev server is not meant to.
- [ ] If you add `ImageField` for coffee photos (Phase 2), configure `MEDIA_ROOT`/`MEDIA_URL` and decide on storage backend (local disk vs. S3-compatible) before the first real upload happens.
- [ ] Move off SQLite for any real deployment — fine for dev/single-user, but no concurrent-write story for production traffic. Postgres is the standard choice for Django.
- [ ] Add `gunicorn`/`uvicorn` + a process manager for actually running this outside `runserver`.

## Phase 6 — Polish & performance (do after the above, not before)

- [ ] Add pagination to `home` (coffee list) and `Biography_views` — both currently do `Model.objects.all()` with no limit; fine at 10 rows, a real bottleneck at 10,000.
- [ ] Add `select_related`/`prefetch_related` once the cart introduces FK lookups (`CartItem.coffee_item` etc.) to avoid N+1 queries in `cart_detail.html`'s loop.
- [ ] Replace the CDN-loaded Bootstrap/Font Awesome `<link>`/`<script>` tags with pinned versions + Subresource Integrity (`integrity="sha384-..."`) hashes — currently trusting the CDN with no tamper detection.
- [ ] Consolidate the three different visual styles currently in the codebase (Bootstrap navbar in `cart_detail.html`/`base.html`, plain custom CSS in `coffee.html`/`biography.html`, a third custom palette in `login.html`/`register.html`) into `static/css/style.css`, which is registered but currently empty.
- [ ] Resolve the duplicate URL mount: `coffee/urls.py` includes `coffeeapp.urls` at both `/` and `/coffee/` — pick one, drop the other, update any hardcoded links.
- [ ] Add `django-debug-toolbar` in dev to catch N+1 queries and slow templates before they ship.

---

## Explicitly out of scope for this roadmap (flag, don't silently decide)

- Payment processing / checkout-to-payment integration — not mentioned anywhere in the current code; needs its own scoping pass (Stripe vs. other) before Phase 3 can be called "done."
- Email delivery (password reset, order confirmations) — no `EMAIL_BACKEND` configured; needed the moment "forgot password" or order receipts are wanted.
- Multi-tenancy / horizontal scaling — nothing in the current single-shop model suggests this is needed yet; don't build for it speculatively.
