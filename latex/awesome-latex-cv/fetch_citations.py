#!/usr/bin/env python3
r"""Fetch citation counts for the papers listed in the CV and write citations_data.tex.

Usage:
  python3 fetch_citations.py
  python3 fetch_citations.py --force        # ignore TTL cache
  SCHOLAR_USER=xxxx python3 fetch_citations.py

Sources, tried in order:
  1. Google Scholar profile page (exact Scholar numbers, but Google often
     answers 403/CAPTCHA from datacenter or repeat-visitor IPs)
  2. OpenAlex title search (open API, no key; counts of duplicate records for
     the same title — e.g. arXiv preprint + published version — are summed,
     which mirrors how Scholar merges versions)
  3. Semantic Scholar title search (aggressively rate-limited without a key)
  4. whatever is already in citations_data.tex

Paper titles are read straight out of the .tex sources, from the title argument
of \ghhref / \paperhref / \pubhref / \pubtitle, and are used verbatim as the
LaTeX lookup key — nothing to keep in sync by hand.
"""

from __future__ import annotations

import difflib
import gzip
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "citations_data.tex"
CACHE_TTL_SEC = int(os.environ.get("CITATIONS_TTL", str(24 * 3600)))
SCHOLAR_USER = os.environ.get("SCHOLAR_USER", "ZMbWaLkAAAAJ")
CONTACT_EMAIL = os.environ.get("OPENALEX_MAILTO", "a943678231@gmail.com")
# Minimum title similarity (0-1) for a remote record to count as the same paper.
MATCH_CUTOFF = 0.87

# CV title -> title as indexed remotely, for papers renamed between preprint and
# publication (fuzzy matching cannot bridge a real rename). Add entries here when
# the run reports "no data" for a paper you know is on your Scholar profile.
TITLE_ALIASES = {
    "Towards Real-time Scalable Dense Mapping using Robot-centric Implicit Representation":
        "Towards Large-Scale Incremental Dense Mapping using Robot-centric Implicit Neural Representation",
}

# \ghhref{repo}{title} | \paperhref{url}{repo}{title} | \pubhref{url}{title} | \pubtitle{title}
TITLE_MACROS = {
    "ghhref": 2,      # title is the 2nd argument
    "paperhref": 3,
    "pubhref": 2,
    "pubtitle": 1,
}
MACRO_RE = re.compile(r"\\(ghhref|paperhref|pubhref|pubtitle)\s*((?:\{[^{}]*\}\s*){1,3})")
ARG_RE = re.compile(r"\{([^{}]*)\}")

UA = f"jianhengLiu-cv-citation-fetch (mailto:{CONTACT_EMAIL})"


def strip_comments(text: str) -> str:
    return "\n".join(re.sub(r"(?<!\\)%.*", "", line) for line in text.splitlines())


def find_titles(tex_paths: list[Path]) -> list[str]:
    titles: list[str] = []
    seen: set[str] = set()
    for path in tex_paths:
        body = strip_comments(path.read_text(encoding="utf-8", errors="ignore"))
        for m in MACRO_RE.finditer(body):
            name = m.group(1)
            args = ARG_RE.findall(m.group(2))
            idx = TITLE_MACROS[name] - 1
            if len(args) <= idx:
                continue
            title = " ".join(args[idx].split())
            if len(title) < 12 or title in seen:
                continue
            seen.add(title)
            titles.append(title)
    return titles


def norm(s: str) -> str:
    """Normalize a title for fuzzy comparison."""
    s = re.sub(r"\\[a-zA-Z]+\s*", " ", s)          # drop stray LaTeX macros
    s = re.sub(r"[^a-z0-9]+", " ", s.lower())
    return " ".join(s.split())


