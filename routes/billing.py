"""routes/billing.py — GRID CONTROL billing endpoints (blueprint). S2b split."""
from core import *  # noqa: F401,F403  (app, helpers, stdlib re-exports)
from flask import Blueprint

bp = Blueprint("billing", __name__)



@bp.route("/api/billing/plans", methods=["GET"])
def billing_plans():
    """List available billing plans from Supabase."""
    try:
        rows = _db._client.table("billing_plans").select("*").eq("is_active", True).order("amount_paise").execute()
        return jsonify(success=True, data=rows.data)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@bp.route("/api/billing/subscription", methods=["GET"])
@require_auth
def billing_get_subscription():
    """Get the active subscription for a brand."""
    brand_id = _resolve_brand_id(request.args.get("brand_slug") or request.args.get("brand_id", ""))
    if not brand_id:
        return jsonify(success=False, error="brand_slug required"), 400
    try:
        rows = _db._client.table("subscriptions").select("*, billing_plans(*)").eq("brand_id", brand_id).execute()
        sub = rows.data[0] if rows.data else None
        return jsonify(success=True, data=sub)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@require_auth
@rate_limit(max_requests=3, window_seconds=60)
@bp.route("/api/billing/subscribe", methods=["POST"])
@require_auth
def billing_subscribe():
    """Create a Razorpay subscription for a brand."""
    if not _razorpay_ok:
        return jsonify(success=False, error="Razorpay not configured"), 503
    body = request.get_json(force=True)
    brand_id = _resolve_brand_id(body.get("brand_slug") or body.get("brand_id", ""))
    plan_slug = body.get("plan_slug")
    customer_email = body.get("email", "")
    customer_name = body.get("name", "")

    if not brand_id or not plan_slug:
        return jsonify(success=False, error="brand_slug and plan_slug required"), 400

    try:
        # Fetch plan from Supabase
        plan_rows = _db._client.table("billing_plans").select("*").eq("slug", plan_slug).eq("is_active", True).execute()
        if not plan_rows.data:
            return jsonify(success=False, error=f"Plan '{plan_slug}' not found"), 404
        plan = plan_rows.data[0]

        # Create Razorpay plan if not yet synced
        rz_plan_id = plan.get("razorpay_plan_id")
        if not rz_plan_id:
            rz_plan = _rz.create_plan(
                name=plan["name"],
                amount_paise=plan["amount_paise"],
                interval=plan["interval"],
                description=plan.get("description", ""),
            )
            rz_plan_id = rz_plan["id"]
            _db._client.table("billing_plans").update({"razorpay_plan_id": rz_plan_id}).eq("id", plan["id"]).execute()

        # Create Razorpay customer
        rz_customer = _rz.create_customer(
            name=customer_name or "Grid Control User",
            email=customer_email or "user@gridcontrol.ai",
        )

        # Create Razorpay subscription
        rz_sub = _rz.create_subscription(
            plan_id=rz_plan_id,
            customer_id=rz_customer["id"],
            total_count=12,
            notes={"brand_id": brand_id, "plan_slug": plan_slug},
        )

        # Store in Supabase
        _db._client.table("subscriptions").upsert({
            "brand_id": brand_id,
            "plan_id": plan["id"],
            "razorpay_subscription_id": rz_sub["id"],
            "razorpay_customer_id": rz_customer["id"],
            "status": rz_sub.get("status", "created"),
            "metadata": {"razorpay_short_url": rz_sub.get("short_url", "")},
        }, on_conflict="brand_id").execute()

        return jsonify(success=True, data={
            "subscription_id": rz_sub["id"],
            "short_url": rz_sub.get("short_url", ""),
            "status": rz_sub.get("status", "created"),
        })
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@bp.route("/api/billing/verify", methods=["POST"])
@require_auth
def billing_verify():
    """Verify subscription payment after Razorpay checkout."""
    if not _razorpay_ok:
        return jsonify(success=False, error="Razorpay not configured"), 503
    body = request.get_json(force=True)
    sub_id = body.get("razorpay_subscription_id")
    payment_id = body.get("razorpay_payment_id")
    signature = body.get("razorpay_signature")

    if not all([sub_id, payment_id, signature]):
        return jsonify(success=False, error="Missing verification fields"), 400

    try:
        valid = _rz.verify_subscription_signature(sub_id, payment_id, signature)
        if not valid:
            return jsonify(success=False, error="Invalid signature"), 403

        # Update subscription status
        rz_sub = _rz.fetch_subscription(sub_id)
        _db._client.table("subscriptions").update({
            "status": rz_sub.get("status", "active"),
            "current_period_start": rz_sub.get("current_start"),
            "current_period_end": rz_sub.get("current_end"),
        }).eq("razorpay_subscription_id", sub_id).execute()

        # Record payment
        rz_pay = _rz.fetch_payment(payment_id)
        sub_rows = _db._client.table("subscriptions").select("id, brand_id").eq("razorpay_subscription_id", sub_id).execute()
        if sub_rows.data:
            _db._client.table("payments").insert({
                "brand_id": sub_rows.data[0]["brand_id"],
                "subscription_id": sub_rows.data[0]["id"],
                "razorpay_payment_id": payment_id,
                "amount_paise": rz_pay.get("amount", 0),
                "currency": rz_pay.get("currency", "INR"),
                "status": rz_pay.get("status", "captured"),
                "method": rz_pay.get("method", ""),
            }).execute()

        return jsonify(success=True, data={"status": "active"})
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@bp.route("/api/billing/cancel", methods=["POST"])
@require_auth
def billing_cancel():
    """Cancel a subscription (at end of billing cycle)."""
    if not _razorpay_ok:
        return jsonify(success=False, error="Razorpay not configured"), 503
    body = request.get_json(force=True)
    brand_id = _resolve_brand_id(body.get("brand_slug") or body.get("brand_id", ""))
    if not brand_id:
        return jsonify(success=False, error="brand_slug required"), 400

    try:
        sub_rows = _db._client.table("subscriptions").select("razorpay_subscription_id").eq("brand_id", brand_id).execute()
        if not sub_rows.data or not sub_rows.data[0].get("razorpay_subscription_id"):
            return jsonify(success=False, error="No active subscription"), 404

        rz_sub_id = sub_rows.data[0]["razorpay_subscription_id"]
        _rz.cancel_subscription(rz_sub_id, cancel_at_cycle_end=True)
        _db._client.table("subscriptions").update({
            "status": "cancelled",
            "cancelled_at": "now()",
        }).eq("brand_id", brand_id).execute()

        return jsonify(success=True, data={"status": "cancelled"})
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@bp.route("/api/billing/usage", methods=["GET"])
@require_auth
def billing_usage():
    """Get usage stats for a brand (current month)."""
    brand_id = _resolve_brand_id(request.args.get("brand_slug") or request.args.get("brand_id", ""))
    if not brand_id:
        return jsonify(success=False, error="brand_slug required"), 400
    try:
        # Count agent runs this month
        from datetime import datetime
        month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0).isoformat()
        rows = _db._client.table("usage_logs").select("agent_slug, model_used, estimated_cost_usd, input_tokens, output_tokens").eq("brand_id", brand_id).gte("created_at", month_start).execute()

        total_runs = len(rows.data)
        total_cost = sum(float(r.get("estimated_cost_usd", 0)) for r in rows.data)
        total_input = sum(r.get("input_tokens", 0) for r in rows.data)
        total_output = sum(r.get("output_tokens", 0) for r in rows.data)

        # Group by agent
        by_agent = {}
        for r in rows.data:
            slug = r.get("agent_slug", "unknown")
            if slug not in by_agent:
                by_agent[slug] = {"runs": 0, "cost_usd": 0}
            by_agent[slug]["runs"] += 1
            by_agent[slug]["cost_usd"] += float(r.get("estimated_cost_usd", 0))

        return jsonify(success=True, data={
            "total_runs": total_runs,
            "total_cost_usd": round(total_cost, 4),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "by_agent": by_agent,
            "period_start": month_start,
        })
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@bp.route("/api/billing/payments", methods=["GET"])
@require_auth
def billing_payments():
    """Get payment history for a brand."""
    brand_id = _resolve_brand_id(request.args.get("brand_slug") or request.args.get("brand_id", ""))
    if not brand_id:
        return jsonify(success=False, error="brand_slug required"), 400
    try:
        rows = _db._client.table("payments").select("*").eq("brand_id", brand_id).order("created_at", desc=True).limit(20).execute()
        return jsonify(success=True, data=rows.data)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@bp.route("/api/billing/webhook", methods=["POST"])
