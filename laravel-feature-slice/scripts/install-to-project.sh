#!/usr/bin/env bash
# Copy this skill into a Laravel app so Laravel Boost installs it for the whole team.
#
#   ./scripts/install-to-project.sh /path/to/laravel-app
#   ./scripts/install-to-project.sh /path/to/laravel-app --dry-run
#
# Copies SKILL.md, references/ and scripts/ into <app>/.ai/skills/laravel-feature-slice/.
# Boost reads that directory on `php artisan boost:update`, and it should be committed
# so teammates and CI get the same rules.
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAME="$(basename "$SRC")"
APP="${1:-}"
DRY="${2:-}"

[ -n "$APP" ] || { echo "usage: $0 /path/to/laravel-app [--dry-run]" >&2; exit 2; }
[ -d "$APP/app" ] || { echo "error: $APP has no app/ directory — is it a Laravel root?" >&2; exit 2; }

DEST="$APP/.ai/skills/$NAME"

if [ "$DRY" = "--dry-run" ]; then
  echo "would copy $NAME to $DEST"
  find "$SRC" -maxdepth 1 -mindepth 1 ! -name 'README.md' ! -name 'LICENSE' \
    ! -name 'evals' ! -name '.git' -print | sed "s|^$SRC|  |"
  exit 0
fi

mkdir -p "$DEST"
for item in SKILL.md references scripts; do
  [ -e "$SRC/$item" ] || continue
  cp -R "$SRC/$item" "$DEST/"
done

# Boost discovers skills by name; a stray __pycache__ just adds noise.
find "$DEST" -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true

echo "copied → $DEST"
echo
echo "next:"
echo "  cd $APP && php artisan boost:update"
echo "  git add .ai/skills/$NAME"
