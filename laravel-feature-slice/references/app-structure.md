# Application structure: what each directory is for

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

## Do not create

- `app/Repositories` — Eloquent is already the data layer
- a service that wraps one model — that is an Action with a worse name
- a DTO for a single scalar
- an interface per Action unless a test must swap it
- a `BaseController` of helpers
- a `Concerns` trait used by one class
