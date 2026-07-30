# Backlog

The exact, sequential issue backlog referenced by `CLAUDE.md`'s "Git & GitHub Workflow (Per Issue)" section. Derived from `TODO.md` (the technical roadmap); this file exists to turn that roadmap into individually-shippable, one-at-a-time GitHub issues.

> **Status: all items complete.** BL-01 through BL-20 all shipped — see `TODO.md`'s per-phase notes for implementation detail and the `git log` for the actual PRs/commits. The GitHub Issues blocker below turned out to be permanent for this repo, not a to-do: every item from BL-17 onward shipped by skipping the `Issue:` step entirely (branch named with the `BL-NN` slug directly, PR body referencing the backlog entry instead of a real issue number) — same adapted workflow `Note/MANAGEMENT_BACKLOG.md` uses throughout.

Phases 0 and 1 from `TODO.md` are already done (committed directly, not through this issue flow — see git log `aed1a8b..733c83f`) and are not re-listed here. This file starts at Phase 2.

## How to use this file

Work items **top to bottom, one at a time**, per `CLAUDE.md`. For each:

1. `BL-NN`'s **Title** is the exact string for `gh issue create --title`.
2. **Type** is the Conventional Commit type — determines the branch prefix (`<type>/issue-<N>-<slug>`) where `N` is the real number `gh issue create` returns (not the `BL-NN` label below — that's just this file's ordering).
3. **Labels** need `gh label create <label> --force --color <hex> --description "<desc>"` the first time each is used.
4. **Acceptance criteria** is the issue body checklist.
5. **Depends on** — don't start an item until the ones it lists are merged; the order below already respects this, so working strictly top-to-bottom is safe.

---

## Phase 2 — Data model correctness

### BL-01
- **Title**: Correct coffeeapp model field types and naming
- **Type**: `fix`
- **Labels**: `models`, `bug`
- **Depends on**: none
- **Acceptance criteria**:
  - [x] `coffee` class renamed to `Coffee`, `biography` renamed to `Biography` (update all imports/references in `views.py`, `admin.py`)
  - [x] `Coffee.image`: `CharField(max_length=2083)` → `URLField()`
  - [x] `Biography.mobile`: `IntegerField()` → `CharField` with a phone-format validator
  - [x] `Biography.data_birth` → renamed `date_birth`, type `DateTimeField` → `DateField`
  - [x] `Coffee.__str__` added (matches existing `Biography.__str__`)
  - [x] Migration generated and applied; `manage.py test` and `manage.py check` still pass

### BL-02
- **Title**: Add user profile model
- **Type**: `feat`
- **Labels**: `models`, `users`
- **Depends on**: none
- **Acceptance criteria**:
  - [x] Decision recorded in the PR description: does this app need more than Django's built-in `auth.User` (address, phone, order history)?
  - [x] If yes: `Profile` model added with `OneToOneField(User)`, migration generated
  - [x] If no: PR body states why and closes this as won't-do rather than merging a placeholder model

---

## Phase 3 — Finish the cart feature

`cart_detail.html` already references `add_to_cart`/`remove_from_cart`/`delete_from_cart`/`clear_cart` — none exist as views/URLs/models yet.

### BL-03
- **Title**: Decide cart storage architecture
- **Type**: `chore`
- **Labels**: `cart`, `question`
- **Depends on**: none
- **Acceptance criteria**:
  - [x] Decision recorded (design doc or issue comment, not just a commit message): session-based cart vs. DB-backed `Cart`/`CartItem` tied to `request.user`
  - [x] Rationale documented — given `users` auth already works end-to-end, DB-backed is the likely default, but confirm before BL-04 starts
  - [x] No code in this issue — decision only

### BL-04
- **Title**: Add Cart and CartItem models
- **Type**: `feat`
- **Labels**: `cart`, `models`
- **Depends on**: BL-03
- **Acceptance criteria**:
  - [x] Models match the BL-03 decision
  - [x] Migration generated and applied

### BL-05
- **Title**: Implement cart views with CSRF-safe mutations and atomic stock guard
- **Type**: `feat`
- **Labels**: `cart`, `security`
- **Depends on**: BL-04
- **Acceptance criteria**:
  - [x] `add_to_cart`, `remove_from_cart`, `delete_from_cart`, `clear_cart`, `cart_detail` views + URL names added in `coffeeapp/urls.py`
  - [x] All four mutating actions are **POST forms with `{% csrf_token %}`** — no `<a href>` GET links (GET must stay idempotent)
  - [x] Stock decrement is atomic (`F()` expressions or `select_for_update()` in a transaction) — no naive read-then-write race that could oversell
  - [x] `cart_detail.html` updated to match the real view/URL names
  - [x] Tests deferred to BL-09, but manual verification of add/remove/delete/clear noted in the PR

### BL-06
- **Title**: Add cart link to site navigation
- **Type**: `feat`
- **Labels**: `cart`, `frontend`
- **Depends on**: BL-05
- **Acceptance criteria**:
  - [x] `base.html` nav includes a "Cart" link using `{% url 'cart_detail' %}`
  - [x] Confirmed no `NoReverseMatch` on any page (this was deliberately withheld until BL-05 landed, to avoid a site-wide 500)

---

## Phase 4 — Testing

### BL-07
- **Title**: Add test coverage for users auth flow
- **Type**: `test`
- **Labels**: `testing`
- **Depends on**: none
- **Acceptance criteria**:
  - [x] `users/tests.py` created
  - [x] Covers: successful login, failed login, registration, logout (including that logout rejects GET)

