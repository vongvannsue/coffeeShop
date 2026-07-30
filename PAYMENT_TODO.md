# Payment Processing Integration — Roadmap

Right now `place_order` (`coffeeapp/views.py`) creates a permanent `Order`
record straight from the cart and redirects to a confirmation page — no
money ever changes hands. This roadmap closes that gap: real card payment
via Stripe, without which the "checkout" added in #14 is closer to a demo
than a functioning storefront.

**Separate initiative** from `MANAGEMENT_TODO.md` (staff-facing, complete)
and `TODO.md` (customer-facing infra, complete). This one touches the
customer-facing checkout flow directly, so it's scoped on its own rather
than folded into either.

**Architecture decisions (confirmed 2026-07-30, before scoping further):**
- **Provider: Stripe.** Best-documented Python SDK, industry standard for
  a Django app at this stage.
- **Flow: hosted Stripe Checkout (redirect), not embedded Elements.**
  Customer is redirected to Stripe's own payment page and back — card data
  never touches this server, which keeps PCI scope minimal (SAQ A) and is
  the standard first-payment-integration choice. Traded off against a more
  custom on-site card form, which is bigger scope for a marginal UX gain
  right now.
- **`Order.payment_status`: a separate field from the existing
  `Order.status`** (fulfillment, from MB-02: pending/preparing/ready/
  completed/cancelled). Payment and fulfillment are orthogonal — an order
  can be paid but not yet prepared, or prepared with a payment later
  disputed. Keeps MB-02's free-form fulfillment-status semantics untouched.

## Assumptions (flagging per project convention — correct me before Phase 1 starts)

- **Currency: USD.** Not currently modeled anywhere (prices are bare
  `FloatField`s); assumed rather than confirmed. Say so if this shop needs
  multi-currency — that's a materially bigger change (Stripe Checkout
  supports it, but line-item/display logic doesn't right now).
- **Order created eagerly, before payment completes** — a Stripe Checkout
  Session is created and the customer redirected *after* an `Order` row
  already exists with `payment_status='unpaid'`. This matches the existing
  architecture (stock is already reserved at add-to-cart time, independent
  of order placement — see `TODO.md` Phase 3), not the alternative of
  deferring `Order`/`OrderItem` creation until a webhook confirms payment.
  The alternative avoids ever having an "unpaid order" row, but means
  reconstructing line items from Stripe metadata at webhook time instead
  of your own DB — more fragile, not chosen.
- **Cart is cleared only once payment is confirmed (webhook), not at
  Checkout Session creation.** This is a **behavior change** from today's
  `place_order`, which clears the cart immediately. Necessary here: if the
  cart cleared before payment and the customer's card was declined or they
  abandoned Stripe's page, they'd lose their cart for a purchase that never
  happened.
- **Stock is released back on failed/cancelled payment.** Proposed default,
  not yet built anywhere — confirm before Phase 3. Otherwise every declined
  card or abandoned checkout permanently leaks reserved stock, since
  today's `place_order` never restores stock once reserved (`TODO.md`
  Phase 3 note: "stock should stay reserved, not bounce back on checkout" —
  written for the completed-sale case, not the failed-payment case this
  roadmap introduces).
- **Refunds are V1-manual**: staff issue the actual refund via the Stripe
  Dashboard directly, then mark `payment_status='refunded'` in this app's
  admin. Calling Stripe's refund API from within `/admin/` is real, useful
  future scope — not built here, to keep this roadmap's blast radius to
  "can a customer pay," not "can staff self-serve every payment operation."
- **`stripe` (the official Python SDK) is a new, accepted dependency.**
  Unlike MB-04's "no new dependency" call for the sales dashboard, there's
  no reasonable way to build PCI-sensitive payment code without the
  vendor's own SDK — hand-rolling this would be a real security downgrade,
  not a simplification.
- **Local development requires the Stripe CLI** (`stripe listen --forward-
  to localhost:8000/...`) to receive webhooks — a dev-only tool, not a pip
  package, but a new local-setup step worth documenting in `CLAUDE.md`
  once this ships.
