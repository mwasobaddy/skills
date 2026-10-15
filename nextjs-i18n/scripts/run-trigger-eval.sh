#!/usr/bin/env bash
# Measures how reliably the SKILL.md description triggers the skill.
#
# Method: https://agentskills.io/skill-creation/optimizing-descriptions
#
# Usage:
#   bash scripts/run-trigger-eval.sh [options]
#
#   --runs N          runs per query (default 3 — below this, results are noise)
#   --threshold F     pass threshold (default 0.5)
#   --split S         all | train | validation (default all)
#   --client C        claude | opencode (default claude)
#   --skill NAME      skill to detect (default: inferred from this script's location)
#   --detector-cmd C  shell command reading raw client output on stdin; exit 0 =
#                     triggered, 1 = not. Escape hatch for other clients.
#   --only N          run a single query by index (debugging)
#   --dry-run         print the plan, make no API calls
#   --out FILE        write the full JSON report
#
# The skill must be discoverable by the client under test — run scripts/install.sh
# from the skills container first.
set -uo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL_NAME="$(basename "$SKILL_DIR")"
QUERIES="$SKILL_DIR/evals/trigger-queries.json"

RUNS=3
THRESHOLD="0.5"
SPLIT="all"
CLIENT="claude"
ONLY=null
DRY_RUN=0
OUT=""
DETECTOR_CMD=""

die() { printf 'error: %s\n' "$1" >&2; exit 1; }

while [ $# -gt 0 ]; do
  case "$1" in
    --runs)          RUNS="$2"; shift 2 ;;
    --threshold)     THRESHOLD="$2"; shift 2 ;;
    --split)         SPLIT="$2"; shift 2 ;;
    --client)        CLIENT="$2"; shift 2 ;;
    --skill)         SKILL_NAME="$2"; shift 2 ;;
    --detector-cmd)  DETECTOR_CMD="$2"; shift 2 ;;
    --only)          ONLY="$2"; shift 2 ;;
    --out)           OUT="$2"; shift 2 ;;
    --dry-run)       DRY_RUN=1; shift ;;
    -h|--help)       sed -n '2,23p' "$0" | sed 's/^#\{0,1\} \{0,1\}//'; exit 0 ;;
    *) printf 'unknown option: %s\n' "$1" >&2; exit 1 ;;
  esac
done

command -v jq >/dev/null 2>&1 || die "jq is required"
[ -f "$QUERIES" ] || die "missing $QUERIES"
case "$SPLIT" in all|train|validation) ;; *) die "--split must be all, train or validation" ;; esac

# --- clients ----------------------------------------------------------------------
# run_client emits the raw agent output on stdout.

run_client() {
  # stdin must come from /dev/null: this runs inside a `while read` loop whose stdin is
  # the query list, and an agent CLI that reads stdin would swallow the remaining queries.
  case "$CLIENT" in
    # stream-json is required: the single-result `json` format omits tool calls
    # entirely, so a Skill invocation is invisible there.
    claude)   claude -p "$1" --output-format stream-json --verbose </dev/null 2>/dev/null ;;
    opencode) opencode run --format json "$1" </dev/null 2>/dev/null ;;
    *) die "unknown client '$CLIENT' (or supply --detector-cmd)" ;;
  esac
}

# A broken client must never be scored as "the skill did not fire". An auth
# failure looks exactly like a non-trigger otherwise, and silently poisons the
# whole run. Abort instead.
client_looks_broken() {
  local out="$1"
  [ -z "$out" ] && return 0
  case "$CLIENT" in
    claude)
      printf '%s' "$out" | grep -qE '"is_error"[[:space:]]*:[[:space:]]*true' && return 0
      printf '%s' "$out" | grep -qiE 'not logged in|please run /login|"api_error_status"' && return 0
      ;;
    opencode)
      printf '%s' "$out" | grep -qiE '"type"[[:space:]]*:[[:space:]]*"error"|unauthorized|invalid.*api.*key' && return 0
      ;;
  esac
  return 1
}

# --- detectors --------------------------------------------------------------------
# Each reads raw client output on stdin; exit 0 means the skill was consulted.

# Claude Code stream-json: assistant tool_use blocks, name "Skill", input.skill.
detect_claude() {
  jq -e --arg skill "$SKILL_NAME" -s '
    any(.[];
        .. | objects
        | select(.type? == "tool_use" and .name? == "Skill" and .input.skill? == $skill))
  ' >/dev/null 2>&1
}

# opencode event stream: {"type":"tool","part":{"tool":"skill","state":{"input":{...}}}}
detect_opencode() {
  jq -e --arg skill "$SKILL_NAME" -s '
    any(.[].part?;
        (.tool? == "skill" and (.state.input | tostring | contains($skill))))
  ' >/dev/null 2>&1
}

check_triggered() {
  if [ -n "$DETECTOR_CMD" ]; then
    run_client "$1" | bash -c "$DETECTOR_CMD" </dev/stdin
  elif [ "$CLIENT" = "opencode" ]; then
    run_client "$1" | detect_opencode
  else
    run_client "$1" | detect_claude
  fi
}

