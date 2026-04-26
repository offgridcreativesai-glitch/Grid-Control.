import os
import json
from dotenv import load_dotenv

load_dotenv()

class AccountValidator:
    def __init__(self):
        self.results = {}

    def check_anthropic(self):
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key or key.strip() == "":
            self.results["anthropic"] = {"status": "MISSING", "message": "ANTHROPIC_API_KEY is empty in .env"}
            return False
        self.results["anthropic"] = {"status": "OK", "message": "Key present"}
        return True

    def check_apify(self):
        key = os.getenv("APIFY_API_KEY")
        if not key or key.strip() == "":
            self.results["apify"] = {"status": "MISSING", "message": "APIFY_API_KEY is empty in .env"}
            return False
        self.results["apify"] = {"status": "OK", "message": "Key present"}
        return True

    def check_notion(self):
        key = os.getenv("NOTION_API_KEY")
        page = os.getenv("NOTION_PAGE_ID")
        if not key or key.strip() == "":
            self.results["notion"] = {"status": "MISSING", "message": "NOTION_API_KEY is empty in .env"}
            return False
        if not page or page.strip() == "":
            self.results["notion"] = {"status": "MISSING", "message": "NOTION_PAGE_ID is empty in .env"}
            return False
        self.results["notion"] = {"status": "OK", "message": "Keys present"}
        return True

    def check_meta(self):
        token = os.getenv("META_GRAPH_API_TOKEN")
        if not token or token.strip() == "":
            self.results["meta"] = {"status": "MISSING", "message": "META_GRAPH_API_TOKEN is empty — Instagram data will not work"}
            return False
        self.results["meta"] = {"status": "OK", "message": "Token present"}
        return True

    def run_all_checks(self):
        print("\n========================================")
        print("   OFFGRID MARKETING OS — SYSTEM CHECK")
        print("========================================\n")

        checks = {
            "Anthropic API": self.check_anthropic(),
            "Apify": self.check_apify(),
            "Notion": self.check_notion(),
            "Meta Graph API": self.check_meta(),
        }

        # Map display names to results keys
        key_map = {
            "Anthropic API": "anthropic",
            "Apify":         "apify",
            "Notion":        "notion",
            "Meta Graph API": "meta",
        }

        print("RESULTS:")
        all_passed = True
        for name, passed in checks.items():
            status = "✅ OK" if passed else "❌ MISSING"
            print(f"  {status} — {name}")
            if not passed:
                result_key = key_map.get(name, name.lower().replace(" ", "_"))
                message = self.results.get(result_key, {}).get("message", f"{name} key is missing in .env")
                print(f"         → {message}")
                all_passed = False

        print("\n========================================")
        if all_passed:
            print("✅ ALL CHECKS PASSED — System ready to run")
        else:
            print("❌ SOME CHECKS FAILED — Fill in the missing keys in your .env file")
            print("   Open .env and add the missing values then run again")
        print("========================================\n")

        return all_passed


if __name__ == "__main__":
    validator = AccountValidator()
    validator.run_all_checks()
