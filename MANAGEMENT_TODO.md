# Coffee Shop Management System — Roadmap

Staff-facing management layer on top of the now-complete customer-facing site
(`TODO.md`, Phases 0–6, all done as of 2026-07-29). This is a **separate
initiative**, not a continuation of that roadmap — the customer site (browse,
cart, checkout, order placement per #14) is out of scope here except as the
data source (`Order`, `OrderItem`, `Coffee`) this system manages.

**Architecture decision (recorded 2026-07-29): lean on Django admin.**
Rather than building bespoke staff-facing pages (new app, new templates, new
views), this extends `django.contrib.admin` — custom `ModelAdmin`s, admin
actions, `Group`/`Permission`-based roles, and a custom admin dashboard view
for reporting. Reuses `Coffee`, `Order`, `OrderItem` (`coffeeapp/models.py`)
rather than introducing parallel models.

## Assumptions (flagging per project convention — correct me before Phase 1 starts)

- **Order status values**: `pending → preparing → ready → completed`, plus
  `cancelled`. If this shop's real workflow differs (e.g. no `preparing`
  step for a small counter operation), say so before BL work starts.
- **Inventory = `Coffee.quantity` as-is**, with a low-stock threshold and a
  restock admin action — **not** a full ingredient/raw-material tracking
  system (flour, milk, beans as separate stock lines). That's a materially
  bigger system; call it out explicitly if it's actually what's wanted.
- **No audit trail by default**: stock and status changes overwrite in
  place, no `StockLog`/history model. Flagged as its own decision item
  (Phase 3) rather than assumed either way, since it's a real scope call.
- **Roles are Django `Group`s** (Barista, Manager, Owner/Admin) with scoped
  `Permission`s — not a new custom role model. Baristas get `is_staff=True`
  and land in the real `/admin/` UI (not a custom-branded staff app); this
  is the direct tradeoff of the "lean on admin" decision — flagging it since
  non-technical staff using stock Django admin is a real UX cost, not a
  neutral one.
- **Reporting has no new Python dependency.** Aggregates via Django ORM
  (`Sum`, `Count`, `TruncDate`) rendered in a custom admin index/dashboard
  view; charts (if any) via Chart.js pinned from CDN with SRI, matching the
  precedent set for Bootstrap/Font Awesome in Phase 6 of `TODO.md` — not a
  new `pip install`.
- **Single shop, single location** — no multi-location inventory or
  per-location order routing. Matches `TODO.md`'s existing out-of-scope call
  on multi-tenancy.

---

## Phase 1 — Staff roles & permissions (foundation)

Other phases restrict admin actions by role, so this goes first.

- [ ] Define three `Group`s: `Barista`, `Manager`, `Owner/Admin` (data
      migration or management command, not manual admin clicks — needs to
      be reproducible across dev/staging/prod).
- [ ] Permission mapping (**decision needed, confirm before building**):
  - Barista: view `Order`/`OrderItem`, change `Order.status` only.
  - Manager: Barista's permissions + view/change `Coffee` (including stock),
    view reports.
  - Owner/Admin: full `is_superuser` (existing Django behavior, no new work).
- [ ] Decide how staff accounts get created — reuse the existing customer
      `users` app registration flow with `is_staff` toggled by an
      Owner/Admin, or a separate staff-only creation path? (No staff
      accounts exist today — this is a real gap, not a formality.)
- [ ] Test: log in as each role, confirm `/admin/` shows only the
      permitted models/actions, confirm direct URL access to a
      not-permitted change form 403s, not just hides the nav link.

## Phase 2 — Order / POS management

