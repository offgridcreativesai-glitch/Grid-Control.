import os
import sys
import json

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, '.env'))

def main():
    print("\n========================================")
    print("   OFFGRID MARKETING OS — STARTING UP")
    print("========================================\n")

    print("Step 1: Running account validation...\n")
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "account_validator",
        os.path.join(ROOT, "validators", "account_validator.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    validator = mod.AccountValidator()
    all_passed = validator.run_all_checks()

    if not all_passed:
        print("Fix the missing keys in .env and run again.\n")
        sys.exit(1)

    print("Step 2: Loading brand profile...\n")
    with open(os.path.join(ROOT, "data", "brand_profile.json"), "r") as f:
        brand = json.load(f)
    print(f"Brand: {brand['brand_name']}")
    print(f"Product: {brand['product']}")
    print(f"Phase: {brand['phase']}\n")

    print("Step 3: Loading session state...\n")
    with open(os.path.join(ROOT, "data", "session_state.json"), "r") as f:
        state = json.load(f)
    print(f"Agents run: {state['agents_run']}")
    print(f"Agents approved: {state['agents_approved']}\n")

    print("========================================")
    print("System initialized. CEO Brain standing by.")
    print("========================================\n")

if __name__ == "__main__":
    main()
