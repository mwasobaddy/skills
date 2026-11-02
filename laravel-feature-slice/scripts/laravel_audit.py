#!/usr/bin/env python3
"""Check a Laravel app for architectural drift.

    python3 laravel_audit.py /path/to/app
    python3 laravel_audit.py . --json report.json
    python3 laravel_audit.py --selftest

Flags thin-controller violations: inline validation, Eloquent writes in a
controller, raw Request injection, missing Form Request members, missing route
targets, Inertia/Livewire views that don't exist, and debug calls left in.

Exit code is 1 when an error exists, so it drops into CI.
"""
import argparse
import json
import os
import re
import sys
from collections import Counter

ERROR, WARN, INFO = "error", "warn", "info"

SKIP_DIRS = {"vendor", "node_modules", "storage", "bootstrap/cache", ".git",
             "public", "database/migrations"}


def service_inventory(root):
    """Classify public service methods as write use cases or read collaborators."""
    base = os.path.join(root, "app/Services")
    rows = []
    for path in php_files(root, "app/Services"):
        src = read(path)
        code = strip_php(src)
        methods = []
        for m in re.finditer(r"public\s+function\s+(\w+)\s*\(([^)]*)\)[^{;]*\{", code):
            name = m.group(1)
            start = m.end()
            depth, i = 1, start
            while i < len(code) and depth:
                if code[i] == "{":
                    depth += 1
                elif code[i] == "}":
                    depth -= 1
                i += 1
            body = code[start:i - 1]
            write = bool(re.search(
                r"\$this->(save|delete|transaction)\s*\(|::create\s*\(|->update\s*\(|"
                r"->delete\s*\(|->save\s*\(|::updateOrCreate\s*\(", body))
            methods.append({"method": name, "write": write,
                            "lines": body.count("\n") + 1})
        if methods:
            rows.append({"service": os.path.basename(path)[:-4],
                         "file": rel(root, path), "methods": methods})
    return rows


def print_inventory(rows):
    total_w = sum(1 for r in rows for m in r["methods"] if m["write"])
    total = sum(len(r["methods"]) for r in rows)
    print(f"\nservices: {len(rows)}   public methods: {total}   "
          f"write use cases: {total_w}   read/aggregate: {total - total_w}")
    print("\nwrite methods are Action candidates; read/aggregate methods stay in the service\n")
    for r in sorted(rows, key=lambda x: x["service"]):
        w = [m for m in r["methods"] if m["write"]]
        rd = len(r["methods"]) - len(w)
        if not w:
            print(f"  {r['service']:38} {len(r['methods']):2} read  (query service — leave it)")
            continue
        print(f"  {r['service']:38} {len(w):2} write / {rd:2} read")
        for m in w:
            print(f"      -> {m['method']:28} {m['lines']:3} lines")
    print()


