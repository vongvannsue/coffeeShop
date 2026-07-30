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

**Status: all 5 phases complete (2026-07-29 – 2026-07-30).** See
`Note/MANAGEMENT_BACKLOG.md` for the MB-01..MB-05 issue-level detail,
confirmed decisions, and PRs (#15–#19).

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

## Phase 1 — Staff roles & permissions (foundation) ✅ done 2026-07-29 (MB-01, #15)

Other phases restrict admin actions by role, so this goes first.

- [x] Defined `Barista` and `Manager` `Group`s via a reversible, idempotent
      data migration (`users/migrations/0003_add_staff_role_groups.py`),
      not manual admin clicks. `Owner/Admin` uses `is_superuser` directly —
      no group needed, superuser bypasses Django's permission system.
- [x] Permission mapping confirmed **as proposed**: Barista = view/change
      `Order` + view `OrderItem` (no add/delete). Manager = Barista's
      permissions + view/change `Coffee` (no add/delete). "View reports"
      deferred to Phase 4 — no dashboard existed yet to gate.
- [x] Staff account creation confirmed: reuse the existing `users` app
      registration flow for the account; an Owner/Admin promotes it via
      `is_staff=True` + Group assignment in `/admin/`. No new signup UI.
- [x] Tests assert the real 200/403 boundary on actual admin URLs (not
      just that the groups/permissions exist as objects).

## Phase 2 — Order / POS management ✅ done 2026-07-29 (MB-02, #16)

`Order` currently has no status field at all — orders are placed (#14) but
staff have no way to track fulfillment. This is the gap this phase closes.

- [x] Added `Order.status` (`pending`/`preparing`/`ready`/`completed`/
      `cancelled`, default `pending`, `db_index=True`), migration applied.
- [x] `OrderAdmin`: colour-coded status badge in `list_display`
      (not plain text), `list_filter` on status, four bulk actions
      (mark preparing/ready/completed/cancelled).
- [x] Status transitions confirmed **free-form** — no enforced sequence,
      no validation in `save()`/`clean()`. Verified via a direct
      change-form POST (Phase 5), not just bulk actions.
- [x] Known limitation accepted, not fixed: no live/auto-refresh, staff
      reload to see new orders.
- [x] Concurrent-edit edge case accepted, not fixed: last write wins, no
      optimistic locking. Both limitations documented in the MB-02 PR
      rather than silently ignored.

## Phase 3 — Inventory management ✅ done 2026-07-29 (MB-03, #17)

- [x] Decision confirmed: **no audit log**. `Coffee.quantity` overwritten
      directly, no `StockLog`/history model — not built speculatively.
- [x] Low-stock indicator: `Coffee.low_stock_threshold`, **per-item** (not
      a global constant), colour-coded badge in `CoffeeAdmin.list_display`,
      sortable by quantity.
- [x] Restock UX confirmed: fixed-increment bulk action ("Restock selected
      (+10)"), not a custom exact-quantity form.
- [x] Confirmed no collision with cart stock-reservation: restock uses
      `queryset.update(quantity=F('quantity') + 10)` — a single atomic
      `UPDATE` per row, not the `select_for_update()` + Python
      read-modify-write pattern the cart views use for their two-row
      branching logic. Documented in the MB-03 PR why the simpler
      DB-level atomic update is sufficient here. Sequential-restock
      accumulation re-verified in Phase 5.

## Phase 4 — Reporting & analytics ✅ done 2026-07-29 (MB-04, #18)

- [x] Custom admin dashboard at `/admin/dashboard/`, registered by
      wrapping `admin.site.get_urls()` (not a full `AdminSite` subclass).
- [x] Metrics confirmed: total sales + order count (**completed orders
      only** — pending/preparing/ready are in-flight, cancelled excluded),
      best-sellers by **quantity sold** (not revenue), revenue by day.
- [x] Date-range filter: `?range=today|week|month|all`, default `today`.
- [x] Restricted to Manager/Owner via a real `coffeeapp.view_dashboard`
      permission (`Order.Meta.permissions`) granted to `Manager` only —
      not a hardcoded group-name check. Owner/Admin covered by the
      standard superuser bypass.
- [x] Watch item still stands, not actioned: no index on `placed_at` yet.
      `status` already got `db_index=True` in Phase 2. Add a `placed_at`
      index only if/when aggregate queries are actually measured as slow.

## Phase 5 — Polish & hardening ✅ done 2026-07-30 (MB-05, #19)

- [x] `admin.site.site_header`/`site_title`/`index_title` set to Hearth &
      Bean branding. Also added a dashboard nav link (not originally
      scoped here, pulled forward from a gap MB-04 flagged) by wrapping
      `admin.site.get_app_list()` — found after MB-04 shipped that this
      avoids the `INSTALLED_APPS`-reorder risk that PR's notes assumed
      was necessary. Verified against a real rendered admin index page:
      link present for Manager, absent for Barista.
- [x] Test coverage gap-fill: superuser reaches dashboard/Coffee/Order
      admin with no group (implied since Phase 1, never directly
      asserted); free-form status transition re-verified via a direct
      change-form POST, not just bulk actions; two sequential restocks
      confirmed to accumulate correctly (3 → 13 → 23).
- [x] Re-ran `manage.py check --deploy` with `DEBUG=False`/real
      `ALLOWED_HOSTS` — only the expected, deliberately opt-in `W021`
      (HSTS preload) remains. No security regression across Phases 1–5.
      `manage.py test`: 64/64 pass.

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
