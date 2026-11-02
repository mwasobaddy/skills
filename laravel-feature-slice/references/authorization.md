# Authorization: roles, sub-permissions, and policies

This app has **three** authorization tiers, and choosing the wrong one is a security bug rather than a
style problem. Decide the tier before writing the check.

| Tier | Answers | Package | Scope |
| --- | --- | --- | --- |
| **Platform role** | What kind of account is this? | `spatie/laravel-permission` | Central, one role per user |
| **Sub-permission** | What may this member do *in this organization*? | Custom (`SubPermissionKey`) | Per organization, via sub-role |
| **Policy** | May this user act on *this specific record*? | Laravel policies | Per model instance |

`PlatformRole` is only `admin`, `organization-owner`, `searcher`, `occupant`. It is deliberately
coarse. Most feature decisions are **sub-permissions**, not platform roles.

## Tier 1 — platform role

```php
$user->hasRole(PlatformRole::Admin->value);   // platform operator
$user->isPlatformAdmin();
```

Use for: cross-tenant operator surfaces (`Platform/` controllers), and the searcher/occupant split.
Do **not** use it to decide whether a staff member may edit a property — that is tier 2.

## Tier 2 — sub-permission

The catalog is `App\Enums\SubPermissionKey`, keyed `module.action` (`property.edit`, `unit.delegate`,
`deposit_refund.decide`). Each organization has sub-roles (landlord, caretaker, agent, plus owners),
seeded by `App\Support\DefaultSubRoles` and editable by owners.

Route-level enforcement:

```php
Route::post('/properties', [PropertyController::class, 'store'])
    ->middleware('sub.permission:property.create');
```

The middleware `EnsureSubPermission` resolves the organization from `TenancyContext` — never from the
request — and checks:

```php
$user->hasSubPermission($organization, SubPermissionKey::from($permission));
```

`hasSubPermission()` is the only correct call. It applies two bypasses you must not reimplement:

- platform admins always pass
- organization **owners** always pass

Writing `if ($user->is_owner || $user->sub_role->permissions->contains(...))` inline re-implements this
and will drift.

## Tier 3 — policy

Policies decide per record: "may this user act on *this* deposit?" They are what stops a member of
organization A acting on a record belonging to organization B when they happen to know its id.

```php
#[Authorize('update', 'deposit')]        // Laravel 13 attribute, preferred
public function update(UpdateDepositRequest $request, Deposit $deposit) { … }
```

or from the Form Request:

```php
public function authorize(): bool
{
    return $this->user()->can('update', $this->route('deposit'));
}
```

Policies are auto-discovered — do not register them in a provider.

## Which tier for which job

| If the rule is about… | Tier |
| --- | --- |
| Platform operator vs regular user | Platform role |
| "Can this staff member create properties here?" | Sub-permission |
| "Can this user modify *this* record?" | Policy |
| "Is this record even in my organization?" | Policy + tenant scoping (both) |
| Showing or hiding a button | Mirror tiers 1–2 in the UI, **never instead of** the server check |

## Adding a new permission

1. Add a case to `SubPermissionKey` (`module.action`).
2. Decide whether the default sub-roles should grant it — `App\Support\DefaultSubRoles`.
3. Gate the route with `sub.permission:<key>`.
4. If the action targets an existing record, add or extend the policy method.
5. Add a test: a non-permitted staff member is refused **and no row was written**; an owner is allowed.

Changing the enum is a platform-wide contract. Existing organizations hold sub-role permission rows, so
new keys are not retroactively granted — either backfill or accept that owners bypass it and others must
be granted explicitly.

## Common mistakes

| Mistake | Consequence |
| --- | --- |
| Checking a platform role for an org-scoped action | every organization-owner or every staff member passes |
| Creating a spatie permission for `property.edit` | two permission systems, one of them unenforced |
| Inline ownership/sub-role checks | bypass rules drift; owners get locked out |
| Checking the sub-permission against a request-supplied org id | cross-tenant authorization |
| Hiding the button in React only | the route is still callable |
| Forgetting `authorize()` in a Form Request | Laravel defaults it to `true` |
| Authorizing on `create` without the parent record | member can create inside another organization |

## Tests that actually prove it

```php
it('refuses a caretaker without property.create', function () {
    $this->actingAs($caretaker)
        ->post("http://{$this->tenantDomain}/properties", [...])
        ->assertForbidden();

    $this->assertDatabaseCount('properties', 0);   // the refusal happened before the write
});
```

Assert both the refusal **and** the absence of the side effect. A 403 that still wrote a row is worse
than no check, because the tests look green.

For redirect-plus-toast apps, assert the redirect and the toast instead of `assertForbidden()`, and keep
the side-effect assertion — see `references/adapting-to-an-app.md`.
