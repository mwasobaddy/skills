# Starter kits: detect, then branch

The kit decides where the **frontend tail** of a feature goes. Detection is runtime, per project —
never assume, and never infer from a folder name.

## Detect the stack

```bash
grep -E '"(inertiajs/inertia-laravel|livewire/livewire)"' composer.json
grep -E '"(@inertiajs/react|@inertiajs/vue3|@inertiajs/svelte)"' package.json

ls resources/js/pages 2>/dev/null      # Inertia pages
ls resources/views/pages 2>/dev/null   # Livewire 4 full-page components
ls app/Livewire 2>/dev/null            # class-based Livewire, if any
```

Confirm against existing files before writing. The project's format beats any default here, and
Livewire's `config/livewire.php` can change component locations, namespaces, and the `⚡` prefix.

| Detected | Read |
| --- | --- |
| Inertia with React, Vue, or Svelte | `references/inertia.md` |
| Livewire | `references/livewire.md` |

A project can have both — a Livewire app with a plain controller, or an Inertia app with one Livewire
island. Match the surrounding feature; never mix two frontends inside one feature.

## Auth in every starter kit

All official kits ship **Laravel Fortify**. Login, registration, password reset, and email
verification already exist; the customisable actions are in `app/Actions/Fortify`:

- `CreateNewUser` — registration
- `ResetUserPassword` — password reset
- `PasswordValidationRules` — shared password rules

Change behaviour there and in `config/fortify.php`. A second `LoginController` duplicates the
framework and splits the rules and the rate limiting.

## Dual validation

Server-side validation is the only authority. Client-side validation is UX and must mirror it.

| Concern | Server | Client |
| --- | --- | --- |
| Required fields | `rules()` | same field required |
| Format | `email`, `regex`, `Rule::enum` | mirrors it |
| Uniqueness | `unique:` | not duplicated — needs a request |
| Authorization | `authorize()` / policy | hide the control; never rely on it |
| Errors | 422 + field errors | field-level messages |

Define the rules **once, server-side**. Where a Form Request and a Livewire component validate the
same fields, put the rule set in an `app/Concerns` trait and consume it from both — the starter kits
already do this for profile rules. Business validation never moves to JavaScript.
