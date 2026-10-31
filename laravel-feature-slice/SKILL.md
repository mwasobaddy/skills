---
name: laravel-feature-slice
description: Structure Laravel features so controllers stay thin and every layer exists. Use when implementing or reviewing a Laravel feature — login, onboarding, CRUD, payments, admin — and you need the complete file manifest, covering Form Requests, Actions, DTOs, Services, Policies, Enums, Events, Jobs, Resources, migrations, models, tests, and the matching React, Vue, Svelte or Livewire pages with backend and frontend validation on both sides. Also use when fixing bulky controllers, inline validation, or business logic leaking into the wrong layer. Targets Laravel 13 and the official starter kits, and composes with Laravel Boost.
license: MIT
metadata:
  author: mwasobaddy
  version: "1.0"
---

# Laravel feature slices

The default failure mode of AI-assisted Laravel is one controller doing everything: `$request->validate()`,
three `Model::create()` calls, a mail, and a redirect — 300 lines, untestable, and impossible to reuse.
This skill makes a feature a **slice of files**, each with one job.

It is prescriptive on purpose. Laravel Boost already ships descriptive framework guidance; use that
for "how does Inertia work". Use this for "what files does this feature need, and what goes in each".

## The one rule

**The controller routes. The Action acts. The Form Request validates and authorizes.**

Everything else follows from that. If a controller method contains a rule, a query, or a write, the
slice is wrong.

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
| 13 | Tests | Feature per action, unit per Action | `tests/` |

Full manifests for login, onboarding, and a paid order: `references/feature-manifest.md`.

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
| Where | `rules()` in a Form Request | `useForm` (Inertia) or `rules()`/`#[Validate]` (Livewire) |
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
```

**If no directory is found, say so and give the user the command to run.** Do not substitute an
improvised grep over `app/Http/Controllers` and present it as this audit — it will miss the route,
Inertia, Livewire and test checks, and the user will believe the app passed them.

Flags inline validation, Eloquent writes in controllers, raw `Request` injection, Form Requests
missing `rules()`/`authorize()`, oversize controllers/models/actions, `env()` outside config, `dd()`
left in, routes pointing at missing classes or methods, `Inertia::render()` targets with no page
component, Livewire views that don't exist, and controllers with no test.

Exit code `1` on errors, so it runs in CI. Fix errors before warnings, and fix the **template** that
caused them rather than each instance.

## Starter kits

React, Vue, and Svelte use Inertia with `resources/js/{pages,components,layouts,hooks,types}`.
Livewire uses `resources/views/{pages,livewire,components}` with components in `app/Livewire`.
Detect from `composer.json`/`package.json` — never from the folder name.

Paths, form patterns, and per-kit rules: `references/starter-kits.md`.

## Reference map

| File | Read it when |
| --- | --- |
| `references/feature-manifest.md` | Starting a feature and you need the exact file list, in order |
| `references/layers.md` | Writing or reviewing one layer; need the rule and a code shape |
| `references/starter-kits.md` | Frontend work — Inertia or Livewire, and dual validation |
| `references/laravel-13-boost.md` | Laravel 13 specifics, or wiring this into Laravel Boost and project rules |

## Version and scope

Targets **Laravel 13** (PHP 8.3+, released March 2026) and the official starter kits. For Laravel 10
or 11, adjust: there is no `#[Authorize]` attribute, and `app/Http/Kernel.php` still exists in 10.

Covers structure, validation, and authorization. Not covered: deployment, queues infrastructure,
performance tuning, or package selection — those are separate decisions with their own tradeoffs.
