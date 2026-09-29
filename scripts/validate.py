#!/usr/bin/env python3
"""Validate the portable skill bundle using only the Python standard library."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit


MAIN_NAME = "i2e-fable-opus"
# Claude Code subagent definitions carry each role's requested model and effort.
AGENTS = {
    "i2e-fable-lead": ("claude-fable-5-1", "max"),
    "i2e-opus-implementer": ("claude-opus-5-5", "max"),
}
REPO_ROOT = Path(__file__).resolve().parent.parent


class ValidationError(ValueError):
    """A package or installed tree does not satisfy the package contract."""


def tree_snapshot(directory: Path) -> dict[str, str]:
    """Describe the complete tree, refusing links and non-regular entries."""
    if directory.is_symlink() or not directory.is_dir():
        raise ValidationError(f"Expected a real directory: {directory}")
    result: dict[str, str] = {}
    for entry in sorted(directory.rglob("*")):
        name = entry.relative_to(directory).as_posix()
        if entry.is_symlink():
            raise ValidationError(f"Symlinks are not supported: {entry}")
        if entry.is_dir():
            result[name + "/"] = "directory"
        elif entry.is_file():
            result[name] = hashlib.sha256(entry.read_bytes()).hexdigest()
        else:
            raise ValidationError(f"Unsupported filesystem entry: {entry}")
    return result


def string_mappings(text: str, source: Path) -> dict[str, str]:
    """Read the small string-mapping YAML subset used by skill metadata.

    Supports nested mappings, plain/quoted strings, and |/> block strings.
    This deliberately is not a general-purpose YAML parser.
    """
    values: dict[str, str] = {}
    parents: list[tuple[int, str]] = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        index += 1
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.fullmatch(r"( *)([A-Za-z_][A-Za-z0-9_-]*):(?:\s+(.*))?", line)
        if not match:
            raise ValidationError(f"Unsupported metadata syntax in {source}: {line}")
        indent, key, value = len(match[1]), match[2], (match[3] or "").strip()
        while parents and parents[-1][0] >= indent:
            parents.pop()
        full_key = ".".join([parent[1] for parent in parents] + [key])
        if full_key in values:
            raise ValidationError(f"Duplicate metadata key {full_key} in {source}")
        if not value:
            parents.append((indent, key))
            continue
        if value in ("|", "|-", "|+", ">", ">-", ">+"):
            parts = []
            while index < len(lines):
                child = lines[index]
                if child.strip() and len(child) - len(child.lstrip(" ")) <= indent:
                    break
                parts.append(child.strip())
                index += 1
            value = (" " if value.startswith(">") else "\n").join(parts).strip()
        elif value.startswith('"'):
            try:
                value = json.loads(value)
            except json.JSONDecodeError as exc:
                raise ValidationError(f"Invalid quoted string in {source}: {full_key}") from exc
        elif value.startswith("'"):
            if not value.endswith("'") or len(value) < 2:
                raise ValidationError(f"Invalid quoted string in {source}: {full_key}")
            value = value[1:-1].replace("''", "'")
        else:
            value = re.split(r"\s+#", value, maxsplit=1)[0].rstrip()
            if value.lower() in {"true", "false", "null", "~"} or re.fullmatch(r"[-+]?\d+(?:\.\d+)?", value):
                raise ValidationError(f"Expected a metadata string in {source}: {full_key}")
        values[full_key] = value
    return values


def require_string(values: dict[str, str], key: str, source: Path) -> str:
    value = values.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"Missing nonempty string {key} in {source}")
    if value.strip().lower() in {"todo", "tbd", "placeholder", "null", "~"}:
        raise ValidationError(f"Placeholder value for {key} in {source}")
    return value


def markdown_metadata(path: Path, expected_name: str) -> dict[str, str]:
    """Check the frontmatter shared by skills and subagent definitions."""
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", text, re.DOTALL)
    if not match:
        raise ValidationError(f"Missing YAML frontmatter in {path}")
    values = string_mappings(match[1], path)
    if require_string(values, "name", path) != expected_name:
        raise ValidationError(f"Expected name {expected_name} in {path}")
    require_string(values, "description", path)
    if not text[match.end():].strip():
        raise ValidationError(f"Missing instructions in {path}")
    return values


def local_link_targets(text: str) -> list[str]:
    """Extract inline links/images and reference definitions, ignoring code fences."""
    text = re.sub(r"(?ms)^\s*(`{3,}|~{3,}).*?^\s*\1\s*$", "", text)
    inline = re.findall(r"!?\[[^\]\n]*\]\(\s*(<[^>]+>|[^\s)]+)(?:\s+[^)]*)?\)", text)
    references = re.findall(r"(?m)^ {0,3}\[[^\]\n]+\]:\s*(<[^>]+>|\S+)", text)
    return [target.strip("<>") for target in inline + references]


def validate_markdown(bundle: Path, allowed_root: Path) -> None:
    for path in sorted(bundle.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        if re.search(r"\b(?:TODO|TBD|FIXME)\b|\[INSERT\b", text):
            raise ValidationError(f"Unfinished scaffold in {path}")
        for target in local_link_targets(text):
            parsed = urlsplit(target)
            if parsed.scheme == "file" or (not parsed.scheme and parsed.path.startswith("/")):
                raise ValidationError(f"Local links must be relative to the bundle in {path}: {target}")
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            destination = (path.parent / unquote(parsed.path)).resolve()
            if not destination.is_relative_to(allowed_root.resolve()):
                raise ValidationError(f"Local link escapes the bundle in {path}: {target}")
            if not destination.exists():
                raise ValidationError(f"Broken local link in {path}: {target}")


def validate_package(root: Path = REPO_ROOT) -> list[Path]:
    skills = root / "skills"
    if skills.is_symlink():
        raise ValidationError(f"Symlink source directory is not supported: {skills}")
    main = skills / MAIN_NAME
    tree_snapshot(main)
    markdown_metadata(main / "SKILL.md", MAIN_NAME)
    for name, (model, effort) in AGENTS.items():
        path = main / "agents" / f"{name}.md"
        if not path.is_file():
            raise ValidationError(f"Missing subagent definition: {path}")
        values = markdown_metadata(path, name)
        if (values.get("model"), values.get("effort")) != (model, effort):
            raise ValidationError(f"Subagent {name} must pin model {model} with effort {effort}: {path}")
    for name in ("references", "templates"):
        directory = main / name
        if not directory.is_dir() or not any(path.is_file() for path in directory.rglob("*")):
            raise ValidationError(f"Missing or empty required directory: {directory}")
    validate_markdown(main, main)
    return [main]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="Package repository root")
    args = parser.parse_args()
    try:
        bundles = validate_package(args.root)
    except (ValidationError, OSError, UnicodeError) as exc:
        print(f"Validation failed: {exc}", file=sys.stderr)
        return 1
    print("Validated: " + ", ".join(bundle.name for bundle in bundles))
    print("Structural checks passed; this does not evaluate model behavior.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