- **No enforcement that fulfillment can't start on an unpaid order.**
  Staff will see both `status` and the new `payment_status` badge
  side-by-side in `OrderAdmin` (Phase 5), but nothing blocks marking an
  unpaid order "preparing" — matches MB-02's free-form philosophy
  (trust staff, don't add validation friction) rather than introducing the
  project's first hard-enforced state transition. Flag if this is wrong
  for a real till — an unpaid order reaching "completed" is a real loss,
  not just a UX inconsistency.

---

## Phase 1 — Stripe setup & configuration

- [ ] Add `stripe` to `requirements.txt`, pinned.
- [ ] `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`
      added via `django-environ` (same pattern as `SECRET_KEY`/
      `DATABASE_URL` since `TODO.md` Phase 0) — test-mode keys in the
      gitignored `.env`, documented (not filled in) in `.env.example`.
- [ ] Document the Stripe CLI local-webhook-forwarding workflow — without
      it, `checkout.session.completed` never reaches a local dev server.

## Phase 2 — Data model

- [ ] `Order.payment_status` field (`unpaid`/`paid`/`failed`/`refunded`/
      `cancelled`, default `unpaid`), migration. **Decide the exact choice
      set before building** — this list is a starting proposal, not
      confirmed.
- [ ] `Order` gets a `stripe_checkout_session_id` (or `stripe_payment_intent_id`)
      field — needed to match an incoming webhook event back to the right
      order; decide which Stripe object ID is more reliable to key off of.
- [ ] Confirm `place_order`'s current behavior (creates `Order`, clears
      cart synchronously) is being replaced, not extended — this phase is
      where that decision becomes real code, not just the roadmap
      assumption above.

## Phase 3 — Checkout flow (customer-facing)

- [ ] Replace `place_order`'s "create Order and redirect to confirmation"
      with: create `Order` (`payment_status='unpaid'`), create a Stripe
      Checkout Session with `line_items` from the cart and `success_url`/
      `cancel_url` back on this site, redirect the customer to Stripe.
- [ ] `success_url` handler: **not** the source of truth for "payment
      succeeded" (a redirect can be spoofed, replayed, or the tab closed
      before it fires) — shows a "payment processing" state and defers to
      the webhook (Phase 4) for the real status flip.
- [ ] `cancel_url` handler: `payment_status='cancelled'`, stock released
      (per the Phase-2-adjacent assumption above), cart **not** cleared —
      customer lands back on their intact cart, not an empty one.
- [ ] `order_confirmation.html` updated to branch on `payment_status`
      rather than assuming every visible order is a completed sale.

## Phase 4 — Webhook handling

- [ ] Webhook endpoint (CSRF-exempt — Stripe posts to it, not a browser
      form), verifies the Stripe signature against `STRIPE_WEBHOOK_SECRET`
      before trusting any payload content.
- [ ] Handles `checkout.session.completed` (→ `payment_status='paid'`,
      clear the cart now) and payment-failure/expiry events (→
      `payment_status='failed'`, release reserved stock).
- [ ] **Idempotent**: Stripe can and does send duplicate webhook events —
      a second `checkout.session.completed` for an already-`paid` order
      must be a safe no-op, not a double-fulfillment or a crash.
- [ ] Test: signature verification actually rejects a forged/unsigned
      payload (not just that a validly-signed one is accepted) — a
      webhook endpoint that trusts unverified input is a real attack
      surface, worth its own explicit negative test.

## Phase 5 — Staff visibility (admin)

- [ ] `payment_status` badge in `OrderAdmin.list_display`, alongside the
      existing MB-02 fulfillment-status badge — colour-coded, same
      pattern as `status_badge`/`stock_badge`.
- [ ] `list_filter` on `payment_status`.
- [ ] Admin action or direct field edit to mark `payment_status='refunded'`
      after a staff member issues the actual refund via the Stripe
      Dashboard (per the V1-manual-refunds assumption above) — this app
      only *records* the refund, doesn't *issue* it.

## Phase 6 — Testing & hardening

- [ ] Test coverage: Checkout Session creation, webhook signature
      verification (valid and forged), idempotent duplicate-event
      handling, stock-release-on-failure, cart survives a cancelled
      payment.
- [ ] `manage.py check` / `check --deploy` re-run after all changes — same
      discipline as every prior phase in this project.
- [ ] Confirm Stripe test-mode card numbers exercise the real flow
      end-to-end (success, decline, 3D Secure challenge) against a real
      dev server + Stripe CLI, not just mocked webhook payloads.

---

## Explicitly out of scope for this roadmap (flag, don't silently decide)

- In-app refund issuance via the Stripe API — V1 is staff using the Stripe
  Dashboard directly; this app only records the outcome (Phase 5).
- Saved payment methods, subscriptions, or any recurring billing — this is
  a one-off coffee order storefront, not a subscription product.
- Alternative payment methods beyond what Stripe Checkout bundles for free
  (it already includes Apple Pay/Google Pay on supported devices with no
  extra work) — no separate PayPal/other-processor integration.
- Multi-currency — single-currency (USD) per the assumption above.
- Formal PCI compliance paperwork (SAQ A submission, etc.) — hosted
  Checkout minimizes the *technical* scope to SAQ A, but the actual
  compliance paperwork is a business/legal process, not an engineering
  deliverable this roadmap can close.
