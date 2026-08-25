#!/usr/bin/env python3
r"""Fetch citation counts for the papers listed in the CV and write citations_data.tex.

Usage:
  python3 fetch_citations.py
  python3 fetch_citations.py --force        # ignore TTL cache
  SCHOLAR_USER=xxxx python3 fetch_citations.py

Google Scholar is the ONLY accepted source. OpenAlex / Semantic Scholar
undercount robotics work badly (they do not merge the arXiv preprint with the
published conference version the way Scholar does), so letting them fill in
silently corrupts the numbers — that is exactly how the weekly CI run once
rewrote dynamic-vins from 126 down to 108. When Scholar is unavailable (it
answers 403/CAPTCHA from datacenter IPs, i.e. most GitHub Actions runs) the
counts already in citations_data.tex are kept untouched.

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
SITE_ROOT = ROOT.parents[1]  # repo root (jianhengLiu.github.io)
OUT = ROOT / "citations_data.tex"
SITE_OUT = SITE_ROOT / "_data" / "citations.yml"
# key -> exact Scholar title, so the browser-side live refresh can match the
# rows it scrapes from the profile back onto the badges on the page.
SITE_TITLES_OUT = SITE_ROOT / "_data" / "scholar_titles.yml"
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

# CV / Scholar paper title -> short key used by the website Liquid includes
# ({% include citations.html key="gs-sdf" %}) and _data/citations.yml.
WEB_KEYS = {
    "GS-SDF: LiDAR-Augmented Gaussian Splatting and Neural SDF for Geometrically Consistent Rendering and Reconstruction":
        "gs-sdf",
    "Neural Surface Reconstruction and Rendering for LiDAR-Visual Systems":
        "m2mapping",
    "Towards Large-Scale Incremental Dense Mapping using Robot-centric Implicit Neural Representation":
        "rim",
    "Active Implicit Object Reconstruction using Uncertainty-guided Next-Best-View Optimziation":
        "active-implicit-recon",
    "Adaptive trajectory tracking of UAV with a cable-suspended load using vision-inertial-based estimation":
        "adaptive-trajectory-uav",
    "RGB-D Inertial Odometry for a Resource-restricted Robot in Dynamic Environments":
        "dynamic-vins",
    "Sampling-Based View Planning for MAVs in Active Visual-inertial State Estimation":
        "sampling-based-view-planning",
    "Vision-Inertial-based Adaptive State Estimation of Hexacopter with a Cable-Suspended Load":
        "vision-inertial-hexacopter",
    "Vision-encoder-based Payload State Estimation for Autonomous MAV With a Suspended Payload":
        "vision-encoder-payload",
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
        # Still refresh the website YAML from the cached TeX counts.
        write_site_yaml({t: int(v) for t, v in cached.items() if str(v).isdigit()})
        return 0

    scholar = fetch_scholar(SCHOLAR_USER)
    if not scholar:
        print("  ! Google Scholar unavailable — keeping the counts already on disk "
              "(no other source is trusted).", file=sys.stderr)

    counts: dict[str, int] = {}
    scholar_titles: dict[str, str] = {}

    for title in titles:
        n: int | None = None
        matched = ""
        if scholar:
            lookup = TITLE_ALIASES.get(title, title)
            best_key, best_score = None, 0.0
            for k in scholar:
                sc = similar(k, lookup)
                if sc > best_score:
                    best_key, best_score = k, sc
            if best_key is not None and best_score >= MATCH_CUTOFF:
                n, matched = scholar[best_key], best_key
        if n is None:
            if title in cached:
                counts[title] = int(cached[title])
                print(f"  ~ {title[:52]}: kept {cached[title]} (not on Scholar this run)")
            else:
                print(f"  x {title[:52]}: no Scholar entry")
            continue
        counts[title] = n
        scholar_titles[title] = matched
        print(f"  + {title[:52]}: {n}")

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
    write_site_yaml(counts)
    write_scholar_titles(scholar_titles)
    return 0


def web_key_for(title: str) -> str | None:
    """Map a CV/Scholar paper title onto the short key used by the website."""
    key = WEB_KEYS.get(title)
    if key:
        return key
    # Fuzzy-match against WEB_KEYS titles (handles tiny spelling diffs).
    best_key, best_score = None, 0.0
    for t, k in WEB_KEYS.items():
        score = similar(t, title)
        if score > best_score:
            best_key, best_score = k, score
    return best_key if best_score >= MATCH_CUTOFF else None


def write_site_yaml(counts: dict[str, int]) -> None:
    """Mirror citation counts into _data/citations.yml for the personal website."""
    web: dict[str, int] = {}
    for title, n in counts.items():
        if n <= 0:
            continue
        key = web_key_for(title)
        if key:
            web[key] = max(n, web.get(key, 0))

    # Preserve previously known keys if this run missed a title (network blip).
    if SITE_OUT.exists():
        for line in SITE_OUT.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^([A-Za-z0-9_-]+):\s*(\d+)\s*$", line.strip())
            if m and m.group(1) not in web:
                web[m.group(1)] = int(m.group(2))

    SITE_OUT.parent.mkdir(parents=True, exist_ok=True)
    out_lines = [
        "# Auto-generated by latex/awesome-latex-cv/fetch_citations.py — do not edit by hand",
        "# Re-run: python3 latex/awesome-latex-cv/fetch_citations.py [--force]",
        "# Or wait for the weekly GitHub Action sync.",
        "",
    ]
    for key in sorted(web):
        out_lines.append(f"{key}: {web[key]}")
    out_lines.append("")
    SITE_OUT.write_text("\n".join(out_lines), encoding="utf-8")
    print(f"Wrote {SITE_OUT.relative_to(SITE_ROOT)} ({len(web)} entries)")


def write_scholar_titles(scholar_titles: dict[str, str]) -> None:
    """Mirror key -> exact Scholar title into _data/scholar_titles.yml.

    The website's live refresh scrapes the Scholar profile in the visitor's
    browser; it needs to know which scraped row belongs to which badge.
    """
    web: dict[str, str] = {}
    for title, scholar_title in scholar_titles.items():
        key = web_key_for(title)
        if key and scholar_title:
            web[key] = scholar_title

    if not web:  # Scholar was unreachable this run; leave the existing map alone.
        return

    # Keep keys this run did not see (e.g. a paper temporarily off the profile).
    if SITE_TITLES_OUT.exists():
        for line in SITE_TITLES_OUT.read_text(encoding="utf-8").splitlines():
            m = re.match(r'^([A-Za-z0-9_-]+):\s*"(.*)"\s*$', line.strip())
            if m and m.group(1) not in web:
                web[m.group(1)] = m.group(2)

    out_lines = [
        "# Auto-generated by latex/awesome-latex-cv/fetch_citations.py — do not edit by hand",
        "# Maps a badge key to the exact title on the Google Scholar profile, so the",
        "# browser-side live refresh can match scraped rows back onto the badges.",
        "",
    ]
    for key in sorted(web):
        out_lines.append(f'{key}: "{web[key]}"')
    out_lines.append("")
    SITE_TITLES_OUT.write_text("\n".join(out_lines), encoding="utf-8")
    print(f"Wrote {SITE_TITLES_OUT.relative_to(SITE_ROOT)} ({len(web)} entries)")


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
