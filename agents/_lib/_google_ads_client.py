"""
Google Ads API client — Phase 4c (Jun 19 2026).

Wraps google-ads-python SDK. Silent no-op when creds missing.
Currently at TEST access level — only test customer accounts callable until
Google grants Basic Access (1-2 wk review submitted Jun 19).

Public API:
    g = get_google_ads()
    rows = g.search(customer_id="...", query="SELECT campaign.id FROM campaign")
"""
import os
import sys
from typing import Optional
from dotenv import load_dotenv

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))


def _strip_id(s: Optional[str]) -> Optional[str]:
    return s.replace("-", "").strip() if s else None


class GoogleAdsClientWrapper:
    """Thin wrapper. Silent no-op without creds."""

    API_VERSION = None  # SDK picks newest supported

    def __init__(self):
        self._ok = False
        self._client = None
        try:
            dev_token = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN")
            client_id = os.getenv("GOOGLE_ADS_CLIENT_ID")
            client_secret = os.getenv("GOOGLE_ADS_CLIENT_SECRET")
            refresh_token = os.getenv("GOOGLE_ADS_REFRESH_TOKEN")
            login_customer_id = _strip_id(os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID"))

            if not all([dev_token, client_id, client_secret, refresh_token, login_customer_id]):
                return

            from google.ads.googleads.client import GoogleAdsClient
            cfg = {
                "developer_token": dev_token,
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "login_customer_id": login_customer_id,
                "use_proto_plus": True,
            }
            if self.API_VERSION:
                self._client = GoogleAdsClient.load_from_dict(cfg, version=self.API_VERSION)
            else:
                self._client = GoogleAdsClient.load_from_dict(cfg)
            self._ok = True
        except Exception as e:
            print(f"[google_ads] init skipped: {e}")

    @property
    def enabled(self) -> bool:
        return self._ok

    @property
    def raw(self):
        """Escape-hatch — full SDK client for advanced services."""
        return self._client

    def list_accessible_customers(self) -> list[str]:
        """Return resource names of all customers the OAuth user can access.
        Cheapest check that OAuth + dev token are wired correctly."""
        if not self._ok:
            return []
        try:
            svc = self._client.get_service("CustomerService")
            r = svc.list_accessible_customers()
            return list(r.resource_names)
        except Exception as e:
            print(f"[google_ads] list_accessible_customers failed: {e}")
            return []

    def search(self, customer_id: str, query: str) -> list:
        """Run a GAQL query against a specific customer (no hyphens in id)."""
        if not self._ok:
            return []
        try:
            cid = _strip_id(customer_id)
            svc = self._client.get_service("GoogleAdsService")
            stream = svc.search_stream(customer_id=cid, query=query)
            rows = []
            for batch in stream:
                rows.extend(batch.results)
            return rows
        except Exception as e:
            print(f"[google_ads] search failed: {e}")
            return []


_singleton: Optional[GoogleAdsClientWrapper] = None


def get_google_ads() -> GoogleAdsClientWrapper:
    global _singleton
    if _singleton is None:
        _singleton = GoogleAdsClientWrapper()
    return _singleton
