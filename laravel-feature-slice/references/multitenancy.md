# Multitenancy: stancl/tenancy v3 with subdomain identification

This app is multi-tenant. **Every feature decision must answer: which tenant is this for, and how is
that proven?**

Tool: `stancl/tenancy` ^3.10. Identification: **subdomain**, via `InitializeTenancyByDomain`.

## The two kinds of host

| Host | What lives there | Route file |
| --- | --- | --- |
| `malimanager.test` (central) | login, onboarding, platform admin, org management, property picker | `routes/web.php`, `routes/platform.php` |
| `{org-slug}.malimanager.test` (tenant) | everything scoped to one organization | `routes/tenant.php` |

Config: `config/tenancy.php` → `central_domains` and `subdomain_base` (env `TENANT_SUBDOMAIN_BASE`).

Each organization gets a `domains` row when it is created. The host is not derived from a session —
it is a real DNS-ish identifier stored in the central `domains` table, so two organizations can never
claim the same subdomain.

## The login → tenant flow

A user authenticates on the **central** domain. There is no tenant yet at that point — tenancy is
initialized by the host, and the host is central. After authentication `App\Support\AuthLanding`
decides where to send them, ending at a URL shaped like:

```
https://kelvin-properties.malimanager.test/kelvin-properties-residences/dashboard
└──────────── tenant subdomain ────────┘ └──── property slug ────┘ └ route ┘
```

- **Host** identifies the tenant (organization).
- **First path segment** identifies the property or workspace within that tenant.
- Everything after belongs to a normal named route.

So the same route name resolves on many hosts, and one tenant's property can never be addressed on
another tenant's host — the middleware rejects it before routing.

## The route middleware chain

`routes/tenant.php` wraps tenant routes with:

```php
InitializeTenancyByDomain::class,
PreventAccessFromCentralDomains::class,
```

- `InitializeTenancyByDomain` resolves the host to a tenant and boots tenancy. An unknown host is not a
  404 route — it is a failed identification.
- `PreventAccessFromCentralDomains` stops tenant routes being reached on the central domain. This is
  what prevents `/kelvin-properties/dashboard` existing on `malimanager.test`.

Never add a tenant route to `routes/web.php`. It will appear on every host.

## Reading the current tenant

`App\Support\TenancyContext` is the only sanctioned accessor:

```php
TenancyContext::initialized(): bool
TenancyContext::tenant(): ?Tenant
TenancyContext::tenantId(): ?string
TenancyContext::organization(): ?Organization
TenancyContext::domain(): ?Domain
```

Do not call `tenant()` directly in new code, and never read tenant identity from a request parameter
(`?organization_id=`) — that is the classic cross-tenant read.

## Isolation is application-level here

**`DatabaseTenancyBootstrapper` is disabled** in `config/tenancy.php`. All tenants share one database.

That is a deliberate architectural choice, and it means **nothing scopes your queries for you**.
Tenant separation comes from explicit `organization_id` scoping plus policies. An unscoped
`Property::all()` returns every organization's rows.

Every query that serves a tenant must be constrained by the current organization, and every model
bound from the URL must be verified to belong to it — route-model binding will happily resolve
another tenant's row by id.

```php
// wrong: id from the URL, no tenant predicate
$deposit = Deposit::findOrFail($request->route('deposit'));

// right: scoped to the current organization
$deposit = TenancyContext::organization()
    ->deposits()
    ->findOrFail($request->route('deposit'));
```

## Disabled and enabled bootstrappers

| Bootstrapper | State | Consequence |
| --- | --- | --- |
| Database | **disabled** | one database; scope everything yourself |
| Filesystem | **disabled** | media stays on the central `public` disk; `getUrl()` resolves |
| Cache | enabled | cache keys are tenant-prefixed — a cache written on one tenant is invisible to another |
| Queue | enabled | jobs carry tenant context |

**Do not re-enable `FilesystemTenancyBootstrapper`** without reading `.ai/rules/media.md`: uploads
would move to `storage/tenant{id}/app/public`, which the media library's `getUrl()` cannot resolve,
breaking every existing image.

## Queues and jobs

Queue tenancy is on, so a job dispatched inside a tenant request runs with that tenant initialized.
A job dispatched from a **central** context — a platform admin action, a scheduled command, an event
fired after a response — does **not**. It will either see no tenant or the wrong one.

If a job touches tenant data, either dispatch it from within tenant context or pass the organization
id explicitly and initialize tenancy in the job:

```php
public function handle(): void
{
    tenancy()->initialize($this->organizationId);
    // ...
}
```

Test this. A job that works in a request and fails from a command is the normal failure mode.

## Testing tenant behaviour

Tenant HTTP tests must use the tenant host, otherwise middleware rejects the request before your code
runs:

```php
$tenant = Tenant::create(['id' => 'acme']);
$tenant->domains()->create(['domain' => 'acme.malimanager.test']);

$this->get('http://acme.malimanager.test/overview')->assertOk();
```

For a cross-tenant test, create two tenants with one model each and assert user A cannot read B's row
by id. That test is the only thing standing between a scoping change and an incident.

## Checklist before calling a tenant feature done

- [ ] Tenant identity comes from the host, never a query parameter
- [ ] Every query is scoped to `TenancyContext::organization()`
- [ ] Route-model binding is verified against the current organization
- [ ] The policy checks organization membership, not just ownership
- [ ] Any queued work has tenant context, or initializes it
- [ ] Cache keys are safe under tenant prefixing
- [ ] One test proves a second tenant cannot read the row
- [ ] Central-only routes are not reachable on tenant hosts, and vice versa

## Common mistakes

| Mistake | Result |
| --- | --- |
| Tenant route added to `routes/web.php` | reachable on every host, with no tenant initialized |
| Reading `organization_id` from the request | cross-tenant read |
| `Model::find()` on a URL id | resolves another tenant's row |
| Job dispatched from a central action | runs with no tenant, writes nowhere or everywhere |
| Re-enabling filesystem tenancy | every uploaded file's URL breaks |
| Assuming a separate database per tenant | it is one database; nothing is scoped for you |
