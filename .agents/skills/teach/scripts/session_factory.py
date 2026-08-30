#!/usr/bin/env python3
"""Create a reciprocal current-protocol learning-session note and sidecar."""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import date
from pathlib import Path


PROTOCOL_VERSION = "2026-08-26.1"
VAULT_ROOT = Path(__file__).resolve().parents[4]
NOTE_TEMPLATE = VAULT_ROOT / "Templates" / "Learning Session Template.md"
LOG_TEMPLATE = VAULT_ROOT / "Templates" / "Learning Session Log Template.md"


class FactoryError(ValueError):
    pass


def validate_title(title: str) -> str:
    clean = title.strip()
    if not clean or clean in {".", ".."} or any(char in clean for char in "/\\\n\r"):
        raise FactoryError("title must be a nonblank filename-safe note title")
    return clean


def validate_date(value: str) -> str:
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as error:
        raise FactoryError("created date must be YYYY-MM-DD") from error


def obsidian_link(from_dir: Path, target: Path) -> str:
    relative = Path(os.path.relpath(target, from_dir)).as_posix()
    if relative.endswith(".md"):
        relative = relative[:-3]
    return f"[[{relative}]]"


def render(template: str, *, title: str, created: str) -> str:
    return template.replace("{{title}}", title).replace("{{date:YYYY-MM-DD}}", created)


def create_session(
    output_dir: Path,
    title: str,
    created: str,
    source_note: Path | None = None,
) -> tuple[Path, Path]:
    title = validate_title(title)
    created = validate_date(created)
    output_dir = output_dir.resolve()
    if not output_dir.is_dir():
        raise FactoryError(f"output directory does not exist: {output_dir}")

    note_path = output_dir / f"{title}.md"
    log_path = output_dir / f"{title} — Session Log.md"
    occupied = [path for path in (note_path, log_path) if path.exists()]
    if occupied:
        raise FactoryError("refusing to overwrite: " + ", ".join(str(path) for path in occupied))

    note_template = NOTE_TEMPLATE.read_text(encoding="utf-8")
    log_template = LOG_TEMPLATE.read_text(encoding="utf-8")
    note = render(note_template, title=title, created=created)
    log = render(log_template, title=f"{title} — Session Log", created=created)
    log = re.sub(r"(?m)^session-note:\s*$", f'session-note: "[[{title}]]"', log, count=1)

    if source_note is not None:
        source_note = source_note.resolve()
        if not source_note.is_file() or source_note.suffix.lower() != ".md":
            raise FactoryError(f"source note must be an existing Markdown file: {source_note}")
        note = re.sub(
            r"(?m)^source-note:\s*$",
            f'source-note: "{obsidian_link(output_dir, source_note)}"',
            note,
            count=1,
        )

    # Write only after all inputs and both outputs have been validated.
    note_path.write_text(note, encoding="utf-8")
    try:
        log_path.write_text(log, encoding="utf-8")
    except Exception:
        note_path.unlink(missing_ok=True)
        raise
    return note_path, log_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("title")
    parser.add_argument("--output-dir", type=Path, default=Path.cwd())
    parser.add_argument("--created", default=date.today().isoformat())
    parser.add_argument("--source-note", type=Path)
    args = parser.parse_args()
    try:
        note, log = create_session(
            args.output_dir, args.title, args.created, args.source_note
        )
    except (OSError, FactoryError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(f"SESSION_NOTE: {note}")
    print(f"SESSION_LOG: {log}")
    print(f"PROTOCOL_VERSION: {PROTOCOL_VERSION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
