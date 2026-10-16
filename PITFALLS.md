# PITFALLS.md — error classes we've hit, and how to avoid repeating them

Every entry here is a bug that actually shipped in this repo. Most were caught only by
running the thing rather than reading it. Read this before writing scripts or changing
tooling. Rules are cheap; a silent wrong answer is not.

---

## 1. Verify the output shape, not just the exit code

**What happened.** The trigger eval's Claude detector read `.messages` from
`claude --output-format json`. That format's real schema has no `.messages` key at all —
tool calls are omitted entirely. The detector was structurally incapable of ever returning
true, and the eval reported every query as a non-trigger.

**Rule.** Never write a parser against an assumed schema. Capture one real response, print
its top-level keys, and confirm the field you depend on exists:

```bash
claude -p "test" --output-format json | jq 'keys'
opencode run --format json "test" | head -1 | jq 'keys'
```

`jq 'keys'` on real output costs one call and has caught every parser bug here.

## 2. An error response is not a negative result

**What happened.** The `claude` CLI was unauthenticated. It replied `"Not logged in"`,
which the detector read as "the skill did not fire." All 12 queries scored as failures. Had
the description been blamed, it would have been rewritten to satisfy a phantom problem.

**Rule.** Distinguish *absence of signal* from *negative signal*. Any harness that can fail
independently of the thing it measures needs a preflight that proves the instrument works
before results are trusted:

```bash
out="$(run_client "$probe_query")"
if client_looks_broken "$out"; then
  printf 'The client is not answering — scores would be meaningless. Aborting.\n'
  exit 1
fi
```

Same class: a script that exits 0 having produced nothing, or a validator that passes
because it parsed zero files.

## 3. Conditions can be direction-blind

**What happened.** The eval compared every query's trigger rate against `rate >= threshold`.
A should-**not**-trigger query passes when its rate is *below* the threshold. The one-sided
check reported four correctly-ignored queries as failures, producing a confident "8/12,
description is too broad" conclusion from a description that scored 12/12.

**Rule.** Write both branches explicitly, and never let a threshold comparison run without
its direction stated:

```bash
if [ "$should_trigger" = "true" ]; then
  awk -v r="$rate" 'BEGIN {exit !(r >= 0.5)}'      # passes when it fires
else
  awk -v r="$rate" 'BEGIN {exit !(r <  0.5)}'      # passes when it stays quiet
fi
```

For scoring logic generally: test it against mocked extremes in **both** directions. An
always-passes and a always-fails mock prove far more than a happy-path run.

## 4. Anything run inside a `while read` may eat the loop's stdin

**What happened.** The eval looped over a query list on stdin, then invoked an agent CLI
per iteration without redirecting stdin. The CLI read and consumed the remaining queries.
The run reported results for 1 of 12 queries and presented them as complete.

**Rule.** Redirect stdin explicitly for every command that could read it:

```bash
run_client() {
  claude -p "$1" --output-format stream-json --verbose </dev/null
}
```

Then assert the loop covered everything: compare the printed progress count against the
query count, and fail loudly on a mismatch.

## 4b. A function called in `$(...)` must not print UI to stdout

**What happened.** The agent picker in `install.sh` was called as
`read -r -a SELECTED <<< "$(choose_agents)"`. The function printed its numbered menu to
stdout *and* the final selection. Command substitution captured both, the menu's leading
blank line became the first line, and the selection parsed as empty — the script exited with
"no agents selected" while the user saw no menu at all, because stdout was captured rather
than displayed.

**Rule.** Anything invoked in a command substitution writes its result to stdout and
everything else to stderr. An interactive prompt that a caller captures is invisible by
construction:

```bash
{
  printf 'menu\n'
  printf '  [x] 1 Claude Code\n'
  printf 'Selection: '
} >&2
printf '%s\n' "$selected_ids"      # stdout carries only the answer
```

## 4c. Never guess an install path — read it from the tool

**What happened.** `install.sh` wrote Codex skills to `~/.codex/skills`. The `npx skills`
CLI actually puts them in `~/.agents/skills`; `~/.codex` is only used to *detect* that Codex
is installed. The script created a directory no agent reads, and a user following it would
have concluded Codex "doesn't support skills."

**Rule.** Transcribe paths from the tool that defines them, and record where you got them:

```bash
# paths come from the npx skills CLI agent registry
# codex globalSkillsDir = join(home, ".agents", "skills")
# codex detectInstalled = existsSync(join(home, ".codex"))   <- detection only
```

Two more traps from the same source:

- **Several agents share one directory.** `codex`, `universal`, `amp` and `cline` all use
  `~/.agents/skills`. Deduplicate targets before linking, or you write the same symlink four
  times and report it as four successes.
- **A "detected" directory may be an installer's residue.** `npx skills add -g` creates an
  empty `<agent>/skills/` for every agent it touches, so bare `-e` detection then reports
  ~16 agents as installed. Require an entry other than `skills/` before counting an agent.

## 5. macOS `find -regex` is BRE — no alternation

**What happened.** `find . -regex ".*\.\(tsx|jsx|ts\)$"` matched nothing on macOS. BSD
`find` uses basic regular expressions, where `|` is a literal character. The script printed
"0 candidates" and exited 0 — looking like a clean bill of health on a codebase full of
hardcoded strings.