# --------------------------------------------------------------------------- helpers
def strip_php(src):
    """Remove comments and string literals so code checks don't match prose."""
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if c == "/" and i + 1 < n and src[i + 1] == "/":
            j = src.find("\n", i)
            i = n if j < 0 else j
        elif c == "#" and not src.startswith("#[", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
        elif src.startswith("/*", i):
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
        elif c in "'\"":
            quote, j = c, i + 1
            while j < n:
                if src[j] == "\\":
                    j += 2
                    continue
                if src[j] == quote:
                    break
                j += 1
            i = j + 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def strip_comments(src):
    """Remove comments but keep string literals — needed for route and view names."""
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if c == "/" and i + 1 < n and src[i + 1] == "/":
            j = src.find("\n", i)
            i = n if j < 0 else j
        elif c == "#" and not src.startswith("#[", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
        elif src.startswith("/*", i):
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def method_bodies(code):
    """Map method name -> (body, param_string) using brace matching."""
    result = {}
    for m in re.finditer(r"function\s+(\w+)\s*\(([^)]*)\)[^{;]*\{", code):
        name, params = m.group(1), m.group(2)
        start = m.end()
        depth, i = 1, start
        while i < len(code) and depth:
            if code[i] == "{":
                depth += 1
            elif code[i] == "}":
                depth -= 1
            i += 1
        result[name] = (code[start:i - 1], params)
    return result


def php_files(root, sub):
    base = os.path.join(root, sub)
    out = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            if f.endswith(".php"):
                out.append(os.path.join(dirpath, f))
    return sorted(out)


def rel(root, path):
    return os.path.relpath(path, root)


def read(path):
    try:
        return open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return ""


# --------------------------------------------------------------------------- auditor
class Finding:
    __slots__ = ("severity", "rule", "file", "message", "fix")

    def __init__(self, severity, rule, file, message, fix=""):
        self.severity, self.rule, self.file = severity, rule, file
        self.message, self.fix = message, fix

    def as_dict(self):
        return {"severity": self.severity, "rule": self.rule, "file": self.file,
                "message": self.message, "fix": self.fix}


class LaravelAudit:
    CONTROLLER_WARN = 200
    CONTROLLER_ERROR = 400
    MODEL_WARN = 400
    ACTION_WARN = 200
    METHOD_WARN = 25

    def __init__(self, root):
        self.root = os.path.abspath(root)
        self.findings = []
        self.checked = 0

    def add(self, sev, rule, path, msg, fix=""):
        self.findings.append(Finding(sev, rule, path, msg, fix))

    # ---- controllers
    def controllers(self):
        for path in php_files(self.root, "app/Http/Controllers"):
            src = read(path)
            code = strip_php(src)
            r = rel(self.root, path)
            lines = src.count("\n") + 1
            self.checked += 1

            if lines > self.CONTROLLER_ERROR:
                self.add(ERROR, "controller-too-large", r, f"{lines} lines",
                         "Split by use case: one controller per resource, logic into Actions.")
            elif lines > self.CONTROLLER_WARN:
                self.add(WARN, "controller-too-large", r, f"{lines} lines",
                         "Move orchestration into Actions; controllers should only route a request.")

            if re.search(r"->validate\s*\(", code):
                self.add(ERROR, "inline-validation", r,
                         "$request->validate() in a controller",
                         "Extract to a Form Request. Validation in a controller cannot be reused "
                         "or unit-tested, and authorization has no home.")
            for pat, label in ((r"::create\s*\(", "::create()"),
                               (r"->save\s*\(", "->save()"),
                               (r"->update\s*\(", "->update()"),
                               (r"->delete\s*\(", "->delete()"),
                               (r"::updateOrCreate\s*\(", "::updateOrCreate()")):
                if re.search(pat, code):
                    self.add(WARN, "model-write-in-controller", r,
                             f"{label} called in a controller",
                             "Move the write into an Action. Controllers should not persist.")
                    break
            if re.search(r"\bDB::", code):
                self.add(WARN, "db-in-controller", r, "DB facade used in a controller",
                         "Move queries into a repository, Action, or query scope.")

            # Method-level checks: index/show legitimately take a raw Request for filters
            # and pagination, and write methods should take a Form Request instead.
            GET_METHODS = {"index", "show", "create", "edit"}
            # `Request` must be the whole type name. Without the boundary, "UpdateFooRequest
            # $request" matches, which flags exactly the Form Requests this skill tells you
            # to write.
            RAW_REQUEST = re.compile(r"(?<![A-Za-z0-9_\\])\\?Request\s+\$request")
            for name, (body, params) in method_bodies(code).items():
                if RAW_REQUEST.search(params) and name not in GET_METHODS:
                    self.add(WARN, "raw-request-parameter", r,
                             f"{name}() takes a raw Illuminate\\Http\\Request",
                             "Type-hint a Form Request instead; it carries rules and authorize().")
                size = body.count("\n") + 1
                if name in GET_METHODS:
                    continue  # list endpoints with filters legitimately run longer
                if size > self.METHOD_WARN and name != "__construct":
                    self.add(WARN, "method-too-large", r,
                             f"{name}() is {size} lines",
                             "A controller method should call an Action and return a response.")

    # ---- form requests
    def form_requests(self):
        for path in php_files(self.root, "app/Http/Requests"):
            src = read(path)
            code = strip_php(src)
            r = rel(self.root, path)
            self.checked += 1
            if "FormRequest" not in src:
                continue
            if not re.search(r"function\s+authorize\s*\(", code):
                self.add(WARN, "formrequest-no-authorize", r,
                         "Form Request has no authorize()",
                         "Declare who may submit this form. Silently defaulting to true hides "
                         "authorization in controllers or, worse, in the route file.")
            if not re.search(r"function\s+rules\s*\(", code):
                self.add(ERROR, "formrequest-no-rules", r,
                         "Form Request has no rules()",
                         "A Form Request without rules validates nothing.")
            m = re.search(r"function\s+authorize\s*\([^)]*\)[^{]*\{\s*return\s+true\s*;", code)
            if m:
                self.add(INFO, "authorize-always-true", r,
                         "authorize() always returns true",
                         "Fine for public forms. Otherwise delegate to a policy.")

    # ---- models
    def models(self):
        for path in php_files(self.root, "app/Models"):
            src = read(path)
            code = strip_php(src)
            r = rel(self.root, path)
            self.checked += 1
            lines = src.count("\n") + 1
            if lines > self.MODEL_WARN:
                self.add(WARN, "model-too-large", r, f"{lines} lines",
                         "Extract query scopes, casts, or related logic into Actions or dedicated classes.")
            if re.search(r"\bDB::", code):
                self.add(WARN, "db-in-model", r, "DB facade used in a model",
                         "Prefer Eloquent and query scopes; raw DB rows bypass casts and events.")

    # ---- actions / services
    def actions(self):
        for sub in ("app/Actions", "app/Services"):
            for path in php_files(self.root, sub):
                src = read(path)
                code = strip_php(src)
                r = rel(self.root, path)
                # Traits under Concerns/ hold shared helpers, not use cases. They have
                # no entrypoint by design and are not Actions.
                if re.search(r"^\s*trait\s+\w+", code, re.M) or "/Concerns/" in r.replace("\\", "/"):
                    continue
                self.checked += 1
                lines = src.count("\n") + 1
                if lines > self.ACTION_WARN:
                    self.add(WARN, "action-too-large", r, f"{lines} lines",
                             "An action should do one thing. Split it or compose smaller actions.")
                if sub.endswith("Actions") and not re.search(
                        r"function\s+(execute|handle|__invoke)\s*\(", code):
                    self.add(WARN, "action-no-entrypoint", r,
                             "no execute()/handle()/__invoke() entrypoint",
                             "Give each action one public entrypoint so its contract is obvious.")

    # ---- app-wide code hygiene
    def app_hygiene(self):
        for path in php_files(self.root, "app"):
            src = read(path)
            code = strip_php(src)
            r = rel(self.root, path)
            if re.search(r"(?<![A-Za-z_])env\s*\(", code):
                self.add(ERROR, "env-outside-config", r,
                         "env() called outside config/",
                         "env() returns null once config is cached. Read config('x.y') instead.")
            m = re.search(r"(?<![A-Za-z_])(dd|dump|var_dump|ray)\s*\(", code)
            if m:
                self.add(ERROR, "debug-left-in", r, f"{m.group(1)}() left in application code",
                         "Remove it. It dumps data to the response or a log in production.")

    # ---- routes
    def routes(self):
        route_files = []
        for sub in ("routes",):
            base = os.path.join(self.root, sub)
            if os.path.isdir(base):
                route_files += [os.path.join(base, f) for f in sorted(os.listdir(base))
                                if f.endswith(".php")]
        pat = re.compile(
            r"Route::(get|post|put|patch|delete|resource|apiResource)\s*\(\s*['\"][^'\"]*['\"]\s*,"
            r"\s*(?:\[\s*)?([A-Za-z_][A-Za-z0-9_\\]*)::class"
            r"(?:\s*,\s*['\"](\w+)['\"])?")
        for path in route_files:
            raw = read(path)
            src = strip_comments(raw)
            r = rel(self.root, path)
            # Route files reference imported short names (RegisterController::class),
            # so resolve `use` imports before looking for the class on disk.
            uses = {}
            for u in re.finditer(
                    r"^use\s+([A-Za-z_\\][A-Za-z0-9_\\]*)(?:\s+as\s+(\w+))?\s*;", src, re.M):
                fq = u.group(1).lstrip("\\")
                uses[u.group(2) or fq.split("\\")[-1]] = fq
            for m in pat.finditer(src):
                verb, cls, method = m.groups()
                fqcn = cls.lstrip("\\")
                if "\\" not in fqcn:
                    fqcn = uses.get(fqcn, f"App\\Http\\Controllers\\{fqcn}")
                target = os.path.join(self.root, fqcn.replace("\\", "/") + ".php")
                if not os.path.exists(target):
                    self.add(ERROR, "route-target-missing", r,
                             f"route points at {fqcn}, which has no file",
                             "Fix the class name or create the controller.")
                    continue
                if method:
                    code = strip_php(read(target))
                    if not re.search(r"function\s+%s\s*\(" % re.escape(method), code):
                        self.add(ERROR, "route-target-missing", r,
                                 f"{fqcn} has no {method}()",
                                 "The route resolves to a method that does not exist.")

    # ---- Inertia pages
    def inertia(self):
        roots = [os.path.join(self.root, "resources/js/pages"),
                 os.path.join(self.root, "resources/js/Pages")]
        exts = (".tsx", ".jsx", ".vue", ".svelte")
        for path in php_files(self.root, "app"):
            code = strip_comments(read(path))
            for m in re.finditer(r"Inertia::render\s*\(\s*['\"]([^'\"]+)['\"]", code):
                page = m.group(1)
                found = False
                for base in roots:
                    for cand in (page, page.lower(), page[0].lower() + page[1:]):
                        # Inertia resolves `a/b` to either a/b.tsx or a/b/index.tsx
                        if any(os.path.exists(os.path.join(base, cand + e)) for e in exts) or \
                           any(os.path.exists(os.path.join(base, cand, "index" + e)) for e in exts):
                            found = True
                            break
                    if found:
                        break
                if not found:
                    self.add(ERROR, "inertia-page-missing", rel(self.root, path),
                             f"Inertia::render('{page}') has no page component",
                             f"Expected resources/js/pages/{page}.(tsx|jsx|vue|svelte).")

    # ---- Livewire views
    def livewire(self):
        for path in php_files(self.root, "app"):
            code = strip_comments(read(path))
            for m in re.finditer(r"view\s*\(\s*['\"](livewire[^'\"]*)['\"]", code):
                view = m.group(1)
                target = os.path.join(self.root, "resources/views", view.replace(".", "/") + ".blade.php")
                if not os.path.exists(target):
                    self.add(ERROR, "livewire-view-missing", rel(self.root, path),
                             f"view('{view}') has no Blade file",
                             f"Expected resources/views/{view.replace('.', '/')}.blade.php.")

    # ---- tests
    def tests(self):
        tests_dir = os.path.join(self.root, "tests")
        if not os.path.isdir(tests_dir):
            return
        corpus = []
        for dirpath, dirnames, filenames in os.walk(tests_dir):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for f in filenames:
                if f.endswith(".php"):
                    corpus.append(read(os.path.join(dirpath, f)))
        blob = "\n".join(corpus).lower()
        for path in php_files(self.root, "app/Http/Controllers"):
            name = os.path.basename(path)[:-4]
            stem = name[:-10] if name.endswith("Controller") else name
            if not stem:
                continue
            if stem.lower() not in blob and name.lower() not in blob:
                self.add(INFO, "missing-feature-test", rel(self.root, path),
                         f"no test references {stem}",
                         "Feature tests are the primary test type in Laravel; one per action is a "
                         "reasonable floor.")

    def run(self):
        if not os.path.isdir(self.root):
            return []
        self.controllers()
        self.form_requests()
        self.models()
        self.actions()
        self.app_hygiene()
        self.routes()
        self.inertia()
        self.livewire()
        self.tests()
        return self.findings


# --------------------------------------------------------------------------- report
def report(findings, checked, out_json=None, baseline=None, fail_on_new=False):
    order = {ERROR: 0, WARN: 1, INFO: 2}
    findings = sorted(findings, key=lambda f: (order[f.severity], f.rule, f.file))
    counts = Counter(f.severity for f in findings)
    errors, warns = counts.get(ERROR, 0), counts.get(WARN, 0)
    score = max(0, 100 - 8 * errors - 2 * warns)

    print(f"\nfiles checked: {checked}")
    print(f"score: {score}/100   errors: {errors}   warnings: {warns}   info: {counts.get(INFO, 0)}")

    delta = None
    if baseline:
        base = {(b["rule"], b["file"]): b["severity"]
                for b in baseline.get("findings", [])}
        now = {(f.rule, f.file): f.severity for f in findings}
        new = {k: v for k, v in now.items() if k not in base}
        fixed = {k: v for k, v in base.items() if k not in now}
        new_err = sum(1 for v in new.values() if v == ERROR)
        new_warn = sum(1 for v in new.values() if v == WARN)
        fixed_err = sum(1 for v in fixed.values() if v == ERROR)
        fixed_warn = sum(1 for v in fixed.values() if v == WARN)
        delta = {"introduced_errors": new_err, "introduced_warnings": new_warn,
                 "resolved_errors": fixed_err, "resolved_warnings": fixed_warn,
                 "introduced": [{"rule": r, "file": f} for (r, f) in sorted(new)]}
        print(f"\nvs baseline   introduced: {new_err} errors, {new_warn} warnings"
              f"    resolved: {fixed_err} errors, {fixed_warn} warnings")
        print("  (score is absolute and floors on legacy debt; the delta is the progress signal)")

    if not findings:
        print("\nno findings\n")

    current = None
    for f in findings:
        if f.severity != current:
            current = f.severity
            print(f"\n{f.severity.upper()}S")
        print(f"  [{f.severity.upper()[:4]}] {f.rule:28} {f.file}")
        print(f"         {f.message}")
        if f.fix:
            print(f"         fix: {f.fix}")

    if out_json:
        payload = {"score": score, "files_checked": checked, "counts": dict(counts),
                   "findings": [f.as_dict() for f in findings]}
        if delta:
            payload["delta"] = delta
        json.dump(payload, open(out_json, "w"), indent=1)
        print(f"\nwrote {out_json}")
    print()

    if fail_on_new:
        return 1 if (delta and delta["introduced_errors"]) else 0
    return 1 if errors else 0


# --------------------------------------------------------------------------- selftest
FAT_CONTROLLER = """<?php
namespace App\\Http\\Controllers;

use Illuminate\\Http\\Request;

class RegistrationController extends Controller
{
    public function store(Request $request)
    {
        $data = $request->validate([
            'name' => 'required',
            'email' => 'required|email',
        ]);
        $user = \\App\\Models\\User::create($data);
        $user->save();
        dd($user);
        $token = env('SECRET');
        return \\Inertia\\Inertia::render('Auth/MissingPage');
    }
}
"""

GOOD_FORM_REQUEST = """<?php
namespace App\\Http\\Requests\\Auth;

use Illuminate\\Foundation\\Http\\FormRequest;

class StoreRegistrationRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return ['name' => ['required']];
    }
}
"""

BAD_FORM_REQUEST = """<?php
namespace App\\Http\\Requests\\Auth;

use Illuminate\\Foundation\\Http\\FormRequest;

class StoreBadRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }
}
"""

GOOD_CONTROLLER = """<?php
namespace App\\Http\\Controllers\\Auth;

use App\\Http\\Requests\\Auth\\StoreRegistrationRequest;

class RegisterController extends Controller
{
    public function store(StoreRegistrationRequest $request)
    {
        return redirect()->route('dashboard');
    }
}
"""

ROUTES_BAD = """<?php
use Illuminate\\Support\\Facades\\Route;
use App\\Http\\Controllers\\Auth\\RegisterController;

Route::post('/register', [RegisterController::class, 'missingMethod']);
Route::get('/ghost', [App\\Http\\Controllers\\GhostController::class, 'index']);
"""

# A read endpoint legitimately takes a raw Request (filters, pagination) and runs long.
GET_CONTROLLER = """<?php
namespace App\\Http\\Controllers;

use Illuminate\\Http\\Request;

class ListController extends Controller
{
    public function index(Request $request)
    {
        $rows = ['a', 'b', 'c'];
        return response()->json(['rows' => $rows, 'page' => $request->query('page')]);
    }
}
"""


def selftest():
    import tempfile
    ok = True
    with tempfile.TemporaryDirectory() as root:
        def put(relpath, content):
            p = os.path.join(root, relpath)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "w", encoding="utf-8").write(content)

        put("app/Http/Controllers/RegistrationController.php", FAT_CONTROLLER)
        put("app/Http/Requests/Auth/StoreRegistrationRequest.php", GOOD_FORM_REQUEST)
        put("app/Http/Requests/Auth/StoreBadRequest.php", BAD_FORM_REQUEST)
        put("routes/web.php", ROUTES_BAD)
        put("tests/Feature/RegisterTest.php", "<?php test('x', fn () => true);")

        findings = LaravelAudit(root).run()
        rules = {f.rule for f in findings}
        must_fire = {"inline-validation", "model-write-in-controller", "raw-request-parameter",
                     "debug-left-in", "env-outside-config", "inertia-page-missing",
                     "route-target-missing", "formrequest-no-rules"}
        if must_fire - rules:
            print(f"FAIL: did not fire: {sorted(must_fire - rules)}")
            ok = False
        if "formrequest-no-authorize" in rules:
            print("FAIL: flagged a Form Request that has authorize()")
            ok = False

        # The regex must match `Request` as a whole type, not `FooRequest`. Flagging a Form
        # Request would penalise exactly what the skill instructs you to write.
        raw = [f for f in findings if f.rule == "raw-request-parameter"]
        if len(raw) != 1 or "RegistrationController" not in raw[0].file:
            print(f"FAIL: raw-request-parameter hit {[f.file for f in raw]} — expected only the "
                  f"controller with a true Illuminate Request")
            ok = False

    with tempfile.TemporaryDirectory() as root:
        def put2(relpath, content):
            p = os.path.join(root, relpath)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "w", encoding="utf-8").write(content)

        put2("app/Http/Controllers/Auth/RegisterController.php", GOOD_CONTROLLER)
        put2("app/Http/Controllers/ListController.php", GET_CONTROLLER)
        put2("app/Http/Requests/Auth/StoreRegistrationRequest.php", GOOD_FORM_REQUEST)
        put2("routes/web.php",
             "<?php\nuse App\\Http\\Controllers\\Auth\\RegisterController;\n"
             "Route::post('/register', [RegisterController::class, 'store']);")
        findings = LaravelAudit(root).run()
        clean = [f for f in findings if f.severity == ERROR]
        if clean:
            print(f"FAIL: clean fixture produced errors: {[f.rule for f in clean]}")
            ok = False
        noise = [f for f in findings
                 if f.rule in ("raw-request-parameter", "method-too-large")]
        if noise:
            print(f"FAIL: clean fixture flagged {[(f.rule, f.file) for f in noise]} — "
                  f"a Form Request hint and a GET index must both be accepted")
            ok = False

    print("selftest:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", nargs="?", help="Laravel application root")
    ap.add_argument("--json", help="write a machine-readable report")
    ap.add_argument("--baseline", help="previous --json report; prints introduced/resolved counts")
    ap.add_argument("--fail-on-new", action="store_true",
                    help="with --baseline, fail only when a NEW error is introduced")
    ap.add_argument("--services", action="store_true",
                    help="inventory app/Services and classify methods as Action candidates")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if not args.path:
        ap.error("give the Laravel app root, or use --selftest")
    if not os.path.isdir(os.path.join(args.path, "app")):
        print(f"error: no app/ directory in {args.path} — is this a Laravel root?", file=sys.stderr)
        return 2

    baseline = None
    if args.baseline:
        try:
            baseline = json.load(open(args.baseline))
        except Exception as e:
            print(f"error: cannot read baseline {args.baseline}: {e}", file=sys.stderr)
            return 2

    auditor = LaravelAudit(args.path)
    if args.services:
        print_inventory(service_inventory(args.path))
        return 0
    return report(auditor.run(), auditor.checked, args.json, baseline, args.fail_on_new)


if __name__ == "__main__":
    sys.exit(main())
