# Multitenancy: identify the model, then apply the rules

Tenant code fails in the same place regardless of stack: something reads tenant identity from the
request instead of from the tenant context, or a query runs without a scope. The fixes differ by
model, so establish the model first (`project-discovery.md`).

## The two axes

| Axis | Options | Consequence |
| --- | --- | --- |
| **Identification** | subdomain, custom domain, URL path, query/column, session | decides where tenant identity comes from and which routes exist |
| **Storage** | separate database per tenant, shared database with a tenant column | decides whether isolation is free or entirely your responsibility |

Common combinations:

| Setup | Isolation | Typical stack |
| --- | --- | --- |
| Subdomain + separate DB | connection switching | `stancl/tenancy` with `DatabaseTenancyBootstrapper` |
| Subdomain + shared DB | **application-level only** | `stancl/tenancy` with the DB bootstrapper disabled, or spatie multitenancy |
| Path prefix + shared DB | application-level only | custom middleware, `/app/{tenant}/...` |
| Column only, no host change | application-level only | custom scoping, often a global scope |
| Single-tenant | none | not a tenant app; skip this file |

The dangerous row is **shared database**: nothing prevents a cross-tenant read except your own
scopes. That is where the checklist below matters most.

## Rules that apply to every model

1. **Identity comes from the tenant context, never from input.** No `?organization_id=`, no hidden
   form field, no route parameter used as the tenant.
2. **Every query is scoped.** If storage is shared, the scope is explicit. If a global scope exists,
   know exactly where it applies and where it is bypassed (`withoutGlobalScope`, raw queries, jobs).
3. **Route-model binding must be re-verified.** `Model::findOrFail($id)` resolves any tenant's row.
   Bind through the tenant's relation, or check membership in the policy.
4. **Route placement follows the host.** Central routes and tenant routes live in separate files with
   separate middleware. A tenant route in the central file is exposed on every host.
5. **Queued work loses context.** Queue tenancy helps only when the job is dispatched inside a tenant
   request. Jobs from commands, central admin actions, or after-response callbacks need the tenant id
   passed and initialized explicitly.
6. **Cache keys are shared** unless the cache bootstrapper prefixes them. A cached payload written for
   one tenant can be read by another.
7. **Test isolation, not just features.** One test per resource proving tenant B cannot read tenant A's
   row by id. That test is the only thing between a scoping change and an incident.

## If a separate database per tenant

- Migrations live in a tenant path (`database/migrations/tenant`) and run per tenant.
- Connection switching is automatic inside the tenant request; raw `DB::connection()` calls can escape it.
- Cross-tenant queries need an explicit connection switch — a feature that spans tenants is a design
  smell, not a query tweak.
- Seeding, backups and schema changes are per tenant: a new migration is not "done" until every tenant
  has it.

## If the database is shared

- Every model that belongs to a tenant carries the tenant key; every query filters on it.
- Prefer relation-based binding (`$tenant->deposits()->findOrFail($id)`) over `Model::findOrFail()`.
- Policies must check organization membership, not just ownership of the record.
- Aggregates and reports are the usual leak: a dashboard query that forgets the scope returns other
  tenants' totals and looks plausible.

## If identification is by path

- The tenant segment is part of every URL and every generated link; a missing segment silently
  resolves to the wrong tenant or a 404.
- Route middleware must reject a tenant segment that the user is not a member of, not merely resolve it.
- Named routes need the tenant parameter everywhere; a bare `route('dashboard')` will either fail or
  drop the tenant.

## Reference implementation

One real app, for concreteness — treat it as an example, not a requirement:

| Aspect | Its choice |
| --- | --- |
| Stack | `stancl/tenancy` v3, subdomain identification |
| Hosts | central `malimanager.test`; tenant `{org-slug}.malimanager.test` |
| Storage | **shared database** — `DatabaseTenancyBootstrapper` disabled |
| Bootstrappers | cache and queue enabled; filesystem **disabled** on purpose (media on the central disk) |
| Context accessor | `App\Support\TenancyContext::organization()` / `tenantId()` |
| URL shape | `https://{org}.host/{property-slug}/dashboard` |
| Routes | `routes/tenant.php` with `InitializeTenancyByDomain` + `PreventAccessFromCentralDomains` |
| Login | central domain, then redirect to the tenant host after authentication |

Two details from that app that are easy to get wrong when copying a tutorial:

- Because the DB bootstrapper is disabled, **nothing** is scoped automatically. A plain
  `Property::all()` returns every organization's rows.
- The filesystem bootstrapper is disabled deliberately: enabling it moves uploads to a per-tenant disk
  path that the media library's URL resolver cannot see, breaking existing images.

## Common mistakes

| Mistake | Result |
| --- | --- |
| Tenant id read from the request | cross-tenant read or write |
| `Model::find($id)` on a tenant model | resolves another tenant's row |
| Tenant route added to the central route file | reachable on every host, no tenant initialized |
| Job dispatched from central context | runs without a tenant |
| Assuming a separate DB because the package supports it | it may be a single DB; verify the bootstrappers |
| Re-enabling a bootstrapper "because the docs say so" | changes storage paths and breaks existing URLs |
| Only testing the happy path | the leak is never exercised |
