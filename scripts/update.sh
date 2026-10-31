#!/usr/bin/env bash
# Pull the latest skills and refresh this machine.
#
#   ./scripts/update.sh              # pull, re-link, validate, run self-tests
#   ./scripts/update.sh --check      # report whether anything is available, change nothing
#   ./scripts/update.sh --relink     # only refresh symlinks, no network
#
# Skills are symlinked into agent directories, so pulling is normally the whole
# update. This script also re-links (in case an agent was installed since) and
# verifies each skill still valid.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 2

MODE="${1:-update}"

fail=0
skills() {
  local d
  for d in "$ROOT"/*/; do
    d="${d%/}"
    case "$(basename "$d")" in templates|scripts) continue ;; esac
    [ -f "$d/SKILL.md" ] && basename "$d"
  done
}

# ---------------------------------------------------------------- check
if [ "$MODE" = "--check" ]; then
  git fetch -q origin 2>/dev/null || { echo "cannot reach origin"; exit 2; }
  behind="$(git rev-list --count HEAD..@{u} 2>/dev/null || echo 0)"
  if [ "$behind" = "0" ]; then
    echo "up to date at $(git rev-parse --short HEAD)"
  else
    echo "$behind commit(s) available — run ./scripts/update.sh"
    git log --oneline HEAD..@{u} | sed 's/^/  /'
  fi
  exit 0
fi

# ---------------------------------------------------------------- pull
if [ "$MODE" != "--relink" ]; then
  git fetch -q origin 2>/dev/null || echo "warning: cannot reach origin, skipping pull"
  behind="$(git rev-list --count HEAD..@{u} 2>/dev/null || echo 0)"
  if [ "$behind" = "0" ]; then
    echo "already up to date at $(git rev-parse --short HEAD)"
  elif git pull --ff-only -q 2>/dev/null; then
    echo "pulled $behind commit(s) -> $(git rev-parse --short HEAD)"
  else
    echo "error: local commits diverge from origin — resolve manually" >&2
    fail=1
  fi
fi

# ---------------------------------------------------------------- relink
echo
echo "refreshing symlinks:"
while read -r name; do
  [ -n "$name" ] || continue
  if ./scripts/install.sh "$name" --all-detected >/dev/null 2>&1; then
    echo "  ok      $name"
  else
    echo "  FAILED  $name"
    fail=1
  fi
done < <(skills)

# ---------------------------------------------------------------- validate
echo
echo "validating:"
while read -r name; do
  [ -n "$name" ] || continue
  if ./scripts/validate-skill.sh "$name" --strict >/dev/null 2>&1; then
    echo "  valid   $name"
  else
    echo "  INVALID $name"
    ./scripts/validate-skill.sh "$name" --strict 2>&1 | grep -E "invalid|error" | sed 's/^/          /'
    fail=1
  fi
done < <(skills)

# ---------------------------------------------------------------- selftest
echo
echo "self-tests:"
while read -r name; do
  for script in "$ROOT/$name"/scripts/*.py; do
    [ -f "$script" ] || continue
    grep -q -- "--selftest" "$script" 2>/dev/null || continue
    if printf '%s\n' "$(python3 "$script" --selftest 2>&1 | tail -1)" | grep -q PASS; then
      echo "  PASS    $name/$(basename "$script")"
    else
      echo "  FAIL    $name/$(basename "$script")"
      fail=1
    fi
  done
done < <(skills)

# ---------------------------------------------------------------- mixed-install warning
LOCK="$HOME/.agents/.skill-lock.json"
if [ -f "$LOCK" ] && command -v python3 >/dev/null 2>&1; then
  # shellcheck disable=SC2046
  tracked="$(python3 - "$LOCK" $(skills | tr '\n' ' ') <<'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
except Exception:
    sys.exit(0)
names = set((d.get("skills") or {}).keys())
print(" ".join(n for n in sys.argv[2:] if n in names))
PY
)"
  if [ -n "$tracked" ]; then
    echo
    echo "warning: also managed by \`npx skills\`, which installs COPIES:"
    echo "         $tracked"
    echo "         \`npx skills update -g\` would replace the symlinks with copies."
    echo "         Detach them first: npx skills remove --skill <name> -g -y"
  fi
fi

echo
if [ "$fail" = "0" ]; then
  echo "done — all skills current and valid."
else
  echo "done with problems — see above."
fi
exit "$fail"
