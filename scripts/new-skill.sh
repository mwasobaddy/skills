#!/usr/bin/env bash
# Scaffolds a new skill folder. Skills live in this single repository — there is
# no separate git repo per skill.
#
# Usage: ./scripts/new-skill.sh <skill-name> "description ..."
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATE="$ROOT/templates/skill-template"

die() { printf 'error: %s\n' "$1" >&2; exit 1; }

[ $# -eq 2 ] || die "Usage: $0 <skill-name> \"description ...\""
NAME="$1"
DESCRIPTION="$2"

# Validate the folder name against the Agent Skills spec.
[[ "$NAME" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]] \
  || die "Invalid name '$NAME'. Use kebab-case: lowercase letters, digits, single hyphens."
[ "${#NAME}" -le 64 ] || die "Name is ${#NAME} chars; the spec allows max 64."

TARGET="$ROOT/$NAME"
[ ! -e "$TARGET" ] || die "$TARGET already exists."

DESC_LEN=${#DESCRIPTION}
[ "$DESC_LEN" -ge 1 ] && [ "$DESC_LEN" -le 1024 ] \
  || die "Description is $DESC_LEN chars; must be 1-1024."

[ -d "$TEMPLATE" ] || die "Template not found at $TEMPLATE"

# Copy the template, then substitute the frontmatter placeholders.
cp -R "$TEMPLATE" "$TARGET"
rm -f "$TARGET/references/PLACEHOLDER.md"
# Don't scaffold empty directories; the author adds them when there is content to defer.
rmdir "$TARGET/references" 2>/dev/null || true

# Use a portable sed expression: escape any sed metacharacter in the values.
ESCAPED_NAME="$(printf '%s' "$NAME" | sed 's/[\/&]/\\&/g')"
ESCAPED_DESC="$(printf '%s' "$DESCRIPTION" | sed 's/[\/&]/\\&/g')"

sed -i '' "s|^name: skill-name$|name: ${ESCAPED_NAME}|" "$TARGET/SKILL.md"
sed -i '' "s|^description: TODO.*$|description: ${ESCAPED_DESC}|" "$TARGET/SKILL.md"
sed -i '' "s|^# Skill Name$|# ${ESCAPED_NAME}|" "$TARGET/SKILL.md"
sed -i '' "s|skill-name|${ESCAPED_NAME}|g" "$TARGET/README.md"

cat <<EOF

Created $TARGET.

Next:
  1. Replace every TODO in SKILL.md — template text must not survive into a commit.
  2. Delete references/ if the skill has nothing to defer.
  3. Write the real README.md.
  4. $ROOT/scripts/validate-skill.sh ${ESCAPED_NAME} --strict
  5. git -C "$ROOT" add -A
  6. git -C "$ROOT" commit -m "feat(${ESCAPED_NAME}): <what it does>"
  7. Add a row to the registry table in the root README.md.

Install it with:
  npx skills add mwasobaddy/skills --skill ${ESCAPED_NAME}

EOF
