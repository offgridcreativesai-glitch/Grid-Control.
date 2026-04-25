#!/usr/bin/env python3
"""
managed_agents/setup.py

One-time setup script — creates 15 Managed Agent definitions + 1 shared Environment
via the Anthropic SDK. Writes agent IDs and environment ID to registry.json.

Run once:
    python3 managed_agents/setup.py

Run again safely — will UPDATE existing agents if IDs already exist in registry.
"""

import os
import sys
import json
import pathlib

# Ensure project root is on path
ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(override=True)

import anthropic

REGISTRY_PATH = pathlib.Path(__file__).parent / "registry.json"
PROMPTS_DIR   = pathlib.Path(__file__).parent / "prompts"


def load_registry() -> dict:
    with open(REGISTRY_PATH) as f:
        return json.load(f)


def save_registry(registry: dict) -> None:
    with open(REGISTRY_PATH, "w") as f:
        json.dump(registry, f, indent=2)
    print(f"[setup] registry.json updated.")


def load_prompt(prompt_file: str) -> str:
    path = PROMPTS_DIR / prompt_file
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text()


def create_or_update_agent(client: anthropic.Anthropic, name: str, config: dict, existing_id: str) -> str:
    """Create a new agent or return existing ID. Anthropic SDK doesn't support update via beta.agents — recreate if needed."""
    instructions = load_prompt(config["prompt_file"])
    model        = config["model"]

    if existing_id:
        # Try to fetch — if it exists, reuse it (no update needed for immutable system prompts)
        try:
            agent = client.beta.agents.retrieve(existing_id)
            print(f"  [skip]   {name} — already exists ({agent.id})")
            return agent.id
        except Exception:
            print(f"  [recreate] {name} — existing ID invalid, creating new")

    agent = client.beta.agents.create(
        name=name,
        model=model,
        system=instructions,
        betas=["managed-agents-2026-04-01"],
    )
    print(f"  [created] {name} — {agent.id}")
    return agent.id


def create_or_reuse_environment(client: anthropic.Anthropic, existing_id: str) -> str:
    """Create a shared cloud environment, or reuse existing one."""
    if existing_id:
        try:
            env = client.beta.environments.retrieve(existing_id)
            print(f"  [skip]   environment — already exists ({env.id})")
            return env.id
        except Exception:
            print("  [recreate] environment — existing ID invalid, creating new")

    env = client.beta.environments.create(
        name="offgrid-marketing-os",
        config={
            "type": "cloud",
            "networking": {"type": "unrestricted"},
        },
        betas=["managed-agents-2026-04-01"],
    )
    print(f"  [created] environment — {env.id}")
    return env.id


def main():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("[error] ANTHROPIC_API_KEY not set. Source your .env first.")
        sys.exit(1)

    client   = anthropic.Anthropic(api_key=api_key)
    registry = load_registry()

    print("\n=== OffGrid Marketing OS — Managed Agents Setup ===\n")

    # 1. Create/reuse shared environment
    print("[1/2] Environment")
    env_id = create_or_reuse_environment(client, registry.get("environment_id", ""))
    registry["environment_id"] = env_id

    # 2. Create/reuse all 15 agents
    print("\n[2/2] Agents")
    for agent_name, config in registry["agents"].items():
        existing_id = config.get("agent_id", "")
        agent_id    = create_or_update_agent(client, agent_name, config, existing_id)
        registry["agents"][agent_name]["agent_id"] = agent_id

    save_registry(registry)
    print("\n=== Setup complete. All agent IDs written to managed_agents/registry.json ===\n")


if __name__ == "__main__":
    main()
