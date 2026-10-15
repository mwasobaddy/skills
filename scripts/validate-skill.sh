#!/usr/bin/env bash
# Validates a skill folder against the Agent Skills spec.
#
# Usage: ./scripts/validate-skill.sh <skill-name> [--strict]
#   --strict  also fail on leftover TODO/template text
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ALLOWED_KEYS="name description license compatibility metadata allowed-tools"
RESERVED_NAMES="synced anthropic-skills"

STRICT=0
[ "${2:-}" = "--strict" ] && STRICT=1

NAME="${1:-}"
if [ -z "$NAME" ]; then
  printf 'Usage: %s <skill-name> [--strict]\n' "$0" >&2
  exit 1
fi

DIR="$ROOT/$NAME"
FAIL=0
ok()   { printf '  ok    %s\n' "$1"; }
err()  { printf '  FAIL  %s\n' "$1"; FAIL=1; }
warn() { printf '  warn  %s\n' "$1"; }

[ -d "$DIR" ] || { printf 'error: no such skill folder: %s\n' "$DIR" >&2; exit 1; }
SKILL_MD="$DIR/SKILL.md"

printf '\n%s\n' "$NAME"

# --- folder name -------------------------------------------------------------------
if [[ "$NAME" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]] && [ "${#NAME}" -le 64 ]; then
  ok "folder name is valid kebab-case"
else
  err "folder name must be 1-64 chars of a-z0-9 with single hyphens"
fi

for reserved in $RESERVED_NAMES; do
  [ "$NAME" = "$reserved" ] && err "'\$reserved' is a reserved name"
done

# --- required files ----------------------------------------------------------------
[ -f "$SKILL_MD" ] && ok "SKILL.md exists" || { err "SKILL.md missing"; printf '\n'; exit 1; }

# --- frontmatter -------------------------------------------------------------------
FIRST_LINE="$(head -1 "$SKILL_MD")"
[ "$FIRST_LINE" = "---" ] || err "frontmatter must start on line 1 with ---"

FRONTMATTER="$(awk 'NR==1 && /^---$/ {in_fm=1; next} in_fm && /^---$/ {exit} in_fm' "$SKILL_MD")"

FM_NAME="$(printf '%s\n' "$FRONTMATTER" | sed -n 's/^name:[[:space:]]*//p' | head -1)"
FM_NAME="${FM_NAME//\"/}"
FM_NAME="${FM_NAME//\'/}"
FM_NAME="$(printf '%s' "$FM_NAME" | awk '{print $1}')"
[ -n "$FM_NAME" ] || err "frontmatter: name is required"
if [ -n "$FM_NAME" ]; then
  [ "$FM_NAME" = "$NAME" ] \
    && ok "frontmatter name matches folder name" \
    || err "frontmatter name '$FM_NAME' != folder name '$NAME'"
  [ "${#FM_NAME}" -le 64 ] || err "name is ${#FM_NAME} chars; max 64"
fi

DESC="$(printf '%s\n' "$FRONTMATTER" | sed -n 's/^description:[[:space:]]*//p' | head -1)"
DESC_LEN=${#DESC}
[ "$DESC_LEN" -ge 1 ] \
  && ok "description present (${DESC_LEN} chars)" \
  || err "description is required"
if [ "$DESC_LEN" -gt 1024 ]; then
  err "description is $DESC_LEN chars; max 1024"
fi
case "$DESC" in
  *"TODO"*) err "description still contains template TODO" ;;
  *"what it does"*|*"What it does"*) warn "description looks like template placeholder text" ;;
esac

# --- unexpected / missing keys -----------------------------------------------------
KEYS="$(printf '%s\n' "$FRONTMATTER" | sed -n 's/^\([a-z][a-zA-Z-]*\):.*/\1/p' | sort -u)"
for key in $KEYS; do
  case " $ALLOWED_KEYS " in
    *" $key "*) ;;
    *) err "unsupported frontmatter key '$key' (spec allows only: $ALLOWED_KEYS)" ;;
  esac
done
for required in name description; do
  printf '%s\n' "$KEYS" | grep -qx "$required" || err "frontmatter missing required key '$required'"
