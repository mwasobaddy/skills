# Laravel 13 and Laravel Boost

Two facts change how this skill should be applied: the framework version, and Boost's existence.

## Laravel 13 at a glance

Released 17 March 2026. Requires **PHP 8.3–8.5**. Bug fixes until Q3 2027, security until March 2028.

Relevant to feature structure:

| Change | Consequence for this skill |
| --- | --- |
| Controller attributes: `#[Middleware]`, `#[Authorize]` | Authorization can sit on the method instead of the constructor or route file. Prefer it. |
| `PreventRequestForgery` middleware | The CSRF story is formalised; don't hand-roll token checks. |
| JSON:API resources | Use them when an API must be spec-compliant, instead of hand-built arrays. |
| `Queue::route()` | Queue/connection routing belongs in a service provider, not on every job. |
| Expanded job attributes `#[Tries]`, `#[Backoff]`, `#[Timeout]` | Declare retry policy on the job class rather than in a config array. |
| `Cache::touch()` | Extend TTL without re-storing; relevant to caching read models. |
| Vector search / AI SDK | Embedding work belongs in an Action or Job, never a controller. |

Upgrading from 12 is described as a relatively minor effort — the release notes emphasise a
"minimal breaking changes" cycle.

**Do not write Laravel 10/11 idioms into a 13 project.** In particular: `app/Http/Kernel.php` no
longer exists (middleware is configured in `bootstrap/app.php`), and route middleware is not
registered in the kernel.

## Laravel Boost

`composer require laravel/boost --dev && php artisan boost:install`

Boost gives agents four things. Know which is which, because they solve different problems:

| Mechanism | Loaded | Covers | Who owns it |
| --- | --- | --- | --- |
| **Guidelines** | Always, upfront | Laravel conventions per package/version | Boost |
| **Skills** | On demand | Task patterns (`inertia-react-development`, `livewire-development`, `pest-testing`, `infer-conventions`, …) | Boost |
| **Project rules** | On demand, by glob | *Your* application's conventions | You |
| **MCP tools** | On call | Schema, routes, logs, docs search, tinker | Boost |

### Why this skill exists alongside Boost

Boost's shipped skills are **descriptive of the framework**. `infer-conventions` is descriptive of
*your codebase* — it records what your code already does, including a 300-line controller if that is
the pattern. Neither one tells an agent "for this feature, produce these 14 files, in this order."

That is the gap this skill fills. It is **prescriptive**: a target architecture, not an observation.

Do not duplicate Boost. If the question is "how do I use Inertia's `useForm`", the Boost
`inertia-react-development` skill is the better source. If the question is "what files does an
onboarding flow need", this one is.

### Adding this skill to a project (Boost-managed)

Copy or link the skill into the app so Boost installs it for the whole team:

```
your-app/.ai/skills/laravel-feature-slice/SKILL.md
your-app/.ai/skills/laravel-feature-slice/references/…
```

`php artisan boost:update` then installs it alongside Boost's own skills. This directory **should be
committed** — unlike generated guideline files.

To replace a Boost skill instead of adding one, use a matching name in `.ai/skills/`; Boost
prefers yours.

### Project rules to record alongside it

This skill describes a target; project rules pin the choices that are specific to you. Record them
so they apply by glob:

```markdown
---
paths:
  - app/Http/Controllers/**
---

# Controllers

Never call `$request->validate()` or any Eloquent write in a controller.
Controllers take a Form Request, call one Action, and return a response.
```

```markdown
---
paths:
  - app/**
---

# Money

All monetary values are integer cents, stored and compared as integers. Never floats.
```

Use Boost's `record-rule` MCP tool rather than creating rule files by hand — it regenerates
`.ai/rules/index.md`, without which an agent will not discover the file.

### What Boost's guidelines already cover, so don't repeat them

Eloquent basics, migrations, Blade, routing, Tailwind, Pest syntax, Inertia component APIs,
Livewire lifecycle, Flux components, Wayfinder helpers. If a rule is in the framework documentation,
it belongs to Boost, not here.

One exception: custom Eloquent builders (`#[UseEloquentBuilder]`) are public API but appear in neither
the docs nor Boost's guidelines, which still say "prefer local scopes". The *choice* of when to
escalate lives here (`references/layers.md`); the mechanics stay with Boost and the framework source.

## Practical setup order

1. `composer require laravel/boost --dev && php artisan boost:install` — pick your editors and skills.
2. Add this skill to `.ai/skills/` and run `boost:update`.
3. Record three or four project rules for the choices this skill leaves open (money format,
   tenancy, ID strategy, soft deletes).
4. Run `python3 scripts/laravel_audit.py .` to see where the app currently stands against the target.
5. Fix the errors first, then the warnings. Do not rewrite the app in one pass.
