---
name: laravel-feature-slice
description: Structure Laravel features so controllers stay thin and every layer exists, in multi-tenant codebases. Use when implementing or reviewing a feature — login, onboarding, CRUD, payments, admin — where a tenant is identified by subdomain, custom domain, URL path, or a tenant column, and where roles, permissions or policies decide what a member may do. Starts with a discovery pass that detects the app's tenancy model, authorization tiers, base classes, money representation and frontend stack before any code is written, then gives the file manifest for Form Requests, Actions, DTOs, Services, Policies, Enums, Events, Jobs, Resources, migrations, models and tests, with backend and frontend validation on both sides. Works with stancl/tenancy, spatie multitenancy, custom organization scoping, and single-tenant Laravel apps. Covers the official Inertia React/Vue/Svelte and Livewire 4 starter kits. Targets Laravel 13 and Laravel Boost.
license: MIT
metadata:
  author: mwasobaddy
  version: "1.0"
---

# Laravel feature slices for multi-tenant apps

The default failure mode of AI-assisted Laravel is one controller doing everything: `$request->validate()`,
three `Model::create()` calls, a mail, and a redirect — 300 lines, untestable, and impossible to reuse.
This skill makes a feature a **slice of files**, each with one job.

It is prescriptive on purpose. Laravel Boost already ships descriptive framework guidance; use that
for "how does Inertia work". Use this for "what files does this feature need, and what goes in each".

## When not to use this

This skill is a default, not a requirement. Applied wholesale to a small app it produces ceremony:
an Action whose `handle()` is one call to `$model->update()`, a DTO with one field, a directory with
one file per verb and nothing else.

Adopt the full slice when **at least two** of these hold:

- multi-tenant, where scoping is a security boundary
- more than one permission tier (coarse role + scoped permission + policy)
- writes span several models, or need a transaction
- money, or another value with a canonical representation
- more than ~3 developers touching the same controllers

Below that, start with Laravel's defaults — controllers, Form Requests, policies — and add a layer
when a specific need appears:

| Add | When |
| --- | --- |
| `Actions/` | a use case touches 2+ models, fires events, or needs a transaction |
| `Data/` | a payload crosses 3+ layers, or a method takes 4+ arguments |
| `Resources/` | an API needs a shape that is not the model |
| `Enums/` | a value set is closed (do this early; it is the cheapest layer) |

The auditor is worth running regardless of which structure you choose — it finds things like routes
pointing at methods that do not exist. The folder manifest is the optional part; the checks are not.

## Discover the project first

This skill's defaults are wrong for some project, including probably yours. Tenancy model, authorization
tiers, base classes, money representation and frontend stack all vary, and each changes the answer.

**A documented project rule always beats a default here.** If `.ai/rules`, `AGENTS.md` or `CLAUDE.md`
states a convention, that is the answer; this skill only fills the gaps.

Spend one pass producing a six-line profile before writing code — `references/project-discovery.md` has
the commands. The three questions that matter most:

1. **How is the tenant identified?** Subdomain, custom domain, URL path, or a column. This decides which
   routes exist and where identity comes from.
2. **Is storage shared or per-tenant?** A separate database scopes for you. A shared database scopes
   nothing, and every query becomes your responsibility.
3. **Which authorization tiers exist?** Coarse role, scoped permission, record policy — or a mix.
   Choosing the wrong one fails open.

A feature that gets these wrong is wrong even when its tests pass, because the failure mode is
cross-tenant data exposure.

- Tenancy detail — `references/multitenancy.md`
- Authorization detail — `references/authorization.md`

## Authorization has three tiers

Picking the wrong tier is a security bug, not a style problem.

| Tier | Answers | Typical implementation |
| --- | --- | --- |
| **Coarse role** | What kind of account is this? | enum, or a role on the user |
| **Scoped permission** | What may this member do *in this scope*? | permission keys, granted per team/organization |
| **Policy** | May this user act on *this record*? | Laravel policy |

Most feature decisions are **scoped permissions**, not coarse roles. Where a helper already grants
super-admin and owner bypasses, do not reimplement them inline — and never evaluate a permission against
a scope supplied by the request.

Full model, the "adding a permission" sequence, and the mistake table: `references/authorization.md`.

## The one rule

**The controller routes. The Action acts. The Form Request validates and authorizes.**

Everything else follows from that. If a controller method contains a rule, a query, or a write, the
slice is wrong.

In a Livewire feature the full-page component is the entrypoint, and the controller and Form Request
disappear. The Action, Policy, and one server-side rule set do not.

## Build order

Never start with the page. Each layer's contract determines the next.

