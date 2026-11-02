# Livewire starter kit

The official kit is Livewire 4 + Flux 2 + Tailwind 4 + Fortify, with single-file components as the
default. Detect with `references/starter-kits.md`.

## Component formats

| Format | Files |
| --- | --- |
| Single-file (default) | `resources/views/components/{name}.blade.php` — class and template in one file |
| Full page | `resources/views/pages/{name}.blade.php` |
| Multi-file | `resources/views/components/{name}/{name}.php` + `.blade.php` |
| Class-based (v3 style) | `app/Livewire/{Name}.php` + `resources/views/livewire/{name}.blade.php` |

Names may carry a `⚡` prefix depending on `config/livewire.php`. **Match the files already in the
project** — format, prefix, and locations — rather than the default. Boost's `livewire-development`
skill owns `make:livewire`, conversions, and the component syntax; do not repeat it here.

## Page and route

A page is a full-page component plus a `Route::livewire()` entry:

```php
Route::livewire('settings/profile', 'pages::settings.profile')->name('profile.edit');
```

`pages::settings.profile` resolves to `resources/views/pages/settings/profile.blade.php`. A page with
no state can stay a plain `Route::view()`.

## Write path

There is no controller and no Form Request for a page write. The component method is the entrypoint:

```php
new class extends Component
{
    use ProfileValidationRules;

    public string $name = '';

    public function save(UpdateProfile $updateProfile): void
    {
        $validated = $this->validate($this->profileRules(auth()->id()));

        $updateProfile->handle(auth()->user(), $validated);

        Flux::toast(variant: 'success', text: __('Profile updated.'));
    }
};
```

- `$this->validate()` before every write. Public properties are client-editable; the server is the
  only authority.
- Rules used by more than one entrypoint belong in an `app/Concerns` trait. The kit shares
  `ProfileValidationRules` between a Livewire component and the Form Request used by any plain
  controller.
- `#[Validate]` is fine for one or two simple fields. Use a Livewire form object for a large rule
  set; do not create twenty public properties.
- Authorization uses the same policies and `authorize()` calls as a controller.

## UI

Flux components (`flux:input`, `flux:button`, `flux:modal`) and Tailwind. `wire:model` is deferred by
default; add `.live` only where the server must react per keystroke. Put `wire:key` in every loop.
Directive and component details belong to Boost's `livewire-development` skill.

## Tests

A Livewire feature has two seams:

```php
$this->actingAs($user)->get(route('profile.edit'))->assertOk();

Livewire::test('pages::settings.profile')
    ->set('name', 'Test User')
    ->call('save')
    ->assertHasNoErrors();
```

Assert the database after the interaction. The HTTP test proves the page renders and authorization
runs; the Livewire test proves the state change.

## Rules

- Do not add `app/Livewire` or `resources/views/livewire` to a kit that does not already use them.
- Do not duplicate rules between a component and a Form Request — share the trait.
- One component can be the page, the form, and the entrypoint; do not add a controller for it.
- Mixing SFC and class-based components inside one feature is a bug.
