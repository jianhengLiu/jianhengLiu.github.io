#!/usr/bin/env bash
# Refresh the GitHub-star and Google-Scholar-citation data files, then commit and
# push if anything moved.
#
# Meant to run from a machine on a residential IP: Google Scholar serves a
# CAPTCHA to every datacenter IP, which is why the GitHub Action cannot do this
# job (it used to silently fall back to OpenAlex/Semantic Scholar and rewrite
# dynamic-vins from 126 down to 108). fetch_citations.py is now Scholar-only and
# keeps the previous numbers whenever Scholar is unreachable, so a failed run is
# a no-op rather than a regression.
#
# Install as a daily timer:  ./sync_metrics.sh --install-timer
# Run once by hand:          ./sync_metrics.sh

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DATA_FILES=(
  "latex/awesome-latex-cv/github_stars_data.tex"
  "latex/awesome-latex-cv/citations_data.tex"
  "_data/github_stars.yml"
  "_data/citations.yml"
  "_data/scholar_titles.yml"
)

install_timer() {
  local unit_dir="$HOME/.config/systemd/user"
  mkdir -p "$unit_dir"

  cat > "$unit_dir/site-metrics-sync.service" <<UNIT
[Unit]
Description=Sync GitHub stars and Google Scholar citations for $REPO
After=network-online.target

[Service]
Type=oneshot
WorkingDirectory=$REPO
ExecStart=$REPO/latex/awesome-latex-cv/sync_metrics.sh
UNIT

  cat > "$unit_dir/site-metrics-sync.timer" <<UNIT
[Unit]
Description=Daily sync of website star/citation badges

[Timer]
OnCalendar=daily
RandomizedDelaySec=2h
Persistent=true

[Install]
WantedBy=timers.target
UNIT

  systemctl --user daemon-reload
  systemctl --user enable --now site-metrics-sync.timer
  echo "Installed. Next run:"
  systemctl --user list-timers site-metrics-sync.timer --no-pager
  echo
  echo "So it also runs while you are logged out:  sudo loginctl enable-linger $USER"
}

if [[ "${1:-}" == "--install-timer" ]]; then
  install_timer
  exit 0
fi

cd "$REPO"

python3 latex/awesome-latex-cv/fetch_github_stars.py --force
python3 latex/awesome-latex-cv/fetch_citations.py --force

# Stage only the generated data files, so this never sweeps up work in progress.
existing=()
for f in "${DATA_FILES[@]}"; do
  [[ -e "$f" ]] && existing+=("$f")
done
git add -- "${existing[@]}"

if git diff --staged --quiet -- "${existing[@]}"; then
  echo "No metric changes."
  git reset --quiet -- "${existing[@]}"
  exit 0
fi

git -c user.name="${GIT_AUTHOR_NAME:-$(git config user.name)}" \
    -c user.email="${GIT_AUTHOR_EMAIL:-$(git config user.email)}" \
    commit --only -m "chore: sync GitHub stars and citation counts" -- "${existing[@]}"
git push
echo "Pushed updated metrics."
