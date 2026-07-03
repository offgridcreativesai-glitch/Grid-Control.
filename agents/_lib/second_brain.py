"""
Second Brain — per-brand linked knowledge vault for the agent team (Jul 3 2026).

The answer to "should GC's agents have an Obsidian-style second brain":
YES — but NOT as a sixth memory store. GC already has five (Supabase KV
brand_memory, Voyage+pgvector semantic memory, brand_narrative story-so-far,
agent_learnings.jsonl, per-agent skills/*.md). Each is write-only-ish and none
of them link to each other, so no agent (or human) can traverse "this hook won
→ because this audience insight → which came from this scrape". This module is
the UNIFYING layer: a human-readable, git-diffable, linked-markdown vault at
brands/{slug}/second_brain/ that

  1. sync() — renders the EXISTING stores into linked notes (idempotent, no
     LLM, zero API cost; Supabase-backed sources are skipped silently offline),
  2. note() — lets agents write durable cross-session insight notes with
     [[wikilinks]] to other notes,
  3. context_block() — gives every agent ONE call that assembles a
     prompt-ready block from the vault (index + linked-note traversal),
     instead of juggling five separate recall APIs.

Isolation: everything lives under brands/{slug}/ — invariant 3 holds.
Zero fabrication: notes must carry a `source:` field naming the run/file that
produced them; sync-generated notes cite their source store.

Layout:
    brands/{slug}/second_brain/
        INDEX.md                    ← one line per note (the recall surface)
        notes/<kebab-title>.md      ← one fact/insight per file, frontmatter + [[links]]

Frontmatter: name, agent, kind (insight|decision|profile|skill|narrative),
source, created. Body may reference other notes as [[note-name]].
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BRANDS_DIR = os.environ.get("BRANDS_DIR", os.path.join(_PROJECT_ROOT, "brands"))

_KINDS = ("insight", "decision", "profile", "skill", "narrative", "performance")


def _kebab(text: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9-]", "-", text.lower())).strip("-")[:80]


class SecondBrain:
    def __init__(self, brand_slug: str, brands_dir: str | None = None):
        self.brand_slug = brand_slug
        self.root = os.path.join(brands_dir or BRANDS_DIR, brand_slug, "second_brain")
        self.notes_dir = os.path.join(self.root, "notes")
        self.index_path = os.path.join(self.root, "INDEX.md")

    # ── write ────────────────────────────────────────────────────────────────

    def note(
        self,
        agent: str,
        title: str,
        body: str,
        kind: str = "insight",
        source: str = "",
        links: list[str] | None = None,
    ) -> str | None:
        """Write one durable note. Returns note name (kebab slug) or None.
        `source` should name the run/file/scrape that grounds the note —
        empty source is allowed only for kind='decision' (human decisions)."""
        if kind not in _KINDS:
            kind = "insight"
        if not source and kind != "decision":
            # zero-fabrication: an insight with no source is an opinion — refuse.
            print(f"[second_brain] refused sourceless {kind} note: {title[:50]}")
            return None
        name = _kebab(title)
        if not name:
            return None
        os.makedirs(self.notes_dir, exist_ok=True)
        link_lines = ""
        if links:
            link_lines = "\n\nRelated: " + " ".join(f"[[{_kebab(l)}]]" for l in links)
        content = (
            f"---\n"
            f"name: {name}\n"
            f"agent: {agent}\n"
            f"kind: {kind}\n"
            f"source: {source}\n"
            f"created: {datetime.now(timezone.utc).isoformat()}\n"
            f"---\n\n"
            f"# {title}\n\n{body.strip()}{link_lines}\n"
        )
        with open(os.path.join(self.notes_dir, f"{name}.md"), "w") as f:
            f.write(content)
        self._index_add(name, agent, kind, title)
        return name

    def _index_add(self, name: str, agent: str, kind: str, title: str) -> None:
        line = f"- [[{name}]] · {kind} · {agent} — {title}"
        existing = ""
        if os.path.exists(self.index_path):
            with open(self.index_path) as f:
                existing = f.read()
        if f"[[{name}]]" in existing:
            # replace the stale line for this note
            existing = "\n".join(
                l for l in existing.splitlines() if f"[[{name}]]" not in l
            )
        header = f"# Second Brain — {self.brand_slug}\n"
        if not existing.strip():
            existing = header
        with open(self.index_path, "w") as f:
            f.write(existing.rstrip() + "\n" + line + "\n")

    # ── sync from existing memory stores (no LLM, no cost) ──────────────────

    def sync(self) -> dict:
        """Render existing per-brand stores into the vault. Idempotent.
        Returns counts per source. Supabase-backed stores sync only when DB
        reachable; file stores always sync."""
        counts = {"profile": 0, "archetype": 0, "learnings": 0, "skills": 0, "narrative": 0}
        bdir = os.path.dirname(self.root)

        # brand_profile.json → profile note (the root node everything links to)
        prof_path = os.path.join(bdir, "brand_profile.json")
        if os.path.exists(prof_path):
            try:
                with open(prof_path) as f:
                    prof = json.load(f)
                summary = "\n".join(
                    f"- **{k}**: {json.dumps(v)[:200]}"
                    for k, v in prof.items()
                    if k in ("brand_name", "product", "target_audience", "tone",
                             "tone_of_voice", "platforms", "north_star_metric",
                             "positioning", "unique_tension", "business_model_archetype")
                    and v
                )
                if self.note("system", "brand profile", summary or "(profile present, key fields empty)",
                             kind="profile", source="brand_profile.json"):
                    counts["profile"] = 1
            except Exception as e:
                print(f"[second_brain] profile sync skipped: {e}")

        # brand_archetype.json → archetype note (STEP 0 reasoning record)
        arch_path = os.path.join(bdir, "brand_archetype.json")
        if os.path.exists(arch_path):
            try:
                with open(arch_path) as f:
                    arch = json.load(f)
                body = (
                    f"Archetype: **{arch.get('archetype')}** "
                    f"(source: {arch.get('source')}, confidence: {arch.get('confidence')})\n\n"
                    "Signals:\n" + "\n".join(f"- {s}" for s in arch.get("signals", []))
                )
                if self.note("system", "brand archetype", body, kind="profile",
                             source="brand_archetype.json", links=["brand profile"]):
                    counts["archetype"] = 1
            except Exception as e:
                print(f"[second_brain] archetype sync skipped: {e}")

        # agent_learnings.jsonl → one note per learning (capped at last 50)
        learn_path = os.path.join(bdir, "agent_learnings.jsonl")
        if os.path.exists(learn_path):
            try:
                with open(learn_path) as f:
                    rows = [json.loads(l) for l in f if l.strip()][-50:]
                for r in rows:
                    text = r.get("text") or r.get("content") or ""
                    agent = r.get("agent") or r.get("agent_slug") or "unknown"
                    if not text:
                        continue
                    title = f"{agent} learning {r.get('ts', '')[:10]} {text[:40]}"
                    if self.note(agent, title, text, kind="insight",
                                 source="agent_learnings.jsonl",
                                 links=["brand profile"]):
                        counts["learnings"] += 1
            except Exception as e:
                print(f"[second_brain] learnings sync skipped: {e}")

        # skills/<agent>/*.md → skill notes (already markdown, link them in)
        skills_root = os.path.join(bdir, "skills")
        if os.path.isdir(skills_root):
            for agent_dir in sorted(os.listdir(skills_root)):
                adir = os.path.join(skills_root, agent_dir)
                if not os.path.isdir(adir):
                    continue
                for fn in sorted(os.listdir(adir)):
                    if not fn.endswith(".md"):
                        continue
                    try:
                        with open(os.path.join(adir, fn)) as f:
                            body = f.read()
                        if self.note(agent_dir, f"skill {agent_dir} {fn[:-3]}",
                                     body[:2000], kind="skill",
                                     source=f"skills/{agent_dir}/{fn}",
                                     links=["brand profile"]):
                            counts["skills"] += 1
                    except Exception:
                        continue

        # brand_narrative (Supabase) → rolling narrative note, best-effort
        try:
            import sys
            supa = os.path.join(_PROJECT_ROOT, "supabase")
            if supa not in sys.path:
                sys.path.insert(0, supa)
            import db as _db
            row = _db.get_brand(self.brand_slug)
            if row:
                entries = _db.get_narrative(row["id"], n=30)
                if entries:
                    body = "\n".join(
                        f"- [{(e.get('ts') or '')[:10]}] {e.get('agent','?')} · "
                        f"{e.get('entry_type','?')}: {e.get('summary','')}"
                        for e in entries
                    )
                    if self.note("system", "story so far", body, kind="narrative",
                                 source="supabase.brand_narrative",
                                 links=["brand profile"]):
                        counts["narrative"] = 1
        except Exception:
            pass  # offline / no DB — file stores already synced

        return counts

    # ── read ─────────────────────────────────────────────────────────────────

    def read_index(self) -> str:
        if not os.path.exists(self.index_path):
            return ""
        with open(self.index_path) as f:
            return f.read()

    def _read_note(self, name: str) -> str:
        path = os.path.join(self.notes_dir, f"{name}.md")
        if not os.path.exists(path):
            return ""
        with open(path) as f:
            return f.read()

    def context_block(self, agent: str = "", query: str = "", budget_chars: int = 6000) -> str:
        """One-call prompt block: index + best-matching notes + their 1-hop links.
        Keyword match (free, offline); pair with BaseAgent.semantic_recall for
        fuzzy recall when Voyage/Supabase are live."""
        index = self.read_index()
        if not index:
            return ""
        note_names = re.findall(r"\[\[([a-z0-9-]+)\]\]", index)

        # rank: query keywords > agent's own notes > profile/archetype roots
        q_tokens = {t for t in re.split(r"[^a-z0-9]+", query.lower()) if len(t) > 2}
        scored = []
        for line in index.splitlines():
            m = re.search(r"\[\[([a-z0-9-]+)\]\]", line)
            if not m:
                continue
            name = m.group(1)
            score = sum(1 for t in q_tokens if t in line.lower()) * 3
            if agent and agent in line:
                score += 2
            if "profile" in line or "archetype" in line or "story-so-far" in name:
                score += 4
            scored.append((score, name))
        scored.sort(reverse=True)

        picked, seen, used = [], set(), 0
        for _, name in scored:
            if name in seen:
                continue
            content = self._read_note(name)
            if not content:
                continue
            body = content.split("---", 2)[-1].strip()
            if used + len(body) > budget_chars:
                break
            picked.append(body)
            seen.add(name)
            used += len(body)
            # 1-hop link traversal
            for linked in re.findall(r"\[\[([a-z0-9-]+)\]\]", content):
                if linked in seen or linked not in note_names:
                    continue
                lc = self._read_note(linked)
                lbody = lc.split("---", 2)[-1].strip() if lc else ""
                if lbody and used + len(lbody) <= budget_chars:
                    picked.append(lbody)
                    seen.add(linked)
                    used += len(lbody)

        if not picked:
            return ""
        return (
            f"\n## Second Brain — {self.brand_slug} (linked brand knowledge, cite as second_brain/)\n\n"
            + "\n\n---\n\n".join(picked) + "\n"
        )


def get_second_brain(brand_slug: str) -> SecondBrain:
    return SecondBrain(brand_slug)
