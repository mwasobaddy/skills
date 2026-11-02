# Authorization: roles, permissions, and policies

Authorization is where a plausible-looking feature becomes a security bug. Establish which tiers the
app has (`project-discovery.md`), then pick the right one per check. Choosing wrong usually fails
open, not closed.

## The three tiers, as a pattern

Most mature apps end up with some mix of these, whatever the package:

| Tier | Answers | Typical implementation |
| --- | --- | --- |
| **Coarse role** | What kind of account is this? | enum, or a role on the user |
| **Fine-grained permission** | What may this member do in *this scope*? | permission keys, often scoped to a team/organization |
| **Policy** | May this user act on *this record*? | Laravel policy |

Know which tier each rule belongs to before writing the check:

| If the rule is about… | Tier |
| --- | --- |
| Platform operator vs regular user | coarse role |
| "Can this member create properties here?" | fine-grained permission |
| "Can this user modify *this* record?" | policy |
| "Is this record even in my tenant?" | policy **and** tenant scoping — both |
| Showing or hiding a button | mirror the tiers in the UI, **never instead of** the server check |

## Common stacks

| Stack | What to use | Trap |
| --- | --- | --- |
| `spatie/laravel-permission` only | roles + permissions | global permissions cannot express per-tenant grants without teams enabled |
| spatie roles **plus** custom scoped permissions | role for account type, custom key for tenant-scoped action | adding a spatie permission for something that belongs in the scoped system |
| Policies only | policy method per action | coarse: "can edit any record" is not a policy |
| Gates only | `Gate::define` | proliferates; policies scale better |

If the app has **two** permission systems, the skill's job is to tell you which one a new check
belongs to — not to add a third.

## Rules

1. **Enforce on the server.** A hidden button is a UX affordance, not a permission.
2. **`authorize()` in the Form Request is mandatory.** Laravel's default is `true`, so a missing method
   silently grants access.
3. **Record-level checks go in a policy.** Policies are auto-discovered; do not register them.
4. **Never reimplement a bypass.** Most helper methods already grant access to a super-admin and to an
   owner/creator. Inline `if ($user->is_admin || $user->is_owner || ...)` drifts from the helper and
   eventually locks out the person it was meant to let through.
5. **The scope must come from the tenant context**, not the request. A permission check against an
   organization id supplied by the client is a cross-tenant authorization bug.
6. **Check membership, not just ownership.** "This user owns the record" ignores whether the record is
   still in the tenant they are acting in.
7. **Authorize before the write, not after.** A 403 that already persisted a row is worse than no check,
   because the suite stays green.

## Adding a permission

Adapt the names to the stack; the order matters.

1. **Add the key** to the catalog (enum, constants, or config) using a stable `module.action` shape.
2. **Decide the defaults** — which built-in roles get it. Seeded roles only affect *new* tenants;
   existing ones hold their own rows.
3. **Gate the route** with the middleware/gate for that tier.
4. **Add or extend the policy** if the action targets an existing record.
5. **Test both directions**: a member without it is refused and no row was written; someone with it
   succeeds.
6. **Backfill** if existing tenants must be granted it — otherwise only super-admins and owners have it.

Changing a permission catalog is a platform-wide contract. Treat new keys as an additive migration, not
a rename.

## When the route middleware is the gate

Some apps enforce authorization in route middleware (`sub.permission:occupant.delete`) and leave the
Form Request with nothing to check. That is a valid design — but a bare `return true` is
indistinguishable from a missing check, so the next reader cannot tell whether it was decided or
forgotten.

Say which, in the method:

```php
public function authorize(): bool
{
    // Enforced by the `sub-permission:occupant.delete` middleware on the route;
    // this form is not a second gate.
    return true;
}
```

The auditor reports `authorize-always-true` as **info**, not a defect, precisely because this comment is
the evidence that it was a decision. Without the comment the info is the only signal, and a reader has to
guess.

Two rules that follow:

- If the route gate is the enforcement point, the Form Request must not silently duplicate it in a way
  that can drift — name the gate instead.
- If no gate exists on the route, `return true` is a hole. Check before writing it.

## Tests that actually prove it

```php
it('refuses a member without the create permission', function () {
    $this->actingAs($limitedMember)
        ->post($this->tenantUrl('/properties'), [...])
        ->assertForbidden();

    $this->assertDatabaseCount('properties', 0);   // the refusal happened before the write
});
```

- Assert the refusal **and** the absence of the side effect.
- If the app returns a redirect with a toast instead of 403, assert the redirect and the toast, and keep
  the side-effect assertion (`adapting-to-an-app.md`).
- Add one cross-tenant case: user from tenant A acts on tenant B's record id.

## Common mistakes

| Mistake | Consequence |
| --- | --- |
| Coarse role checked for a scoped action | every member of that role passes |
| Adding a second permission system | one of them is unenforced; nobody knows which |
| Inline ownership/super-admin checks | bypasses drift; owners get locked out |
| Permission evaluated against a client-supplied scope | cross-tenant authorization |
| Hidden UI only | the route is still callable |
| `authorize()` missing in a Form Request | defaults to allow |
| Authorizing `create` without the parent record | member creates inside another tenant |
| No test for the refusal | the leak ships |

## Reference implementation

One real app, for concreteness — an example of the pattern, not a requirement:

| Tier | Its implementation |
| --- | --- |
| Coarse role | `spatie/laravel-permission`; `PlatformRole` enum — admin, organization-owner, searcher, occupant |
| Scoped permission | custom `SubPermissionKey` catalog (`property.edit`, `unit.delegate`), granted via per-organization sub-roles seeded by `DefaultSubRoles` |
| Record policy | `app/Policies`, plus `#[Authorize]` attributes on controllers |
| Enforcement | `sub.permission:<key>` middleware resolving the organization from `TenancyContext` |
| Helper | `$user->hasSubPermission($organization, SubPermissionKey::X)` — already grants platform admins and organization owners |

The reason it matters: `hasSubPermission()` contains the bypass logic. Any feature that re-derives the
answer inline will disagree with it, and the disagreement will surface as an owner losing access or a
non-member gaining it.
