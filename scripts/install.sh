#!/usr/bin/env bash
# Links skills into the agent directories installed on this machine.
#
# Usage:
#   ./scripts/install.sh                     # interactive agent picker
#   ./scripts/install.sh --agents claude-code,opencode
#   ./scripts/install.sh <skill-name>
#   ./scripts/install.sh --all
#   ./scripts/install.sh --list              # agents and where they read skills from
#
# Paths below are transcribed from the `npx skills` CLI (vercel-labs/skills) so this
# script and the official installer agree. Codex reads ~/.agents/skills, NOT
# ~/.codex/skills — ~/.codex is only used to detect that Codex exists.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLAUDE_HOME="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
XDG_CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}"

die() { printf 'error: %s\n' "$1" >&2; exit 1; }

# --- agent registry ---------------------------------------------------------------
# Format: id | display name | global skills dir | detection path ("" = always present)
#
# Agents sharing a directory (codex, amp, cline, universal -> ~/.agents/skills) are
# linked once; the script deduplicates targets before creating links.
AGENTS=(
  "claude-code|Claude Code|$CLAUDE_HOME/skills|$CLAUDE_HOME"
  "opencode|OpenCode|$XDG_CONFIG/opencode/skills|$XDG_CONFIG/opencode"
  "codex|Codex|$HOME/.agents/skills|$HOME/.codex"
  "universal|Universal|$HOME/.agents/skills|"
  "cursor|Cursor|$HOME/.cursor/skills|$HOME/.cursor"
  "claude-desktop|Claude Desktop|$HOME/.claude/skills|$CLAUDE_HOME"
  "amp|Amp|$HOME/.agents/skills|$XDG_CONFIG/amp"
  "cline|Cline|$HOME/.agents/skills|$HOME/.cline"
  "gemini-cli|Gemini CLI|$HOME/.gemini/skills|$HOME/.gemini"
  "github-copilot|GitHub Copilot|$HOME/.copilot/skills|$HOME/.copilot"
  "windsurf|Windsurf|$HOME/.codeium/windsurf/skills|$HOME/.codeium"
  "goose|Goose|$XDG_CONFIG/goose/skills|$XDG_CONFIG/goose"
  "qwen-code|Qwen Code|$HOME/.qwen/skills|$HOME/.qwen"
  "junie|Junie|$HOME/.junie/skills|$HOME/.junie"
  "crush|Crush|$XDG_CONFIG/crush/skills|$XDG_CONFIG/crush"
  "kilo|Kilo Code|$HOME/.kilo/skills|$HOME/.kilo"
  "trae|Trae|$HOME/.trae/skills|$HOME/.trae"
  "rovodev|Rovo Dev|$HOME/.rovodev/skills|$HOME/.rovodev"
)

field() { printf '%s\n' "$1" | cut -d'|' -f"$2"; }

