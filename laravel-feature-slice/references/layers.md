# Layers: what each file is for

Two views of the same thing: **the map** (which directory, and why) and **the rules**
(one layer at a time, with code). Read the map to place a file; read the rules to write it.

## The map
Every directory below has one job. New code goes where its job is, not where it is convenient. When
two directories could plausibly own something, the deciding question is *what changes when it
changes*.

```
laravel-project/
├── app/
│   ├── Actions/                  # one class per write use case
│   ├── Concerns/                 # traits shared across models or domains
│   ├── Console/                  # custom Artisan commands
│   ├── Data/                     # DTOs / typed payloads
│   ├── Enums/                    # strongly-typed states
│   ├── Exceptions/               # application-level exceptions
│   ├── Foundation/               # low-level framework extensions
│   ├── Http/
│   │   ├── Controllers/          # request entry points, thin
│   │   ├── Middleware/           # request filters
│   │   ├── Requests/             # validation + authorization
│   │   └── Resources/            # response transformers
│   ├── Jobs/                     # queued work
│   ├── Mail/                     # mailables
│   ├── Models/                   # Eloquent models
│   ├── Policies/                 # authorization rules
│   ├── Providers/                # bootstrap and bindings
│   ├── Services/                 # queries, aggregates, third-party clients
│   └── Support/                  # app-wide helpers and small value utilities
```

## What each does

| Directory | Job | In this app | Rule |
| --- | --- | --- | --- |
| `Actions/` | One class, one write use case, one `handle()` | `Deposits/DecideDepositRefund`, `Occupants/MoveOutOccupant` | Extends `App\Services\Service` for `transaction()` / `save()` |
| `Concerns/` | Traits reused by several models or domains | `LogsTenantActivity`, `PasswordValidationRules` | A trait with a single user is a private method that has not found its home |
| `Console/` | Artisan commands | scheduled and maintenance commands | Command calls an Action or Service; no business logic inline |
| `Data/` | Typed payloads crossing layers, `final readonly` | `Metering/RecordMeterReadingData` | Worth a class when it crosses 2+ layers or a method takes 3+ args |
| `Enums/` | Every fixed set of values, backed | `RentalStatus`, `NoteVisibility` | Never string constants, never raw strings in columns |
| `Exceptions/` | Domain failures that callers handle | — | Throw these instead of `abort()` inside Actions |
| `Foundation/` | Parts of the framework being replaced or extended | `TenantAwareVite` | Only when the framework itself must change behaviour |
| `Http/Controllers/` | Route target: validate → call → respond | `Tenant/`, `Platform/`, `Auth/`, `Searcher/` | 1–15 lines per method, no `validate()`, no writes |
| `Http/Middleware/` | Request-level filters | `EnsureSubPermission`, `EnsureUserIsActive` | Cross-cutting only; not business rules |
| `Http/Requests/` | `rules()` + `authorize()` | 71 of them | Both methods mandatory |
| `Http/Resources/` | Response shape, one per model surfaced | `PropertyResource` | Never return a raw model from an API endpoint |
| `Jobs/` | Work that must survive the request | report generation, notifications | Runs outside tenancy unless told otherwise — see `multitenancy.md` |
| `Mail/` | Mailables | — | Content in the mailable; sending happens in an Action or Listener |
| `Models/` | Casts, relations, scopes, accessors | 36 models | No orchestration, no `Mail::`, no HTTP |
| `Policies/` | Who may do what | `DepositRefundPolicy` | Auto-discovered; no provider registration needed |
| `Providers/` | Bindings, event wiring, tenancy bootstrapping | `AppServiceProvider`, `FortifyServiceProvider` | Configuration only |
| `Services/` | Queries, aggregates, third-party API wrappers | `DashboardService`, `PropertyAccessService` | **Not** for a single write use case — that is an Action |
| `Support/` | App-wide helpers, small value objects | `TenancyContext`, `AuthLanding`, `CsvReader` | Must be framework-agnostic or tenancy-aware; no business rules |

