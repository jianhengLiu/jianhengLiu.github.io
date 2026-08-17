#!/usr/bin/env bash
# Refresh GitHub star counts, then compile the CV with XeLaTeX.
#
# Usage:
#   ./build.sh                        # build liujianheng-cv-eng.tex
#   ./build.sh liujianheng-cv-cn      # build a specific CV
#   ./build.sh liujianheng-cv-cn -f   # force-refresh the star cache
set -euo pipefail

cd "$(dirname "$0")"

DOC="${1:-liujianheng-cv-eng}"
DOC="${DOC%.tex}"
FORCE="${2:-}"

python3 fetch_github_stars.py ${FORCE:+--force} || echo "star refresh failed; using cached counts"

xelatex -synctex=1 -interaction=nonstopmode -file-line-error "$DOC.tex"

echo "built $DOC.pdf"
