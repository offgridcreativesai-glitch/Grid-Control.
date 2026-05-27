"""
Razorpay integration for Grid Control billing.
Handles plans, subscriptions, customers, and webhook verification.
"""
import os
import hmac
import hashlib
import razorpay
from typing import Optional

# ── Client ──────────────────────────────────────────────────
_key_id = os.getenv("RAZORPAY_KEY_ID", "")
_key_secret = os.getenv("RAZORPAY_KEY_SECRET", "")

client: Optional[razorpay.Client] = None
if _key_id and _key_secret:
    client = razorpay.Client(auth=(_key_id, _key_secret))


def is_configured() -> bool:
    return client is not None


# ── Plans ───────────────────────────────────────────────────
def create_plan(name: str, amount_paise: int, interval: str = "monthly",
                description: str = "", currency: str = "INR") -> dict:
    """Create a subscription plan in Razorpay."""
    period = "monthly" if interval == "monthly" else "yearly"
    plan_data = {
        "period": period,
        "interval": 1,
        "item": {
            "name": name,
            "amount": amount_paise,
            "currency": currency,
            "description": description,
        },
    }
    return client.plan.create(data=plan_data)


def fetch_plan(plan_id: str) -> dict:
    return client.plan.fetch(plan_id)


def list_plans(count: int = 10, skip: int = 0) -> dict:
    return client.plan.all({"count": count, "skip": skip})


# ── Customers ───────────────────────────────────────────────
def create_customer(name: str, email: str, contact: str = "") -> dict:
    """Create a Razorpay customer."""
    data = {"name": name, "email": email}
    if contact:
        data["contact"] = contact
    return client.customer.create(data=data)


def fetch_customer(customer_id: str) -> dict:
    return client.customer.fetch(customer_id)


# ── Subscriptions ───────────────────────────────────────────
def create_subscription(plan_id: str, customer_id: str = "",
                        total_count: int = 12,
                        notes: dict = None) -> dict:
    """Create a subscription. total_count = max billing cycles."""
    data = {
        "plan_id": plan_id,
        "total_count": total_count,
        "quantity": 1,
    }
    if customer_id:
        data["customer_id"] = customer_id
    if notes:
        data["notes"] = notes
    return client.subscription.create(data=data)


def fetch_subscription(subscription_id: str) -> dict:
    return client.subscription.fetch(subscription_id)


def cancel_subscription(subscription_id: str, cancel_at_cycle_end: bool = True) -> dict:
    return client.subscription.cancel(subscription_id,
                                       {"cancel_at_cycle_end": 1 if cancel_at_cycle_end else 0})


def pause_subscription(subscription_id: str) -> dict:
    return client.subscription.pause(subscription_id)


def resume_subscription(subscription_id: str) -> dict:
    return client.subscription.resume(subscription_id)


# ── Payments ────────────────────────────────────────────────
def fetch_payment(payment_id: str) -> dict:
    return client.payment.fetch(payment_id)


# ── Payment Links (for one-time or quick payments) ──────────
def create_payment_link(amount_paise: int, description: str,
                        customer_name: str = "", customer_email: str = "",
                        currency: str = "INR", callback_url: str = "") -> dict:
    data = {
        "amount": amount_paise,
        "currency": currency,
        "description": description,
        "customer": {},
    }
    if customer_name:
        data["customer"]["name"] = customer_name
    if customer_email:
        data["customer"]["email"] = customer_email
    if callback_url:
        data["callback_url"] = callback_url
        data["callback_method"] = "get"
    return client.payment_link.create(data=data)


# ── Webhook Verification ───────────────────────────────────
def verify_webhook_signature(body: str, signature: str, secret: str = "") -> bool:
    """Verify Razorpay webhook signature (HMAC SHA256)."""
    webhook_secret = secret or os.getenv("RAZORPAY_WEBHOOK_SECRET", _key_secret)
    expected = hmac.new(
        webhook_secret.encode("utf-8"),
        body.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_payment_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """Verify payment signature after checkout."""
    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        })
        return True
    except razorpay.errors.SignatureVerificationError:
        return False


def verify_subscription_signature(subscription_id: str, payment_id: str, signature: str) -> bool:
    """Verify subscription payment signature."""
    try:
        client.utility.verify_subscription_payment_signature({
            "razorpay_subscription_id": subscription_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        })
        return True
    except razorpay.errors.SignatureVerificationError:
        return False
