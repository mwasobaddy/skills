# Starter kits and dual validation

The starter kits decide where frontend files go. The validation rule is the same for all of them.

## The dual-validation contract

Server-side validation is the **only** authority. Client-side validation exists to give fast feedback
and must mirror the server rules, never replace them.

| Concern | Server | Client |
| --- | --- | --- |
| Required fields | `rules()` | same field required |
| Format | `email`, `regex`, `Rule::enum` | mirrors it |
| Uniqueness | `unique:` | not duplicated — needs a request |
| Authorization | `authorize()` / policy | hide the control, but never rely on it |
| Error display | 422 + field errors | field-level messages |

**Define the rules once, server-side.** The client copy is a UX affordance; if the two drift, the
server is right and the client is a bug. Do not implement business validation in JavaScript.

---

## Auth in every starter kit

All starter kits use **Laravel Fortify**. Login, registration, password reset, and email
verification already exist, and the customisable actions are in `app/Actions/Fortify`:

- `CreateNewUser` — registration
- `ResetUserPassword` — password reset
- `PasswordValidationRules` — the shared password rule set

Change behaviour by editing those and `config/fortify.php`. Registering a second `LoginController`
duplicates the framework and splits the rules in two.

---

## React starter kit (Inertia 3, React 19, TypeScript)

```
resources/js/
├── components/     # reusable, presentational
├── hooks/          # data + form logic
├── layouts/        # shell, nav
├── lib/            # utils, route helpers (Wayfinder)
├── pages/          # one file per Inertia::render target
└── types/          # mirrors DTOs
```

Server renders the page, so this is not a client-rendered SPA:

```php
return Inertia::render('onboarding/wizard', [
    'steps' => OnboardingStep::cases(),
    'profile' => new OnboardingProfileResource($profile),
]);
```

Form with mirrored validation:

```tsx
import { useForm } from '@inertiajs/react';

const { data, setData, post, processing, errors } = useForm({
  name: '',
  email: '',
  goal: '',
});

const submit = (e) => {
  e.preventDefault();
  post('/onboarding');           // 422 populates `errors`
};
```

Rules:

- The page file path must match the `Inertia::render` string exactly (`onboarding/wizard` →
  `resources/js/pages/onboarding/wizard.tsx`). A mismatch is a blank screen, not an error.
- Types in `resources/js/types` mirror the **DTO**, not the database row.
- Never `fetch()` the data a page needs — pass it as props from the controller.
- Use Wayfinder's typed route helpers rather than hardcoded URLs where available.

## Vue and Svelte starter kits (Inertia)

Identical structure and identical rules; only the component syntax changes.

```vue
<script setup lang="ts">
import { useForm } from '@inertiajs/vue3';
const form = useForm({ name: '', email: '', goal: '' });
</script>
```

Page directory is `resources/js/pages`; extensions are `.vue` and `.svelte`.

## Livewire starter kit (Livewire 4, Flux UI)

```
resources/views/
├── components/
├── flux/
├── layouts/
├── pages/          # Livewire pages
└── partials/
```

Validation lives in the component, and `FormRequest` applies only to any plain controller endpoints
you add alongside it:

```php
namespace App\Livewire\Onboarding;

use Livewire\Component;
use Livewire\Attributes\Validate;

class Wizard extends Component
{
    #[Validate('required|string|max:120')]
    public string $name = '';

    #[Validate('required|email')]
    public string $email = '';

    public function submit()
    {
        $this->validate();                    // server-side, always

        $this->dispatch('onboarding-started');

        return redirect()->route('onboarding.show');
    }

    public function render()
    {
        return view('livewire.onboarding.wizard');
    }
}
```

Rules:

- `wire:model` gives instant binding; `wire:model.live` only where you need live server round-trips.
- `$this->validate()` before every write. Never trust the client state — it is editable.
- Validation errors surface automatically; do not hand-roll an `errors` array.
- Views must exist at `resources/views/livewire/...`, or the component renders nothing.
- For complex rule sets use a form object (`Livewire\Form`) rather than 20 public properties.

---

## Choosing which to write

| Situation | Frontend to produce |
| --- | --- |
| Project uses Inertia React | `resources/js/pages/**` + `types/**` |
| Project uses Inertia Vue/Svelte | same, with `.vue`/`.svelte` |
| Project uses Livewire | `app/Livewire/**` + `resources/views/pages|livewire/**` |
| Project has both | match the surrounding feature, never mix within one feature |

Detect from `composer.json` (`livewire/livewire`, `inertiajs/inertia-laravel`) and `package.json`
(`@inertiajs/react`, `@inertiajs/vue3`, `@inertiajs/svelte`). Do not guess from the folder name.
