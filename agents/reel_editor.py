"""
reel_editor — Founder-Journal reel assembly for OffGrid Marketing OS.

Called by the Creative Director (agent #4) to turn a founder talking-head clip into a
finished vertical reel with:
  • the founder seated full-frame (NO crop) on a Founder-Journal cream backdrop
  • kinetic captions (Fraunces, paper chip, red keywords) timed to the transcript
  • branded motion-graphic inserts (real CSS animations, recorded via Playwright)
  • AI b-roll inserts (FAL text-to-video) at chosen beats

Reliability choices: Playwright video-recording for smooth motion graphics + ffmpeg for
all compositing (proven stable here) instead of moviepy. fal_client for b-roll.

Public entry: build_reel(founder_video, transcript, out_path, handle="@askgauravai") -> dict
  transcript = {"text": str, "words": [{"word","start","end"}, ...]}
"""
from __future__ import annotations
import os, json, shutil, subprocess, tempfile, glob, math
from pathlib import Path

FFMPEG  = "/opt/homebrew/bin/ffmpeg"
FFPROBE = "/opt/homebrew/bin/ffprobe"

W, H = 1080, 1920
PAPER="#f4efe3"; PAPER2="#efe8d8"; INK="#211d18"; MUTE="#6f675a"; RED="#b23a2e"; LINE="#d8cdb8"

_FONTS = ("@import url('https://fonts.googleapis.com/css2?"
 "family=Fraunces:ital,opsz,wght@0,9..144,600;0,9..144,800;0,9..144,900;1,9..144,600;1,9..144,800"
 "&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500"
 "&family=Caveat:wght@700&display=swap');")


def _esc(s):
    if s is None: return ""
    return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")


# ──────────────────────────────────────────────────────────────────────────────
#  Motion-graphic scenes  (autoplaying CSS animations; recorded in real time)
# ──────────────────────────────────────────────────────────────────────────────
_CHROME = f"""
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:{W}px;height:{H}px;background:{PAPER};overflow:hidden;-webkit-font-smoothing:antialiased}}
.stage{{position:relative;width:{W}px;height:{H}px;
 background:radial-gradient(120% 70% at 100% 0%,rgba(178,58,46,0.05),transparent 55%),{PAPER}}}
.frame{{position:absolute;inset:46px;border:2px solid {LINE}}}
.wm{{position:absolute;top:84px;left:110px;font-family:'Newsreader',serif;font-size:30px;font-weight:500;
 letter-spacing:.22em;text-transform:uppercase;color:{MUTE}}}
.kick{{position:absolute;top:150px;left:110px;font-family:'Caveat',cursive;font-size:66px;color:{RED}}}
.serif{{font-family:'Fraunces',serif;font-weight:900;color:{INK};letter-spacing:-0.01em}}
.r{{color:{RED}}}
@keyframes pop{{0%{{opacity:0;transform:scale(.4) rotate(-6deg)}}70%{{opacity:1;transform:scale(1.08) rotate(-2deg)}}
 100%{{opacity:1;transform:scale(1) rotate(-1.5deg)}}}}
@keyframes fadeup{{0%{{opacity:0;transform:translateY(40px)}}100%{{opacity:1;transform:translateY(0)}}}}
@keyframes floatin{{0%{{opacity:0;transform:translate(var(--dx),var(--dy)) scale(.6)}}
 60%{{opacity:1}}100%{{opacity:.92;transform:translate(0,0) scale(1)}}}}
@keyframes drawx{{0%{{width:0}}100%{{width:var(--w)}}}}
@keyframes dropbtn{{0%{{opacity:0;transform:translateY(-50px) rotate(-1.2deg)}}
 60%{{opacity:1;transform:translateY(8px) rotate(-1.2deg)}}100%{{transform:translateY(0) rotate(-1.2deg)}}}}
@keyframes dot{{0%{{opacity:0;transform:scale(0)}}100%{{opacity:1;transform:scale(1)}}}}
@keyframes growline{{0%{{stroke-dashoffset:var(--len)}}100%{{stroke-dashoffset:0}}}}
"""

