#!/usr/bin/env python3
"""Verify Codex adapters reference the 14 canonical FAR specialist skills.

Codex adapters are discovery/routing metadata only. Specialist procedures remain
in .claude/skills/<name>/SKILL.md; this check never executes skill instructions.
"""
from __future__ import annotations

import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('.claude/skills')
CODEX_SKILLS = Path('.agents/skills')
CODEX_AGENTS = Path('.codex/agents')
SKIP = {'security-audit'}  # vendored Cloudflare skill, not a FAR specialist
SLUG = re.compile(r'far-[a-z0-9]+(?:-[a-z0-9]+)*\Z')


def metadata(source: str) -> tuple[str, str]:
    """Read the deliberately minimal required YAML frontmatter without YAML deps."""
    lines = source.splitlines()
    if not lines or lines[0] != '---':
        raise ValueError('missing frontmatter')
    try:
        stop = lines.index('---', 1)
    except ValueError as exc:
        raise ValueError('unterminated frontmatter') from exc
    values: dict[str, str] = {}
    for line in lines[1:stop]:
        key, sep, value = line.partition(':')
        if not sep or key not in {'name', 'description'} or key in values:
            raise ValueError('unexpected or duplicate frontmatter field')
        value = value.strip()
        if value.startswith('"'):
            value = json.loads(value)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f'empty {key}')
        values[key] = value
    if set(values) != {'name', 'description'}:
        raise ValueError('required metadata missing')
    return values['name'], values['description']


def render_skill(name: str, description: str) -> str:
    link = f'../../../.claude/skills/{name}/SKILL.md'
    return (
        f'---\nname: {name}\n'
        f'description: {json.dumps(description, ensure_ascii=False)}\n---\n\n'
        '# Codex discovery adapter\n\n'
        'Before using this specialist, read the complete current root `AGENTS.md` '
        'and its governing sources.\n\n'
        f'Read the **complete** canonical skill at '
        f'[`{SOURCE / name / "SKILL.md"}`]({link}). '
        'Its instructions define this specialist.\n\n'
        'This file only exposes existing FAR behavior to Codex skill discovery; '
        'it grants no additional authorization or assurance.\n'
    )


def agent_id(name: str) -> str:
    return name.replace('-', '_')


def render_agent(name: str, description: str) -> str:
    instructions = (
        f'You are the Codex routing adapter for FAR specialist `{name}`.\n'
        'Before any specialist work, read the complete current root `AGENTS.md` '
        'and its governing sources. Read the entire canonical specialist '
        f'instruction file `.claude/skills/{name}/SKILL.md` from this checkout.\n'
        'That file is the sole specialist procedure source. Do not invent or '
        'substitute procedures. If it is missing or unreadable, report the '
        'blocker and do not act as that specialist.\n'
        'Respect current repository governance and the task authorization. '
        'Keep findings separate from accepted claims, external independence, '
        'review approvals, and protected merge authority. Report observed '
        'evidence, unexecuted checks, and limitations.\n'
    )
    return (
        f'name = {json.dumps(agent_id(name))}\n'
        f'description = {json.dumps(description, ensure_ascii=False)}\n'
        f'developer_instructions = {json.dumps(instructions, ensure_ascii=False)}\n'
    )


def check(root: Path) -> list[str]:
    errors: list[str] = []
    source_dir = root / SOURCE
    if not source_dir.is_dir() or source_dir.is_symlink():
        return [f'missing or symlinked canonical source: {SOURCE}']
    names: set[str] = set()
    for entry in source_dir.iterdir():
        if entry.name in SKIP:
            continue
        if not entry.is_dir() or entry.is_symlink() or not SLUG.fullmatch(entry.name):
            errors.append(f'unexpected specialist entry: {entry.name}')
            continue
        names.add(entry.name)
    if len(names) != 14:
        errors.append(f'expected 14 canonical FAR specialists, found {len(names)}')
    for name in sorted(names):
        source = source_dir / name / 'SKILL.md'
        if source.is_symlink() or not source.is_file():
            errors.append(f'missing or symlinked canonical skill: {source.relative_to(root)}')
            continue
        try:
            actual_name, description = metadata(source.read_text(encoding='utf-8'))
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append(f'invalid canonical metadata for {name}: {exc}')
            continue
        if actual_name != name:
            errors.append(f'canonical name mismatch: {name} != {actual_name}')
            continue
        for path, expected in (
            (root / CODEX_SKILLS / name / 'SKILL.md', render_skill(name, description)),
            (root / CODEX_AGENTS / f'{agent_id(name)}.toml', render_agent(name, description)),
        ):
            if path.is_symlink() or not path.is_file():
                errors.append(f'missing or symlinked Codex adapter: {path.relative_to(root)}')
                continue
            try:
                actual = path.read_text(encoding='utf-8')
            except (OSError, UnicodeError) as exc:
                errors.append(f'unreadable adapter {path.relative_to(root)}: {exc}')
                continue
            if actual != expected:
                errors.append(f'Codex adapter drift: {path.relative_to(root)}')
            if path.suffix == '.toml':
                try:
                    parsed = tomllib.loads(actual)
                    if set(parsed) != {'name', 'description', 'developer_instructions'}:
                        errors.append(f'unexpected Codex agent fields: {path.relative_to(root)}')
                except tomllib.TOMLDecodeError as exc:
                    errors.append(f'invalid Codex TOML {path.relative_to(root)}: {exc}')
    agents_dir = root / CODEX_AGENTS
    if not agents_dir.is_dir() or agents_dir.is_symlink():
        errors.append('missing or symlinked .codex/agents directory')
    else:
        for entry in agents_dir.iterdir():
            if entry.name.startswith('far_') and entry.name not in {
                f'{agent_id(n)}.toml' for n in names
            }:
                errors.append(f'stale/unregistered FAR agent: {entry.name}')
    skills_dir = root / CODEX_SKILLS
    if not skills_dir.is_dir() or skills_dir.is_symlink():
        errors.append('missing or symlinked .agents/skills directory')
    else:
        for entry in skills_dir.iterdir():
            if entry.name.startswith('far-') and entry.name not in names:
                errors.append(f'stale/unregistered FAR skill: {entry.name}')
    return errors


def main() -> int:
    errors = check(ROOT)
    for error in errors:
        print('FAIL', error)
    if errors:
        return 1
    print('Codex FAR specialist adapters verified: 14 skills and 14 agent profiles')
    return 0


if __name__ == '__main__':
    sys.exit(main())