def billing_webhook():
    """Razorpay webhook handler. Updates subscription/payment status."""
    sig = request.headers.get("X-Razorpay-Signature", "")
    body_raw = request.get_data(as_text=True)

    if not _razorpay_ok:
        return jsonify(success=False), 503

    # Verify signature
    if sig and not _rz.verify_webhook_signature(body_raw, sig):
        return jsonify(success=False, error="Invalid signature"), 403

    payload = request.get_json(force=True)
    event = payload.get("event", "")
    entity = payload.get("payload", {})

    try:
        if event == "subscription.authenticated":
            sub = entity.get("subscription", {}).get("entity", {})
            _db._client.table("subscriptions").update({
                "status": "authenticated",
            }).eq("razorpay_subscription_id", sub.get("id")).execute()

        elif event == "subscription.activated":
            sub = entity.get("subscription", {}).get("entity", {})
            _db._client.table("subscriptions").update({
                "status": "active",
                "current_period_start": sub.get("current_start"),
                "current_period_end": sub.get("current_end"),
            }).eq("razorpay_subscription_id", sub.get("id")).execute()

        elif event in ("subscription.cancelled", "subscription.expired"):
            sub = entity.get("subscription", {}).get("entity", {})
            new_status = "cancelled" if "cancelled" in event else "expired"
            _db._client.table("subscriptions").update({
                "status": new_status,
                "cancelled_at": sub.get("ended_at"),
            }).eq("razorpay_subscription_id", sub.get("id")).execute()

        elif event == "subscription.charged":
            pay = entity.get("payment", {}).get("entity", {})
            sub = entity.get("subscription", {}).get("entity", {})
            sub_rows = _db._client.table("subscriptions").select("id, brand_id").eq("razorpay_subscription_id", sub.get("id")).execute()
            if sub_rows.data:
                _db._client.table("payments").upsert({
                    "brand_id": sub_rows.data[0]["brand_id"],
                    "subscription_id": sub_rows.data[0]["id"],
                    "razorpay_payment_id": pay.get("id"),
                    "amount_paise": pay.get("amount", 0),
                    "currency": pay.get("currency", "INR"),
                    "status": pay.get("status", "captured"),
                    "method": pay.get("method", ""),
                }, on_conflict="razorpay_payment_id").execute()

        elif event == "payment.failed":
            pay = entity.get("payment", {}).get("entity", {})
            _db._client.table("payments").upsert({
                "razorpay_payment_id": pay.get("id"),
                "amount_paise": pay.get("amount", 0),
                "currency": pay.get("currency", "INR"),
                "status": "failed",
                "method": pay.get("method", ""),
                "brand_id": pay.get("notes", {}).get("brand_id", "00000000-0000-0000-0000-000000000000"),
            }, on_conflict="razorpay_payment_id").execute()

    except Exception as e:
        print(f"Webhook error: {e}")
        return jsonify(success=False), 500

    return jsonify(success=True), 200
