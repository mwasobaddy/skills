# Layers: what each file is for

One rule per layer, then the code. If a rule and the code disagree, the rule wins.

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

Money as integer cents. Never floats. Cast enums, never store raw strings for a fixed set.

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
- **Unit test per Action** with branching logic — no HTTP, no container.
- Test the **failure** path: invalid input rejected, unauthorized user forbidden, gateway failure
  handled.

```php
it('rejects an invalid goal', function () {
    $this->actingAs(User::factory()->create())
        ->post(route('onboarding.store'), ['name' => 'A', 'email' => 'a@b.c', 'goal' => 'nope'])
        ->assertSessionHasErrors('goal');
});
```
