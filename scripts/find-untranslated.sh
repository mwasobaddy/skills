#!/usr/bin/env bash
# Flags likely-hardcoded user-facing strings in a Next.js/React codebase, so you can
# size an i18n retrofit before touching it.
#
# Usage: bash find-untranslated.sh <dir> [dir...]
#        bash find-untranslated.sh --json <dir>
#
# Heuristic, not a compiler. It errs toward recall: review every hit, then move real
# strings into your message catalog and re-run until clean.
set -uo pipefail

JSON=0
DIRS=()
for arg in "$@"; do
  if [ "$arg" = "--json" ]; then JSON=1; else DIRS+=("$arg"); fi
done

if [ "${#DIRS[@]}" -eq 0 ]; then
  printf 'Usage: %s [--json] <dir> [dir...]\n' "$0" >&2
  exit 1
fi


# Matches user-visible literal text in these positions:
#   >Some text<            JSX text node
#   "Some text"            string in JSX attribute: placeholder=, alt=, aria-label=, title=
# Line-based to stay readable; no AST available without extra deps.
PATTERNS=(
  '>[[:space:]]*[A-Za-z][A-Za-z0-9 .,!?&%$-]{2,}[[:space:]]*<'
  '(placeholder|alt|aria-label|title|label|aria-description)=["'"'"'][A-Za-z][^"'"'"']{1,}["'"'"']'
)

# Lines we should never report — imports, class strings, URLs, paths, log calls.
NEGATIVE='^[[:space:]]*(import|export|const|let|var|function|type|interface|//|\*|/\*)'
NEGATIVE="${NEGATIVE}|require\(|from ['\"]|\.(png|jpg|jpeg|svg|webp|css|scss)|"
NEGATIVE="${NEGATIVE}https?://|data:|^[[:space:]]*\*|^\}|^\)|className=|useTranslations|useFormatter|from ['\"]next-"

hits=0
files=0

# One line can match several patterns (e.g. a <button placeholder="...">Search</button>).
# Buffer and de-duplicate by file:line while preserving source order.
BUFFER="$(mktemp)"
trap 'rm -f "$BUFFER"' EXIT

for dir in "${DIRS[@]}"; do
  [ -d "$dir" ] || { printf 'skip  %s (not a directory)\n' "$dir" >&2; continue; }

  while IFS= read -r file; do
    files=$((files + 1))

    for pattern in "${PATTERNS[@]}"; do
      while IFS= read -r line; do
        lineno="${line%%:*}"
        content="${line#*:}"

        printf '%s\n' "$content" | grep -qE "$NEGATIVE" && continue
        printf '%s\n' "$content" | grep -qE '^[[:space:]]*$' && continue
        # Already wrapped in a translation call
        printf '%s\n' "$content" | grep -qE '\{t\(|t\.rich\(|t\.raw\(|<Trans' && continue

        printf '%s\t%s\n' "$file" "$lineno" >> "$BUFFER"
      done < <(grep -nE "$pattern" "$file" 2>/dev/null)
    done
  done < <(find "$dir" -type f \
             \( -name '*.tsx' -o -name '*.jsx' -o -name '*.ts' \
                -o -name '*.js' -o -name '*.mjs' \) \
             -not -path '*/node_modules/*' -not -path '*/.next/*' \
             -not -path '*/.git/*' -not -path '*/dist/*' \
             -not -path '*/build/*' | sort)
done

# De-duplicate by file:line and sort into source order (patterns run in sequence,
# so raw buffer order can put line 12 before line 11).
UNIQUE="$(awk -F'\t' '!seen[$1 FS $2]++' "$BUFFER" | sort -t"$(printf '\t')" -k1,1 -k2,2n)"
hits="$(printf '%s' "$UNIQUE" | grep -c . || true)"

if [ "$hits" -gt 0 ]; then
  printf '%s\n' "$UNIQUE" | while IFS=$'\t' read -r file lineno; do
    [ -n "$file" ] || continue
    text="$(sed -n "${lineno}p" "$file" 2>/dev/null \
             | sed 's/^[[:space:]]*//' | cut -c1-110)"

    if [ "$JSON" -eq 1 ]; then
      printf '{"file":"%s","line":%s,"text":"%s"}\n' \
        "$file" "$lineno" "$(printf '%s' "$text" | sed 's/\\/\\\\/g; s/"/\\"/g')"
    else
      printf '  %s:%s: %s\n' "$file" "$lineno" "$text"
    fi
  done
fi

if [ "$JSON" -eq 0 ]; then
  printf '\n%d candidate string(s) across %d file(s).\n' "$hits" "$files"
  printf 'Review each hit, extract real strings into your message catalog, then re-run.\n'
  printf 'Ignore: log messages, test fixtures, CSS classes, URLs, and dev-only copy.\n'
fi

[ "$hits" -gt 0 ] && exit 1 || exit 0