| # | Layer | Produce | Lives in |
| --- | --- | --- | --- |
| 1 | Migration | Columns, indexes, FKs | `database/migrations` |
| 2 | Model | Casts, relations, scopes | `app/Models` |
| 3 | Enum | Every fixed set of values | `app/Enums` |
| 4 | DTO | `final readonly` boundary object | `app/Data/{Domain}` |
| 5 | Form Request | `rules()` + `authorize()` | `app/Http/Requests/{Domain}` |
| 6 | Action | One class per use case | `app/Actions/{Domain}` |
| 7 | Policy | Authorization rules | `app/Policies` |
| 8 | Controller | 1–15 line methods | `app/Http/Controllers/{Domain}` |
| 9 | Route | Named route | `routes/` |
| 10 | Resource | JSON response shape | `app/Http/Resources/{Domain}` |
| 11 | Frontend types | Mirror the DTO | `resources/js/types` |
| 12 | Frontend page | Form with mirrored validation | per starter kit |
| 13 | Tests | Feature per entrypoint, unit per Action | `tests/` |

In a Livewire feature, steps 5, 8 and 12 collapse into one full-page component, and step 9 becomes
`Route::livewire(...)`. Everything else — the Action, Policy, enum, DTO, resource and tests — is
unchanged.

Full manifests for login, onboarding, and a paid order: `references/feature-manifest.md`.

## When the app already disagrees

Most apps have conventions older than this skill, often written into `.ai/rules` or `AGENTS.md`.
**A documented project rule wins.** This skill is the default when the app has not decided.

| Conflict | Default resolution |
| --- | --- |
| App documents Services in `.ai/rules` | Follow the app. Do not add Actions alongside it — that is how two idioms appear. |
| App uses Services but has no written rule | New work in Actions; existing Services stay until touched. Record it. |
| App stores `decimal(14,2)`, this skill's example says cents | Match the app. Two money representations is a bug factory. |
| App uses custom Eloquent builders | Add new filters to the existing builder; do not duplicate them as scopes. |
| `tests/Unit` doesn't boot Laravel | Bind `Unit/Actions` to the TestCase, or use Feature for actions that hit the DB. |
| Authorization returns redirect + toast, not 403 | Assert the redirect, the toast, **and** that nothing was written. |
| Tenancy is ambient | Pass the tenant id in the DTO; keep the context out of Actions. |
| Wayfinder typed routes | `npm run dev` or `npm run build` regenerates them; use `php artisan wayfinder:generate --with-form` for a one-off. After a deploy with cached routes, `php artisan route:clear` first. |

Full detail: `references/adapting-to-an-app.md`. Whatever you decide, write it to a rule file so the
next agent doesn't resolve the same conflict differently.

## Thin controller, before and after

```php
// Wrong — five responsibilities in one method
public function store(Request $request)
{
    $data = $request->validate(['name' => 'required', 'email' => 'required|email']);
    $user = User::create($data);
    $user->save();
    Mail::to($user)->send(new WelcomeMail($user));
    return redirect()->route('dashboard');
}
```

```php
// Right — validate, act, respond
public function store(StoreRegistrationRequest $request, RegisterUser $register)
{
    $user = $register->handle($request->toData());

    return redirect()->route('dashboard');
}
```

The validation moved to a Form Request, the write and the mail to an Action, and the controller
stopped knowing either of them.

## Both sides validate

Server validation is the only authority. Client validation is UX, and it must mirror the server
rules — never replace them, never carry business logic.

| | Server | Client |
| --- | --- | --- |
| Where | `rules()` in a Form Request, or a shared `app/Concerns` trait | `<Form>` + Wayfinder `.form()` (Inertia), or `#[Validate]`/`rules()` (Livewire) |
| Authority | Yes | No |
| Uniqueness | `unique:` | not duplicated client-side |
| Errors | 422 + field errors | field-level messages |

If the two ever disagree, the server is correct and the client is a bug.

## Do not rebuild auth

Every official starter kit ships **Laravel Fortify**. Login, registration, password reset, and
email verification already exist, with customisable actions in `app/Actions/Fortify`
(`CreateNewUser`, `ResetUserPassword`, `PasswordValidationRules`).

"Implement login" means **customise those** and `config/fortify.php` — not create a
`LoginController` with its own validation. A second auth path splits the rules and the rate limiting.

## Target shapes

**Action** — one public entrypoint, no HTTP concepts:

```php
class StartOnboarding
{
    public function handle(User $user, OnboardingData $data): OnboardingProfile
    {
        return $user->onboardingProfile()->create([
            'goal' => $data->goal,
            'step' => OnboardingStep::Profile,
        ]);
    }
}
```

**Form Request** — always both methods:

```php
public function authorize(): bool { return $this->user()->can('create', OnboardingProfile::class); }

public function rules(): array
{
    return ['goal' => ['required', Rule::enum(OnboardingGoal::class)]];
}
```

**DTO** — `final readonly`, constructor-promoted, no logic:

```php
final readonly class OnboardingData
{
    public function __construct(
        public string $name,
        public string $email,
        public OnboardingGoal $goal,
    ) {}
}
```

Per-layer rules, anti-patterns, and code: `references/layers.md`.

## Do not over-generate

Over-correction produces a different mess. Skip these unless you can name the reason:

- a repository per model — Eloquent already is the data layer
- a builder class per model — scopes first; a builder only for 3+ reused constraints
- a service that wraps one model — that is an Action with a worse name
- a DTO for a single scalar
- a validation service — Form Requests exist
- an interface for every Action — only when a test must swap it
- a `BaseController` of helpers — it becomes a dumping ground

