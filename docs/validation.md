# Validation evidence

## Package validation — 2026-09-28

- `python3 scripts/validate.py`: the bundle passes structure, metadata, pinned
  subagent model/effort, and local link checks. The skill's links remain inside its
  own bundle.
- `python3 -m unittest discover -s tests -v`: 26 tests pass, including install,
  exact backup preservation of both bundles, two-bundle rollback, source/target
  overlap rejection, symlink rejection (including symlinked `skills/` and `agents/`
  directories), unrelated skill and agent preservation, model/effort pin
  enforcement, and read-only check/dry-run.
- Three deliberately introduced defects were each caught by the corresponding test:
  a rollback that does not restore backups, a validator that ignores the model/effort
  pin, and a missing symlink check on the `skills/` and `agents/` directories.
- Anthropic skill-creator `quick_validate.py`: the skill passes.
- The frontmatter of the skill and both subagent definitions parses as YAML with
  the expected name, model, and effort values.
- Before porting, the source package's 27 tests passed on the same machine.
- CI configuration is supplied as an optional template, not an active workflow;
  local validation results are not presented as GitHub CI results.

## Installation and discovery — 2026-09-28

- A user-level installation reported `install` for the skill and agent bundles,
  then `OK` for both under `--check`. A later `--update` with the
  multiple-implementer wording preserved the first installation in a timestamped
  backup, replaced both bundles, and passed `--check`.
- A Claude Code desktop session that was already running listed the new skill
  immediately after installation. The subagent types were not yet available in that
  turn ("Agent type ... not found") and became available at the session's next turn.
- In that session, one `i2e-fable-lead` and two `i2e-opus-implementer` subagents
  were started concurrently without a model override. Asked what their environment
  states, the lead reported `claude-fable-5-1` with max effort and both implementers
  reported `claude-opus-5-5` with max effort. Each used about 53k tokens for a
  trivial prompt, nearly all of it fixed startup context.
- A headless CLI check did not run because the CLI's sign-in had expired (HTTP 401);
  the in-session check above replaced it.

## Behavior and limits

Structural checks do not prove that models will make correct decisions. No live
workflow smoke test has been run with this package, so there is no evidence yet of
a completed Fable-led, Opus-implemented run, parallel implementers integrating
separate slices, the two-failed-round takeover path, or live shipping. The
Astra/Terra smoke test and policy checks recorded for the Codex package are not
evidence for this package. No comparison against Astra/Terra, account-charge
measurement, or cost-saving claim is established by this validation.

Model and effort evidence is what each subagent's runtime environment states, not
billing or provider records.

The generic workflow retains project-specific requirements. This package does not
provide browser access, credentials, GitHub permissions, model availability, or
production environment access. Live shipping and high-risk migration behavior
require evidence in the actual target project.
