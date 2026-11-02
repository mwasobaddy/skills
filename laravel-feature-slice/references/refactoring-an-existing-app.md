# Auditing and refactoring an existing app

The auditor tells you where the app is, not what to do about it. This is the loop from findings to
merged refactor, and the fix for each rule.

## The loop

```bash
# 0. green baseline -- never refactor on a red suite
php artisan test

# 1. record the starting point (the score is meaningless without it)
python3 scripts/laravel_audit.py . --json .audit/before.json

# 2. read the findings, triage by rule (table below)

# 3. fix one thing, then measure what you introduced
python3 scripts/laravel_audit.py . --baseline .audit/before.json
```

`--baseline` prints `introduced` vs `resolved`. In a mature app the absolute score is pinned near 0 by
pre-existing debt, so **the delta is the only progress signal**. Put `.audit/` in `.gitignore` — the
report is not an artefact to commit.

## Triage by blast radius, not by count

| Order | Category | Why first |
| --- | --- | --- |
| 1 | Runtime bugs — routes to missing methods, missing Inertia pages | these 500 in production |
| 2 | Security — authorization missing, cross-tenant scoping | they fail open and silently |
| 3 | Architecture — inline validation, writes in controllers | mechanical, safe, high leverage |
| 4 | Size — oversized controllers, methods, models | follow from 3; often disappear |
| 5 | Hygiene — `env()` outside config, `dd()` left in | one-line fixes |

Fixing 3 usually shrinks 4. Do not start with 4 by splitting methods — that moves the same logic around.

## Rule → fix

| Rule | Fix | Reference |
| --- | --- | --- |
| `route-target-missing` | implement the method, or correct/remove the route. **Never leave it.** | — |
| `inertia-page-missing` | create the page, or fix the render path (note `a/b` may resolve to `a/b/index.tsx`) | `starter-kits.md` |
| `livewire-view-missing` | create the Blade view, or fix the component's view name | `starter-kits.md` |
| `inline-validation` | extract a Form Request: `rules()` + `authorize()` + `toData()` | `layers.md#form-request` |
| `raw-request-parameter` | type-hint a Form Request (GET index/show exempt by design) | `layers.md#form-request` |
| `model-write-in-controller` | move the write into an Action; controller calls it | `layers.md#action` |
| `db-in-controller` / `db-in-model` | move the query into a scope, Action or query service | `layers.md#model` |
| `controller-too-large` | split by use case; orchestration into Actions | `migrating-services-to-actions.md` |
| `method-too-large` | the method is doing two things; split, don't indent | `layers.md#controller` |
| `model-too-large` | extract scopes, casts, or related concerns | `layers.md#model` |
| `action-too-large` | split into composable Actions, or a service | `layers.md#action` |
| `action-no-entrypoint` | give the class one `handle()`/`__invoke()` | `layers.md#action` |
| `formrequest-no-rules` | implement `rules()` — this one is a real defect | `layers.md#form-request` |
| `formrequest-no-authorize` | implement `authorize()`, delegating to a policy | `authorization.md` |
| `authorize-always-true` | fine for public forms; otherwise delegate to a policy | `authorization.md` |
| `env-outside-config` | read via `config('x.y')`; add the key to a config file | — |
| `debug-left-in` | remove `dd()`, `dump()`, `var_dump()`, `ray()` | — |
| `missing-feature-test` | add a Feature test per controller action | `layers.md#tests` |
| `page-error` | open the file; the auditor could not parse it | — |

## Worked example: this app at 24 errors

```
15  route-target-missing     routes/web.php, tenant.php, platform.php -> history(),
                             showConversation(), destroyConversation()
 9  inline-validation        $request->validate() in controllers
```

**Fix 15 first.** `Platform\AssistantController` defines `page()` and `ask()` but three route files
register `history`, `showConversation`, `destroyConversation`. Those routes 500 at runtime. Either
implement the methods or delete the routes — decide which, but do not leave both.

**Then the 9.** Each is a mechanical extraction:

1. `php artisan make:request StoreXRequest`
2. move the rules array into `rules()`
3. move any `$request->user()->can(...)` into `authorize()`
4. type-hint the request in the controller
5. run the controller's tests

One commit per controller. If a controller has no test, write the characterization test first — that is
the safety net for the extraction, not a nice-to-have.

## Commit granularity

```
fix(routes): implement assistant history endpoints
refactor(search): extract SearchRequest from controller
refactor(settings): extract PersonalAiRequest
```

A commit that touches nine controllers cannot be reviewed or reverted. Each of these is independently
green or independently revertable.

## When you inherit a red suite

Stop. Fix or quarantine the failing tests before refactoring, because otherwise you cannot tell your
breakage from theirs. Record the baseline counts (`tests: 551 passed, 1 skipped`) and do not let them
change as a side effect of a refactor.

If a test fails *because of* your refactor and the behaviour is unchanged, the test was asserting an
implementation detail — decide deliberately whether to change the test or the code. Do not edit it to
match whatever the new code does.

## The trap in mature apps

`score: 0/100` reads like "everything is broken" and invites a big-bang rewrite. It is not. The score is
absolute; the app has accumulated debt over years. Ship one fixed rule at a time and watch `resolved`
grow in the baseline delta.
