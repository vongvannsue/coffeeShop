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

## Not yet broken down

Phases 2–5 of `MANAGEMENT_TODO.md` (order status/POS, inventory, reporting,
polish) will get their own `MB-NN` entries here when each phase starts, per
`CLAUDE.md`'s one-issue-at-a-time workflow — not pre-planned now.
