# Adapting the slice to an existing app

The 13-layer manifest is a target, not a licence to introduce a second way of doing everything.
Almost every real app already has conventions, and some of them conflict. Decide **before** writing
code which way the boundary runs, then record the decision so the next agent doesn't re-litigate it.

## Precedence: a documented project rule beats this skill

If the app carries rule files (`.ai/rules`, `AGENTS.md`, `.cursor/rules`) that state a convention,
**follow them**. This skill is a default for apps that have not decided; it is not an argument
against a decision the team already wrote down.

Seen in practice: an app's `.ai/rules/services.md` said "all business logic with side effects goes in
`App\Services`". An agent followed this skill instead, wrote Actions, and produced two coexisting
idioms. The skill was wrong for that app — the rule file was right.

The split to keep straight:

| Question | Authority |
| --- | --- |
| Where does this file go in *this* app? | The project's rule file |
| What does Laravel 13 / this framework require? | The framework documentation |
| What does Google require? | The Search documentation |
| Is there a documented rule for it? | Nothing — use this skill's default |

When they genuinely conflict, say so once, record the decision, and move on. Silently obeying the
skill against a written rule is the failure mode.

## Read the app first

| What to check | Where | Why it changes the plan |
| --- | --- | --- |
| Existing `app/Services` vs `app/Actions` | directory listing | Determines whether a new Action is consistent or a third idiom |
| Test bootstrapping | `tests/Pest.php`, `tests/TestCase.php` | `tests/Unit` is often bound to plain PHPUnit, so an Action test that touches Eloquent fails |
| Money representation | model casts, migrations | `decimal:2` vs integer cents — picking the other one splits the codebase |
| Authorization failure style | middleware, exception handler | A 403-for-everything app and a redirect-plus-toast app need different assertions |
| Tenancy | `stancl/tenancy`, global scopes, a context service | Tenant scoping has to be somewhere explicit |
| Route helper generation | `laravel/wayfinder`, `@laravel/vite-plugin-wayfinder` | Typed route imports do not exist until generated |
| Frontend | `composer.json` / `package.json` | Inertia React/Vue/Svelte vs Livewire |
| Permission model | policies vs a role package | Determines whether `authorize()` or a custom check is idiomatic |

## The four conflicts you will actually hit

### 1. The app has Services, the skill says Actions

Do not rewrite working code, and do not silently create a parallel system. Pick one:

- **New work uses Actions; Services stay** — the honest default. New slices are consistent with each
  other; old code migrates when it is next touched. Record the boundary in `.ai/rules` so nobody
  "fixes" a Service into an Action mid-review.
- **Everything uses Services** — follow the app, and treat "Action" as "a method on a domain
  service". Less clean, but consistent. Only choose this if the team will not migrate.

Say which one you chose, in the PR description and in a rule file. Two idioms with no stated border
is the worst outcome, and it is the default if you say nothing.

### 2. Money is decimal, not cents

If the app stores `decimal(14,2)` with a `decimal:2` cast, **use that** for new tables. Introducing
integer cents into a decimal codebase creates two representations and a conversion bug at every
boundary.

- Match the existing representation unless you are migrating all of it.
- If you do choose cents (greenfield), record it as a rule — the skill's default is not an argument.
- Never mix in one release.

### 3. `tests/Unit` does not boot the framework

Many apps bind only `tests/Feature` to `Tests\TestCase`:

```php
pest()->extend(TestCase::class)->use(RefreshDatabase::class)->in('Feature');
```

An Action that writes through Eloquent then fails in `tests/Unit` with a "no application" error,
which reads like a broken test rather than a missing binding. Three options:

```php
// A. give action tests their own booted directory (opt-in database per file)
pest()->extend(TestCase::class)->in('Unit/Actions');

// B. put action tests in Feature — they exercise the app, which is the point
// C. keep Unit for pure logic only: no Eloquent, no container
```

Prefer **A** when actions need the database sometimes and not always; prefer **B** when they always
do. Do not "fix" it by adding `RefreshDatabase` to the whole `Unit` directory — that makes genuinely
pure tests pay for a database.

### 4. Authorization failures do not return 403

If the app redirects with an error toast instead of aborting, `assertForbidden()` asserts the wrong
contract. Assert what the app does, and assert the side effect too:

```php
$this->actingAs($otherTenantUser)
    ->post(route('deposit-refunds.store', $deposit))
    ->assertRedirect();

assertErrorToast();
$this->assertDatabaseCount('deposit_refunds', 0);   // nothing was written
```

The second assertion matters more than the first: it proves the refusal happened before the write,
not after.

## Tenancy

Multi-tenant apps scope queries by an ambient context. Keep that context out of Actions where you
can, or the action becomes untestable without booting the tenant:

- **Prefer** passing the tenant/organization id in the DTO, so the action is a pure function of its
  arguments.
- **Acceptable** to read the context inside a policy, where the framework already has it.
- **Avoid** hiding tenancy inside a global scope *and* also in the action — two sources of truth
  diverge silently, and the failure mode is cross-tenant data exposure.

Whatever you choose, write one test that proves a second tenant cannot read the row. That test is the
only thing standing between a scoping change and an incident.

## Route helpers (Wayfinder)

If the app uses Wayfinder, typed route imports are **generated**, not static. They land in
`resources/js/{wayfinder,actions,routes}`, which the starter kits gitignore.

The Vite plugin regenerates them on dev-server start and during a build, so a normal `npm run dev` or
`npm run build` is enough. For a one-off generation, or a CI build that does not run Vite:

```bash
php artisan wayfinder:generate --with-form
```

`--with-form` is required for the `form()` variant the starter kits use. If a generated import is
missing after a deploy, clear the cached routes before rebuilding — Wayfinder reads the registered
router, and a stale route cache silently omits new routes:

```bash
php artisan route:clear && npm run build
```

## Recording the decisions

Anything you had to decide belongs in a rule file with a glob, not in your memory:

```markdown
---
paths:
  - app/Actions/**
  - app/Services/**
---

# Actions vs Services

New features use Actions. Existing Services are not converted unless the feature is
already being touched. Do not create a Service for a single use case.
```

That is what stops the next agent rediscovering the same six conflicts and resolving two of them
differently.