`Order` currently has no status field at all — orders are placed (#14) but
staff have no way to track fulfillment. This is the gap this phase closes.

- [ ] Add `Order.status` field (`pending`/`preparing`/`ready`/`completed`/
      `cancelled`, default `pending`), migration.
- [ ] Custom `OrderAdmin`: `list_display` includes status with visual
      distinction (e.g. color via `list_display` method + admin CSS, not
      just plain text — staff scanning a list of orders needs this at a
      glance), `list_filter` on status, admin actions to bulk-transition
      status (e.g. "Mark selected as preparing").
- [ ] Decide (and document) valid status transitions — can an order jump
      `pending → completed` directly, or must it pass through `preparing`/
      `ready`? Enforce in `Order.save()` or leave admin free-form? Free-form
      is less code but lets staff mis-click a `completed` order back to
      `pending`; pick deliberately, don't default silently.
- [ ] Known limitation to accept or push back on now: Django admin has no
      live/auto-refresh — a barista must reload the page to see new orders.
      Acceptable for a low-volume counter operation; a real bottleneck if
      order volume is high. Flag if this matters before building further.
- [ ] Concurrent-edit edge case: two staff opening the same order's admin
      change form and saving both — last write wins, no optimistic locking.
      Low risk at small scale; note explicitly rather than silently ignore.

## Phase 3 — Inventory management

- [ ] **Decision needed**: keep it simple (edit `Coffee.quantity` directly
      in admin + a restock action) or add a `StockLog`/`InventoryAdjustment`
      model for audit history (who changed stock, when, by how much)? Only
      build the audit model if the answer is "we need to know who changed
      what" — don't build it speculatively.
- [ ] Low-stock indicator: threshold (constant or per-`Coffee` field —
      decide which; a per-item threshold is more correct since a bean SKU
      and a pastry have very different reorder points, but it's one more
      field to maintain), visually flagged in `CoffeeAdmin.list_display`.
- [ ] Admin action: "Restock selected" — either a fixed increment prompt or
      a custom admin form for an exact new quantity; decide which UX,
      don't ship both.
- [ ] Confirm this doesn't collide with the existing cart stock-reservation
      logic (`CartItem` decrements `Coffee.quantity` on add, per Phase 3 of
      `TODO.md`) — a manager restocking mid-checkout is a real concurrent
      scenario given the existing `select_for_update()` guard; make sure
      restock goes through the same atomic path, not a naive `quantity += n`
      outside a transaction.

## Phase 4 — Reporting & analytics

- [ ] Custom admin dashboard view (override `AdminSite.index` or add a URL
      via `get_urls()`) — not the default admin index, which has no
      aggregate/report capability.
- [ ] Metrics (**confirm this list is right, not assumed**): total sales
      (sum of `Order.total`, `completed` only — decide whether `cancelled`
      orders count), best-sellers (`OrderItem` grouped by `name`/
      `coffee_item`), revenue over time (daily/weekly via `TruncDate`).
- [ ] Date-range filtering on the dashboard (at minimum: today / this week /
      this month / all time).
- [ ] Restrict dashboard to Manager/Owner roles only (Phase 1 permissions),
      not all `is_staff` users.
- [ ] Watch item, not urgent now: raw aggregate queries over `Order`/
      `OrderItem` with no index on `status`/`placed_at` will get slow as
      order volume grows past what's realistic for testing today. Add
      indexes when it's actually measured as slow, not preemptively.

## Phase 5 — Polish & hardening

- [ ] Custom admin site header/branding (`admin.site.site_header` etc.) so
      staff aren't looking at generic "Django administration" — cheap, but
      real for a non-technical audience per the Phase 1 UX note.
- [ ] Test coverage: permission boundaries per role (Phase 1), status
      transition rules (Phase 2), restock atomicity (Phase 3), dashboard
      access restriction (Phase 4) — extends the existing 27-test suite
      (`TODO.md` Phase 4), not a new testing setup.
- [ ] Re-run `manage.py check` / `check --deploy` after all model/admin
      changes — same discipline as `TODO.md` Phase 0–1, don't skip it just
      because this is "just admin config."

---

## Explicitly out of scope for this roadmap (flag, don't silently decide)

- Real-time order updates (websockets/polling for live POS screens) —
  Django admin's page-reload model is the accepted tradeoff of "lean on
  admin"; revisit only if Phase 2's limitation becomes a real complaint.
- Ingredient/raw-material-level inventory (flour, milk, beans as separately
  tracked stock, recipe-based deduction) — current scope is finished-product
  (`Coffee`) quantity only, per the Phase 3 assumption above.
- External POS hardware/terminal integration (card readers, receipt
  printers) — nothing in the current stack suggests this is needed yet.
- Multi-location inventory or order routing — single-shop assumption,
  matches `TODO.md`'s existing stance.
- Customer-facing order tracking (e.g. "your order is being prepared") —
  this roadmap is staff-facing only; a customer-facing status page would be
  its own initiative built on the `Order.status` field from Phase 2.
