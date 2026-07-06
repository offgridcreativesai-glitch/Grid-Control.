"""Non-public validation of the new media paths: upload/register/process the asset
on each platform but DO NOT create the post. Catches bugs before unattended auto-post."""
import os, sys
from pathlib import Path
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from agents._lib import token_crypto
BRAND = "askgauravai"; BRAND_DIR = BASE / "brands" / BRAND

# load env (brand overlays global)
for p in (BASE/".env", BRAND_DIR/".env"):
    if p.exists():
        for ln in p.read_text().splitlines():
            ln=ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k,v=ln.split("=",1); os.environ[k.strip()]=token_crypto.decrypt(v.strip().strip('"').strip("'"))
g=os.getenv
slide = "brands/askgauravai/visuals/carousels/20260603_post1_intro/slide_01.png"
reel  = str(BRAND_DIR/"outputs/approved/Creative Director/reels/20260604_142050_askgauravai_insta_and_yt_reel__reel.mp4")

print("── LinkedIn upload (image + video), no post ──")
try:
    import publishing.linkedin_publisher as li
    tok, urn = g("LINKEDIN_ACCESS_TOKEN",""), g("LINKEDIN_URN","")
    a_img = li._register_and_upload(tok, urn, slide, "urn:li:digitalmediaRecipe:feedshare-image")
    print("  ✅ image asset:", a_img[:40])
    a_vid = li._register_and_upload(tok, urn, reel, "urn:li:digitalmediaRecipe:feedshare-video")
    print("  ✅ video asset:", a_vid[:40])
except Exception as e:
    print("  ❌", str(e)[:300])

print("── X upload (image + chunked video), no tweet ──")
try:
    import publishing.twitter_publisher as tw
    o = tw._session(g("TWITTER_API_KEY",""),g("TWITTER_API_SECRET",""),g("TWITTER_ACCESS_TOKEN",""),g("TWITTER_ACCESS_SECRET",""))
    mid_img = tw._upload_image(o, slide); print("  ✅ image media_id:", mid_img)
    mid_vid = tw._upload_video_chunked(o, reel); print("  ✅ video media_id:", mid_vid)
except Exception as e:
    print("  ❌", str(e)[:300])

print("── Instagram reel: host + container to FINISHED, no publish ──")
try:
    import publishing.instagram_publisher as ig, requests
    tok = g("META_GRAPH_API_TOKEN","")
    url = ig.upload_video_to_storage(BRAND, reel, "validate_P2")
    print("  ✅ hosted:", url[:80]+"…")
    node = ig._ig_node()
    r = requests.post(f"{ig.GRAPH_HOST}/{ig.GRAPH_VERSION}/{node}/media",
        data={"media_type":"REELS","video_url":url,"caption":"(validation)","access_token":tok}, timeout=60)
    j=r.json() or {}
    if "id" not in j: print("  ❌ container:", j.get("error", j))
    else:
        st = ig._wait_container_ready(j["id"], tok, tries=30, delay=3.0)
        print(f"  {'✅' if st=='FINISHED' else '❌'} container {j['id']} status: {st}  (NOT published)")
except Exception as e:
    print("  ❌", str(e)[:300])
