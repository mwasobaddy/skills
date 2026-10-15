---
name: skill-name
description: TODO — one or two sentences stating what this skill does and when to use it. Use this skill when the user asks for X, mentions Y, or works with Z. Must be under 1024 characters.
license: MIT
metadata:
  author: mwasobaddy
  version: "1.0"
---

# Skill Name

<!-- TODO: one line on the problem this skill solves -->

## When to Use This Skill

<!-- TODO: the concrete situations. Be pushy — name contexts where this applies even if
     the user never uses the domain word. Delete this section only if it adds nothing. -->

- User asks for …
- User has a file that …

## Procedure

<!-- TODO: numbered steps for the task. Keep it to the sequence that actually works.
     Provide a default, not a menu. If several approaches are valid, pick one and note
     when the alternatives apply. -->

1. …
2. …

## Gotchas

<!-- The highest-value section in the skill. Facts that defy reasonable assumption —
     things the agent will get wrong without being told. Every time you correct an
     agent's mistake, add it here. -->

- `users` uses soft deletes; every query needs `WHERE deleted_at IS NULL`.
- The `/health` endpoint returns 200 even when the database is down. Use `/ready`.

## Output

<!-- TODO: a concrete template when the format matters. Agents pattern-match on structure
     far more reliably than on prose. Delete this section if the task has no fixed output. -->

```markdown
# [Title]

## Summary
[…]

## Findings
- …
```

## References

Read `references/FILE.md` when … <!-- one line per file, stating WHEN to read it. Keep
reference files one level deep. Delete empty reference files before committing. -->
