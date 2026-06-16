"""routes/leads.py — Lead-magnet funnel (Phase F4): public capture + opt-in page.

PUBLIC endpoints (no auth — a website visitor submits the form):
  POST /api/leads/capture        — store a subscriber (service-role upsert)
  GET  /lead-magnet/<brand_slug> — render the branded opt-in form

Decorator order note: @bp.route is OUTERMOST so @rate_limit actually wraps the
registered view (Flask's route decorator returns the original function, so a
rate_limit placed *above* route would never run — see the Wave-3 finding).
Degrades honestly if the `subscribers` table isn't migrated yet (503, no fake ok).
"""
import re
import html as _html

from core import *  # noqa: F401,F403  (app, _db, rate_limit, request, jsonify, Response, _validate_brand_slug)
from flask import Blueprint

bp = Blueprint("leads", __name__)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@bp.route("/api/leads/capture", methods=["POST"])
@rate_limit(max_requests=10, window_seconds=60)
def leads_capture():
    body = request.get_json(silent=True) or {}
    slug = (body.get("brand_slug") or "").strip()
    email = (body.get("email") or "").strip()
    name = (body.get("name") or "").strip() or None
    interest = (body.get("product_interest") or "").strip() or None
    source = (body.get("source") or "lead_magnet").strip() or None

    if not _validate_brand_slug(slug):
        return jsonify({"success": False, "error": "invalid brand"}), 400
    if not _EMAIL_RE.match(email) or len(email) > 254:
        return jsonify({"success": False, "error": "invalid email"}), 400

    brand = _db.get_brand(slug)
    if not brand:
        return jsonify({"success": False, "error": "unknown brand"}), 404

    row = _db.add_subscriber(brand["id"], email, name, interest, source)
    if not row:
        # table not migrated yet, or insert failed — honest, never a fake success
        return jsonify({"success": False, "error": "capture temporarily unavailable"}), 503
    # Do not echo PII back.
    return jsonify({"success": True, "captured": True}), 201


@bp.route("/lead-magnet/<brand_slug>", methods=["GET"])
@rate_limit(max_requests=30, window_seconds=60)
def lead_magnet_page(brand_slug: str):
    if not _validate_brand_slug(brand_slug):
        return Response("invalid brand", status=400)
    brand = _db.get_brand(brand_slug)
    if not brand:
        return Response("unknown brand", status=404)

    bname = _html.escape(str(brand.get("name") or brand_slug))
    slug_js = _html.escape(brand_slug)
    page = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__BRAND__ — Free Guide</title>
<style>
  :root{color-scheme:light dark}
  body{font:16px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;margin:0;
       display:grid;place-items:center;min-height:100vh;background:#0f1115;color:#f4f4f5}
  .card{max-width:420px;width:90%;background:#181b22;border:1px solid #262b36;
        border-radius:16px;padding:32px}
  h1{font-size:22px;margin:0 0 8px} p{color:#a1a1aa;margin:0 0 20px}
  input{width:100%;box-sizing:border-box;padding:12px;margin:6px 0;border-radius:10px;
        border:1px solid #2c313c;background:#0f1115;color:#fff;font-size:15px}
  button{width:100%;padding:13px;margin-top:10px;border:0;border-radius:10px;
         background:#f97316;color:#111;font-weight:600;font-size:15px;cursor:pointer}
  .msg{margin-top:14px;font-size:14px} .ok{color:#22c55e} .err{color:#ef4444}
</style></head><body>
<div class="card">
  <h1>Get the free guide from __BRAND__</h1>
  <p>Drop your email and I'll send it over. No spam.</p>
  <form id="f">
    <input id="name" placeholder="First name (optional)" autocomplete="given-name">
    <input id="email" type="email" required placeholder="you@email.com" autocomplete="email">
    <button type="submit">Send me the guide</button>
  </form>
  <div id="msg" class="msg"></div>
</div>
<script>
const f=document.getElementById('f'),m=document.getElementById('msg');
f.addEventListener('submit',async e=>{e.preventDefault();m.textContent='Sending…';m.className='msg';
 try{const r=await fetch('/api/leads/capture',{method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({brand_slug:'__SLUG__',email:document.getElementById('email').value,
   name:document.getElementById('name').value,product_interest:'lead_magnet',source:'lead_magnet_page'})});
  const d=await r.json();
  if(r.ok&&d.success){m.textContent='Done — check your inbox shortly.';m.className='msg ok';f.reset();}
  else{m.textContent=(d.error||'Something went wrong')+'. Please try again.';m.className='msg err';}
 }catch(_){m.textContent='Network error. Please try again.';m.className='msg err';}});
</script></body></html>"""
    page = page.replace("__BRAND__", bname).replace("__SLUG__", slug_js)
    return Response(page, mimetype="text/html")