## The three that get confused

**`Actions` vs `Services`** — the boundary this skill exists to make explicit:

| | Action | Service |
| --- | --- | --- |
| Intent | Does one thing once, for one caller | Answers a question, or wraps a collaborator |
| Shape | `handle(...)`, returns a model/DTO | Several methods, returns data |
| Example | `CreateMaintenanceRequest` | `DashboardService::payload()` |
| Test | One scenario per method | Shape of the returned data |

A service with twelve `create`/`update` methods is a pile of Actions that never got separated.

**`Support` vs `Foundation`** — `Support` is your code (helpers, context objects). `Foundation` is
where you change how the framework itself behaves. Most applications never need `Foundation`.

**`Data` vs `Resources`** — `Data` goes *in* (request → action). `Resources` comes *out*
(model → response). They are not interchangeable.

## Where new code goes

1. Is it a write use case? → `Actions/{Domain}/`
2. Does it validate a request? → `Http/Requests/{Domain}/`
3. Does it decide permission? → `Policies/` (or `authorize()` in the Form Request)
4. Is it a query or aggregate? → the relevant `Services/` class
5. Is it a fixed set of values? → `Enums/`
6. Does it shape a response? → `Http/Resources/`
7. Is it shared across models? → `Concerns/`
8. Is it a helper with no domain knowledge? → `Support/`
9. Nothing fits? → it is probably two things; split it

---

## Controller — routing only

**Rule:** a method reads the request, calls one action, returns a response. Nothing else.

```php
class OnboardingController extends Controller
{
    public function store(StoreOnboardingRequest $request, StartOnboarding $start)
    {
        $profile = $start->handle($request->user(), $request->toData());

        return redirect()->route('onboarding.show', $profile);
    }
}
```

Do not: `$request->validate()`, `Model::create()`, `DB::`, `Mail::`, `Storage::`, `if/else` chains
over business rules, `try/catch` around domain errors you could model.

Laravel 13 lets middleware and authorization be declared as attributes:

```php
#[Middleware('auth')]
class OnboardingController extends Controller
{
    #[Authorize('update', 'profile')]
    public function update(UpdateOnboardingStepRequest $request, OnboardingProfile $profile) { … }
}
```

## Form Request — validation and authorization

**Rule:** `rules()` and `authorize()` are both mandatory. `toData()` is optional but encourages a
typed boundary.

```php
class StoreOnboardingRequest extends FormRequest
{
    public function authorize(): bool
    {
        return $this->user()->can('create', OnboardingProfile::class);
    }

    public function rules(): array
    {
        return [
            'name'  => ['required', 'string', 'max:120'],
            'email' => ['required', 'email', 'unique:users,email'],
            'goal'  => ['required', Rule::enum(OnboardingGoal::class)],
        ];
    }

    public function toData(): OnboardingData
    {
        return new OnboardingData(
            name: $this->string('name')->toString(),
            email: $this->string('email')->toString(),
            goal: OnboardingGoal::from($this->input('goal')),
        );
    }
}
```

Keep authorization here or in a policy — **not** in the controller, and never only in the route file.

## DTO — the boundary object

**Rule:** `final readonly`, constructor-promoted, no logic, no Eloquent.

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

A DTO is worth it when a value crosses 2+ layers, or when an action takes more than 2 arguments.
Otherwise pass the scalar.

## Action — one use case

**Rule:** one public entrypoint (`handle` or `__invoke`), dependencies injected, no HTTP concepts.

```php
class StartOnboarding
{
    public function __construct(private CompleteOnboarding $complete) {}

    public function handle(User $user, OnboardingData $data): OnboardingProfile
    {
        $profile = $user->onboardingProfile()->create([
            'goal' => $data->goal,
            'step' => OnboardingStep::Profile,
        ]);

        return $profile;
    }
}
```

