#!/usr/bin/env bash
# Symlinks skills into agent skill directories for local, live-editing installs.
#
# Usage: ./scripts/install.sh <skill-name>
#        ./scripts/install.sh --all
#        ./scripts/install.sh --list
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Agent skill directories that exist on this machine.
TARGET_DIRS=(
  "$HOME/.claude/skills"
  "$HOME/.config/opencode/skills"
  "$HOME/.agents/skills"
  "$HOME/.codex/skills"
)

die() { printf 'error: %s\n' "$1" >&2; exit 1; }

# A folder is a skill if it has a SKILL.md. Anything else is not ours to touch.
is_skill() { [ -f "$1/SKILL.md" ]; }

link_one() {
  local name="$1" src="$ROOT/$1" linked=0
  for dir in "${TARGET_DIRS[@]}"; do
    [ -d "$(dirname "$dir")" ] || continue
    mkdir -p "$dir"
    if [ -L "$dir/$name" ]; then
      rm "$dir/$name"
    elif [ -e "$dir/$name" ]; then
      printf '  skip  %s (a real folder already exists there)\n' "$dir/$name"
      continue
    fi
    ln -s "$src" "$dir/$name"
    printf '  link  %s -> %s\n' "$dir/$name" "$src"
    linked=1
  done
  [ "$linked" -eq 1 ] || printf '  warn  %s: no known agent directory available\n' "$name"
}

case "${1:-}" in
  --list)
    printf 'Installed skills:\n\n'
    for dir in "${TARGET_DIRS[@]}"; do
      [ -d "$dir" ] || continue
      for entry in "$dir"/*; do
        [ -e "$entry" ] || continue
        name="$(basename "$entry")"
        printf '  %-40s %s\n' "$name" "$dir"
      done
    done
    ;;
  --all)
    found=0
    for d in "$ROOT"/*/; do
      d="${d%/}"
      [ "$(basename "$d")" = "templates" ] && continue
      [ "$(basename "$d")" = "scripts" ] && continue
      is_skill "$d" || continue
      found=1
      link_one "$(basename "$d")"
    done
    [ "$found" -eq 1 ] || die "no skills found in $ROOT"
    ;;
  "")
    die "Usage: $0 <skill-name> | --all | --list"
    ;;
  *)
    is_skill "$ROOT/$1" || die "not a skill: $1 (no SKILL.md in $ROOT/$1)"
    link_one "$1"
    ;;
esac
