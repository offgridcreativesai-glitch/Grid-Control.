"""
Create a test sub-customer under the MCC via Google Ads API.
Test access level allows this — no Basic Access needed.
Run once. Output: 10-digit test customer ID (paste into .env).
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, ".")

from agents._lib._google_ads_client import get_google_ads, _strip_id

g = get_google_ads()
if not g.enabled:
    raise SystemExit("google-ads client disabled — check creds in .env")

client = g.raw
mcc_id = _strip_id(os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID"))

# Build the new customer payload (proto-plus: get_type returns instance)
new_customer = client.get_type("Customer")
new_customer.descriptive_name = "OffGrid Test Account"
new_customer.currency_code = "INR"
new_customer.time_zone = "Asia/Kolkata"
new_customer.test_account = True   # ← critical, free + no real ads

svc = client.get_service("CustomerService")
resp = svc.create_customer_client(
    customer_id=mcc_id,
    customer_client=new_customer,
)

# Resource name shape: "customers/<id>"
created_resource = resp.resource_name
created_id = created_resource.split("/")[-1]

print()
print("=" * 60)
print(f"TEST CUSTOMER CREATED: {created_id}")
print()
print(f"GOOGLE_ADS_TEST_CUSTOMER_ID={created_id}")
print("=" * 60)
