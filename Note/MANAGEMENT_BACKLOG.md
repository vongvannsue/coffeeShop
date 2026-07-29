# Management System Backlog

The exact, sequential issue backlog for `MANAGEMENT_TODO.md`, following the
same per-issue workflow as `Note/BACKLOG.md` (`CLAUDE.md`'s "Git & GitHub
Workflow (Per Issue)" section). Separate numbering (`MB-NN`) from `BL-NN` to
avoid collision — this is a distinct initiative, not a continuation of the
customer-facing roadmap.

> **GitHub Issues remain disabled on this repo** (confirmed 2026-07-29,
> `gh issue list` still returns "the repository has disabled issues"). Per
> the precedent set for BL-17..BL-20 (#9–#12), the `Issue:` step is skipped
> entirely — go straight from backlog entry to branch to PR, with the PR
> body referencing the `MB-NN` entry directly instead of a real issue
> number. No labels are applied (none were on the BL-17..20 PRs either).

Items are added phase-by-phase as each phase of `MANAGEMENT_TODO.md` starts,
not all up front — matches how this project actually works one phase at a
time rather than pre-planning every issue before Phase 1 has shipped.

---

## Phase 1 — Staff roles & permissions

### MB-01
- **Title**: Add staff role groups and permissions (Barista/Manager)
- **Type**: `feat`
- **Depends on**: none
- **Decisions recorded (confirmed 2026-07-29, in PR description)**:
  - Permission mapping: **Barista** = view/change `Order` + view
    `OrderItem` (no add/delete — orders are only ever created by the
    checkout flow, never by staff directly). **Manager** = Barista's
    permissions + view/change `Coffee` (no add/delete — adding new menu
    items wasn't in scope for this issue; revisit if/when needed).
    **Owner/Admin** = `is_superuser=True`, no group needed (superuser
    bypasses Django's permission system entirely — no new work).
  - Staff account creation: reuse the existing `users` app registration
    flow for the account itself; an existing Owner/Admin promotes it via
    `is_staff=True` + Group assignment in `/admin/`. No new signup/invite
    UI built in this issue.
  - "View reports" permission (mentioned in `MANAGEMENT_TODO.md`'s Phase 1
    note) is **deferred to Phase 4** — there's no report/dashboard view to
    gate yet, so granting a permission for it now would be speculative.
- **Acceptance criteria**:
  - [ ] Data migration (in `users` app, alongside the existing `Profile`
        backfill migration) creates `Barista` and `Manager` `Group`s with
        the permissions above. Reversible — reverse migration removes the
        groups.
  - [ ] No changes needed to `coffeeapp/admin.py`'s `OrderAdmin`/
        `CoffeeAdmin` for this issue — Django's built-in permission checks
        (`has_view_permission`/`has_change_permission`) already gate access
        based on group permissions; confirmed empirically, not assumed.
  - [ ] Tests: a `Barista`-group user can reach `Order` change view (200)
        but not `Coffee` change view (403); a `Manager`-group user can
        reach both; an unaffiliated `is_staff` user with no group can
        reach neither. Covers the actual security boundary, not just that
        the groups exist.
  - [ ] `manage.py check` and `manage.py test` pass.
  - [ ] PR body documents the three decisions above (matches the BL-02
        precedent of recording architecture decisions in the PR
        description, not just the commit).

---

## Phase 2 — Order / POS management

### MB-02
- **Title**: Add Order status field and staff status management
- **Type**: `feat`
- **Depends on**: MB-01 (Barista/Manager `change_order` permission gates
  who can move status)
- **Decision recorded (confirmed 2026-07-29, in PR description)**:
  status transitions are **free-form** — any status settable at any time
  via the admin dropdown or bulk actions, no enforced sequence and no
  validation in `Order.save()`/`clean()`. Least code, matches the
  "lean on admin" architecture decision; accepted tradeoff is that staff
  could mis-click an order from `pending` straight to `completed` or back
  from `completed` to `pending` with nothing stopping them.
- **Acceptance criteria**:
  - [ ] `Order.status` field added: `CharField` with choices
        (`pending`/`preparing`/`ready`/`completed`/`cancelled`), default
        `pending`, `db_index=True` (used immediately by `list_filter`,
        not speculative). Migration generated and applied; existing
        `Order` rows backfill to `pending` via the field default.
  - [ ] Checkout (`coffeeapp/views.py`'s order-placement view, #14)
        needs no changes — it doesn't pass `status` explicitly, so new
        orders get `pending` automatically from the model default.
  - [ ] `OrderAdmin.list_display` shows a colour-coded status badge (not
        plain text) so staff can scan a list of orders at a glance;
        `list_filter` includes `status`.
  - [ ] Four bulk admin actions: mark selected as
        preparing/ready/completed/cancelled. Gated by Django's normal
        `change_order` permission check (no extra gating needed — Barista
        and Manager already have it from MB-01).
  - [ ] Known, accepted limitations (not fixed in this issue): no
        live/auto-refresh (staff must reload to see new orders); no
        optimistic locking (concurrent edits to the same order, last
        write wins).
  - [ ] Tests: new `Order` defaults to `pending`; each bulk action updates
        status only for selected orders, exercised as a `Barista`-group
        staff user (proves the MB-01 permission actually authorizes this,
        not just that the action code runs).
  - [ ] `manage.py check` and `manage.py test` pass.

---

## Phase 3 — Inventory management

### MB-03
- **Title**: Add low-stock indicator and restock action for Coffee
- **Type**: `feat`
- **Depends on**: MB-01 (Manager `change_coffee` permission gates who can
  restock)
- **Decisions recorded (confirmed 2026-07-29, in PR description)**:
  - **No audit log**: restocks and manual quantity edits overwrite
    `Coffee.quantity` directly, no `StockLog`/history model. Revisit only
    if there's a confirmed need to know who changed what and when — not
    built speculatively.
  - **Per-item threshold**: `Coffee.low_stock_threshold` field (not a
    single global constant) — a bean SKU and a pastry have very different
    reorder points.
  - **Restock UX**: fixed-increment bulk action ("Restock selected
    (+10)"), not a custom form for an exact quantity — matches the
    existing bulk-action pattern from MB-02, no new form/template needed.
- **Acceptance criteria**:
  - [ ] `Coffee.low_stock_threshold` field added (`PositiveIntegerField`,
        sensible default). Migration generated and applied.
  - [ ] `CoffeeAdmin.list_display` shows a colour-coded stock badge
        (quantity vs. threshold), sortable by quantity
        (`admin_order_field`).
  - [ ] Bulk admin action "Restock selected (+10)" — implemented as
        `queryset.update(quantity=F('quantity') + 10)`, a single atomic
        `UPDATE` statement per row. **Not** `select_for_update()` +
        Python read-modify-write — that pattern exists elsewhere
        (`coffeeapp/views.py`'s cart mutations) because those need to
        read-then-branch across two related rows in one transaction;
        restock is a single-field bulk update with no branching, so the
        DB-level atomic `F()` update alone is sufficient and correct
        without extra locking.
  - [ ] Confirmed no naive `quantity += n` read-modify-write race exists
        anywhere in the new code — this was flagged as a real concurrency
        risk in `MANAGEMENT_TODO.md` given the existing cart reservation
        logic touches the same field.
  - [ ] Tests: threshold/badge logic at the model boundary; restock action
        increments only the selected `Coffee` rows, exercised as a
        `Manager`-group staff user (proves the MB-01 permission actually
        authorizes this).
  - [ ] `manage.py check` and `manage.py test` pass.

---

## Not yet broken down

Phases 4–5 of `MANAGEMENT_TODO.md` (reporting, polish) will get their own
`MB-NN` entries here when each phase starts, per `CLAUDE.md`'s
one-issue-at-a-time workflow — not pre-planned now.
