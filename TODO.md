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

## Phase 1 — Security hardening (from `manage.py check --deploy`) ✅ done 2026-07-29

All 7 were real, currently-firing warnings — not hypothetical. `W009`/`W020` were already fixed in Phase 0.

- [x] `security.W018` — `DEBUG` is env-driven (Phase 0); confirmed `False` clears this.
- [x] `security.W012` — `SESSION_COOKIE_SECURE = env.bool('SESSION_COOKIE_SECURE', default=not DEBUG)` — off in dev, on automatically once `DEBUG=False`.
- [x] `security.W016` — `CSRF_COOKIE_SECURE`, same pattern.
- [x] `security.W008` — `SECURE_SSL_REDIRECT`, same pattern. **Caveat**: if this app runs behind a TLS-terminating reverse proxy/load balancer, this will redirect-loop unless `SECURE_PROXY_SSL_HEADER` is also set to match that proxy's forwarded-proto header — confirm the proxy config before flipping `DEBUG=False` in real deployment.
- [x] `security.W004` — `SECURE_HSTS_SECONDS`, defaults to `3600` when `DEBUG=False`, `0` in dev.
- [x] `SECURE_HSTS_INCLUDE_SUBDOMAINS` added alongside HSTS, same secure-by-default pattern.
- [x] `SECURE_HSTS_PRELOAD` deliberately left `default=False` even in prod — submitting to the browser preload list is close to irreversible (affects every subdomain, hard to undo), so it's a manual opt-in via env var, not an automatic default. Enabling it produced the *only* remaining warning (`W021`) in the simulated-prod check below, which is expected.
- [x] Verified: re-ran `check --deploy` with real dev `.env` (`DEBUG=True`) — the 5 warnings still show, correctly, since dev shouldn't enforce HTTPS. Re-ran with `DEBUG=False ALLOWED_HOSTS=example.com` env overrides (no `.env` edits) — all 5 cleared, only the expected `W021` (HSTS preload, opt-in) remained.
- [x] `.env.example` documents all new production-only variables, commented out, with the default-off-in-dev behavior explained inline.

## Phase 2 — Data model correctness ✅ done (BL-01, BL-02)

- [x] `coffeeapp/models.py`: renamed `coffee`/`biography` classes to `Coffee`/`Biography` (no migration needed — Django's default table naming already lowercases model names, so this was purely a Python-level rename).
- [x] `coffee.image`: `CharField(max_length=2083)` → `URLField()`.
- [x] `biography.mobile`: `IntegerField()` → `CharField` with a phone-format validator.
- [x] `biography.data_birth` → renamed `date_birth`, `DateTimeField` → `DateField`. Needed 3 migrations, not 1 — see `git log` on `coffeeapp/migrations/0003..0005` for why (renaming+retyping in one step loses data; SQLite's `AlterField` copies old text verbatim, needing a `RunSQL` normalization step first).
- [x] `Coffee.__str__` added.
- [x] Decision: **yes**, added a `Profile` model (`users/models.py`) — `phone`, `address_line1`, `city`, `postal_code` — since the cart/checkout below needs this data and retrofitting after real accounts exist would mean a data migration. A `post_save` signal auto-creates one for every new `User`; existing users backfilled via data migration.

## Phase 3 — Finish the cart feature ✅ done (BL-03..BL-06)

- [x] **Architecture decision**: DB-backed `Cart`/`CartItem` tied to `request.user` (not session-based) — `users` auth already worked end-to-end, and this avoids merging an anonymous session cart on login.
- [x] `Cart`/`CartItem` models added, migration applied.
- [x] `add_to_cart`, `remove_from_cart`, `delete_from_cart`, `clear_cart`, `cart_detail` views + URL names added.
- [x] **Security**: all mutations are `@login_required` + `@require_POST` with `{% csrf_token %}` — verified GET returns 405, POST without a CSRF token returns 403.
- [x] Cart link added to `base.html` nav (shown only when authenticated).
- [x] Overselling guard: stock changes wrapped in `transaction.atomic()` + `select_for_update()`. Confirmed empirically that SQLite (`has_select_for_update = False`) no-ops this — real row locking only kicks in once Postgres is the DB (see Phase 5). Also fixed along the way: `login_view` now honors a validated `?next=` so an anonymous user redirected to login from a cart action lands back where they were, not always on `home`.

## Phase 4 — Testing ✅ done (BL-07..BL-10)

- [x] `coffeeapp/tests.py` and `users/tests.py` — 27 tests, 0 → 27.
- [x] Covers login/register/logout, cart add/remove/delete/clear + out-of-stock rejection, model `__str__`/validators, view permission boundaries (anonymous → redirected to login). The stock-race test is explicitly scoped to sequential logic, not true concurrency — see the test's docstring for why a meaningful threaded test needs Postgres, not SQLite.
- [x] `manage.py test` + `manage.py check` wired into `.github/workflows/tests.yml`, verified against real GitHub Actions runners (not just locally) — checked the actual run at `gh pr checks`, not assumed.

## Phase 5 — Static/media & deployment shape ✅ done (BL-11..BL-14)

- [x] `STATIC_ROOT` set, `collectstatic` runs clean, `whitenoise` wired into `MIDDLEWARE` + `STORAGES`.
  - **Found and fixed a real bug while verifying**: `STATICFILES_DIRS` was never configured, so the project-level `static/` dir was invisible to Django's finders/`collectstatic` — silently tolerated in dev (default storage doesn't check file existence before building a `{% static %}` URL) but would 500 *every page on the site* once manifest-based storage (whitenoise) validated against it. Caught this by actually testing `DEBUG=False` end-to-end (`django.test.Client` + a real `gunicorn` process), not by assuming the config was correct.
  - Also added `coffee/storage.py`'s `ForgivingManifestStaticFilesStorage` (`manifest_strict = False`) as defense-in-depth against any *future* missing static reference doing the same thing.
- [x] Media storage (`MEDIA_ROOT`/`MEDIA_URL`) — **not needed**: BL-01 kept `Coffee.image` as `URLField` rather than switching to `ImageField`, so there's no local upload storage to configure.
- [x] Postgres: added `psycopg[binary]` to `requirements.txt`. Actually verified against a real local Postgres 18 instance (not just assumed compatible) — all migrations apply clean from zero, `manage.py check`/`test` (all 27) pass against it, and confirmed `has_select_for_update = True` on Postgres (unlike SQLite), meaning the Phase 3 stock guard's row locking actually takes effect once this is the production DB. `DATABASE_URL` (env-driven since Phase 0) is all that needs to change; SQLite stays the local dev default.
- [x] `gunicorn` added to `requirements.txt`, `Procfile` added (`web: gunicorn coffee.wsgi:application --bind 0.0.0.0:$PORT`, `release: python manage.py migrate`) — verified it actually serves real requests, including whitenoise-served static files, under `DEBUG=False`.

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