Actions **may** orchestrate: call other actions, dispatch events, run a transaction. They may not
read `request()`, `session()`, or return a `Response`.

```php
public function handle(OrderData $data): Order
{
    return DB::transaction(function () use ($data) {
        $order = $this->createOrder->handle($data);
        $this->chargeCard->handle($order);
        OrderPlaced::dispatch($order);

        return $order;
    });
}
```

## Service — only when it is not one use case

**Rule:** use a service for a collaborator shared by several actions with **internal state or a
third-party client** (a gateway wrapper, a pricing engine). If it maps 1:1 to a use case, it is an
Action.

```php
class StripeGateway
{
    public function charge(Order $order): PaymentResultData { … }
}
```

## Model — data and relationships

**Rule:** casts, relations, scopes, accessors. No orchestration, no `Mail::`, no calls to actions.

```php
class Order extends Model
{
    protected $fillable = ['user_id', 'total_cents', 'status'];
    protected $casts = ['status' => OrderStatus::class, 'total_cents' => 'integer'];

    public function user(): BelongsTo { return $this->belongsTo(User::class); }

    public function scopePaid(Builder $q): Builder
    {
        return $q->where('status', OrderStatus::Paid);
    }
}
```

Money is a representation decision, not a rule. **Match what the app already stores** — an app with
`decimal(14,2)` and a `decimal:2` cast should get `decimal` for new tables, not integer cents, or you
have two money types and a conversion bug at every boundary. Integer cents are the better default
only for greenfield. Record whichever you pick. Never floats. Cast enums, never store raw strings for
a fixed set.

## Policy — authorization

**Rule:** one policy per model you authorize against. Controllers call `authorize()`, Form Requests
call `can()`, views call `@can`.

```php
class OnboardingProfilePolicy
{
    public function update(User $user, OnboardingProfile $profile): bool
    {
        return $user->id === $profile->user_id;
    }
}
```

## Enum — every fixed set

```php
enum OnboardingStep: string
{
    case Profile = 'profile';
    case Goals = 'goals';
    case Complete = 'complete';
}
```

## Resource — response shape

**Rule:** never return a raw model from an API. Resources are the contract.

```php
class OrderResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'status' => $this->status->value,
            'total_cents' => $this->total_cents,
        ];
    }
}
```

Laravel 13 adds JSON:API resources if you need spec compliance.

## Events, listeners, jobs, notifications

| Type | Use for |
| --- | --- |
| Event | Something happened that others may care about (`OrderPlaced`) |
| Listener | A reaction, queued if slow (`SendOrderConfirmation`) |
| Job | Work that must survive the request (`ReconcilePayment`) |
| Notification | A user-facing message over a channel (mail, SMS, database) |

Dispatch from an Action, not a controller. Anything doing network I/O in a request path should be
queued.

## Tests

- **Feature test per controller action** — the HTTP contract, validation, authorization, redirect.
- **Unit test per Action** with branching logic — no HTTP. Check whether `tests/Unit` actually boots
  the app first: in many projects only `tests/Feature` is bound to `Tests\TestCase`, so an Action that
  touches Eloquent fails there with a confusing "no application" error. Either bind the Actions
  subdirectory to the TestCase, move them to Feature, or keep Unit for pure logic only
  (`references/adapting-to-an-app.md`).
- Test the **failure** path: invalid input rejected, unauthorized user refused, gateway failure
  handled. Assert the refusal the way the app expresses it — a redirect plus a toast is not
  `assertForbidden()`, and the side-effect assertion ("no row written") proves the refusal happened
  before the write.

```php
it('rejects an invalid goal', function () {
    $this->actingAs(User::factory()->create())
        ->post(route('onboarding.store'), ['name' => 'A', 'email' => 'a@b.c', 'goal' => 'nope'])
        ->assertSessionHasErrors('goal');
});
```
