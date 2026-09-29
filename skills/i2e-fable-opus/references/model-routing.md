# Fable 5.1 Max / Opus 5.5 Max routing

## Runtime and roles

Use runtime-provided model and effort identifiers. This profile requests
`claude-fable-5-1` with `max` effort, and `claude-opus-5-5` with `max` effort. In
Claude Code a subagent's model and effort come from its definition: the bundled
[`i2e-fable-lead`](../agents/i2e-fable-lead.md) and
[`i2e-opus-implementer`](../agents/i2e-opus-implementer.md) pin them, and the
package installer registers them as user-level agents. The Agent tool has no effort
argument, and a per-call `model` argument overrides the definition, so pass neither.
Max is not an instruction to invent an API parameter.

Confirm both agent types are available before delegating. A missing type means an
incomplete installation: report it, and install the bundled definitions only when
authorized; a new session may be needed to load them. If the runtime cannot run the
requested pairing, explain the limitation; continue useful non-model-dependent
work and obtain a user-selected fallback before representing another profile as
the requested hybrid. A skill does not provide model access, subscriptions, or quota.

If the root is already Fable 5.1 at max effort, it is the decision lead. Otherwise,
create one `i2e-fable-lead` with a focused contract/discovery task and reuse it for
ordinary review by continuing it with SendMessage. The root relays tools and
integrates work without duplicating the lead's planning. Current-agent direct work
remains appropriate for tiny tasks and non-implementation requests; report that
exception honestly.

Fable owns the contract, architecture, cross-module invariants, material scope
changes, and final judgment. Opus implements stable, bounded work, writes relevant
tests, and repairs local failures. For an uncertain migration, concurrency defect,
tenant boundary, or other consequential invariant, Fable investigates and can
implement the critical part; delegate only the separable settled portion.

## Delegation packet

Give each worker the objective, exact base/worktree, owned files or module, relevant
pattern, invariants and exclusions, acceptance-to-proof map, allowed commands and
actions, and unresolved questions. Include direct source pointers so it can inspect
necessary dependencies; an evidence capsule is not a ban on useful investigation.
Subagents do not inherit this skill, so point them by path to the bundled references
they need, such as the review standard for a reviewer. Tell workers they share the
codebase and must preserve others' changes. Do not fork the whole conversation just
to populate a task packet.

For Claude Code's Agent tool, the relevant fields are:

```json
{
  "description": "Implement pagination slice",
  "subagent_type": "i2e-opus-implementer",
  "prompt": "The task-specific contract, owned paths, evidence, and verification."
}
```

Start a separate `i2e-opus-implementer` for each slice that needs one; implementers
with disjoint write ownership can run in parallel. For a separate decision lead or
fresh critical reviewer, select `i2e-fable-lead` and a fresh bounded context. Follow
the actual tool schema if different. Use subagents rather than starting user-visible
sessions unless the user asks for one. The root owns worker spawning, integration,
and relay. Workers request additional help through the root so overlapping work and
repeated investigation remain visible. Do not spend a slot on duplicate verification
of unchanged inputs.

## Review and repair

Each Opus worker returns changed files, decisions, acceptance/proof mapping, commands
and outcomes, unresolved concerns, its reported model, and usage metadata when
available.
Fable reads the actual production diff and important test assertions, including
omitted behavior. For ordinary review, reuse the lead promptly. For consequential
changes, use an independent `i2e-fable-lead` reviewer with the requirements, raw
diff, and evidence; avoid feeding it the author's approval conclusion as its task.

Consolidate material findings into one repair packet per affected slice and return
ordinary fixes to the Opus worker that owns it. After two unsuccessful rounds, or
earlier evidence of a misunderstood invariant, Fable diagnoses the cause, corrects
the contract, and takes over or reassigns a smaller settled slice. Do not create an
endless relay or use the repair count as a completion condition. Parallel workers
must have disjoint write ownership; shared-contract changes happen before dependent
implementation.

## Cost accounting

Optimize cost per accepted result. Record actual model/effort, input/cached/output
usage, reasoning usage if exposed, elapsed time, repair count, and proof quality.
Include root coordination, workers, reviews, retries, and evaluation in comparisons.
Do not count cached input twice, or add reasoning output twice when the provider
already includes it in output. State missing usage as unavailable. Estimated rate
card credits are not observed account charges or quota savings; date the rate card.
Matching an earlier Astra/Terra or Sol/Luna benchmark does not prove Fable/Opus
quality or savings.
