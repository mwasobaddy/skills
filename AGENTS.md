# AGENTS.md — Rules for this skills repository

This folder is a **collection of Agent Skills**. All skills live in this one repository and
are installed individually.

Follow these rules for any work in this folder. They override default habits.

> **Read [PITFALLS.md](PITFALLS.md) before writing or changing any script.** Every entry
> there is a bug that actually shipped in this repo. Most were invisible to code review and
> only surfaced when the script was actually run.

---

## 1. What a skill is

A skill is a directory containing a `SKILL.md` file: YAML frontmatter + Markdown
instructions. It follows the open [Agent Skills](https://agentskills.io/specification)
standard, so it loads in Claude Code, opencode, Codex, Cursor, and any compatible client.

```
<skill-name>/
├── SKILL.md        # REQUIRED — frontmatter + instructions
├── README.md       # human-facing: what it does, how to install
├── LICENSE         # MIT
├── references/     # optional — detail loaded on demand
├── scripts/        # optional — executable code
└── assets/         # optional — templates, images, data
```

### Frontmatter — the only 6 portable fields

```yaml
---
name: skill-name              # required, must match folder name
description: ...              # required, max 1024 chars
license: MIT                  # optional
compatibility: ...            # optional, max 500 chars
metadata:                     # optional, string->string map
  author: mwasobaddy
  version: "1.0"
allowed-tools: Read Grep      # optional, space-separated
---
```

**Only these 6 fields.** Anything else (`disable-model-invocation`, `argument-hint`,
`model`, `context`, `paths`, …) is a Claude Code extension. Adding one breaks
`skills-ref validate` and fails packaging on other clients. If a feature is only
available in Claude Code, put it in the Markdown body and note it there instead.

Field rules:

| Field | Rule |
| --- | --- |
| `name` | 1–64 chars, `a-z0-9-` only, no leading/trailing/double hyphen, **must equal the folder name** |
| `description` | 1–1024 chars. Must state *what it does* AND *when to use it* |
| `metadata` | Flat `string: string`. Quote versions (`version: "1.0"`), unquoted becomes a float |

---

## 2. Naming convention

Folder name **is** the skill name **is** the `/command` name. There is one source of truth.

- Format: `kebab-case` — lowercase letters, digits, single hyphens
- Length: 2–5 words, descriptive of the *task*, not the tool
- Prefix when a skill belongs to a family: `seo-audit`, `gsap-core`, `gsap-scrolltrigger`
- No version numbers in the folder name (`seo-audit`, not `seo-audit-v2`)
- No underscores, capitals, dots, or spaces
- Never use the reserved names `synced` or `anthropic-skills`

Good: `vercel-deploy-check` · `pdf-form-filler` · `sql-perf-audit`
Bad: `VercelDeploy` · `deploy_vercel_v2` · `my-skill`

---

## 3. Writing the content

These rules come from the Agent Skills best practices. Apply them to every skill.

### Progressive disclosure — three levels

1. **Metadata** (~100 tokens): `name` + `description` load at startup, for *every* skill
2. **Body** (< 5,000 tokens, < 500 lines): loads only when the skill activates
3. **Resources**: `references/`, `scripts/`, `assets/` load only when the task needs them

Move detail out of `SKILL.md` into `references/`. Tell the agent **when** to read each file:

> Good: "Read `references/api-errors.md` if the API returns a non-200 status."
> Bad: "See references/ for details."

Reference files stay **one level deep** from `SKILL.md`. No chained reference chains.

### Write only what the agent would get wrong without the skill

For every line ask: *would the agent get this wrong or miss it otherwise?* If no, cut it.

- Cut: "A database migration updates a database schema."
- Keep: "This project uses `prisma migrate dev`; never `db push` — it skips migrations."

Skills written from an LLM's general knowledge alone are worthless. Ground them in real
expertise: a task you performed, project artifacts, runbooks, code review comments, past
incidents. Specific beats comprehensive.

### The description is the whole triggering mechanism

The agent only sees `name` + `description` when deciding whether to load the skill.

- Imperative: "Use this skill when…", not "This skill does…"
- Describe **user intent**, not internals
- Be pushy: name contexts where it applies even if the user doesn't use the domain word
  ("…even if they don't explicitly mention 'CSV' or 'analysis'")
- Include trigger keywords a user would actually type
- Under 1024 chars. Longer descriptions cost context in *every* session

```yaml
# Weak — will not trigger reliably
description: Helps with PDFs.

# Strong
description: Extract text and tables from PDFs, fill AcroForm fields, and merge
  documents. Use when the user works with .pdf files, needs OCR on scans, or asks
  to split, combine, or extract data from a PDF.
```

### Calibrate control per section

| Situation | Style |
| --- | --- |
| Fragile, order-dependent, or must be exact | Prescriptive — exact commands, "do not modify" |
| Several valid approaches, tolerance for variance | Explain the *why*, let the agent choose |
| Multiple tools could work | Pick one **default**, mention alternatives in one line |

Never present a menu of equal options. Never give three options and no default.

### High-value patterns to include

- **Gotchas** — facts that defy reasonable assumption. Highest-value content in a skill.
  Keep in `SKILL.md` unless the agent can't recognize the trigger. Every time you correct
  an agent's mistake, add the correction here.
- **Output templates** — concrete structure beats prose description
- **Checklists** — for multi-step workflows with dependencies
- **Validation loops** — do work → run validator → fix → repeat until it passes
- **Plan-validate-execute** — for batch or destructive operations

---

## 4. Creating a skill

Do not hand-assemble directories. Use the scaffolding script:

```bash
./scripts/new-skill.sh <skill-name> "What it does. Use when ..."
```

This copies `templates/skill-template/`, substitutes the name and description, and prints
the remaining steps.

Then:

1. Replace every placeholder in `SKILL.md` — no template text survives into a commit
2. Delete `references/` or `assets/` if empty; don't ship empty directories
3. Write the real `README.md`
4. Validate: `./scripts/validate-skill.sh <skill-name> --strict`
5. Add a row to the registry table in the root `README.md`
6. Commit — in **this** repo

---

## 5. Git rules

**One repository holds everything.** Skills are ordinary directories tracked in this repo.
There is no separate git repo per skill.

```bash
git add -A
git commit -m "feat(<skill-name>): ..."
```

- One logical change per commit. Never mix two skills in one commit.
- Never create a nested git repo inside a skill folder — it breaks skill discovery and
  confuses tooling. `.gitignore` has a `**/.git` guard for this.
- Never commit secrets, `.env` files, or credentials.
- End the task with the changes committed.
- Skill folders live at the repo root because that is where the `npx skills` CLI looks for
  them. After any layout change, confirm discovery still works:
  `npx skills add ./ --list`

---

## 6. Validation

Run before every commit:

```bash
./scripts/validate-skill.sh <skill-name> --strict
```

Checks `name` format and folder match, `description` presence and length, allowed
frontmatter keys, required files, reserved names, leftover `TODO` text, and possible
secrets. `--strict` makes template leftovers fatal.

The official validator is worth running too. Note the executable is `agentskills`, not
`skills-ref`:

```bash
uvx --from skills-ref agentskills validate ./<skill-name>
```

---

## 7. Installation

Skills install individually from this repo.

**One skill from GitHub:**

```bash
npx skills add mwasobaddy/skills --skill <skill-name>
```

**Browse or install everything:**

```bash
npx skills add mwasobaddy/skills --list
npx skills add mwasobaddy/skills --skill '*'
```

**Local symlink** (live editing on this machine):

```bash
./scripts/install.sh <skill-name>          # symlink into agent skill dirs
./scripts/install.sh --all
```

That symlinks into `~/.claude/skills`, `~/.config/opencode/skills`, `~/.agents/skills` and
`~/.codex/skills`. Edits take effect immediately.

---

## 8. Rules summary

1. Folder name = `name` field = command. Kebab-case. Never diverge.
2. Only the 6 spec frontmatter fields. No client-specific keys.
3. `SKILL.md` under 500 lines; depth goes into `references/`.
4. `description` says what *and* when. Under 1024 chars.
5. Content must be specific to a domain, not generic advice.
6. Ground skills in real expertise and real execution, not plausible-sounding prose.
7. Validate before committing.
8. One repo, skills tracked directly at the root, never nested repos.
9. Never commit secrets, and never ship a placeholder author.