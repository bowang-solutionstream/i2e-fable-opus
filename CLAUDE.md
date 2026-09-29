# Package maintenance

The source of truth is `skills/i2e-fable-opus/`, including the subagent definitions
in its `agents/` directory. It must work without any other installed workflow skill.
Keep conditional detail in the bundled references and load only what the task needs.

Preserve the Fable 5.1 Max / Opus 5.5 Max role contract, user authority, repository
requirements, and honest completion states. Do not add credentials, customer
examples, machine-specific paths, or historical private run logs.

Validate package changes with `python3 scripts/validate.py`. For installer or
validator changes, also run `python3 -m unittest discover -s tests -v`.
Behavioral scenario runs are separate from these structural checks; do not claim
model quality or cost savings from package validation.