### BL-08
- **Title**: Add test coverage for coffeeapp models and views
- **Type**: `test`
- **Labels**: `testing`
- **Depends on**: BL-01cl
- **Acceptance criteria**:
  - [x] Covers `Coffee`/`Biography` `__str__` and field validation
  - [x] Covers `home` and `Biography_views` render correctly with and without data

### BL-09
- **Title**: Add test coverage for cart flow
- **Type**: `test`
- **Labels**: `testing`, `cart`
- **Depends on**: BL-06
- **Acceptance criteria**:
  - [x] Covers add/remove/delete/clear happy paths
  - [x] Covers the stock-race scenario from BL-05 (concurrent adds don't oversell)
  - [x] Covers permission boundary (can an anonymous user reach checkout/cart, per the BL-03 decision?)

### BL-10
- **Title**: Add CI workflow to run test suite on pull requests
- **Type**: `chore`
- **Labels**: `ci`
- **Depends on**: none (can run in parallel with BL-07..09, sequenced last here to match `TODO.md`)
- **Acceptance criteria**:
  - [x] GitHub Actions workflow runs `manage.py test` on every PR
  - [x] Fails the check on non-zero exit

---

## Phase 5 — Static/media & deployment shape

### BL-11
- **Title**: Configure static file serving for production
- **Type**: `feat`
- **Labels**: `deployment`
- **Depends on**: none
- **Acceptance criteria**:
  - [x] `STATIC_ROOT` set, `collectstatic` runs cleanly
  - [x] `whitenoise` added and wired into `MIDDLEWARE`

### BL-12
- **Title**: Configure media storage for coffee images
- **Type**: `feat`
- **Labels**: `deployment`
- **Depends on**: BL-01
- **Acceptance criteria**:
  - [x] **Conditional**: only needed if BL-01 chose `ImageField` over `URLField` — if `URLField` was kept, close this as not-needed and say so
  - [x] If needed: `MEDIA_ROOT`/`MEDIA_URL` configured, storage backend decided (local disk vs. S3-compatible)

### BL-13
- **Title**: Migrate production database to Postgres
- **Type**: `chore`
- **Labels**: `deployment`, `database`
- **Depends on**: none
- **Acceptance criteria**:
  - [x] `DATABASE_URL` (already read via `env.db()` since Phase 0) points at Postgres in the prod env
  - [x] Confirmed migrations run clean against Postgres, not just SQLite
  - [x] SQLite remains the local dev default — no change needed there

### BL-14
- **Title**: Add gunicorn and process manager configuration
- **Type**: `chore`
- **Labels**: `deployment`
- **Depends on**: BL-11
- **Acceptance criteria**:
  - [x] `gunicorn` (or `uvicorn`) added to `requirements.txt`
  - [x] Startup command documented in `CLAUDE.md`

---

## Phase 6 — Polish & performance

### BL-15
- **Title**: Add pagination to coffee and biography list views
- **Type**: `perf`
- **Labels**: `performance`
- **Depends on**: none
- **Acceptance criteria**:
  - [x] `home` and `Biography_views` use Django's `Paginator`
  - [x] Templates updated with page navigation

### BL-16
- **Title**: Add query optimization for cart views
- **Type**: `perf`
- **Labels**: `performance`, `cart`
- **Depends on**: BL-05
- **Acceptance criteria**:
  - [x] `select_related`/`prefetch_related` added where `CartItem.coffee_item` (or equivalent) is accessed in a loop
  - [x] Confirmed via `django-debug-toolbar` (BL-20) or query count assertion in tests that N+1 queries are gone

### BL-17
- **Title**: Pin CDN assets with Subresource Integrity hashes
- **Type**: `fix`
- **Labels**: `security`, `frontend`
- **Depends on**: none
- **Acceptance criteria**:
  - [x] Bootstrap/Font Awesome `<link>`/`<script>` tags get `integrity="sha384-..."` + `crossorigin` matching the pinned CDN version

### BL-18
- **Title**: Consolidate site styles into static/css/style.css
- **Type**: `chore`
- **Labels**: `frontend`
- **Depends on**: none
- **Acceptance criteria**:
  - [x] The three current visual styles (Bootstrap navbar, plain custom CSS, login/register's own palette) consolidated into the currently-empty `static/css/style.css`
  - [x] No visual regression on any page

### BL-19
- **Title**: Resolve duplicate coffeeapp URL mounting
- **Type**: `fix`
- **Labels**: `bug`
- **Depends on**: none
- **Acceptance criteria**:
  - [x] Decide whether `coffeeapp.urls` stays mounted at `/` only, `/coffee/` only, or genuinely both (state the reason)
  - [x] Drop the unused mount in `coffee/urls.py`, update any hardcoded links

### BL-20
- **Title**: Add django-debug-toolbar for local development
- **Type**: `chore`
- **Labels**: `enhancement`
- **Depends on**: none
- **Acceptance criteria**:
  - [x] Added as a dev-only dependency (not in production `requirements.txt`, or gated behind `DEBUG`)
  - [x] Confirmed it surfaces N+1 queries on at least one existing page

---

## Not in this backlog (deliberately — see `TODO.md`)

- Payment processing / checkout-to-payment integration — needs its own scoping pass before it can become backlog items.
- Email delivery (password reset, order confirmations) — no `EMAIL_BACKEND` configured yet; add when "forgot password" or receipts are actually wanted.
- Multi-tenancy / horizontal scaling — nothing in the current single-shop model justifies this yet.