def _scene_scatter(kick):
    import random
    random.seed(11)
    toks = ["+42%","ROAS","CPM","0.7×","CTR","–18%","₹2.4L","CPC","AOV"]  # 3×3 grid
    cols = [180, 470, 760]; rows = [600, 800, 1000]
    chips=[]
    for i,t in enumerate(toks):
        x = cols[i % 3] + random.randint(-18,18)
        y = rows[i // 3] + random.randint(-22,22)
        dx = f"{random.randint(-200,200)}px"; dy=f"{random.randint(-140,140)}px"
        rot = random.randint(-8,8)
        chips.append(
          f"<div class='serif' style='position:absolute;left:{x}px;top:{y}px;font-size:50px;font-weight:800;"
          f"color:{MUTE};--dx:{dx};--dy:{dy};transform:rotate({rot}deg);"
          f"animation:floatin .7s {0.05*i:.2f}s both ease-out'>{t}</div>")
    qmark=(f"<div class='serif r' style='position:absolute;left:0;right:0;top:1180px;text-align:center;"
           f"font-size:520px;line-height:1;animation:pop .6s 1.2s both'>?</div>")
    return ("<div class='stage'><div class='frame'></div><div class='wm'>ASKGAURAV.AI</div>"
            f"<div class='kick'>{_esc(kick)}</div>" + "".join(chips) + qmark + "</div>")

def _scene_strikeout(kick, words):
    a,b = (words+["COURSE","DASHBOARD"])[:2]
    def row(word, top, delay):
        return (f"<div style='position:absolute;left:110px;top:{top}px;animation:pop .5s {delay}s both'>"
                f"<span class='serif' style='font-size:150px;position:relative'>{_esc(word)}"
                f"<span style='position:absolute;left:-8px;top:54%;height:12px;background:{RED};border-radius:6px;"
                f"--w:104%;width:0;animation:drawx .35s {delay+0.45}s both ease-out'></span></span></div>")
    return ("<div class='stage'><div class='frame'></div><div class='wm'>ASKGAURAV.AI</div>"
            f"<div class='kick'>{_esc(kick)}</div>"
            + row(a, 760, 0.25) + row(b, 1080, 1.0) + "</div>")

def _scene_plot(kick, label, endword):
    # axes + 5 rising dots + red trend line + arrow→MOVE
    pts = [(180,1500),(340,1430),(500,1300),(660,1180),(820,1000)]
    dots="".join(
       f"<div style='position:absolute;left:{x-14}px;top:{y-14}px;width:28px;height:28px;border-radius:50%;"
       f"background:{INK};animation:dot .25s {0.5+0.18*i:.2f}s both'></div>" for i,(x,y) in enumerate(pts))
    path="M "+" L ".join(f"{x} {y}" for x,y in pts)
    length=int(sum(math.hypot(pts[i+1][0]-pts[i][0],pts[i+1][1]-pts[i][1]) for i in range(len(pts)-1)))
    line=(f"<svg style='position:absolute;left:0;top:0' width='{W}' height='{H}'>"
          f"<path d='{path}' fill='none' stroke='{RED}' stroke-width='8' stroke-linecap='round' "
          f"style='--len:{length};stroke-dasharray:{length};animation:growline 1.0s 0.6s both ease-out'/></svg>")
    axes=(f"<svg style='position:absolute;left:0;top:0' width='{W}' height='{H}'>"
          f"<path d='M 150 560 L 150 1560 L 900 1560' fill='none' stroke='{LINE}' stroke-width='4'/></svg>")
    move=(f"<div class='serif r' style='position:absolute;left:560px;top:760px;font-size:120px;"
          f"animation:pop .5s 1.7s both'>→ {_esc(endword)}</div>")
    return ("<div class='stage'><div class='frame'></div><div class='wm'>ASKGAURAV.AI</div>"
            f"<div class='kick'>{_esc(kick)}</div>"
            f"<div class='serif' style='position:absolute;left:110px;top:250px;font-size:62px;font-weight:800;max-width:860px'>{_esc(label)}</div>"
            + axes + dots + line + move + "</div>")

def _scene_stamp(word):
    return ("<div class='stage'><div class='frame'></div><div class='wm'>ASKGAURAV.AI</div>"
            f"<div class='serif r' style='position:absolute;left:0;right:0;top:820px;text-align:center;"
            f"font-size:170px;animation:pop .5s .1s both;text-transform:uppercase'>{_esc(word)}</div></div>")

def _scene_endcard(handle):
    return ("<div class='stage'><div class='frame'></div><div class='wm'>ASKGAURAV.AI</div>"
            f"<div class='kick'>building it in public</div>"
            f"<div class='serif' style='position:absolute;left:110px;top:700px;font-size:150px;line-height:.95;"
            f"animation:fadeup .6s .1s both'>Watch the<br>real work.</div>"
            f"<div style='position:absolute;left:110px;top:1120px;width:140px;height:7px;background:{RED};border-radius:4px'></div>"
            f"<div style='position:absolute;left:110px;top:1230px;background:{RED};color:{PAPER};"
            f"font-family:Fraunces,serif;font-weight:800;font-size:64px;padding:38px 60px;border-radius:8px;"
            f"box-shadow:14px 14px 0 rgba(143,44,34,.28);animation:dropbtn .6s .5s both'>FOLLOW ALONG</div>"
            f"<div class='serif r' style='position:absolute;left:110px;bottom:120px;font-size:40px;"
            f"font-family:Newsreader,serif'>{_esc(handle)}</div></div>")

def _scene_html(spec):
    t = spec["type"]
    if t=="scatter":   inner=_scene_scatter(spec.get("kick",""))
    elif t=="strikeout": inner=_scene_strikeout(spec.get("kick",""), spec.get("words",[]))
    elif t=="plot":    inner=_scene_plot(spec.get("kick",""), spec.get("label",""), spec.get("endword","MOVE"))
    elif t=="stamp":   inner=_scene_stamp(spec.get("word",""))
    elif t=="endcard": inner=_scene_endcard(spec.get("handle","@askgauravai"))
    else: inner="<div class='stage'></div>"
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{_FONTS}{_CHROME}</style></head><body>{inner}</body></html>"


def record_motion(spec, dur, out_mp4, log=print):
    """Record a real-time CSS animation to mp4 via Playwright video, then normalize with ffmpeg."""
    from playwright.sync_api import sync_playwright
    tmp = Path(tempfile.mkdtemp(prefix="motion_"))
    html = _scene_html(spec)
    with sync_playwright() as pw:
        b = pw.chromium.launch(args=["--force-color-profile=srgb"])
        ctx = b.new_context(viewport={"width":W,"height":H},
                            record_video_dir=str(tmp),
                            record_video_size={"width":W,"height":H})
        pg = ctx.new_page()
        pg.set_content(html, wait_until="networkidle", timeout=20000)
        pg.wait_for_timeout(int(dur*1000)+500)   # let the animation play + hold
        ctx.close(); b.close()
    webm = sorted(glob.glob(str(tmp/"*.webm")))
    if not webm:
        log(f"  ⚠️ motion record produced no video for {spec.get('type')}")
        return None
    Path(out_mp4).parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([FFMPEG,"-y","-i",webm[0],"-t",f"{dur}",
                    "-vf",f"scale={W}:{H},fps=30,format=yuv420p",
                    "-an","-c:v","libx264","-crf","18","-preset","medium",str(out_mp4)],
                   capture_output=True, text=True)
    shutil.rmtree(tmp, ignore_errors=True)
    return out_mp4 if Path(out_mp4).exists() else None


# ──────────────────────────────────────────────────────────────────────────────
#  Kinetic captions  (paper-chip PNGs, red keywords)
# ──────────────────────────────────────────────────────────────────────────────
_REDWORDS = {"data","gut","feelings","building","system","real","move","guessing",
             "outputs","follow","along","problem","working","actual","actually",
             "competitor","market","gaurav","d2c"}

def _phrase_groups(words, max_words=5):
    """Group words into short caption phrases, breaking on sentence punctuation."""
    groups=[]; cur=[]
    for wd in words:
        cur.append(wd)
        ends = wd["word"].strip().endswith((".","?","!",","))
        if len(cur) >= max_words or ends:
            groups.append(cur); cur=[]
    if cur: groups.append(cur)
    out=[]
    for g in groups:
        txt=" ".join(w["word"].strip() for w in g).strip()
        st=g[0]["start"]; en=g[-1]["end"] if g[-1]["end"]>0 else st+1.5
        # red-emphasis keywords
        def deco(tok):
            bare="".join(c for c in tok.lower() if c.isalnum())
            isnum=any(c.isdigit() for c in tok)
            return f"<b>{_esc(tok)}</b>" if (bare in _REDWORDS or isnum) else _esc(tok)
        html=" ".join(deco(t) for t in txt.split())
        out.append({"start":round(st,2),"end":round(en,2),"text":txt,"html":html})
    return out

def render_captions(words, out_dir, log=print):
    from playwright.sync_api import sync_playwright
    out_dir=Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    phrases=_phrase_groups(words)
    css=(_FONTS+f"""*{{margin:0;padding:0;box-sizing:border-box}}
    html,body{{width:{W}px;background:transparent}}
    .wrap{{width:{W}px;display:flex;justify-content:center;padding:0 80px}}
    .cap{{font-family:'Fraunces',serif;font-weight:900;font-size:74px;line-height:1.12;text-align:center;
     color:{INK};letter-spacing:-0.01em;background:{PAPER};padding:14px 30px;border-radius:14px;
     box-shadow:0 12px 30px rgba(33,29,24,.20)}} .cap b{{color:{RED}}}""")
    man=[]
    with sync_playwright() as pw:
        b=pw.chromium.launch(); ctx=b.new_context(viewport={"width":W,"height":600},device_scale_factor=2)
        pg=ctx.new_page()
        for i,p in enumerate(phrases):
            pg.set_content(f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head>"
                           f"<body><div class='wrap'><div class='cap'>{p['html']}</div></div></body></html>",
                           wait_until="networkidle", timeout=20000)
            pg.wait_for_timeout(200)
            f=out_dir/f"cap_{i:02d}.png"
            pg.query_selector(".wrap").screenshot(path=str(f), omit_background=True)
            man.append({"file":str(f),"start":p["start"],"end":p["end"]})
        b.close()
    log(f"  ✅ {len(man)} caption frames")
    return man


# ──────────────────────────────────────────────────────────────────────────────
#  AI b-roll  (FAL text-to-video)
# ──────────────────────────────────────────────────────────────────────────────
def generate_broll(prompt, out_mp4, dur=5, log=print):
    key=os.getenv("FAL_API_KEY","").strip()
    if not key:
        log("  ℹ️ FAL key missing — skipping b-roll"); return None
    try:
        import fal_client, urllib.request, ssl, certifi, shutil as _sh
        os.environ["FAL_KEY"]=key
        sslctx=ssl.create_default_context(cafile=certifi.where())
        models=["fal-ai/kling-video/v1.6/standard/text-to-video",
                "fal-ai/minimax/video-01","fal-ai/luma-dream-machine"]
        url=None
        for m in models:
            try:
                log(f"  b-roll via {m} …")
                r=fal_client.subscribe(m, arguments={"prompt":prompt,"duration":"5","aspect_ratio":"9:16"})
                v=r.get("video") or {}
                url=v.get("url") if isinstance(v,dict) else None
                if not url and r.get("videos"): url=r["videos"][0].get("url")
                if url: break
            except Exception as e:
                log(f"    {m} failed: {e}")
        if not url: log("  ⚠️ all b-roll models failed"); return None
        log(f"  b-roll url: {url}")
        Path(out_mp4).parent.mkdir(parents=True, exist_ok=True)
        raw=str(out_mp4)+".raw.mp4"
        with urllib.request.urlopen(url, context=sslctx) as resp, open(raw,"wb") as fh:
            _sh.copyfileobj(resp, fh)
        # warm grade + crop/fit to 1080x1920
        subprocess.run([FFMPEG,"-y","-i",raw,"-t",f"{dur}",
            "-vf",(f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                   f"eq=contrast=1.04:saturation=1.02:gamma=1.03,"
                   f"colorbalance=rs=0.03:bs=-0.04:rm=0.03:bh=-0.03,fps=30,format=yuv420p"),
            "-an","-c:v","libx264","-crf","18","-preset","medium",str(out_mp4)],
            capture_output=True,text=True)
        try: os.remove(raw)
        except OSError: pass
        return out_mp4 if Path(out_mp4).exists() else None
    except Exception as e:
        log(f"  ⚠️ b-roll error: {e}"); return None


# ──────────────────────────────────────────────────────────────────────────────
#  Backdrop + plan + assembly
# ──────────────────────────────────────────────────────────────────────────────
def make_backdrop(out_png, log=print):
    from playwright.sync_api import sync_playwright
    html=(f"<!doctype html><html><head><meta charset='utf-8'><style>{_FONTS}"
          f"*{{margin:0;padding:0;box-sizing:border-box}}html,body{{width:{W}px;height:{H}px}}"
          f".bg{{position:relative;width:{W}px;height:{H}px;"
          f"background:radial-gradient(130% 60% at 50% -10%,rgba(178,58,46,0.05),transparent 55%),{PAPER}}}"
          f".frame{{position:absolute;inset:46px;border:2px solid {LINE}}}"
          f".wm{{position:absolute;top:84px;left:0;right:0;text-align:center;font-family:Newsreader,serif;"
          f"font-size:32px;font-weight:500;letter-spacing:.24em;text-transform:uppercase;color:{MUTE}}}"
          f".rule{{position:absolute;left:0;right:0;top:1090px;margin:auto;width:120px;height:6px;"
          f"background:{RED};border-radius:3px}}"
          f".tag{{position:absolute;left:0;right:0;bottom:120px;text-align:center;font-family:Newsreader,serif;"
          f"font-size:34px;color:{RED};font-weight:500;letter-spacing:.05em}}</style></head>"
          f"<body><div class='bg'><div class='frame'></div><div class='wm'>ASKGAURAV.AI</div>"
          f"<div class='rule'></div><div class='tag'>@askgauravai</div></div></body></html>")
    with sync_playwright() as pw:
        b=pw.chromium.launch(); ctx=b.new_context(viewport={"width":W,"height":H},device_scale_factor=1)
        pg=ctx.new_page(); pg.set_content(html,wait_until="networkidle",timeout=20000); pg.wait_for_timeout(200)
        pg.screenshot(path=str(out_png),clip={"x":0,"y":0,"width":W,"height":H}); b.close()
    return out_png

def _find(words, target, after=0.0):
    t=target.lower()
    for w in words:
        bare="".join(c for c in w["word"].lower() if c.isalnum())
        if bare==t and w["start"]>=after:
            return w["start"]
    return None

def plan_inserts(words, handle="@askgauravai"):
    """Locate beats in the transcript and attach branded motion / b-roll inserts."""
    last=words[-1]["end"] if words else 36.0
    P=[]
    t=_find(words,"data")
    if t is not None: P.append({"type":"scatter","kick":"every week, same problem",
                                "start":t-0.15,"dur":1.9,"kind":"motion"})
    t=_find(words,"course")
    if t is not None: P.append({"type":"strikeout","kick":"not a course, not a dashboard",
                                "words":["A COURSE","A DASHBOARD"],"start":t-0.4,"dur":2.2,"kind":"motion"})
    t=_find(words,"system")
    if t is not None: P.append({"type":"plot","kick":"so I started building","label":"real competitor + market data",
                                "endword":"MOVE","start":t-0.1,"dur":2.9,"kind":"motion"})
    t=_find(words,"guessing")
    if t is not None: P.append({"type":"stamp","word":"No guessing.","start":t-0.25,"dur":1.1,"kind":"motion"})
    # b-roll #1 — over the "actual move" tail, b-roll #2 — over "real work"
    t=_find(words,"outputs")
    if t is not None: P.append({"type":"broll","start":t+0.2,"dur":2.6,"kind":"broll",
        "prompt":("cinematic close-up of a focused founder at a wooden desk reviewing glowing marketing "
                  "dashboards and competitor data on a laptop, warm cream and brick-red tones, shallow depth "
                  "of field, 35mm, soft window light, documentary feel, no text")})
    t=_find(words,"follow")
    if t is not None: P.append({"type":"endcard","handle":handle,"start":t-0.2,"dur":max(1.6,last-(t-0.2)),"kind":"motion"})
    return P


def build_reel(founder_video, transcript, out_path, handle="@askgauravai",
               work_dir=None, enable_broll=True, tail_hold=2.6, log=print):
    founder_video=Path(founder_video); out_path=Path(out_path)
    work=Path(work_dir) if work_dir else out_path.parent/"_reelwork"
    work.mkdir(parents=True, exist_ok=True)

    # normalize transcript -> words[{word,start,end}]
    words=[]
    if transcript.get("words"):
        words=transcript["words"]
    else:
        for seg in transcript.get("segments",[]):
            if isinstance(seg,dict):
                ts=seg.get("timestamp",[0,0])
                token=(seg.get("word") or seg.get("text") or "").strip()
                words.append({"word":token,
                              "start":ts[0] if isinstance(ts,list) and ts else 0,
                              "end":ts[1] if isinstance(ts,list) and len(ts)>1 else 0})
    dur=float(subprocess.run([FFPROBE,"-v","error","-show_entries","format=duration",
            "-of","default=nokey=1:noprint_wrappers=1",str(founder_video)],
            capture_output=True,text=True).stdout.strip() or 0)
    log(f"founder {dur:.2f}s, {len(words)} words")

    caps=render_captions(words, work/"caps", log)
    plan=plan_inserts(words, handle)

    # hold the end card as the final frame: extend it to cover a frozen tail
    TOTAL=round(dur+tail_hold,2)
    for ins in plan:
        if ins["type"]=="endcard":
            ins["dur"]=round(TOTAL-ins["start"],2)

    # render inserts
    rendered=[]
    for i,ins in enumerate(plan):
        f=work/f"insert_{i:02d}.mp4"
        if ins["kind"]=="motion":
            r=record_motion(ins, ins["dur"], f, log)
        elif ins["kind"]=="broll" and enable_broll:
            if f.exists() and f.stat().st_size>0:
                log(f"  ↺ reusing cached b-roll {f.name} (no FAL charge)")
                r=str(f)
            else:
                r=generate_broll(ins["prompt"], f, dur=ins["dur"], log=log)
        else:
            r=None
        if r: rendered.append({"file":str(f),"start":ins["start"],"dur":ins["dur"],"type":ins["type"]})
        else: log(f"  · insert {ins['type']} skipped")

    # ── ffmpeg compose ── (footage is already vertical 9:16 → scale to fill, no crop)
    inputs=["-i",str(founder_video)]
    idx=1; capidx=[]
    for c in caps: inputs+=["-i",c["file"]]; capidx.append((idx,c["start"],c["end"])); idx+=1
    insidx=[]
    for r in rendered: inputs+=["-i",r["file"]]; insidx.append((idx,r["start"],r["dur"])); idx+=1

    # base: founder filled to 1080x1920 (no crop for exact 9:16) + warm Founder-Journal grade + light grain
    fc=[(f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=30,"
         "eq=contrast=1.05:brightness=0.012:saturation=1.03:gamma=1.04,"
         "colorbalance=rs=0.03:gs=0.01:bs=-0.05:rm=0.04:bm=-0.05:rh=0.03:bh=-0.04,"
         "noise=alls=5:allf=t,vignette=PI/6,"
         f"tpad=stop_mode=clone:stop_duration={tail_hold},setsar=1[v0]")]
    prev="v0"
    for in_i,st,en in capidx:
        tag=f"c{in_i}"; out=f"vc{in_i}"
        fc.append(f"[{in_i}:v]scale=900:-1[{tag}]")
        fc.append(f"[{prev}][{tag}]overlay=x=(W-w)/2:y=1500:enable='between(t,{st},{en})'[{out}]")
        prev=out
    for in_i,st,d in insidx:
        tag=f"i{in_i}"; out=f"vi{in_i}"
        fc.append(f"[{in_i}:v]scale={W}:{H},setsar=1,setpts=PTS+{st}/TB[{tag}]")
        fc.append(f"[{prev}][{tag}]overlay=0:0:enable='between(t,{st},{st+d})'[{out}]")
        prev=out
    fc.append(f"[0:a]aresample=async=1,loudnorm=I=-16:TP=-1.5:LRA=11,"
              f"apad=whole_dur={TOTAL},afade=t=out:st={TOTAL-0.45}:d=0.45[aout]")

    cmd=[FFMPEG,"-y",*inputs,"-filter_complex",";".join(fc),
         "-map",f"[{prev}]","-map","[aout]","-t",f"{TOTAL}",
         "-r","30","-c:v","libx264","-profile:v","high","-pix_fmt","yuv420p",
         "-crf","19","-preset","medium","-c:a","aac","-b:a","192k",
         "-movflags","+faststart",str(out_path)]
    log(f"composing → {out_path.name} ({len(fc)} filters, {len(rendered)} inserts, {len(caps)} captions, {TOTAL}s)")
    p=subprocess.run(cmd,capture_output=True,text=True)
    if p.returncode!=0:
        log("FFMPEG ERROR:\n"+p.stderr[-2500:]); return None
    return {"output":str(out_path),"inserts":len(rendered),"captions":len(caps),"duration":TOTAL}


if __name__ == "__main__":
    import sys
    base=Path(__file__).parent.parent
    src=base/"brands/askgauravai/visuals/videos/AskGauravAI insta and YT reel 1.mov"
    tr=json.load(open(base/"brands/askgauravai/visuals/videos/_edit/audio.json"))
    words=[]
    for s in tr["segments"]:
        for w in s.get("words",[]):
            words.append({"word":w["word"].strip(),"start":round(w["start"],2),"end":round(w["end"],2)})
    out=base/"brands/askgauravai/visuals/videos/AskGauravAI_reel1_v2.mp4"
    broll = "--broll" in sys.argv
    r=build_reel(src, {"words":words}, out, enable_broll=broll)
    print(r)