agent_exists() {
  local detect; detect="$(field "$1" 4)"
  [ -z "$detect" ] && return 0                      # always available (universal)
  [ -d "$detect" ] || return 1

  # A real agent install has more than a skills directory. `npx skills add -g`
  # creates an empty <agent>/skills/ for every agent it links, so checking bare
  # existence reports almost everything as installed after one global install.
  # Require at least one entry other than skills/.
  local entry base
  for entry in "$detect"/* "$detect"/.[!.]*; do
    [ -e "$entry" ] || continue
    base="$(basename "$entry")"
    [ "$base" = "skills" ] && continue
    return 0
  done
  return 1
}

# --- interactive picker -----------------------------------------------------------
# Numbered multi-select. Agents detected on this machine start checked. Accepts a
# space- or comma-separated list of numbers, `all`, `none`, or Enter for the defaults.
choose_agents() {
  local -a ids names dirs detects
  local i=0 entry id name dir detect

  for entry in "${AGENTS[@]}"; do
    id="$(field "$entry" 1)"; name="$(field "$entry" 2)"
    dir="$(field "$entry" 3)"; detect="$(field "$entry" 4)"
    if agent_exists "$entry"; then
      ids[$i]="$id"; names[$i]="$name"; dirs[$i]="$dir"
      detects[$i]="x"
    else
      ids[$i]="$id"; names[$i]="$name"; dirs[$i]="$dir"
      detects[$i]=" "
    fi
    i=$((i + 1))
  done

  # Non-interactive (piped, CI): use the detected defaults without prompting.
  if [ ! -t 0 ]; then
    local out=() j
    for j in "${!ids[@]}"; do [ "${detects[$j]}" = "x" ] && out+=("${ids[$j]}"); done
    [ "${#out[@]}" -gt 0 ] || out=("claude-code")
    printf '%s\n' "${out[*]}"
    return
  fi

  local selection
  while :; do
    # The menu goes to stderr; stdout carries only the final selection, because the
    # caller captures stdout via $(...). Printing the menu to stdout swallows it into
    # the return value and the selection parses as empty.
    {
      printf '\n  %-18s %-17s %s\n' "" "AGENT" "SKILLS DIR"
      printf '  %s\n' "---------------------------------------------------------------"
      for j in "${!ids[@]}"; do
        printf '  [%s] %2d %-16s %s\n' "${detects[$j]}" "$((j + 1))" "${names[$j]}" "${dirs[$j]}"
      done
      printf '\n  Toggle agents by number (e.g. "1 3 5"), or "all" / "none".\n'
      printf '  Agents marked [x] were detected on this machine.\n'
      printf '  Selection: '
    } >&2
    read -r selection || selection=""
    [ -z "$selection" ] && selection="__defaults__"

    [ "$selection" = "__defaults__" ] && break
    [ "$selection" = "all" ] || [ "$selection" = "ALL" ] && selection="$(seq -s' ' 1 "${#ids[@]}")"
    [ "$selection" = "none" ] || [ "$selection" = "NONE" ] && selection="__none__"

    if [ "$selection" = "__none__" ]; then
      for j in "${!ids[@]}"; do detects[$j]=" "; done
      selection=""
    else
      for tok in $selection; do
        case "$tok" in
          [0-9]*)
            n=$((10#$tok))
            if [ "$n" -ge 1 ] && [ "$n" -le "${#ids[@]}" ]; then
              k=$((n - 1))
              if [ "${detects[$k]}" = "x" ]; then detects[$k]=" "; else detects[$k]="x"; fi
            else
              printf '  no agent #%s — try again\n' "$tok" >&2
            fi
            ;;
          *) printf '  not a number: %s — try again\n' "$tok" >&2 ;;
        esac
      done
    fi
  done

  local out=()
  for j in "${!ids[@]}"; do [ "${detects[$j]}" = "x" ] && out+=("${ids[$j]}"); done
  printf '%s\n' "${out[*]-}"
}

# --- link -------------------------------------------------------------------------
# One link per unique target directory: several agents share ~/.agents/skills.
link_agents() {
  local name="$1"; shift
  local -a wanted=("$@")
  local -a seen_dirs=()
  local linked=0 entry id name_ dir detect

  printf '\nLinking %s:\n' "$name"

  for id in "${wanted[@]}"; do
    [ -n "$id" ] || continue
    local matched=0
    for entry in "${AGENTS[@]}"; do
      [ "$(field "$entry" 1)" = "$id" ] || continue
      matched=1
      dir="$(field "$entry" 3)"
      name_="$(field "$entry" 2)"

      local dup=0 existing
      for existing in "${seen_dirs[@]:-}"; do [ "$existing" = "$dir" ] && dup=1; done
      [ "$dup" -eq 1 ] && { printf '  skip  %-16s (shares %s)\n' "$name_" "$dir"; continue; }

      if [ -L "$dir/$name" ]; then
        rm "$dir/$name"
      elif [ -e "$dir/$name" ]; then
        printf '  skip  %-16s a real folder already exists at %s\n' "$name_" "$dir"
        continue
      fi

      mkdir -p "$dir"
      ln -s "$ROOT/$name" "$dir/$name"
      printf '  link  %-16s -> %s\n' "$name_" "$dir"
      seen_dirs+=("$dir")
      linked=$((linked + 1))
      break
    done
    [ "$matched" -eq 1 ] || printf '  warn  unknown agent id: %s\n' "$id"
  done

  [ "$linked" -eq 0 ] && printf '  no agents selected.\n'
  return 0
}

is_skill() { [ -f "$1/SKILL.md" ]; }

skill_names() {
  local d
  for d in "$ROOT"/*/; do
    d="${d%/}"
    case "$(basename "$d")" in templates|scripts) continue ;; esac
    is_skill "$d" && basename "$d"
  done
}

# --- args -------------------------------------------------------------------------
AGENTS_ARG=""
TARGET=""

while [ $# -gt 0 ]; do
  case "$1" in
    --agents) AGENTS_ARG="$2"; shift 2 ;;
    --list)
      printf 'Agents this script knows about:\n\n'
      for entry in "${AGENTS[@]}"; do
        if agent_exists "$entry"; then mark="detected"; else mark="  -  -  "; fi
        printf '  %s  %-18s %s\n' "$mark" "$(field "$entry" 2)" "$(field "$entry" 3)"
      done
      exit 0
      ;;
    -h|--help) sed -n '2,15p' "$0" | sed 's/^#\{0,1\} \{0,1\}//'; exit 0 ;;
    -*) die "unknown option: $1" ;;
    *)  TARGET="$1"; shift ;;
  esac
done

case "${1:-}" in
  --all) TARGET="--all" ;;
esac

if [ "$TARGET" = "--all" ]; then
  SKILLS=($(skill_names))
  [ "${#SKILLS[@]}" -gt 0 ] || die "no skills found in $ROOT"
else
  [ -n "$TARGET" ] || die "Usage: $0 [<skill-name>|--all] [--agents a,b] | --list"
  is_skill "$ROOT/$TARGET" || die "not a skill: $TARGET (no SKILL.md in $ROOT/$TARGET)"
  SKILLS=("$TARGET")
fi

if [ -n "$AGENTS_ARG" ]; then
  IFS=',' read -r -a SELECTED <<< "$AGENTS_ARG"
else
  read -r -a SELECTED <<< "$(choose_agents)"
fi

[ "${#SELECTED[@]}" -gt 0 ] || die "no agents selected"

for skill in "${SKILLS[@]}"; do
  link_agents "$skill" "${SELECTED[@]}"
done

printf '\nEdits in %s are live — no reinstall needed.\n' "$ROOT"