## Check the app against this

The script lives in **this skill's directory**, not in the user's project — a relative
`scripts/laravel_audit.py` fails unless the working directory is the skill folder. Locate it first:

```bash
SKILL_DIR=""
for d in "$HOME/.claude/skills" "$HOME/.config/opencode/skills" "$HOME/.agents/skills" \
         "$HOME/.cursor/skills" "$HOME/.gemini/skills" "$HOME/.copilot/skills"; do
  [ -d "$d/laravel-feature-slice/scripts" ] && SKILL_DIR="$d/laravel-feature-slice" && break
done
echo "skill dir: ${SKILL_DIR:-NOT FOUND}"

python3 "$SKILL_DIR/scripts/laravel_audit.py" --selftest        # proves it runs
python3 "$SKILL_DIR/scripts/laravel_audit.py" /path/to/app
python3 "$SKILL_DIR/scripts/laravel_audit.py" . --json report.json

# in a legacy app: baseline once, then measure what your work introduced
python3 "$SKILL_DIR/scripts/laravel_audit.py" . --json baseline.json
python3 "$SKILL_DIR/scripts/laravel_audit.py" . --baseline baseline.json --fail-on-new
```

**If no directory is found, say so and give the user the command to run.** Do not substitute an
improvised grep over `app/Http/Controllers` and present it as this audit — it will miss the route,
Inertia, Livewire and test checks, and the user will believe the app passed them.

Flags inline validation, Eloquent writes in controllers, raw `Request` injection, Form Requests
missing `rules()`/`authorize()`, oversize controllers/models/actions, `env()` outside config, `dd()`
left in, routes pointing at missing classes or methods, `Inertia::render()` or `Route::inertia()`
targets with no page component, `Route::livewire()` targets with no component view, and entrypoints
with no test.

Two deliberate carve-outs: `index`/`show`/`create`/`edit` may take a raw `Request` (filters and
pagination have no Form Request) and are exempt from the method-length rule. A Form Request type-hint
is never flagged — the rule matches `Request` as a whole type name.

**In an existing codebase the score is the wrong metric.** Pre-existing debt floors it at 0, so it
reads the same before and after your work. Use `--baseline`: it prints introduced vs resolved, and
`--fail-on-new` exits non-zero only when your changes add an error. Regenerate the baseline after
upgrading the auditor — a delta is only meaningful across the same rule set.

For a full audit-and-refactor pass — triage order, the fix for every rule, commit granularity, and what
to do when the suite starts red — read `references/refactoring-an-existing-app.md`.

Exit code `1` on errors, so it runs in CI. Fix errors before warnings, and fix the **template** that
caused them rather than each instance.

## Starter kits

React, Vue, and Svelte use Inertia 3 with `resources/js/{pages,components,layouts,hooks,types}` plus
generated `resources/js/{wayfinder,actions,routes}`. Livewire 4 uses full-page components in
`resources/views/pages` with `Route::livewire(...)`; `app/Livewire` is optional.

Detect from `composer.json`/`package.json` and the existing directories — never from the folder name.
A project can mix the two; match the surrounding feature.

Read one: `references/inertia.md` or `references/livewire.md`. Detection and shared validation:
`references/starter-kits.md`.

## Reference map

| File | Read it when |
| --- | --- |
| `references/feature-manifest.md` | Starting a feature and you need the exact file list, in order |
| `references/project-discovery.md` | Always first — establish this app's tenancy, authorization, base classes, money and frontend |
| `references/multitenancy.md` | Any feature touching tenant data — hosts, subdomain flow, scoping, queues, cross-tenant tests |
| `references/authorization.md` | Any feature with permissions — choosing between platform role, sub-permission, and policy |
| `references/layers.md` | Writing or reviewing one layer; need the rule and a code shape |
| `references/adapting-to-an-app.md` | The app already has conventions that differ — Services vs Actions, money representation, test bootstrapping, tenancy, Wayfinder |
| `references/migrating-services-to-actions.md` | You are converting an existing service layer to Actions, per use case |
| `references/refactoring-an-existing-app.md` | Auditing a real app — triage order, the fix for each rule, one commit per change |
| `references/starter-kits.md` | First frontend decision — detect the installed kit, auth, dual validation, shared rules |
| `references/inertia.md` | The app uses Inertia (React, Vue, or Svelte) — pages, controllers, forms, Wayfinder |
| `references/livewire.md` | The app uses Livewire — component formats, page routes, validation, tests |
| `references/laravel-13-boost.md` | Laravel 13 specifics, or wiring this into Laravel Boost and project rules |

## Version and scope

Targets **Laravel 13** (PHP 8.3+, released March 2026) and the official starter kits (Inertia 3 and
Livewire 4). For Laravel 10 or 11, adjust: there is no `#[Authorize]` attribute, and
`app/Http/Kernel.php` still exists in 10.

Covers structure, validation, and authorization. Not covered: deployment, queues infrastructure,
performance tuning, or package selection — those are separate decisions with their own tradeoffs.
