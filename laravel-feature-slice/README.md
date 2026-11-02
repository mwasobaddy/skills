# laravel-feature-slice

A prescriptive architecture for Laravel features on **multi-tenant** apps (stancl/tenancy, subdomain
identification): every file that should exist, in the order it should be written, with the controller
reduced to routing and tenant scoping made explicit.

## The problem it solves

Ask an agent to "implement login and onboarding" in a Laravel app and you typically get one 300-line
controller with `$request->validate()`, three `Model::create()` calls, a mail sent inline, and no
tests. It works, and it is unmaintainable.

This skill replaces that with a **feature slice**: migration → model → enum → DTO → Form Request →
Action → Policy → Controller → Route → Resource → frontend types → page → tests.

## What it does

- **The build order** — 13 layers, each contract deciding the next, so the page isn't written first
  and rewritten later.
- **Thin controllers** — before/after code showing the same feature done both ways.
- **Dual validation** — server rules are authoritative, client rules mirror them; a table of what
  goes where, for Inertia and Livewire.
- **Don't rebuild auth** — all starter kits ship Fortify; the login slice is customisation, not a
  new `LoginController`.
- **A checker** — flags the drift mechanically: inline validation, Eloquent writes in controllers,
  FatController, missing `rules()`/`authorize()`, `env()` outside config, routes pointing at nothing,
  `Inertia::render()` targets with no component, controllers with no tests.
- **Anti-pattern list** — what *not* to generate, so over-correction doesn't replace under-structure.

## When to use it

Implementing or reviewing a feature where file placement matters: auth, onboarding, CRUD, payments,
admin. Also when a controller has grown, validation is duplicated, or business logic sits in a model.

## Relationship to Laravel Boost

Complementary, not competing. Boost ships **descriptive** framework guidance and per-package skills;
its `infer-conventions` skill records what your codebase already does — including bad patterns.

This skill is **prescriptive**: a target architecture, and the file manifest per feature. Install
both. Boost answers "how does Inertia's `useForm` work"; this answers "what files does this feature
need".

## Install

```bash
npx skills add mwasobaddy/skills --skill laravel-feature-slice

# live editing
../scripts/install.sh laravel-feature-slice
```

To make it available to the whole team through Boost, copy it to
`your-app/.ai/skills/laravel-feature-slice/` and run `php artisan boost:update`. That directory
should be committed.

## Audit

> Run these from this skill's directory — that is where `scripts/` lives. If you are
> elsewhere, substitute the resolved path shown in `SKILL.md`.

```bash
python3 scripts/laravel_audit.py /path/to/app
python3 scripts/laravel_audit.py . --json report.json
python3 scripts/laravel_audit.py . --baseline report.json --fail-on-new
python3 scripts/laravel_audit.py --selftest
```

Read-only, no PHP execution, no `vendor/` scan. Exit code `1` when an error exists.

**A clean audit means the structure is sound, not that the app is correct.** It cannot see runtime
behaviour, query performance, or whether the business rules are right.

## Contents

- `SKILL.md` — the one rule, build order, thin-controller contract, dual validation
- `references/feature-manifest.md` — exact file lists for login, onboarding, and a paid order, plus what not to create
- `references/layers.md` — every layer: rule, code shape, anti-pattern
- `references/adapting-to-an-app.md` — Services vs Actions, money representation, test bootstrapping, tenancy, Wayfinder
- `references/multitenancy.md` — stancl/tenancy subdomain model, the login → tenant flow, scoping rules, queues, cross-tenant tests
- `references/authorization.md` — the three tiers: platform role, sub-permission, policy
- `references/app-structure.md` — the full `app/` directory map and what each layer does
- `references/migrating-services-to-actions.md` — the strangler procedure for converting a service layer
- `references/starter-kits.md` — React, Vue, Svelte, Livewire paths and form validation
- `references/laravel-13-boost.md` — Laravel 13 changes, and wiring this into Boost and project rules
- `scripts/laravel_audit.py` — the checker, with `--selftest`
- `scripts/install-to-project.sh` — copy the skill into a Laravel app's `.ai/skills/` for Boost
- `evals/trigger-queries.json` — trigger evaluation set

## Testing

`--selftest` builds a deliberately bad Laravel slice and a clean one, then asserts the expected rules
fire and the clean slice produces no errors. Verified against a fixture app with a fat onboarding
controller, a valid Form Request, a model, and routes.

## Scope

Targets Laravel 13 and the official starter kits. Not covered: deployment, queue infrastructure,
performance tuning, package selection.

## License

MIT
