#!/usr/bin/env python3
"""Validate deterministic invariants for a persisted learning session."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


PROTOCOL_VERSION = "2026-08-25.6"
REQUIRED_SECTIONS = (
    "Goal",
    "Source pack",
    "Learner map",
    "Dependency plan",
    "Lessons",
    "Transfer and retrieval",
    "Related",
)
LESSON_HEADINGS = (
    "Why this node",
    "Core rule",
    "Derivation",
    "Worked example or contrast",
    "Connection",
    "Verification",
    "Active check",
)
EVIDENCE_STATES = {"unknown", "introduced", "supported", "demonstrated"}
SESSION_STATUSES = {
    "probing",
    "planning",
    "teaching",
    "awaiting-retrieval",
    "complete",
}
LOG_STATUSES = {"active", "awaiting-retrieval", "complete"}
CLOSED_STATUSES = {"awaiting-retrieval", "complete"}


def prose_outside_code(text: str) -> str:
    """Remove fenced and inline code before checking Markdown syntax."""
    without_fences = re.sub(
        r"^(?P<fence>`{3,}|~{3,})[^\n]*\n.*?^(?P=fence)\s*$",
        "",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    return re.sub(r"`[^`\n]*`", "", without_fences)


def invalid_obsidian_math_delimiters(text: str) -> list[str]:
    prose = prose_outside_code(text)
    return sorted(set(re.findall(r"(?<!\\)\\[\[\]\(\)]", prose)))


def frontmatter(text: str, path: Path) -> dict[str, str]:
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        raise ValueError(f"{path}: missing YAML frontmatter")

    properties: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line or line[0].isspace() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        properties[key.strip()] = value.strip().strip('"').strip("'")
    return properties


def section(text: str, heading: str) -> str | None:
    pattern = rf"^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    return match.group(1) if match else None


def normalized(text: str) -> str:
    return " ".join(text.split())


def node_name(heading: str) -> str:
    name = re.sub(r"^Node\s+\d+\s+[—-]\s+", "", heading, flags=re.IGNORECASE)
    return normalized(name).casefold()


def lesson_nodes(lessons: str) -> list[tuple[str, str]]:
    matches = list(re.finditer(r"^### (Node\s+\d+\s+[—-]\s+.+?)\s*$", lessons, re.MULTILINE))
    nodes: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(lessons)
        nodes.append((match.group(1), lessons[match.end() : end]))
    return nodes


def active_check(node_body: str) -> str | None:
    reteaches = list(re.finditer(r"^#### Reteach (\d+)\s*$", node_body, re.MULTILINE))
    if reteaches:
        latest = reteaches[-1]
        reteach_body = node_body[latest.end() :]
        markers = list(re.finditer(r"^Active check:\s*$", reteach_body, re.MULTILINE))
        if len(markers) != 1:
            return None
        return reteach_body[markers[0].end() :].strip() or None

    match = re.search(
        r"^#### Active check\s*\n+(.*?)(?=^#### |^### |^## |\Z)",
        node_body,
        re.MULTILINE | re.DOTALL,
    )
    return match.group(1).strip() if match else None


def dependency_roots(dependency_plan: str) -> tuple[set[str], dict[str, str]]:
    blocks = re.findall(r"```mermaid\s*\n(.*?)```", dependency_plan, re.DOTALL)
    if not blocks:
        return set(), {}
    graph = blocks[-1]
    labels = {
        match.group(1): match.group(2)
        for match in re.finditer(
            r'^\s*([A-Za-z][A-Za-z0-9_]*)\s*\[\s*"([^"]+)"\s*\]\s*$',
            graph,
            re.MULTILINE,
        )
    }
    edges = re.findall(
        r"^\s*([A-Za-z][A-Za-z0-9_]*)\s*-->\s*(?:\|[^|]*\|\s*)?"
        r"([A-Za-z][A-Za-z0-9_]*)\s*$",
        graph,
        re.MULTILINE,
    )
    sources = {source for source, _ in edges}
    targets = {target for _, target in edges}
    return sources - targets, labels


def root_audit(dependency_plan: str) -> tuple[list[dict[str, str]], str | None]:
    match = re.search(
        r"^Root audit:\s*\n+(.*?)(?=^```mermaid\s*$)",
        dependency_plan,
        re.MULTILINE | re.DOTALL,
    )
    if not match:
        return [], "missing Root audit table immediately above the dependency Mermaid block"
    table_lines = [line.strip() for line in match.group(1).splitlines() if line.strip()]
    if len(table_lines) < 3 or not all(line.startswith("|") and line.endswith("|") for line in table_lines):
        return [], "Root audit must be a Markdown table"

    def cells(line: str) -> list[str]:
        return [cell.strip() for cell in line.strip("|").split("|")]

    expected = ["Root", "Classification", "Conditions / caveats", "Evidence or establishment"]
    if cells(table_lines[0]) != expected:
        return [], "Root audit columns must be: " + ", ".join(expected)
    separator = cells(table_lines[1])
    if len(separator) != len(expected) or not all(re.fullmatch(r":?-{3,}:?", cell) for cell in separator):
        return [], "Root audit has an invalid Markdown separator row"

    rows: list[dict[str, str]] = []
    for line in table_lines[2:]:
        values = cells(line)
        if len(values) != len(expected):
            return [], "each Root audit row must have exactly four cells"
        rows.append(dict(zip(expected, values)))
    return rows, None


def validate_closeout(
    note_path: Path,
    log_path: Path,
    note_meta: dict[str, str],
    log_meta: dict[str, str],
    note: str,
    log: str,
    current_status: str,
) -> list[str]:
    errors: list[str] = []
    session_status = note_meta.get("status", "")
    if session_status not in CLOSED_STATUSES:
        return [f"{note_path}: closeout status must be awaiting-retrieval or complete"]
    if log_meta.get("status") != session_status:
        errors.append(f"{log_path}: status must match closed session status {session_status!r}")
    if current_status != "demonstrated":
        errors.append(f"{note_path}: closeout requires learner-map Status `demonstrated`")
    next_retrieval = note_meta.get("next-retrieval", "")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", next_retrieval):
        errors.append(f"{note_path}: closeout requires YYYY-MM-DD next-retrieval")

    transfer = section(note, "Transfer and retrieval") or ""
    result = re.search(r"^- Result and verification:\s*(.+)$", transfer, re.MULTILINE)
    if not result or normalized(result.group(1)).casefold().startswith("pending"):
        errors.append(f"{note_path}: closeout requires a non-pending transfer result")
    for label in ("Retrieve on", "Interleave/discriminate on"):
        match = re.search(rf"^- {re.escape(label)}:\s*(.+)$", transfer, re.MULTILINE)
        if not match or not match.group(1).strip():
            errors.append(f"{note_path}: closeout requires '{label}'")
    for label in ("Known", "Inference", "Unknown", "To verify", "Smallest next action"):
        if not re.search(rf"^{re.escape(label)}:\s*.+$", transfer, re.MULTILINE):
            errors.append(f"{note_path}: closeout requires '{label}:'")
    closeouts = list(re.finditer(r"^### .*closeout.*$", log, re.MULTILINE | re.IGNORECASE))
    if not closeouts:
        errors.append(f"{log_path}: closeout event is missing")
    elif "Assessment: pending learner response." in log[closeouts[-1].end() :]:
        errors.append(f"{log_path}: unresolved pending assessment appears after closeout")
    return errors


def validate(
    note_path: Path,
    log_path: Path,
    require_active_check: bool,
    require_closeout: bool = False,
) -> tuple[list[str], str | None]:
    errors: list[str] = []
    note = note_path.read_text(encoding="utf-8")
    log = log_path.read_text(encoding="utf-8")

    try:
        note_meta = frontmatter(note, note_path)
    except ValueError as error:
        errors.append(str(error))
        note_meta = {}
    try:
        log_meta = frontmatter(log, log_path)
    except ValueError as error:
        errors.append(str(error))
        log_meta = {}

    if note_meta.get("type") != "learning-session":
        errors.append(f"{note_path}: type must be learning-session")
    if log_meta.get("type") != "learning-session-log":
        errors.append(f"{log_path}: type must be learning-session-log")
    if note_meta.get("status") not in SESSION_STATUSES:
        errors.append(f"{note_path}: invalid session status {note_meta.get('status')!r}")
    if log_meta.get("status") not in LOG_STATUSES:
        errors.append(f"{log_path}: invalid session-log status {log_meta.get('status')!r}")
    for path, metadata in ((note_path, note_meta), (log_path, log_meta)):
        if metadata.get("protocol-version") != PROTOCOL_VERSION:
            errors.append(f"{path}: protocol-version must be {PROTOCOL_VERSION}")

    if note_meta.get("session-log") != f"[[{log_path.stem}]]":
        errors.append(f"{note_path}: session-log must link to [[{log_path.stem}]]")
    if log_meta.get("session-note") != f"[[{note_path.stem}]]":
        errors.append(f"{log_path}: session-note must link to [[{note_path.stem}]]")

    for heading in REQUIRED_SECTIONS:
        count = len(re.findall(rf"^## {re.escape(heading)}\s*$", note, re.MULTILINE))
        if count != 1:
            errors.append(f"{note_path}: expected one '## {heading}' heading, found {count}")
    if re.search(r"^## Session log\s*$", note, re.MULTILINE | re.IGNORECASE):
        errors.append(f"{note_path}: raw Session log section belongs in the sidecar")

    bad_math = invalid_obsidian_math_delimiters(note)
    if bad_math:
        errors.append(
            f"{note_path}: unsupported Obsidian math delimiter(s) "
            f"{', '.join(repr(item) for item in bad_math)}; use $...$ or $$...$$"
        )

    if note_meta.get("status") != "probing":
        goal = section(note, "Goal") or ""
        capability = re.search(r"^Independent capability:\s*(.+)$", goal, re.MULTILINE)
        if not capability or not capability.group(1).strip():
            errors.append(f"{note_path}: independent capability is blank")

    lessons = section(note, "Lessons") or ""
    nodes = lesson_nodes(lessons)
    node_by_name: dict[str, tuple[str, str]] = {}
    for heading, body in nodes:
        key = node_name(heading)
        if key in node_by_name:
            errors.append(f"{note_path}: duplicate lesson node name {key!r}")
        node_by_name[key] = (heading, body)
        headings = re.findall(r"^#### (.+?)\s*$", body, re.MULTILINE)
        if tuple(headings[: len(LESSON_HEADINGS)]) != LESSON_HEADINGS:
            errors.append(
                f"{note_path}: {heading} lesson headings must be: " + ", ".join(LESSON_HEADINGS)
            )
        reteach = headings[len(LESSON_HEADINGS) :]
        expected_reteach = [f"Reteach {index}" for index in range(1, len(reteach) + 1)]
        if reteach != expected_reteach:
            errors.append(f"{note_path}: {heading} reteach headings must be sequential")
        if not re.search(r"^> \[!info\] Node status\s*$", body, re.MULTILINE):
            errors.append(f"{note_path}: {heading} is missing its Node status callout")
        evidence = re.search(r"^> \*\*Evidence:\*\* `([^`]+)`\s*$", body, re.MULTILINE)
        if not evidence or evidence.group(1) not in EVIDENCE_STATES:
            errors.append(f"{note_path}: {heading} has an invalid or missing evidence state")

    learner_map = section(note, "Learner map") or ""
    current_match = re.search(r"^Current node:\s*(.+?)\s*$", learner_map, re.MULTILINE)
    status_match = re.search(r"^Status:\s*`([^`]+)`\s*$", learner_map, re.MULTILINE)
    current_name = normalized(current_match.group(1)).casefold() if current_match else ""
    current_status = status_match.group(1) if status_match else ""
    if note_meta.get("status") != "probing" and not current_name:
        errors.append(f"{note_path}: Current node is blank")
    if note_meta.get("status") != "probing" and not current_status:
        errors.append(f"{note_path}: learner-map Status is blank")
    if current_status and current_status not in EVIDENCE_STATES:
        errors.append(f"{note_path}: invalid learner-map status {current_status!r}")

    if note_meta.get("status") != "probing":
        dependency_plan = section(note, "Dependency plan") or ""
        root_ids, labels = dependency_roots(dependency_plan)
        audit_rows, audit_error = root_audit(dependency_plan)
        if audit_error:
            errors.append(f"{note_path}: {audit_error}")
        elif not root_ids:
            errors.append(f"{note_path}: dependency Mermaid graph has no parseable root")
        else:
            audited_names: set[str] = set()
            for row in audit_rows:
                root = normalized(row["Root"].strip("`")).casefold()
                classification = row["Classification"].strip("`")
                audited_names.add(root)
                if classification not in {"demonstrated", "foundation to teach"}:
                    errors.append(
                        f"{note_path}: root {row['Root']!r} has invalid final classification "
                        f"{classification!r}"
                    )
                if not row["Conditions / caveats"] or not row["Evidence or establishment"]:
                    errors.append(f"{note_path}: root {row['Root']!r} has a blank audit field")
            expected_names = {
                normalized(labels.get(root_id, root_id)).casefold() for root_id in root_ids
            }
            if audited_names != expected_names:
                errors.append(
                    f"{note_path}: Root audit names {sorted(audited_names)!r} do not match "
                    f"dependency roots {sorted(expected_names)!r}"
                )

    canonical_check: str | None = None
    if current_name in node_by_name:
        heading, body = node_by_name[current_name]
        evidence = re.search(r"^> \*\*Evidence:\*\* `([^`]+)`\s*$", body, re.MULTILINE)
        if evidence and current_status and evidence.group(1) != current_status:
            errors.append(
                f"{note_path}: {heading} evidence {evidence.group(1)!r} "
                f"does not match learner-map status {current_status!r}"
            )
        canonical_check = active_check(body)
        reteach_headings = list(re.finditer(r"^#### Reteach \d+\s*$", body, re.MULTILINE))
        if reteach_headings and not canonical_check:
            errors.append(
                f"{note_path}: {heading} newest reteach must contain exactly one literal "
                "'Active check:' line followed by a fresh check"
            )

    if require_active_check:
        if note_meta.get("status") != "teaching":
            errors.append(f"{note_path}: active-check mode requires status 'teaching'")
        else:
            if not current_name:
                errors.append(f"{note_path}: Current node is blank")
            elif current_name not in node_by_name:
                errors.append(f"{note_path}: current node has no completed lesson section")
            if not canonical_check:
                errors.append(f"{note_path}: current node has no active check")
            else:
                pending_marker = "Assessment: pending learner response."
                pending_at = log.rfind(pending_marker)
                if pending_at < 0:
                    errors.append(f"{log_path}: no pending learner-response assessment")
                else:
                    check_at = log.rfind("Active check:", 0, pending_at)
                    if check_at < 0:
                        errors.append(f"{log_path}: pending assessment has no preceding Active check")
                    else:
                        logged_check = log[check_at + len("Active check:") : pending_at].strip()
                        if normalized(logged_check) != normalized(canonical_check):
                            errors.append(
                                f"{log_path}: pending Active check differs from the canonical lesson"
                            )

    should_validate_closeout = require_closeout or note_meta.get("status") in CLOSED_STATUSES
    if should_validate_closeout:
        errors.extend(
            validate_closeout(
                note_path,
                log_path,
                note_meta,
                log_meta,
                note,
                log,
                current_status,
            )
        )

    return errors, canonical_check


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_note", type=Path)
    parser.add_argument("session_log", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--require-active-check", action="store_true")
    mode.add_argument("--require-closeout", action="store_true")
    args = parser.parse_args()

    for path in (args.session_note, args.session_log):
        if not path.is_file():
            print(f"ERROR: file does not exist: {path}", file=sys.stderr)
            return 2

    errors, check = validate(
        args.session_note,
        args.session_log,
        args.require_active_check,
        args.require_closeout,
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"VALID: {args.session_note} ↔ {args.session_log}")
    if args.require_active_check and check:
        print("ACTIVE_CHECK_BEGIN")
        print(check)
        print("ACTIVE_CHECK_END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