done

# --- metadata shape ----------------------------------------------------------------
# A spec-compliant metadata value is a plain non-numeric token or a quoted string.
# Bare numbers and booleans parse as float/bool, not string, so they must be quoted.
is_quoted() {
  [ "${#1}" -ge 2 ] || return 1
  [ "${1:0:1}" = "${1: -1}" ] && { [ "${1:0:1}" = '"' ] || [ "${1:0:1}" = "'" ]; }
}

is_bare_scalar() {
  printf '%s' "$1" | grep -qiE '^-?[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$|^(true|false|null|yes|no|on|off)$'
}

if printf '%s\n' "$FRONTMATTER" | grep -q '^metadata:'; then
  BAD_META=""
  while IFS= read -r meta_line; do
    meta_key="$(printf '%s' "$meta_line" | sed -n 's/^[[:space:]]*\([a-zA-Z0-9._-]*\):.*/\1/p')"
    meta_val="$(printf '%s' "$meta_line" | sed -n 's/^[[:space:]]*[a-zA-Z0-9._-]*:[[:space:]]*//p' | sed 's/[[:space:]]*$//')"
    if [ -n "$meta_val" ] \
      && ! is_quoted "$meta_val" \
      && ! printf '%s' "$meta_val" | grep -qE '^[A-Za-z0-9._/-]+$'; then
      BAD_META="${BAD_META}${BAD_META:+, }${meta_key}=${meta_val}"
    elif [ -n "$meta_val" ] && ! is_quoted "$meta_val" && is_bare_scalar "$meta_val"; then
      BAD_META="${BAD_META}${BAD_META:+, }${meta_key}=${meta_val}"
    fi
  done < <(printf '%s\n' "$FRONTMATTER" | sed -n '/^metadata:/,/^[^ ]/p')

  [ -z "$BAD_META" ] \
    && ok "metadata values are strings (quote numeric versions)" \
    || err "metadata values must be strings; quote these: $BAD_META"
fi

# --- body --------------------------------------------------------------------------
BODY="$(awk 'BEGIN{fm=0} /^---$/ {fm++; next} fm>=2' "$SKILL_MD")"
BODY_LINES="$(printf '%s\n' "$BODY" | wc -l | tr -d ' ')"
[ "$BODY_LINES" -lt 500 ] \
  && ok "body is ${BODY_LINES} lines (under 500)" \
  || err "body is ${BODY_LINES} lines; move detail into references/"

if printf '%s\n' "$BODY" | grep -q 'TODO'; then
  if [ "$STRICT" -eq 1 ]; then
    err "body contains TODO; replace or remove before committing"
  else
    warn "body still contains TODO text (use --strict to make this fatal)"
  fi
else
  ok "no leftover TODO in body"
fi

# --- reference depth ---------------------------------------------------------------
DEEP="$(find "$DIR/references" -mindepth 2 -type f 2>/dev/null | head -5)"
[ -z "$DEEP" ] \
  && ok "reference files are one level deep" \
  || warn "references nested more than one level: $DEEP"

EMPTY_DIRS="$(find "$DIR" -mindepth 1 -type d -empty -not -path '*/.git/*' -not -name '.git' 2>/dev/null | head -5)"
[ -z "$EMPTY_DIRS" ] \
  && ok "no empty directories" \
  || warn "delete empty directories before committing: $EMPTY_DIRS"

# --- secrets ------------------------------------------------------------------------
if [ -f "$DIR/.env" ] || grep -rqsE '(sk-[A-Za-z0-9]{20}|ghp_[A-Za-z0-9]{20}|AKIA[0-9A-Z]{16})' "$DIR" 2>/dev/null; then
  err "possible credentials or .env file present; never commit those"
fi

# --- official validator (optional) -------------------------------------------------
if command -v skills-ref >/dev/null 2>&1; then
  if skills-ref validate "$DIR" >/dev/null 2>&1; then
    ok "skills-ref validate"
  else
    err "skills-ref validate failed"
  fi
fi

[ "$FAIL" -eq 0 ] && printf '\n  valid\n\n' || printf '\n  invalid\n\n'
exit "$FAIL"
