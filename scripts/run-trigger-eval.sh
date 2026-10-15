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
  case "$CLIENT" in
    claude)   claude -p "$1" --output-format json 2>/dev/null ;;
    opencode) opencode run --format json "$1" 2>/dev/null ;;
    *) die "unknown client '$CLIENT' (or supply --detector-cmd)" ;;
  esac
}

# --- detectors --------------------------------------------------------------------
# Each reads raw client output on stdin; exit 0 means the skill was consulted.

detect_claude() {
  jq -e --arg skill "$SKILL_NAME" '
    any(.messages[]?.content[]?;
        (.type == "tool_use" and .name == "Skill" and .input.skill == $skill))
  ' >/dev/null 2>&1
}

detect_opencode() {
  # `opencode run --format json` emits a JSON event stream. The event shape for skill
  # activation is not stable across opencode versions, so this looks for any tool event
  # naming the skill. If it misreports, pass --detector-cmd with your own jq filter.
  jq -e --arg skill "$SKILL_NAME" '
    [ .. | objects
      | select(((.tool? // .toolName? // .name? // "") | tostring | ascii_downcase) == "skill")
      | .. | strings
      | select(contains($skill)) ] | length > 0
  ' >/dev/null 2>&1
}

check_triggered() {
  if [ -n "$DETECTOR_CMD" ]; then
    run_client "$1" | bash -c "$DETECTOR_CMD"
  elif [ "$CLIENT" = "opencode" ]; then
    run_client "$1" | detect_opencode
  else
    run_client "$1" | detect_claude
  fi
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
  if awk -v r="$rate" -v th="$THRESHOLD" 'BEGIN {exit !(r >= th)}'; then
    verdict=pass; PASSED=$((PASSED + 1))
  else
    verdict=FAIL; FAILED=$((FAILED + 1))
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