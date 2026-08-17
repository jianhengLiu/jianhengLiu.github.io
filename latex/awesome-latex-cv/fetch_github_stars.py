#!/usr/bin/env python3
"""Fetch GitHub star counts referenced in CV .tex files and write github_stars_data.tex.

Usage:
  python3 fetch_github_stars.py
  python3 fetch_github_stars.py --force          # ignore TTL cache
  GITHUB_TOKEN=ghp_xxx python3 fetch_github_stars.py   # higher rate limit

Scans for:
  - \\ghhref{owner/repo}{...}
  - \\githubstars{owner/repo}
  - \\paperhref{url}{owner/repo}{...}
  - https://github.com/owner/repo  (in hrefs)
"""

from __future__ import annotations

import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "github_stars_data.tex"
# Skip network refresh if cache is newer than this (seconds). Force with --force.
CACHE_TTL_SEC = int(os.environ.get("GITHUB_STARS_TTL", str(6 * 3600)))

REPO_RE = re.compile(
    r"(?:https?://)?(?:www\.)?github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?(?:[/#?]|$)"
)
MACRO_RE = re.compile(
    r"\\(?:ghhref|githubstars|paperhref)\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}(?:\s*\{([^}]+)\})?"
)

# Skip template / personal profile links
SKIP_OWNERS = {"huajh", "academicpages", "nerfies", "boathit", "billryan"}
SKIP_REPOS = {"awesome-latex-cv", "huajh-awesome-latex-cv"}


def find_repos(tex_paths: list[Path]) -> set[str]:
    repos: set[str] = set()
    for path in tex_paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        # Strip comments (naive, line-based)
        lines = []
        for line in text.splitlines():
            if "%" in line:
                # keep \% 
                cleaned = re.sub(r"(?<!\\)%.*", "", line)
                lines.append(cleaned)
            else:
                lines.append(line)
        body = "\n".join(lines)

        for m in REPO_RE.finditer(body):
            owner, repo = m.group(1), m.group(2)
            if owner.lower() in SKIP_OWNERS or repo in SKIP_REPOS:
                continue
            if owner == "github.com":
                continue
            repos.add(f"{owner}/{repo}")

        for m in MACRO_RE.finditer(body):
            first, second = m.group(1), m.group(2)
            cmd = m.group(0)
            if cmd.startswith(r"\paperhref") and second:
                # \paperhref{url}{owner/repo}{text} — first is url, second is repo
                candidate = second.strip()
            elif cmd.startswith(r"\ghhref") or cmd.startswith(r"\githubstars"):
                candidate = first.strip()
            else:
                continue
            if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", candidate):
                repos.add(candidate)

    return repos


def fetch_stars_html(repo: str) -> int | None:
    """Fallback: scrape public repo page when API is rate-limited."""
    url = f"https://github.com/{repo}"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; cv-star-fetch/1.0)"}
    req = urllib.request.Request(url, headers=headers)
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=25) as resp:
            html = resp.read().decode("utf-8", "ignore")
        m = re.search(r"(\d[\d,]*)\s+users?\s+starred this repository", html)
        if not m:
            m = re.search(r'aria-label="(\d[\d,]*)\s+star', html)
        if not m:
            return None
        return int(m.group(1).replace(",", ""))
    except Exception as e:  # noqa: BLE001
        print(f"  ! {repo}: html fallback failed: {e}", file=sys.stderr)
        return None


def fetch_stars(repo: str, token: str | None) -> int | None:
    url = f"https://api.github.com/repos/{repo}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "jianhengLiu-cv-star-fetch",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=20) as resp:
            data = json.load(resp)
        return int(data["stargazers_count"])
    except urllib.error.HTTPError as e:
        print(f"  ! {repo}: HTTP {e.code}, trying HTML fallback...", file=sys.stderr)
        return fetch_stars_html(repo)
    except Exception as e:  # noqa: BLE001
        print(f"  ! {repo}: {e}; trying HTML fallback...", file=sys.stderr)
        return fetch_stars_html(repo)


def load_existing() -> dict[str, str]:
    if not OUT.exists():
        return {}
    existing: dict[str, str] = {}
    for m in re.finditer(
        r"\\csname\s+githubstar@([^\\]+)\\endcsname\{([^}]*)\}",
        OUT.read_text(encoding="utf-8"),
    ):
        existing[m.group(1)] = m.group(2)
    return existing


def format_count(n: int) -> str:
    if n >= 1000:
        return f"{n / 1000:.1f}".rstrip("0").rstrip(".") + "k"
    return str(n)


def main() -> int:
    force = "--force" in sys.argv or "-f" in sys.argv
    tex_files = sorted(ROOT.glob("*.tex")) + sorted(ROOT.glob("section_*.tex"))
    # de-dup
    tex_files = sorted(set(tex_files), key=lambda p: p.name)
    repos = sorted(find_repos(tex_files))
    if not repos:
        print("No GitHub repos found in .tex files.")
        return 0

    print(f"Found {len(repos)} repo(s):")
    for r in repos:
        print(f"  - {r}")

    cached = load_existing()
    cache_fresh = (
        OUT.exists()
        and (time.time() - OUT.stat().st_mtime) < CACHE_TTL_SEC
        and all(r in cached for r in repos)
    )
    if cache_fresh and not force:
        age_min = int((time.time() - OUT.stat().st_mtime) / 60)
        print(f"Cache fresh ({age_min} min old, TTL {CACHE_TTL_SEC // 3600}h); skip API.")
        return 0

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    counts: dict[str, str] = {}

    for i, repo in enumerate(repos):
        if i:
            time.sleep(0.3)  # be gentle on unauthenticated rate limits
        stars = fetch_stars(repo, token)
        if stars is None:
            if repo in cached:
                print(f"  ~ {repo}: using cached {cached[repo]}")
                counts[repo] = cached[repo]
            else:
                print(f"  x {repo}: skipped (no data)")
            continue
        formatted = format_count(stars)
        counts[repo] = formatted
        print(f"  ✓ {repo}: ★ {formatted}")

    lines = [
        "% Auto-generated by fetch_github_stars.py — do not edit by hand",
        "% Re-run: python3 fetch_github_stars.py [--force]",
        "",
    ]
    for repo, count in sorted(counts.items(), key=lambda x: x[0].lower()):
        lines.append(rf"\expandafter\def\csname githubstar@{repo}\endcsname{{{count}}}")
    lines.append("")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT.name} ({len(counts)} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
