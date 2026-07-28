# CLAUDE.md

Role: Senior Engineer.
Behavior Mandate: Act as an experienced technical lead and peer. Do not blindly agree with all user propositions; critically evaluate architectural choices, security postures, and code efficiency. Proactively point out edge cases, structural risks, and state leaks before writing code, offering production-grade alternatives. if you have to make assumption, you should list them down and ask me first.

## Attribution Rules

NEVER add Co-Authored-By: Claude, Generated with Claude Code, 🤖, or any AI/Claude attribution, trailer, or signature to any commit message, PR title, PR body, or issue body.
All commits must be authored solely by my configured git identity (git config user.name / user.email). Never modify authorship, add co-authors, or introduce any bot/AI identity as a contributor.
Commit messages are plain Conventional Commits only: type(scope): description (#N) — nothing appended before or after.
These rules apply in addition to the attribution setting in .claude/settings.json.

## Project overview

A Django coffee shop web app, originally scaffolded on Django 5.2 and now pinned to Django 6.0.7 (see `requirements.txt`). The Django project package is `coffee/` (settings, root URLs, WSGI/ASGI); the main application logic lives in `coffeeapp/`. Dependencies are pinned in `requirements.txt`; install into the project's `venv/` with `pip install -r requirements.txt`.

## Common commands

Run all commands from the repository root (where `manage.py` lives).

```bash
python manage.py runserver              # start dev server at http://127.0.0.1:8000/
python manage.py makemigrations         # generate migrations after model changes
python manage.py migrate                # apply migrations
python manage.py createsuperuser        # create an admin user for /admin/
python manage.py test                   # run the test suite
python manage.py test coffeeapp.tests   # run tests for a single app
```

## Architecture

- `coffee/` — Django project package. `settings.py` reads `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, and `DATABASE_URL` from environment variables via `django-environ` (see `.env`, gitignored; `.env.example` is the committed template). `coffeeapp` and `users` are both registered in `INSTALLED_APPS`. `coffee/urls.py` includes `coffeeapp.urls` twice — once under `coffee/` and once at the root `''` — so every coffeeapp route is reachable both with and without the `/coffee/` prefix (still an unresolved wart, not yet decided which to drop). `users.urls` is mounted once, at `/users/`.
- `coffeeapp/` — the sole active Django app.
  - `models.py` defines `coffee` (name, price, quantity, image URL as `CharField`) and `biography` (personal/bio fields). Note both model classes are lowercase, unlike Django convention.
  - `views.py` has function-based views only: `home` (lists all `coffee` rows) and `Biography_views` (lists all `biography` rows).
  - `urls.py` maps `''` → `home` and `biography/` → `Biography_views`.
  - `templates/` contains `base.html` (shared nav/layout shell — Bootstrap navbar, Home/Biography links, conditional Login/Register vs. username+Logout based on `user.is_authenticated`), `coffee.html`, `biography.html` (both extend `base.html`), and `cart_detail.html` — the last one still references view/URL names (`add_to_cart`, `remove_from_cart`, `delete_from_cart`, `clear_cart`) that don't exist anywhere yet; treat cart as unbuilt, not a working feature.
  - `admin.py` registers both models with list_display/search_fields configured for the Django admin.
- `users/` — active app, registered in `INSTALLED_APPS`, mounted at `/users/`. `login_view`/`register_view`/`logout_view` in `views.py` use Django's built-in `AuthenticationForm`/`UserCreationForm`/`auth.User` (no custom profile model yet — `models.py` is empty). `logout_view` is POST-only by design.
- `static/css/style.css` — global stylesheet; `STATIC_URL = 'static/'` in settings.
- `Note/` — the developer's personal study notes on Django/MVT concepts and a generic scaffold example (`Note/README.md` describes a differently-named example project, `project_coffee`/`menu` app, and does not describe this repo's actual structure — don't treat it as authoritative documentation).

## Git & GitHub Workflow (Per Issue)
Work strictly one issue at a time, in exact sequence from BACKLOG.md. For each issue:

Labels: gh label create <label> --force --color <hex> --description "<desc>" for any labels the issue needs.
Issue: gh issue create --title "<exact backlog title>" --body "<acceptance criteria checklist>" --label <labels>.
Branch: git checkout main && git pull origin main && git checkout -b <type>/issue-<N>-<short-slug> (type matches the Conventional Commit type: feat, fix, test, chore, docs, perf).
Scaffold: create required folders/files respecting Section 4 naming.
Implement: complete, production-ready Dart code. No placeholders, no // TODO.
Verify: dart format lib && flutter analyze && flutter test must all pass before committing.
Commit: git add . && git commit -m "type(scope): description (#N)" — Conventional Commits only, referencing the issue number.
Push: git push -u origin <branch-name>.
PR: gh pr create --title "<same conventional title>" --body "Closes #N" --label <labels> --base main.
Merge: wait for my explicit approval, then gh pr merge --squash && git checkout main && git pull origin main. Do NOT pass --delete-branch — branches are kept after merging (2026-07-14).
Stop. Do not start the next issue until I say "Issue N complete".