**Rule.** Use `-name` predicates, which are portable and unsurprising:

```bash
find "$dir" -type f \( -name '*.tsx' -o -name '*.jsx' -o -name '*.ts' \) -not -path '*/node_modules/*'
```

**General:** a tool that finds zero results when you expect many has usually matched nothing
rather than found nothing. Test a script against a fixture you know contains hits. A clean
report from a broken script is the most expensive kind of wrong.

## 6. Quoting bugs hide behind `-n` checks that don't run

**What happened.** Twice, embedding a literal quote in shell (`tr -d '"'"'"'`,
`grep -E '...'"'"'...'`) produced an unbalanced quote. The script died at *parse* time, so
no validation ever ran — the validator reported "SKILL.md exists" and then stopped. The
guard clause passed; the code after it never executed.

**Rule.** Syntax-check before running, and make sure output stopped early is loud:

```bash
bash -n script.sh && echo "syntax OK"
```

Prefer small helpers over nested quoting tricks. This fixed two bugs and read better:

```bash
is_quoted() {
  [ "${#1}" -ge 2 ] && [ "${1:0:1}" = "${1: -1}" ] \
    && { [ "${1:0:1}" = '"' ] || [ "${1:0:1}" = "'" ]; }
}
```

## 7. Test the failing path, not just the happy path

**What happened.** The untranslated-string finder reported one source line twice, because it
ran two patterns and each matched. It was only visible after running against a fixture.

**Rule.** Every check needs a fixture proving it reports, and a second proving it stays
silent. For finders specifically: hits, no-hits, empty input, and no-arguments.

## 8. Doc and code drift, in both directions

**What happened.** The install script originally wrote to `~/.config/opencode/skill`
(singular). opencode reads `skills`. Fixed the script — and left the same wrong path in the
README, which is what people actually read. Anyone following it would create a directory no
agent reads and conclude the skill doesn't load.

The same commit also documented `uvx skills-ref validate`, but the package ships an
executable named `agentskills`. The documented command had never been run.

**Rule.** After changing a path or command, grep for its other occurrences:

```bash
grep -rnI 'opencode/skill\b' --exclude-dir=.git .
```

And run any command you put in a README once, verbatim, before committing. Documentation
that was never executed is a guess with extra authority.

## 9. Never infer identity, names, or legal text

**What happened.** `metadata.author` was `hiikey7`, carried over from the scaffold template
by whoever wrote it. The MIT LICENSE read `Copyright (c) Kelvin Ramsiel` — I had inferred
the holder from a git email local-part. Both were wrong, and both would have shipped public.

**Rule.** Placeholders must never survive into a commit. The validator checks for `TODO`
under `--strict`; extend that check rather than trusting review.

For anything you inferred rather than were told — copyright holders, author names, handles,
license choices — ask. It is one question, and getting it wrong is permanent in git history.

## 10. Scaffolding must be self-consistent

**What happened.** `new-skill.sh` wrote "Now commit inside the skill's repo" while the root
README said skill folders were gitignored, and the `validate-skill.sh` hint printed a
command that didn't exist in the form given.

**Rule.** Every artifact the scaffolder prints must still be true when you run it:

- Does the suggested command exist and accept those arguments?
- Does the suggested path exist?
- Does the instruction contradict the repo's actual structure?

Run the scaffolder, then follow its own output literally. This is the only way these scripts
stay honest as the repo changes underneath them.

## 11. Keep repo structure and discovery in sync

**What happened.** This repo moved from per-skill repos to one repo. `.gitignore` still
allowlisted meta files and excluded skill folders, which would have made every skill
invisible to `npx skills add`.

**Rule.** The layout is load-bearing, not cosmetic. After moving anything, re-verify the
thing that discovers it:

```bash
npx skills add ./ --list
```

If discovery finds zero skills, the structure broke — not the CLI. `PITFALLS.md` itself
exists because these are the failures that a code review won't catch: they need to be run.

## 12. Reproduce before you rewrite

**What happened.** The eval said 8/12. The instinctive response is to widen the
description. Instead, re-scoring the saved report showed the description was already 12/12
and the scorer was wrong. No description change was needed.

**Rule.** When a measurement disagrees with expectations, re-derive the result from saved
data before changing the subject of the measurement:

```bash
jq -r '.threshold as $th | ([.results[] |
  (if .should_trigger then (.trigger_rate >= $th) else (.trigger_rate < $th) end)]) |
  "passed: \(map(select(.)) | length)/\(length)"' report.json
```

Re-running is expensive; re-scoring saved output is free. Confirm the instrument is wrong
before blaming the thing it measured.

---

## Quick checklist

Before committing any script or harness in this repo:

- [ ] `bash -n script.sh` passes
- [ ] Ran against a fixture that *should* produce hits
- [ ] Ran against a fixture that should stay silent
- [ ] Read real output from the tool being parsed; confirmed the fields exist
- [ ] Failure paths tested, not just the happy path
- [ ] Any loop-invoked command redirects stdin
- [ ] Grepped for the old value of anything you changed
- [ ] Every command in the docs was executed verbatim
- [ ] Any function called via `$(...)` prints UI to stderr, results to stdout
- [ ] Install paths transcribed from the tool that defines them, not guessed
- [ ] No `TODO`, no placeholder author, no inferred identity