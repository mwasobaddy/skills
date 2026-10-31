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

## 4d. Never build a site-level URL by appending to a page URL

**What happened.** The auditor took the target as a base and probed `base + "/robots.txt"`. Given
`https://admin.example.org/admin/users` it fetched `/admin/users/robots.txt`, got a 404, and reported
"no robots.txt" for a subdomain that serves one. The same bug silently skipped the sitemap. Both
false positives appeared in a real report.

It had passed testing because I had only run it against bare origins like `https://example.com`,
where concatenation happens to be correct.

**Rule.** Derive the origin explicitly before building any site-level path:

```python
parts = urlsplit(target)
origin = f"{parts.scheme}://{parts.netloc}"
fetch(origin + "/robots.txt")
```

Then keep the page the user asked about as a separate *seed*, and audit it too:

```python
if seed and seed not in targets:
    targets.insert(0, seed)
```

Test with a **deep path** (`/a/b/c`) and a bare origin. A run that only ever sees `/` cannot detect
this class of bug.

## 4e. Never document a script path relative to the skill directory

**What happened.** The SEO skill's instructions said:

```bash
python3 scripts/seo_audit.py https://example.com
```

That resolves only if the working directory *is* the skill folder. An agent loaded the skill while
working in the user's Laravel project, tried the path, found nothing, and reported:

> The skill's helper scripts aren't installed, so I'll run the audit directly.

It then hand-rolled a crawl with `curl` and presented it as the audit. The scripts were installed the
whole time. Two failures compounded: a relative path that was never valid, and an agent substituting
an improvised procedure for the one the skill exists to provide.

**Rule.** Scripts shipped inside a skill live in the skill's directory, not the user's. Resolve it
explicitly, and require verification before use:

```bash
SKILL_DIR=""
for d in "$HOME/.claude/skills" "$HOME/.config/opencode/skills" "$HOME/.agents/skills"; do
  [ -d "$d/<skill>/scripts" ] && SKILL_DIR="$d/<skill>" && break
done

python3 "$SKILL_DIR/scripts/thing.py" --selftest   # PASS means present and working
```

Then say what to do when it is genuinely missing — **tell the user, do not improvise**. A substitute
procedure is worse than none, because the report looks like the real check ran and the skipped checks
are invisible.

Test by running the documented command from a *different* directory. A command verified only from the
skill folder is unverified.

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

## 5b. Run the command you are about to document

**What happened.** I told the user to select agents with
`npx skills add … -a claude-code,opencode`. The CLI rejects a comma list outright:

```
■  Invalid agents: claude-code,opencode
```

It wants one repeated `-a` flag per agent. I had copied the comma form from `install.sh`,
which does accept commas, and assumed the two CLIs matched. Two follow-on failures came from
the same root cause — an unverified example becoming the basis for the next fix.

**Rule.** Run the exact command, in a sandbox, before putting it in an answer or a README.
For anything that writes outside the repo, redirect the environment instead of trusting
yourself not to clobber real state:

```bash
HOME=/tmp/fakehome npx skills add ./ --skill x -g -a claude-code -y
```

When two tools should behave alike, test both. A working local script is not evidence about
a third-party CLI's flag grammar.

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

## 7b. A detector that never fires is indistinguishable from "nothing to detect"

**What happened.** The crawler flagged pages Google has retired by looking for

```python
'<link rel="canonical" href="https://developers.google.com/search/news"' in html
```

Fifteen pages in the corpus were retired and redirected. The count came back **0**, and a clean
"0 retired" reads exactly like a healthy crawl. The canonical actually points at
`/search/updates`, not `/search/news` — I had guessed the URL from memory instead of reading it.

Every subsequent run would have quietly reported "nothing retired" while the references filled
with dead features.

**Rule.** For any detector, run it once against an input you *know* is positive and once against
one you know is negative, and assert both counts:

```bash
# known-retired page must report retired=1
python3 scripts/crawl-google-docs.py --out /tmp/a --seed <retired-url> --max-hops 0
# known-live page must report retired=0
python3 scripts/crawl-google-docs.py --out /tmp/b --seed <live-url> --max-hops 0
```

And when the signal is a string from an external service, read it out of a real response first.
Grep the fetched HTML for the candidate, rather than trusting the shape you remember:

```bash
grep -o '<link rel="canonical"[^>]*>' html/*.html
```

A verifier that finds nothing, a linter with no warnings, and a grep with no matches are all
statements about the *check*, not the artefact. Prove the check can fail before believing it
passed.

## 7c. A validator that can't detect the failure it exists for

**What happened.** `scripts/validate-skill.sh` reported the new skill as `valid`. The official
validator rejected it:

```
- Invalid YAML in frontmatter: mapping values are not allowed here
  ... ter a deploy. Framework-agnostic: Next.js, Rails, Django ...
```

The description contained an unquoted `": "`. The local validator read the value with
`sed -n 's/^description:[[:space:]]*//p'`, which extracts the text perfectly and never parses it
as YAML. So the one check that exists to catch malformed frontmatter was blind to the most common
way frontmatter breaks.

**Rule.** A validator must be tested against input it should reject, in the same way a detector
must be tested against a known positive:

```bash
# the regression fixture
printf -- '---\nname: bad\ndescription: Does a thing. Framework-agnostic: Next.js\n---\n' > /tmp/bad.md
# then assert the check flags it
```

When a local check and an external check disagree, the external one is the specification. Fix the
local check so the disagreement cannot recur, rather than fixing only the file that failed.

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
- [ ] Every detector was shown to fire on a known-positive input
- [ ] Any loop-invoked command redirects stdin
- [ ] Grepped for the old value of anything you changed
- [ ] Every command in the docs was executed verbatim, in a sandboxed HOME if it writes
- [ ] Any function called via `$(...)` prints UI to stderr, results to stdout
- [ ] Install paths transcribed from the tool that defines them, not guessed
- [ ] No `TODO`, no placeholder author, no inferred identity