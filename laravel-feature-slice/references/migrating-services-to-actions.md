# Migrating Services to Actions

A service layer is not wrong. It becomes a problem when a service is a grab bag: twelve public
methods spanning unrelated write paths, each a separate use case with its own authorization, its own
validation and its own side effects. Extracting those into Actions is worthwhile. Rewriting the whole
layer at once is not.

## Decide the taxonomy first

Not every service method should become an Action. Getting this wrong is how a migration doubles the
code without improving it.

| Kind of method | Example | Becomes |
| --- | --- | --- |
| **Write use case** — one intent, side effects | `create()`, `update()`, `softDelete()`, `decide()` | **Action** — one class, one `handle()` |
| **Query / aggregate** — reads, no writes | `payload()`, `propertyStats()`, `reportsFor()` | **Stays** in the service |
| **Pure predicate** — no I/O | `canTransition()`, `transitionsFrom()` | Enum or model method |
| **Cross-cutting collaborator** — used by many paths | `PropertyAccessService`, `TenantService` | **Stays** |

Rule of thumb: if the method has a verb in its name and writes to the database, it is a candidate. If
it returns a shape of data, it is not.

Inventory a real app with:

```bash
python3 scripts/laravel_audit.py /path/to/app --services
```

It reports every public service method as write or read, and prints the write ones as candidates.

## Why this is a low-risk move here

Most Laravel service layers have a base class holding the persistence primitives:

```php
abstract class Service
{
    protected function transaction(callable $cb): mixed { /* DB::transaction + report + rethrow */ }
    protected function save(Model $model): Model { /* throws on false */ }
    protected function delete(Model $model): void { /* ... */ }
}
```

An Action can extend **the same base**, so it inherits identical transaction and persistence
behaviour. The extraction then moves code without changing semantics — which is the whole point. If
your base class is `abstract class Service`, a new `app/Actions/` class extending it is not a
behavioural change.

```php
namespace App\Actions\Maintenance;

use App\Services\Service;

class CreateMaintenanceRequest extends Service
{
    public function handle(User $raiser, int $organizationId, array $data): MaintenanceRequest
    {
        return $this->transaction(function () use ($raiser, $organizationId, $data) {
            // body moved verbatim
        });
    }
}
```

Later you can rename the base to something neutral (`App\Support\Transactional`) once nothing
depends on the name.

## The strangler procedure, per use case

Do this one method at a time. Each step ends with green tests.

1. **Pin the behaviour first.** If the path has no test, write a characterization test that asserts
   what it does *today*, not what it should do. This is the safety net for every later step.
2. **Create the Action** in `app/Actions/{Domain}/{VerbNoun}.php`, extending the base so
   `transaction()`/`save()` behave identically.
3. **Move the body verbatim.** No renames, no "while I'm here" fixes, no signature changes. Behaviour
   preservation is the requirement; cleanup is a separate commit.
4. **Leave the service method as a delegate** calling the Action:

   ```php
   public function create(User $raiser, int $orgId, array $data): MaintenanceRequest
   {
       return app(CreateMaintenanceRequest::class)->handle($raiser, $orgId, $data);
   }
   ```
5. **Swap callers one at a time** — controller, then job, then listener — running the suite after
   each. Delegation makes this safe: a missed caller still works.
6. **Delete the delegate** only when no caller references it. Grep, don't assume.
7. **Repeat.** When the service is empty of write methods, it is a query service — rename it if the
   name now lies.

## Ordering

Cheapest and safest first, so the pattern is proven before the risky ones:

| Start with | Avoid until confident |
| --- | --- |
| Smallest body (5–15 lines) | The 80+ line method |
| One or two callers | A method called from jobs, listeners and controllers |
| Covered by an existing test | Untested |
| Domain you understand | Money, tenancy, permissions |

The inventory output gives you body sizes. Sort by `lines` ascending.

## Commit granularity

One use case per commit, each independently revertable:

```
refactor(maintenance): extract CreateMaintenanceRequest action
refactor(maintenance): point controller at the action
refactor(maintenance): remove the create() delegate
```

A commit that touches three services cannot be reviewed or reverted.

## Do not

- **Big-bang rewrite.** A branch that converts all services at once cannot be verified; you will not
  know which change broke the suite.
- **Convert query services.** `payload()` is not a use case. Turning it into an Action adds a class
  and a layer without a boundary.
- **Change behaviour while moving.** Rename, restructure, then optimise — three commits, not one.
- **Edit the test to match the new code** when it fails mid-migration. If the test encoded the old
  contract, decide deliberately; don't let it drift to whatever the new code does.
- **Leave the delegate forever.** Two call paths for one intent is the problem you set out to fix.
- **Mix a framework upgrade into it.** Upgrade separately.

## Done, per service

- [ ] Every write method is an Action with one `handle()`
- [ ] No delegate left behind
- [ ] Query methods remain, and the service name is still accurate
- [ ] The suite is green, and the characterization tests are still asserting the original behaviour
- [ ] `.ai/rules` updated so the next agent follows the new layering, not the old one

## If you decide to stop halfway

That is a legitimate outcome. A half-migrated app is fine **if the boundary is written down**: which
services are Actions now, which are not. What is not fine is an undocumented mix — the next agent
picks whichever it saw last.