def similar(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def get(url: str, headers: dict[str, str] | None = None, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        return raw.decode("utf-8", "replace")


# Google Scholar answers 403 to bare urllib requests; it needs a full browser header set.
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "close",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}


# --------------------------------------------------------------------------- #
# Source 1: Google Scholar profile
# --------------------------------------------------------------------------- #
SCHOLAR_ROW_RE = re.compile(
    r'class="gsc_a_at"[^>]*>([^<]+)</a>.*?class="gsc_a_ac[^"]*"[^>]*>\s*([0-9]*)\s*<', re.S
)


def fetch_scholar(user: str) -> dict[str, int]:
    """Return {title: citations} from a public Scholar profile, {} on failure."""
    out: dict[str, int] = {}
    for cstart in (0, 100, 200):
        url = "https://scholar.google.com/citations?" + urllib.parse.urlencode(
            {"user": user, "hl": "en", "cstart": cstart, "pagesize": 100,
             "view_op": "list_works", "sortby": "pubdate"}
        )
        try:
            html = get(url, BROWSER_HEADERS)
        except Exception as e:  # noqa: BLE001
            print(f"  ! Google Scholar unavailable ({e}); falling back", file=sys.stderr)
            return out
        if "gsc_a_at" not in html:
            if cstart == 0:
                print("  ! Google Scholar returned no publication rows (CAPTCHA?); falling back",
                      file=sys.stderr)
            break
        before = len(out)
        for m in SCHOLAR_ROW_RE.finditer(html):
            title = unescape_html(m.group(1)).strip()
            out[title] = int(m.group(2)) if m.group(2).strip() else 0
        if len(out) - before < 100:
            break
        time.sleep(1.0)
    if out:
        print(f"  Google Scholar: {len(out)} entries")
    return out


def unescape_html(s: str) -> str:
    import html

    return html.unescape(s)


# --------------------------------------------------------------------------- #
# Source 2: OpenAlex
# --------------------------------------------------------------------------- #
def fetch_openalex(title: str) -> int | None:
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode(
        {
            "filter": "title.search:" + re.sub(r"[^\w\s-]", " ", title),
            "per-page": 10,
            "mailto": CONTACT_EMAIL,
        }
    )
    try:
        data = json.loads(get(url))
    except Exception as e:  # noqa: BLE001
        print(f"  ! OpenAlex failed for {title[:40]}...: {e}", file=sys.stderr)
        return None
    # Sum duplicate records of the same work (preprint + published), like Scholar merges them.
    total, hits = 0, 0
    for w in data.get("results", []):
        remote = w.get("title") or w.get("display_name") or ""
        if similar(remote, title) >= MATCH_CUTOFF:
            total += int(w.get("cited_by_count") or 0)
            hits += 1
    return total if hits else None


# --------------------------------------------------------------------------- #
# Source 3: Semantic Scholar
# --------------------------------------------------------------------------- #
def fetch_semanticscholar(title: str, attempts: int = 3) -> int | None:
    url = "https://api.semanticscholar.org/graph/v1/paper/search?" + urllib.parse.urlencode(
        {"query": title, "fields": "title,citationCount", "limit": 5}
    )
    headers = {}
    key = os.environ.get("S2_API_KEY")
    if key:
        headers["x-api-key"] = key
    data = None
    for attempt in range(attempts):
        try:
            data = json.loads(get(url, headers))
            break
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < attempts - 1:
                time.sleep(3 * (attempt + 1))  # shared unauthenticated pool; back off
                continue
            print(f"  ! Semantic Scholar failed for {title[:40]}...: {e}", file=sys.stderr)
            return None
        except Exception as e:  # noqa: BLE001
            print(f"  ! Semantic Scholar failed for {title[:40]}...: {e}", file=sys.stderr)
            return None
    if data is None:
        return None
    best = None
    for p in data.get("data", []):
        if similar(p.get("title") or "", title) >= MATCH_CUTOFF:
            n = int(p.get("citationCount") or 0)
            best = n if best is None else max(best, n)
    return best


def load_existing() -> dict[str, str]:
    if not OUT.exists():
        return {}
    out: dict[str, str] = {}
    for m in re.finditer(
        r"\\csname\s+citationcount@(.+?)\\endcsname\{([^}]*)\}",
        OUT.read_text(encoding="utf-8"),
    ):
        out[m.group(1)] = m.group(2)
    return out


def main() -> int:
    force = "--force" in sys.argv or "-f" in sys.argv
    # Only publication sections — \ghhref is also used for project repos, whose
    # short names are not paper titles.
    tex_files = sorted(ROOT.glob("section_publications*.tex"))
    titles = find_titles(tex_files)
    if not titles:
        print("No paper titles found (use \\ghhref/\\paperhref/\\pubhref/\\pubtitle).")
        return 0

    print(f"Found {len(titles)} paper title(s).")
    cached = load_existing()
    if not force and OUT.exists() and (time.time() - OUT.stat().st_mtime) < CACHE_TTL_SEC:
        age_h = (time.time() - OUT.stat().st_mtime) / 3600
        print(f"Cache fresh ({age_h:.1f}h old, TTL {CACHE_TTL_SEC // 3600}h); skip network.")
        return 0

    scholar = fetch_scholar(SCHOLAR_USER)
    counts: dict[str, int] = {}

    for i, title in enumerate(titles):
        n: int | None = None
        src = ""
        if scholar:
            lookup = TITLE_ALIASES.get(title, title)
            best_key, best_score = None, 0.0
            for k in scholar:
                s = similar(k, lookup)
                if s > best_score:
                    best_key, best_score = k, s
            if best_key is not None and best_score >= MATCH_CUTOFF:
                n, src = scholar[best_key], "scholar"
        if n is None:
            # Neither open source alone tracks robotics venues well: OpenAlex misses
            # arXiv-only work, S2 misses some published records. Take the higher of
            # the two — that is the closer approximation of the Scholar number.
            if i:
                time.sleep(0.4)  # be polite to the open APIs
            oa = fetch_openalex(title)
            s2 = fetch_semanticscholar(title)
            candidates = {"openalex": oa, "s2": s2}
            best = [(k, v) for k, v in candidates.items() if v is not None]
            if best:
                src, n = max(best, key=lambda kv: kv[1])
                other = ", ".join(f"{k}={v}" for k, v in best if k != src)
                if other:
                    src = f"{src}; {other}"
        if n is None:
            if title in cached:
                counts[title] = int(cached[title])
                print(f"  ~ {title[:52]}: cached {cached[title]}")
            else:
                print(f"  x {title[:52]}: no data")
            continue
        counts[title] = n
        print(f"  + {title[:52]}: {n} ({src})")

    lines = [
        "% Auto-generated by fetch_citations.py — do not edit by hand",
        "% Re-run: python3 fetch_citations.py [--force]",
        "",
    ]
    for title, n in sorted(counts.items(), key=lambda x: x[0].lower()):
        if n <= 0:
            continue  # uncited / not-yet-indexed papers get no badge
        lines.append(rf"\expandafter\def\csname citationcount@{title}\endcsname{{{n}}}")
    lines.append("")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT.name} ({sum(1 for n in counts.values() if n > 0)} entries)")
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    # Never break a LaTeX build: fall back to whatever counts are already cached.
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        print(f"citation refresh failed ({exc}); using cached counts")
        raise SystemExit(0)
