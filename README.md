# I2E Fable Opus

A self-contained Claude Code Issue-to-Edit workflow: **Fable 5.1 Max** owns
decisions and review; **Opus 5.5 Max** performs bounded implementation.

This is the Claude Code counterpart of
[i2e-astra-terra](https://github.com/bowang-solutionstream/i2e-astra-terra), which
runs the same workflow in Codex with Astra Ultra and Terra xhigh.

Built on engineering workflow practices from
[Addy Osmani's agent-skills](https://github.com/addyosmani/agent-skills).
Credit to Addy Osmani for the foundational engineering skillset; this repository
consolidates and adapts those practices into a standalone Issue-to-Edit workflow
with Fable/Opus routing. It is an independent adaptation, not an official upstream
release or endorsement.

This package includes the complete workflow, supporting references, subagent
definitions, run-record template, installer, and tests. It does **not** require the
Codex package, the old `issue-to-edit-workflow-skills` repository, or its skill stack.

## Install

You need Git, Python 3.10+, and Claude Code (the CLI or the desktop app's Code tab)
with subagent support and access to `claude-fable-5-1` and `claude-opus-5-5` at
`max` effort. Model access and project-specific tools or credentials are not
supplied by a skill.

```sh
git clone https://github.com/bowang-solutionstream/i2e-fable-opus.git
cd i2e-fable-opus
python3 scripts/install.py
python3 scripts/install.py --check
```

The repository can be cloned without a GitHub invitation or authenticated account.
If you prefer GitHub CLI, use `gh repo clone bowang-solutionstream/i2e-fable-opus`.

The installer copies the skill to `skills/i2e-fable-opus` and its two subagent
definitions to `agents/i2e-fable-opus` inside `$CLAUDE_CONFIG_DIR`, or `~/.claude`
when `CLAUDE_CONFIG_DIR` is unset. It has no third-party Python dependency, does not
contact the network, and does not alter project `CLAUDE.md` files, settings, or
model configuration. Start a new Claude Code session after installation to load the
skill and agents.

| Role | Subagent | Model | Effort |
| --- | --- | --- | --- |
| Decision lead and reviewer | `i2e-fable-lead` | `claude-fable-5-1` | `max` |
| Bounded implementer (one or more) | `i2e-opus-implementer` | `claude-opus-5-5` | `max` |

## Use

```text
/i2e-fable-opus implement issue #123 in this repository
```

Asking by name also works, for example "Use i2e-fable-opus to implement issue #123."
State the desired deliverable and any operational boundary, for example local
changes only or an authorized PR. The skill carries existing authorization forward
without treating a model's approval as release permission.

For substantial implementation, the runtime uses Fable 5.1 Max as decision lead and
reviewer and Opus 5.5 Max as implementer. Work that splits into several slices can
use multiple Opus implementers, in parallel when their write sets are independent.
A session already running Fable 5.1 at max
effort acts as the lead; otherwise the coordinator creates one Fable lead subagent.
Tiny edits and non-implementation requests can stay in the current agent when
delegation adds no material value. Actual routing must be reported; unavailable
models are not silently substituted. This is an instruction workflow, not a runtime
setting switch.

The bundled guidance covers repository/issue intake, scope and acceptance criteria,
issue splitting, architecture and implementation, relevant engineering surfaces,
proportional verification, final-diff review and repairs, and authorized handoff or
shipping. Required failed or missing proof means incomplete. Two unsuccessful
repair rounds trigger Fable reassessment/takeover, not permission to abandon the
requested outcome.

Repository-specific rules and native checks still apply. Specialized tools and
skills can be used when available and relevant; none of the former I2E workflow
skills are dependencies of this package.

### Working on a teammate's issue

Issue creators and assignees do not hold an exclusive I2E work lock. A teammate
with the required repository permissions can take over authorized work on the
same issue without the original person's approval or prior reassignment. This also
applies to older issues containing owner-only I2E process notes. Inspect current
progress and coordinate actual conflicting writes; preserve repository protections,
required reviews, and the user's action boundary. Taking over does not automatically
change the assignee, rewrite old issues, or authorize deployment.

## Update or inspect

```sh
git pull --ff-only
python3 scripts/install.py --update
python3 scripts/install.py --check
```

Identical installs are no-ops. Different existing bundles are refused unless
`--update` is given. Every replaced bundle is preserved under a timestamped run in
`.i2e-fable-opus-backups` inside the Claude config directory, outside skill and agent
discovery; the installer prints the exact backup path. Restore by moving the unwanted
installed bundle aside and copying its preserved backup to the original location.
Other installed skills and agents are left untouched.

Use `--dest /path/to/claude-config` for an alternate installation. Add `--dry-run` to
preview without writes; previewing replacement also needs `--update`. `--check` is
read-only and returns nonzero if either bundle is absent or differs.

## Maintain and validate

Edit the source under `skills/`, not an installed copy.

```sh
python3 scripts/validate.py
python3 -m unittest discover -s tests -v
git diff --check
```

The validation script checks package structure, metadata, the pinned subagent
models and effort, and bundled links. Tests exercise installation, updates, backups,
conflicts, and failure behavior. These checks do not establish model quality or cost
savings; see [validation evidence](docs/validation.md) for the scope of behavioral
testing.

An optional [GitHub Actions template](docs/github-actions-validate.yml) runs the
same checks. Copy it to `.github/workflows/validate.yml` when enabling CI with an
account/token authorized to edit workflow files. The install and local checks do
not require it.

## Credits and license notices

- [Addy Osmani's agent-skills](https://github.com/addyosmani/agent-skills) provides
  the foundational engineering practices adapted here, including planning,
  incremental implementation, testing, source-driven development, and review.
  The original [MIT license and copyright notice](skills/i2e-fable-opus/notices/ADDY_AGENT_SKILLS_LICENSE)
  are retained with the installed skill.
- [Pattern, Inc.'s code-mint](https://github.com/patterninc/code-mint) contributed
  the issue-refinement guidance adapted from `interface-ticket-writer`.
  Its [Apache 2.0 license](skills/i2e-fable-opus/notices/CODE_MINT_LICENSE) is retained.

See [the main skill](skills/i2e-fable-opus/SKILL.md) for workflow instructions and
[provenance and upstream notices](skills/i2e-fable-opus/NOTICE.md) for the source
revisions and adaptation details. No repository-wide license is declared for the
original orchestration and tooling, and this adaptation does not relicense them.
Upstream material retains its respective license terms.