# Warm-up run: proves the client is authenticated and the detector matches this
# client's real output before spending N runs on every query.
preflight() {
  local probe out
  probe="$(jq -r '.queries[] | select(.should_trigger) | .query' "$QUERIES" | head -1)"
  printf 'Preflight (%s): ' "$CLIENT"
  out="$(run_client "$probe")"

  if client_looks_broken "$out"; then
    printf 'FAILED\n'
    printf '\nThe %s client is not answering — most likely not authenticated.\n' "$CLIENT"
    case "$CLIENT" in
      claude)   printf 'Run `claude` once and complete /login, then retry.\n' ;;
      opencode) printf 'Check that opencode is signed in, then retry.\n' ;;
    esac
    printf 'Scores from a broken client are meaningless, so this run was aborted.\n'
    exit 1
  fi

  printf 'ok — %s bytes\n' "${#out}"
}

# --- build the query list ---------------------------------------------------------
QUERIES_FILTERED="$(jq -c --arg split "$SPLIT" --argjson only "$ONLY" '
  if   $only != null        then {queries: [.queries[$only]]}
  elif $split == "all"      then {queries: .queries}
  else                            {queries: [.queries[] | select(.split == $split)]}
  end' "$QUERIES")"

TOTAL="$(printf '%s' "$QUERIES_FILTERED" | jq '.queries | length')"
[ "$TOTAL" -gt 0 ] || die "no queries selected"

printf 'Skill:   %s\n' "$SKILL_NAME"
printf 'Client:  %s\n' "$CLIENT"
printf 'Runs:    %s per query (threshold %s)\n' "$RUNS" "$THRESHOLD"
printf 'Queries: %s (%s)\n\n' "$TOTAL" "$SPLIT"

if [ "$DRY_RUN" -eq 1 ]; then
  printf '%s' "$QUERIES_FILTERED" | jq -r '.queries | to_entries[] |
    "\(.key + 1). [\(.value.split)] \(if .value.should_trigger then "TRIGGER" else "SKIP   " end)  \(.value.query)"'
  printf '\ndry run — %s API calls would be made (%s x %s).\n' "$((TOTAL * RUNS))" "$TOTAL" "$RUNS"
  exit 0
fi

# --- run --------------------------------------------------------------------------
# Preflight before spending runs: catches an unauthenticated client immediately
# rather than reporting every query as a non-trigger.
preflight

RESULTS='[]'
PASSED=0
FAILED=0
INDEX=0

while IFS=$'\t' read -r query should_trigger split note; do
  INDEX=$((INDEX + 1))
  triggers=0

  printf '[%2d/%2d] %s… ' "$INDEX" "$TOTAL" "$(printf '%s' "$query" | cut -c1-46)"

  for _ in $(seq 1 "$RUNS"); do
    check_triggered "$query" && triggers=$((triggers + 1))
  done

  rate="$(awk -v t="$triggers" -v r="$RUNS" 'BEGIN {printf "%.2f", t / r}')"

  # The pass condition is direction-aware. A should-trigger query passes when it fires
  # at or above the threshold; a should-not-trigger query passes when it fires *below*
  # it. Comparing both against `>= threshold` marks every correctly-ignored query as a
  # failure, which sends you "fixing" a description that is already right.
  if [ "$should_trigger" = "true" ]; then
    if awk -v r="$rate" -v th="$THRESHOLD" 'BEGIN {exit !(r >= th)}'; then
      verdict=pass; PASSED=$((PASSED + 1))
    else
      verdict=FAIL; FAILED=$((FAILED + 1))
    fi
  else
    if awk -v r="$rate" -v th="$THRESHOLD" 'BEGIN {exit !(r < th)}'; then
      verdict=pass; PASSED=$((PASSED + 1))
    else
      verdict=FAIL; FAILED=$((FAILED + 1))
    fi
  fi
  printf '%d/%d (%s) %s\n' "$triggers" "$RUNS" "$rate" "$verdict"

  RESULTS="$(printf '%s' "$RESULTS" | jq -c \
    --arg q "$query" --argjson st "$should_trigger" --argjson t "$triggers" \
    --argjson r "$RUNS" --arg split "$split" --arg note "$note" \
    --arg verdict "$verdict" \
    '. + [{query: $q, should_trigger: $st, split: $split, triggers: $t, runs: $r,
           trigger_rate: ($t / $r), passed: ($verdict == "pass"), note: $note}]')"
done < <(printf '%s' "$QUERIES_FILTERED" | jq -r \
  '.queries[] | [.query, .should_trigger, .split, .note] | @tsv')

RATE="$(awk -v p="$PASSED" -v t="$TOTAL" 'BEGIN {printf "%.0f", p / t * 100}')"
printf '\n%s/%s passed (%s%%)\n' "$PASSED" "$TOTAL" "$RATE"

# Failures are the actionable output.
printf '%s' "$RESULTS" | jq -r '.[] | select(.passed | not) |
  "\n  [\(.split)] \(.query)\n    expected: \(if .should_trigger then "should trigger" else "should NOT trigger" end) — got \(.trigger_rate)\n    why it matters: \(.note)"'

if [ "$SPLIT" != "validation" ]; then
  printf '\nValidation set not exercised. Re-run with --split validation before trusting edits.\n'
fi

if [ -n "$OUT" ]; then
  printf '%s' "$RESULTS" | jq --arg skill "$SKILL_NAME" --arg client "$CLIENT" \
    --argjson runs "$RUNS" --argjson th "$THRESHOLD" --argjson p "$PASSED" --argjson t "$TOTAL" \
    '{skill: $skill, client: $client, runs_per_query: $runs, threshold: $th,
      passed: $p, total: $t, results: .}' > "$OUT"
  printf '\nReport written to %s\n' "$OUT"
fi

[ "$FAILED" -eq 0 ] || exit 1