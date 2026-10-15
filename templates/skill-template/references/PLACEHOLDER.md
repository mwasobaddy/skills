# Reference file placeholder

Delete this file before committing unless the skill genuinely needs a reference.

Rules for reference files:

- **One level deep only.** `SKILL.md` → `references/foo.md`. Never `references/bar/baz.md`.
- **Name it for the situation, not the topic.** `api-errors.md` beats `part-1.md`.
- **Keep each file small.** It loads whole when the agent opens it. Under 300 lines.
- **Say when to read it** in `SKILL.md`: "Read `references/foo.md` if the API returns a
  non-200 status" — not "see references/ for details".
- **Move content out, don't delete detail.** The point of a reference is that the common
  path stays cheap in `SKILL.md` while the long tail is still reachable.
