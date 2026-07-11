"""routes/creative.py — GRID CONTROL Creative Library endpoints (gap #3, Jul 11 2026).

Thin HTTP layer over creative_library.py (the live asset index). Assets are served for
preview through the existing /api/outputs/media route (each record carries its media_url).
"""
from core import *  # noqa: F401,F403  (app, helpers, stdlib re-exports)
from flask import Blueprint

import creative_library as cl

bp = Blueprint("creative", __name__)


@bp.route("/api/creative-library", methods=["GET"])
@require_auth
def creative_library():
    """Filtered creative assets + facet counts for the library UI.
    Query: brand_slug (req), kind, source_agent, approval_state, tag, q."""
    brand_slug = (request.args.get("brand_slug") or "").strip()
    if not brand_slug or not _validate_brand_slug(brand_slug):
        return jsonify({"success": False, "error": "Valid brand_slug required"}), 400
    assets = cl.list_assets(
        brand_slug,
        kind=(request.args.get("kind") or "").strip() or None,
        source_agent=(request.args.get("source_agent") or "").strip() or None,
        approval_state=(request.args.get("approval_state") or "").strip() or None,
        tag=(request.args.get("tag") or "").strip() or None,
        q=(request.args.get("q") or "").strip() or None,
    )
    return jsonify({"success": True, "data": {"assets": assets, "facets": cl.facets(brand_slug)}})


@bp.route("/api/creative-library/variants", methods=["GET"])
@require_auth
def creative_variants():
    """All assets in one variant family (same post / base name)."""
    brand_slug = (request.args.get("brand_slug") or "").strip()
    group_key = (request.args.get("group_key") or "").strip()
    if not brand_slug or not _validate_brand_slug(brand_slug):
        return jsonify({"success": False, "error": "Valid brand_slug required"}), 400
    if not group_key:
        return jsonify({"success": False, "error": "group_key required"}), 400
    return jsonify({"success": True, "data": cl.variants(brand_slug, group_key)})


@bp.route("/api/creative-library/tags", methods=["POST"])
@require_auth
@require_brand_access
def creative_set_tags():
    """Replace an asset's user tags. Body: { brand_slug, asset_id, tags: [] }."""
    body = request.get_json(silent=True) or {}
    brand_slug = (body.get("brand_slug") or "").strip()
    asset_id = (body.get("asset_id") or "").strip()
    tags = body.get("tags") or []
    if not brand_slug or not _validate_brand_slug(brand_slug):
        return jsonify({"success": False, "error": "Valid brand_slug required"}), 400
    if not asset_id:
        return jsonify({"success": False, "error": "asset_id required"}), 400
    if not isinstance(tags, list):
        return jsonify({"success": False, "error": "tags must be a list"}), 400
    updated = cl.set_tags(brand_slug, asset_id, [str(t) for t in tags])
    if not updated:
        return jsonify({"success": False, "error": "asset not found"}), 404
    return jsonify({"success": True, "data": updated})
