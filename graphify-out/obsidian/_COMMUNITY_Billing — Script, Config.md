---
type: community
cohesion: 0.15
members: 24
---

# Billing — Script, Config

**Cohesion:** 0.15 - loosely connected
**Members:** 24 nodes

## Members
- [[Create a Razorpay customer.]] - rationale - billing/razorpay_client.py
- [[Create a subscription plan in Razorpay.]] - rationale - billing/razorpay_client.py
- [[Create a subscription. total_count = max billing cycles.]] - rationale - billing/razorpay_client.py
- [[Razorpay integration for Grid Control billing. Handles plans, subscriptions, cus]] - rationale - billing/razorpay_client.py
- [[Verify Razorpay webhook signature (HMAC SHA256).]] - rationale - billing/razorpay_client.py
- [[Verify payment signature after checkout.]] - rationale - billing/razorpay_client.py
- [[Verify subscription payment signature.]] - rationale - billing/razorpay_client.py
- [[bool_12]] - code - billing/razorpay_client.py
- [[cancel_subscription()]] - code - billing/razorpay_client.py
- [[create_customer()]] - code - billing/razorpay_client.py
- [[create_payment_link()]] - code - billing/razorpay_client.py
- [[create_plan()]] - code - billing/razorpay_client.py
- [[create_subscription()]] - code - billing/razorpay_client.py
- [[fetch_customer()]] - code - billing/razorpay_client.py
- [[fetch_payment()]] - code - billing/razorpay_client.py
- [[fetch_plan()]] - code - billing/razorpay_client.py
- [[fetch_subscription()]] - code - billing/razorpay_client.py
- [[int_18]] - code - billing/razorpay_client.py
- [[is_configured()]] - code - billing/razorpay_client.py
- [[list_plans()]] - code - billing/razorpay_client.py
- [[razorpay_client.py]] - code - billing/razorpay_client.py
- [[resume_subscription()]] - code - billing/razorpay_client.py
- [[str_43]] - code - billing/razorpay_client.py
- [[verify_webhook_signature()]] - code - billing/razorpay_client.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Billing__Script_Config
SORT file.name ASC
```

## Connections to other communities
- 2 edges to [[_COMMUNITY_Dashboard — Billing, Hook]]

## Top bridge nodes
- [[razorpay_client.py]] - degree 17, connects to 1 community
- [[str_43]] - degree 14, connects to 1 community