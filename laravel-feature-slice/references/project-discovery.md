# Discover the project before applying anything

This skill makes claims about *your* app. Most of them are wrong by default, because tenancy,
authorization, base classes and money handling differ between projects. Spend one pass establishing
the facts, write them down, then apply the rest of the skill against those facts.

**A documented project rule always beats a default in this skill.** If `.ai/rules`, `AGENTS.md` or
`CLAUDE.md` states a convention, that is the answer; this skill only fills the gaps.

## The profile

Produce a short profile — six lines — before writing code. Every later reference assumes you have it.

```markdown
- Laravel / PHP: 13.x / 8.3
- Tenancy: stancl/tenancy v3, subdomain, shared database
- Tenant context accessor: App\Support\TenancyContext
- Authorization: spatie roles (coarse) + custom sub-permissions (org-scoped) + policies
- Write layer: app/Actions (single use case), base App\Services\Service
- Frontend: Inertia 3 + React 19, resources/js/pages
```

## How to establish each line

### Framework and language

```bash
php artisan --version
php -v | head -1
```

### Tenancy

```bash
grep -E 'stancl/tenancy|spatie/laravel-multitenancy|archtechx|tenancy' composer.json
ls config/tenancy.php 2>/dev/null
grep -rn "InitializeTenancy\|InitializeTenancyByDomain\|InitializeTenancyByPath" app routes | head
```

| Question | Look at | Why it matters |
| --- | --- | --- |
| How is a tenant identified? | middleware in `routes/*.php`, `config/tenancy.php` | host, path, session, or column change every URL and route |
| Separate database per tenant, or shared? | `DatabaseTenancyBootstrapper` in `tenancy.bootstrappers` | separate DB scopes for you; shared DB scopes nothing |
| Which accessor gives the current tenant? | grep `tenant()` wrappers, a `Support/*Context` class | never read tenant identity from the request |
| Which bootstrappers are enabled? | `config/tenancy.php` | cache, filesystem, queue and DB behaviour differ per bootstrapper |

### Authorization

```bash
grep -E 'spatie/laravel-permission|bouncer|laratrust' composer.json
ls app/Policies
grep -rn "sub.permission\|can:\|hasPermissionTo\|hasRole" app/Http/Middleware routes | head
```

Three tiers exist in mature apps. Find which ones yours has:

| Tier | Evidence |
| --- | --- |
| Coarse role | a `Role` enum or spatie `roles` table |
| Fine-grained permission | permission keys, a middleware like `can:` or a custom gate middleware |
| Record policy | `app/Policies`, `authorize()` in Form Requests |

### Write layer

```bash
ls -d app/Actions app/Services app/Data 2>/dev/null
ls app/Services/*.php 2>/dev/null | head
```

Decide whether the app is Action-oriented, Service-oriented, or mixed — then follow it. See
`adapting-to-an-app.md`.

### Base classes and helpers

```bash
grep -rn "abstract class Service\|trait.*Transaction" app | head
```

If there is a base class providing `transaction()` / `save()`, new classes extend it so behaviour is
unchanged. If there is not, use `DB::transaction()` directly.

### Money

```bash
grep -rn "decimal:\|_cents\|money:" app/Models | head
grep -rn "->decimal(\|->bigInteger(" database/migrations | head -5
```

Whichever representation already exists is the answer. Never introduce a second one.

### Frontend

```bash
grep -E '"@inertiajs/(react|vue|svelte)"|livewire/livewire' package.json composer.json
ls resources/js/pages resources/views/pages 2>/dev/null | head
```

### Tests

```bash
cat tests/Pest.php 2>/dev/null | head -20
grep -n "DB_CONNECTION\|DB_DATABASE" phpunit.xml
git log --oneline -1  # is the suite green at HEAD? If not, stop and fix that first.
```

Record the baseline before refactoring anything: `php artisan test` and the pass/fail counts.

## Write it down

Put the profile where the next agent will find it — a rule file with a glob, not a chat message:

```markdown
---
paths:
  - app/**
---

# Project profile

Tenancy: stancl/tenancy, subdomain, shared database, context via App\Support\TenancyContext.
Authorization: spatie role (coarse) -> sub-permission (org) -> policy (record).
Write layer: Actions for use cases, Services for queries.
Money: decimal(14,2) with decimal:2 casts.
```

Once it exists, later sections of this skill can be read as "how to apply the pattern", not "what
your app is".
