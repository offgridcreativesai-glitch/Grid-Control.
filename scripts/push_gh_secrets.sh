#!/bin/bash
# One-time helper: pushes required env vars from local .env to GitHub repo secrets
# so GH Actions workflows can run. Run once after editing .env.
#
# Usage: bash scripts/push_gh_secrets.sh

set -e

cd "$(dirname "$0")/.."

if [ ! -f ".env" ]; then
    echo "ERROR: .env not found. Create it first."
    exit 1
fi

REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "")
if [ -z "$REPO" ]; then
    echo "ERROR: gh CLI not authenticated or repo not detected. Run 'gh auth login' first."
    exit 1
fi

echo "Target repo: $REPO"

REQUIRED_KEYS=(
    "ANTHROPIC_API_KEY"
    "APIFY_API_KEY"
    "NOTION_API_KEY"
    "NOTION_PAGE_ID"
)
OPTIONAL_KEYS=(
    "YOUTUBE_API_KEY"
    "TWITTER_BEARER_TOKEN"
    "META_GRAPH_API_TOKEN"
    "META_AD_ACCOUNT_ID"
    "FAL_API_KEY"
    "SUPABASE_URL"
    "SUPABASE_KEY"
    "DASHBOARD_SECRET"
)

push_secret() {
    local key=$1
    local required=$2
    local value
    value=$(grep -E "^${key}=" .env | head -1 | sed -E "s/^${key}=//; s/^[\"']//; s/[\"']$//")

    if [ -z "$value" ]; then
        if [ "$required" = "true" ]; then
            echo "  ❌ $key MISSING (required) — skipping"
        else
            echo "  ⊘  $key empty (optional) — skipping"
        fi
        return
    fi

    if echo "$value" | gh secret set "$key" --repo "$REPO" >/dev/null 2>&1; then
        echo "  ✅ $key pushed"
    else
        echo "  ❌ $key failed to push"
    fi
}

echo ""
echo "Pushing REQUIRED secrets..."
for key in "${REQUIRED_KEYS[@]}"; do
    push_secret "$key" "true"
done

echo ""
echo "Pushing OPTIONAL secrets..."
for key in "${OPTIONAL_KEYS[@]}"; do
    push_secret "$key" "false"
done

echo ""
echo "Done. Verify with: gh secret list --repo $REPO"
echo ""
echo "Run the daily pipeline manually to test:"
echo "  gh workflow run daily-pipeline.yml -f brand_slug=askgauravai --repo $REPO"
echo ""
echo "Generate a carousel manually:"
echo "  gh workflow run carousel-on-demand.yml -f brand_slug=askgauravai -f post_id=week1_post_01 --repo $REPO"
