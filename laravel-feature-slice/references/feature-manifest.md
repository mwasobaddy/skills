# The feature manifest

For any feature, work **data → domain → interface → presentation → tests**. Each layer's contract
decides the shape of the next, so building the page first guarantees a rewrite.

The failure this prevents: an agent writes one 300-line controller with `$request->validate()`,
five `User::create()` calls, and a page. Everything below is the alternative, in order.

---

## Build order

| # | Layer | You produce | Why it comes first |
| --- | --- | --- | --- |
| 1 | Migration | Table, columns, indexes, FKs | Every other decision depends on the shape of the data |
| 2 | Model | Casts, relations, scopes, `$fillable` | Defines the vocabulary |
| 3 | Enums | Backed enums for any fixed set | Kills magic strings before they spread |
| 4 | DTO | `final readonly` data object | The contract between request and action |
| 5 | Form Request | `rules()` + `authorize()` | Server-side validation and authorization |
| 6 | Actions | One class per use case | The only place business logic lives |
| 7 | Policy | `viewAny/view/create/update/delete` | Authorization, separate from validation |
| 8 | Controller | 1–15 line methods | Routes the request; contains no logic |
| 9 | Route | Named route | The public URL contract |
| 10 | Resource | API/JSON:API serialization | Shapes the response |
| 11 | Frontend types | TypeScript/Livewire props | Mirrors the DTO, not the DB |
| 12 | Frontend pages | Form with matching validation | Consumes the contract |
| 13 | Tests | Feature per action, unit per action class | Proves the slice |

---

## Worked example: login

**This is mostly configuration, not new files.** The starter kits ship Laravel Fortify, which
already registers the login, registration, password reset, and email verification routes and
handles them with actions in `app/Actions/Fortify`. Creating your own `LoginController` duplicates
Fortify and is the single most common wrong turn here.

| File | Action |
| --- | --- |
| `config/fortify.php` | Toggle features (2FA, registration, email verification) |
| `app/Actions/Fortify/CreateNewUser.php` | Customize registration (fields, defaults, role assignment) |
| `app/Actions/Fortify/ResetUserPassword.php` | Customize password reset |
| `app/Actions/Fortify/PasswordValidationRules.php` | Shared password rules — the one place to change them |
| `app/Providers/FortifyServiceProvider.php` | Rate limiter, view bindings, login response |
| `resources/js/pages/auth/login.tsx` *(React/Vue/Svelte)* | Use the existing page; adjust fields only |
| `resources/views/livewire/auth/login.blade.php` *(Livewire)* | Same |
| `tests/Feature/Auth/AuthenticationTest.php` | Extend the shipped test |

Create a `LoginController` **only** when you are not using Fortify.

---

## Worked example: onboarding flow

Full slice, assuming a multi-step wizard.

```
database/migrations/2026_01_01_000000_create_onboarding_profiles_table.php
app/Models/OnboardingProfile.php
app/Enums/OnboardingStep.php                  # backed enum: Profile, Goals, Complete
app/Enums/OnboardingGoal.php
app/Data/Onboarding/OnboardingData.php        # final readonly DTO
app/Data/Onboarding/OnboardingStepData.php
app/Http/Requests/Onboarding/StoreOnboardingRequest.php
app/Http/Requests/Onboarding/UpdateOnboardingStepRequest.php
app/Actions/Onboarding/StartOnboarding.php
app/Actions/Onboarding/SaveOnboardingStep.php
app/Actions/Onboarding/CompleteOnboarding.php
app/Policies/OnboardingProfilePolicy.php
app/Http/Controllers/Onboarding/OnboardingController.php
app/Http/Resources/Onboarding/OnboardingProfileResource.php
routes/web.php                                 # Route::resource or explicit verbs
resources/js/types/onboarding.ts               # mirrors OnboardingData
resources/js/pages/onboarding/wizard.tsx
resources/js/components/onboarding/step-form.tsx
resources/js/hooks/use-onboarding.ts
tests/Feature/Onboarding/OnboardingFlowTest.php
tests/Unit/Actions/Onboarding/CompleteOnboardingTest.php
```

Livewire replaces the last four `resources/js/*` entries with:

```
resources/views/pages/onboarding/wizard.blade.php
resources/views/livewire/onboarding/step-form.blade.php
app/Livewire/Onboarding/Wizard.php
app/Livewire/Onboarding/StepForm.php
```

---

## Worked example: order with payment

```
database/migrations/..._create_orders_table.php
database/migrations/..._create_payments_table.php
app/Models/Order.php
app/Models/Payment.php
app/Enums/OrderStatus.php
app/Enums/PaymentStatus.php
app/Data/Orders/CreateOrderData.php
app/Data/Payments/PaymentResultData.php
app/Http/Requests/Orders/StoreOrderRequest.php
app/Actions/Orders/CreateOrder.php
app/Actions/Payments/ChargeCard.php
app/Actions/Payments/RefundPayment.php
app/Events/OrderPlaced.php
app/Listeners/SendOrderConfirmation.php
app/Jobs/ReconcilePayment.php
app/Notifications/OrderConfirmed.php
app/Policies/OrderPolicy.php
app/Http/Controllers/Orders/OrderController.php
app/Http/Resources/Orders/OrderResource.php
tests/Feature/Orders/CreateOrderTest.php
tests/Unit/Actions/Payments/ChargeCardTest.php
```

External calls (Stripe, mail, queues) belong in an **Action** or a **Job**, never in the controller.
If the call can fail, it needs a failure path and a test for it.

---

## What not to create

An agent over-correcting produces a different mess. Do not generate:

| Anti-pattern | Why |
| --- | --- |
| A repository per model | Eloquent is already the data abstraction. Repositories earn their place only when swapping storage. |
| A service that wraps one model | `UserService::create()` is an Action with a misleading name. |
| A DTO for a single scalar | `CreateOrderData(int $id)` adds a file and no clarity. |
| A validation service | Laravel's validator and Form Requests already are that. |
| `BaseController` with helpers | Becomes a dumping ground. Use traits deliberately. |
| An interface for every Action | Useful only when a test needs to swap the implementation. |
| A `LoginController` over Fortify | Duplicates the framework. |
| Enums as string constants classes | Use backed enums; they cast on models. |

---

## Per-feature checklist

Before declaring a feature done:

- [ ] Migration with the right indexes and FK constraints
- [ ] Model with `$fillable`/`$guarded`, casts, relations
- [ ] Enums for every fixed set of values
- [ ] Form Request with `rules()` **and** `authorize()`
- [ ] Frontend validation mirroring the server rules, with field-level errors
- [ ] At least one Action per write path
- [ ] The right authorization tier: sub-permission for org-scoped actions, policy for record-level, platform role only for operator surfaces (`references/authorization.md`)
- [ ] Controller methods under 15 lines, no `validate()`, no `::create()`
- [ ] Named routes
- [ ] Resource if the endpoint returns JSON
- [ ] Feature test hitting the HTTP route
- [ ] Unit test for any Action with branching logic
- [ ] Both success and failure paths tested
