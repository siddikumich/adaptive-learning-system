#!/usr/bin/env python3
"""Transactional state helper for delayed learning-session retrieval."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterator
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


SCHEMA = "1"
STAGES = {"initial", "interleaved", "complete"}
OUTCOMES = {"pass", "partial", "miss", "ungradable"}
CANONICAL = (
    "retrieval-schema",
    "retrieval-enabled",
    "retrieval-timezone",
    "retrieval-started",
    "retrieval-stage",
    "retrieval-required-passes",
    "retrieval-passes",
    "next-retrieval",
    "status",
)


class RetrievalError(ValueError):
    """A repairable session or command error."""


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_frontmatter(text: str, path: Path) -> tuple[dict[str, str], str, list[str]]:
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        raise RetrievalError(f"{path}: missing YAML frontmatter")
    values: dict[str, str] = {}
    order: list[str] = []
    for line in match.group(1).splitlines():
        if not line or line[0].isspace() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        if key:
            values[key] = value.strip().strip('"').strip("'")
            order.append(key)
    return values, match.group(0), order


def quote_value(value: str) -> str:
    if value in {"true", "false"}:
        return value
    if value == "" or any(c in value for c in ":#[]{}"):
        return json.dumps(value)
    return value


def replace_frontmatter(text: str, updates: dict[str, str]) -> str:
    _, block, _ = parse_frontmatter(text, Path("<text>"))
    body = block.removeprefix("---\n").removesuffix("---\n")
    rendered: list[str] = []
    replaced: set[str] = set()
    for line in body.splitlines():
        if line and not line[0].isspace() and ":" in line:
            key = line.split(":", 1)[0].strip()
            if key in updates:
                if key not in replaced:
                    rendered.append(f"{key}: {quote_value(updates[key])}")
                    replaced.add(key)
                continue
        rendered.append(line)
    for key, value in updates.items():
        if key not in replaced:
            rendered.append(f"{key}: {quote_value(value)}")
    return "---\n" + "\n".join(rendered) + "\n---\n" + text[len(block) :]


def section(text: str, heading: str) -> tuple[int, int, str] | None:
    match = re.search(rf"^## {re.escape(heading)}\s*$\n(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
    if not match:
        return None
    return match.start(1), match.end(1), match.group(1)


def local_date(value: str | None, zone: ZoneInfo) -> date:
    if not value:
        return datetime.now(zone).date()
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise RetrievalError(f"invalid --now ISO-8601 value: {value!r}") from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=zone)
    return parsed.astimezone(zone).date()


def as_date(value: str, label: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise RetrievalError(f"{label} must be YYYY-MM-DD") from error


def link_target(value: str) -> str | None:
    match = re.fullmatch(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", value.strip())
    return match.group(1).strip() if match else None


def resolve_link(note_path: Path, value: str) -> Path | None:
    target = link_target(value)
    if not target:
        return None
    candidate = note_path.parent / target
    if candidate.suffix.lower() != ".md":
        candidate = candidate.with_suffix(".md")
    return candidate if candidate.is_file() else None


def prompt_from_note(text: str, stage: str) -> str:
    name = "Initial" if stage == "initial" else "Interleaved"
    boundary = r"^#### |^### |^## |^(?:Known|Inference|Unknown|To verify|Smallest next action):|\Z"
    pattern = rf"^#### {name} retrieval prompt\s*$\n(.*?)(?={boundary})"
    matches = list(re.finditer(pattern, text, re.MULTILINE | re.DOTALL))
    if len(matches) != 1 or not matches[0].group(1).strip():
        raise RetrievalError(f"requires exactly one nonblank {name.lower()} retrieval prompt")
    return matches[0].group(1).strip()


def prompt_fingerprint(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def legacy_prompts(text: str) -> tuple[str, str, str, str] | None:
    initial = re.search(
        r"^- Retrieve on:\s*(\d{4}-\d{2}-\d{2})\s*[—-]\s*(.+)$",
        text,
        re.MULTILINE,
    )
    interleaved = re.search(
        r"^- Interleave/discriminate on:\s*(\d{4}-\d{2}-\d{2})\s*[—-]\s*(.+)$",
        text,
        re.MULTILINE,
    )
    if not initial or not interleaved or not initial.group(2).strip() or not interleaved.group(2).strip():
        return None
    return (
        initial.group(1),
        initial.group(2).strip(),
        interleaved.group(1),
        interleaved.group(2).strip(),
    )


def closeout_date(log: str) -> date | None:
    # A dated closeout heading is evidence; generic metadata timestamps are not.
    found = re.findall(r"^#{2,4}\s+(?:\d{4}-\d{2}-\d{2}\s*[—-]\s*)?.*?closeout.*$", log, re.MULTILINE | re.IGNORECASE)
    for heading in reversed(found):
        match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", heading)
        if match:
            return as_date(match.group(1), "sidecar closeout date")
    return None


def canonical_block(stage: str, passes: int, next_due: str, initial: str, interleaved: str) -> str:
    return (
        "### Delayed retrieval\n\n"
        "- Completion criterion: Two committed delayed passes, in order "
        "(initial then interleaved), each presented after retrieval starts.\n"
        f"- Current stage: {stage}\n"
        f"- Next retrieval: {next_due}\n\n"
        "#### Initial retrieval prompt\n\n"
        f"{initial}\n\n"
        "#### Interleaved retrieval prompt\n\n"
        f"{interleaved}\n"
    )


def sync_smallest_next_action(text: str, stage: str, next_due: str) -> str:
    transfer = section(text, "Transfer and retrieval")
    if not transfer:
        return text
    start, end, body = transfer
    if stage == "complete":
        action = (
            "No scheduled retrieval remains for this session; use the capability "
            "normally and reopen the note only if later performance exposes a gap."
        )
    else:
        action = (
            f"Answer the {stage} retrieval prompt on {next_due} from memory before "
            "reopening the lesson."
        )
    changed, count = re.subn(
        r"^Smallest next action:.*$",
        f"Smallest next action: {action}",
        body,
        count=1,
        flags=re.MULTILINE,
    )
    if count == 0:
        return text
    return text[:start] + changed + text[end:]


def update_main_note(text: str, updates: dict[str, str], stage: str, passes: int, next_due: str, initial: str, interleaved: str) -> str:
    transfer = section(text, "Transfer and retrieval")
    if not transfer:
        raise RetrievalError("missing ## Transfer and retrieval")
    start, end, body = transfer
    delayed_pattern = r"^### Delayed retrieval\s*$\n.*?(?=^### |\Z)"
    replacement = canonical_block(stage, passes, next_due, initial, interleaved).rstrip() + "\n\n"
    if re.search(delayed_pattern, body, re.MULTILINE | re.DOTALL):
        body = re.sub(
            delayed_pattern,
            replacement,
            body,
            count=1,
            flags=re.MULTILINE | re.DOTALL,
        )
        changed = text[:start] + body.rstrip() + "\n" + text[end:]
        return replace_frontmatter(
            sync_smallest_next_action(changed, stage, next_due), updates
        )
    body = re.sub(r"^- (?:Retrieve on|Interleave/discriminate on):.*\n?", "", body, flags=re.MULTILINE)
    # Remove stale canonical prompt blocks before adding the single canonical pair.
    body = re.sub(
        r"^#### (?:Initial|Interleaved) retrieval prompt\s*$\n.*?(?=^#### |^### |\Z)",
        "",
        body,
        flags=re.MULTILINE | re.DOTALL,
    )
    clean = body.rstrip() + "\n\n" if body.strip() else "\n"
    changed = text[:start] + clean + canonical_block(stage, passes, next_due, initial, interleaved) + text[end:]
    return replace_frontmatter(
        sync_smallest_next_action(changed, stage, next_due), updates
    )


@dataclass
class Session:
    note_path: Path
    note: str
    meta: dict[str, str]
    log_path: Path
    log: str
    zone: ZoneInfo
    legacy: bool = False

    @property
    def stage(self) -> str:
        return self.meta.get("retrieval-stage", "")

    @property
    def due(self) -> str:
        return self.meta.get("next-retrieval", "")


def open_session(note_path: Path, allow_legacy: bool = True) -> Session:
    note_path = note_path.resolve()
    if not note_path.is_file():
        raise RetrievalError(f"session note does not exist: {note_path}")
    note = read_text(note_path)
    meta, _, _ = parse_frontmatter(note, note_path)
    if meta.get("type") != "learning-session":
        raise RetrievalError("type must be learning-session")
    log_path = resolve_link(note_path, meta.get("session-log", ""))
    if not log_path:
        raise RetrievalError("session-log must be a valid linked sidecar")
    log = read_text(log_path)
    log_meta, _, _ = parse_frontmatter(log, log_path)
    if log_meta.get("type") != "learning-session-log" or log_meta.get("session-note") != f"[[{note_path.stem}]]":
        raise RetrievalError("linked sidecar must be a reciprocal learning-session-log")
    timezone = meta.get("retrieval-timezone", "America/Detroit")
    try:
        zone = ZoneInfo(timezone)
    except ZoneInfoNotFoundError as error:
        raise RetrievalError(f"invalid retrieval-timezone {timezone!r}") from error
    legacy = meta.get("retrieval-schema") != SCHEMA
    if legacy and not allow_legacy:
        raise RetrievalError("retrieval-schema must be 1")
    return Session(note_path, note, meta, log_path, log, zone, legacy)


def validate_source_and_map(session: Session) -> list[str]:
    errors: list[str] = []
    if not resolve_link(session.note_path, session.meta.get("source-note", "")):
        errors.append("source-note must link to an existing source note")
    source = section(session.note, "Source pack")
    if not source or not re.search(r"^\s*-\s+.+\S", source[2], re.MULTILINE):
        errors.append("Source pack must contain a source entry")
    learner = section(session.note, "Learner map")
    if not learner or not re.search(r"^Current node:\s*\S", learner[2], re.MULTILINE):
        errors.append("Learner map must name a current node")
    return errors


def canonical_errors(session: Session, require_prompts: bool = True) -> list[str]:
    m = session.meta
    errors = validate_source_and_map(session)
    if m.get("retrieval-schema") != SCHEMA:
        errors.append("retrieval-schema must be \"1\"")
    if m.get("retrieval-enabled", "").casefold() != "true":
        errors.append("retrieval-enabled must be true")
    if m.get("retrieval-required-passes") != "2":
        errors.append("retrieval-required-passes must be 2")
    if m.get("retrieval-stage") not in STAGES:
        errors.append("retrieval-stage must be initial, interleaved, or complete")
    if m.get("retrieval-passes") not in {"0", "1", "2"}:
        errors.append("retrieval-passes must be 0, 1, or 2")
    if not m.get("retrieval-started"):
        errors.append("retrieval-started is required")
    else:
        try:
            as_date(m["retrieval-started"], "retrieval-started")
        except RetrievalError as error:
            errors.append(str(error))
    stage = m.get("retrieval-stage", "")
    status = m.get("status", "")
    log_meta, _, _ = parse_frontmatter(session.log, session.log_path)
    if log_meta.get("status") != status:
        errors.append("session-log status must match session status")
    if stage == "complete":
        if m.get("retrieval-passes") != "2" or status != "complete" or m.get("next-retrieval", ""):
            errors.append("complete retrieval requires 2 passes, status complete, and blank next-retrieval")
    else:
        if status != "awaiting-retrieval":
            errors.append("incomplete retrieval requires status awaiting-retrieval")
        try:
            as_date(m.get("next-retrieval", ""), "next-retrieval")
        except RetrievalError as error:
            errors.append(str(error))
    if require_prompts:
        for which in ("initial", "interleaved"):
            try:
                prompt_from_note(session.note, which)
            except RetrievalError as error:
                errors.append(str(error))
        prepared = pending(session.log)
        if prepared:
            stage = str(prepared.get("stage", ""))
            try:
                if stage not in {"initial", "interleaved"} or prepared.get("fingerprint") != prompt_fingerprint(prompt_from_note(session.note, stage)):
                    errors.append("prepared attempt prompt fingerprint does not match the current prompt")
            except RetrievalError as error:
                errors.append(str(error))
    return errors


def events(log: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for raw in re.findall(r"<!-- retrieval-event\s+(\{.*?\})\s+-->", log):
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if value.get("committed") is True:
            found.append(value)
    return found


def pending(log: str) -> dict[str, Any] | None:
    found: dict[str, Any] | None = None
    for raw in re.findall(r"<!-- retrieval-prepared\s+(\{.*?\})\s+-->", log):
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if value.get("active") is True:
            found = value
    if found and any(event.get("attempt_id") == found.get("attempt_id") for event in events(log)):
        return None
    return found


def marker(kind: str, data: dict[str, Any]) -> str:
    return f"<!-- {kind} {json.dumps(data, sort_keys=True, separators=(',', ':'))} -->"


def append_event(log_path: Path, content: str) -> None:
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write("\n" + content.rstrip() + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def atomic_write(path: Path, text: str) -> None:
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def session_lock(note_path: Path) -> Iterator[None]:
    path = note_path.with_name(note_path.name + ".retrieval.lock")
    payload = json.dumps({"pid": os.getpid(), "created": datetime.now().isoformat()})
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        try:
            info = json.loads(read_text(path))
            pid = int(info.get("pid", 0))
            os.kill(pid, 0)
        except ProcessLookupError:
            path.unlink(missing_ok=True)
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except (ValueError, OSError, json.JSONDecodeError):
            raise RetrievalError(f"session is locked: {path}")
        else:
            raise RetrievalError(f"session is locked: {path}")
    try:
        os.write(descriptor, payload.encode("utf-8"))
        os.close(descriptor)
        yield
    finally:
        path.unlink(missing_ok=True)


def migrate(session: Session) -> Session:
    if not session.legacy:
        return session
    if session.meta.get("protocol-version") != "2026-08-25.6":
        raise RetrievalError("legacy migration supports only protocol-version 2026-08-25.6")
    prompts = legacy_prompts(session.note)
    if not prompts:
        raise RetrievalError("legacy session has no usable Retrieve on and Interleave/discriminate on prompts")
    started = closeout_date(session.log)
    if not started:
        raise RetrievalError("legacy session needs repair: sidecar has no dated closeout to evidence retrieval-started")
    try:
        next_due = as_date(
            session.meta.get("next-retrieval", ""),
            "legacy next-retrieval",
        ).isoformat()
    except RetrievalError:
        next_due = as_date(prompts[0], "legacy Retrieve on date").isoformat()
    changed = update_main_note(
        session.note,
        {
            "retrieval-schema": SCHEMA,
            "retrieval-enabled": "true",
            "retrieval-timezone": "America/Detroit",
            "retrieval-started": started.isoformat(),
            "retrieval-stage": "initial",
            "retrieval-required-passes": "2",
            "retrieval-passes": "0",
            "next-retrieval": next_due,
            "status": "awaiting-retrieval",
        },
        "initial", 0, next_due, prompts[1], prompts[3],
    )
    atomic_write(session.note_path, changed)
    atomic_write(
        session.log_path,
        replace_frontmatter(session.log, {"status": "awaiting-retrieval"}),
    )
    return open_session(session.note_path, allow_legacy=False)


def desired_after(event_list: list[dict[str, Any]], session: Session) -> tuple[str, int, str, str]:
    """Replay committed events, returning stage, passes, due, and status."""
    started = as_date(session.meta["retrieval-started"], "retrieval-started")
    stage, passes, due, status = "initial", 0, (started + timedelta(days=2)).isoformat(), "awaiting-retrieval"
    for event in event_list:
        outcome, event_stage = event.get("outcome"), event.get("stage")
        if outcome == "ungradable":
            continue
        if event_stage != stage:
            continue
        assessed = as_date(
            str(event.get("assessed", event.get("presented", ""))),
            "event assessed date",
        )
        if outcome == "pass" and stage == "initial":
            stage, passes, due = "interleaved", 1, (assessed + timedelta(days=5)).isoformat()
        elif outcome == "pass" and stage == "interleaved":
            stage, passes, due, status = "complete", 2, "", "complete"
        elif outcome == "partial":
            due = (assessed + timedelta(days=2)).isoformat()
        elif outcome == "miss":
            due = (assessed + timedelta(days=1)).isoformat()
    return stage, passes, due, status


def sync_from_events(session: Session) -> Session:
    ev = events(session.log)
    if not ev:
        return session
    stage, passes, due, status = desired_after(ev, session)
    initial = prompt_from_note(session.note, "initial")
    interleaved = prompt_from_note(session.note, "interleaved")
    changed = update_main_note(session.note, {
        "retrieval-stage": stage, "retrieval-passes": str(passes), "next-retrieval": due, "status": status,
    }, stage, passes, due, initial, interleaved)
    atomic_write(session.note_path, changed)
    atomic_write(session.log_path, replace_frontmatter(session.log, {"status": status}))
    return open_session(session.note_path, allow_legacy=False)


def prepared_markdown(data: dict[str, Any]) -> str:
    return (
        f"### Retrieval attempt {data['attempt_id']} prepared\n\n"
        f"- Stage: `{data['stage']}`\n"
        f"- Scheduled date: {data['scheduled']}\n"
        f"- Prepared date: {data['presented']}\n"
        f"- Prompt fingerprint: `{data['fingerprint']}`\n"
        f"{marker('retrieval-prepared', data)}"
    )


def committed_markdown(data: dict[str, Any], answer: str, assessment: dict[str, Any]) -> str:
    longest = max((len(run) for run in re.findall(r"`+", answer)), default=0)
    fence = "`" * max(3, longest + 1)
    answer_block = answer if answer.endswith("\n") else answer + "\n"
    basis = assessment["source_lesson_basis"]
    if isinstance(basis, list):
        basis_text = "; ".join(basis)
    else:
        basis_text = basis
    return (
        f"### Retrieval attempt {data['attempt_id']} committed\n\n"
        f"- Stage: `{data['stage']}`\n"
        f"- Scheduled date: {data['scheduled']}\n"
        f"- Presented date: {data['presented']}\n"
        f"- Assessed date: {data.get('assessed', data['presented'])}\n"
        f"- Prompt fingerprint: `{data['fingerprint']}`\n\n"
        "#### Prompt\n\n" + data["prompt"] + "\n\n"
        "#### Verbatim answer\n\n" + fence + "text\n" + answer_block + fence + "\n\n"
        "#### Assessment\n\n"
        f"- Outcome: `{assessment['outcome']}`\n"
        f"- Source/lesson basis: {basis_text}\n"
        f"- Rationale: {assessment['rationale']}\n"
        f"- Corrective feedback: {assessment['corrective_feedback']}\n"
        f"- Next date: {data['next']}\n\n"
        f"{marker('retrieval-event', data)}\n"
        f"<!-- retrieval-transaction committed attempt-id={data['attempt_id']} -->"
    )


def validate_assessment(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(read_text(path))
    except (OSError, json.JSONDecodeError) as error:
        raise RetrievalError(f"invalid assessment JSON: {error}") from error
    if not isinstance(value, dict) or set(value) != {"outcome", "source_lesson_basis", "rationale", "corrective_feedback"}:
        raise RetrievalError("assessment JSON must contain exactly outcome, source_lesson_basis, rationale, corrective_feedback")
    if value["outcome"] not in OUTCOMES:
        raise RetrievalError("assessment outcome must be pass, partial, miss, or ungradable")
    basis = value["source_lesson_basis"]
    valid_basis = isinstance(basis, str) and bool(basis.strip()) or isinstance(basis, list) and bool(basis) and all(isinstance(x, str) and x.strip() for x in basis)
    if not valid_basis:
        raise RetrievalError("assessment source_lesson_basis must be a nonempty string or list of nonempty strings")
    if not isinstance(value["rationale"], str) or not value["rationale"].strip():
        raise RetrievalError("assessment rationale must be a nonempty string")
    if not isinstance(value["corrective_feedback"], str):
        raise RetrievalError("assessment corrective_feedback must be a string")
    return value


def prepare(note_path: Path, now: str | None) -> tuple[str, str]:
    with session_lock(note_path.resolve()):
        session = migrate(open_session(note_path))
        errors = canonical_errors(session)
        if errors:
            raise RetrievalError("; ".join(errors))
        session = sync_from_events(session)
        existing = pending(session.log)
        if existing:
            stage = str(existing.get("stage"))
            prompt = prompt_from_note(session.note, stage)
            if existing.get("fingerprint") != prompt_fingerprint(prompt):
                raise RetrievalError("prepared attempt prompt fingerprint does not match the current prompt; repair or recover it")
            return str(existing["attempt_id"]), prompt
        if session.stage == "complete":
            raise RetrievalError("retrieval is already complete")
        today = local_date(now, session.zone)
        if as_date(session.due, "next-retrieval") > today:
            raise RetrievalError(f"retrieval is not due until {session.due}")
        prompt = prompt_from_note(session.note, session.stage)
        data = {
            "schema": SCHEMA, "active": True, "attempt_id": uuid.uuid4().hex,
            "stage": session.stage, "scheduled": session.due,
            "presented": local_date(now, session.zone).isoformat(), "fingerprint": prompt_fingerprint(prompt),
        }
        append_event(session.log_path, prepared_markdown(data))
        return data["attempt_id"], prompt


def record(note_path: Path, attempt_id: str, answer_path: Path, assessment_path: Path, now: str | None) -> str:
    assessment = validate_assessment(assessment_path)
    answer = read_text(answer_path)
    answer_digest = hashlib.sha256(answer.encode("utf-8")).hexdigest()
    assessment_digest = hashlib.sha256(
        json.dumps(assessment, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    with session_lock(note_path.resolve()):
        session = migrate(open_session(note_path))
        existing_committed = next((event for event in events(session.log) if event.get("attempt_id") == attempt_id), None)
        if existing_committed:
            if (
                existing_committed.get("answer_fingerprint") not in {None, answer_digest}
                or existing_committed.get("assessment_fingerprint")
                not in {None, assessment_digest}
            ):
                raise RetrievalError(
                    "attempt is already committed with different answer or assessment content"
                )
            sync_from_events(session)
            return "IDEMPOTENT"
        current = pending(session.log)
        if not current or current.get("attempt_id") != attempt_id:
            raise RetrievalError("no matching prepared attempt")
        if session.stage != current.get("stage") or session.due != current.get("scheduled"):
            raise RetrievalError("prepared attempt no longer matches session state; recover before recording")
        prompt = prompt_from_note(session.note, session.stage)
        if current.get("fingerprint") != prompt_fingerprint(prompt):
            raise RetrievalError("prepared attempt prompt fingerprint does not match the current prompt")
        presented = str(current.get("presented", ""))
        assessed = local_date(now, session.zone).isoformat()
        started = as_date(session.meta["retrieval-started"], "retrieval-started")
        if assessment["outcome"] == "pass" and as_date(presented, "presented date") <= started:
            raise RetrievalError("a pass must be presented after retrieval-started")
        stage, passes, due, status = session.stage, int(session.meta["retrieval-passes"]), session.due, session.meta["status"]
        if assessment["outcome"] == "pass" and stage == "initial":
            next_stage, next_passes, next_due, next_status = "interleaved", 1, (date.fromisoformat(assessed) + timedelta(days=5)).isoformat(), "awaiting-retrieval"
        elif assessment["outcome"] == "pass" and stage == "interleaved":
            next_stage, next_passes, next_due, next_status = "complete", 2, "", "complete"
        elif assessment["outcome"] == "partial":
            next_stage, next_passes, next_due, next_status = stage, passes, (date.fromisoformat(assessed) + timedelta(days=2)).isoformat(), status
        elif assessment["outcome"] == "miss":
            next_stage, next_passes, next_due, next_status = stage, passes, (date.fromisoformat(assessed) + timedelta(days=1)).isoformat(), status
        else:
            next_stage, next_passes, next_due, next_status = stage, passes, due, status
        data = {
            "schema": SCHEMA, "committed": True, "attempt_id": attempt_id, "stage": stage,
            "scheduled": session.due, "presented": presented, "assessed": assessed,
            "fingerprint": prompt_fingerprint(prompt),
            "answer_fingerprint": answer_digest, "assessment_fingerprint": assessment_digest,
            "outcome": assessment["outcome"], "next": next_due, "prompt": prompt,
        }
        append_event(session.log_path, committed_markdown(data, answer, assessment))
        if assessment["outcome"] != "ungradable":
            changed = update_main_note(session.note, {
                "retrieval-stage": next_stage, "retrieval-passes": str(next_passes),
                "next-retrieval": next_due, "status": next_status,
            }, next_stage, next_passes, next_due, prompt_from_note(session.note, "initial"), prompt_from_note(session.note, "interleaved"))
            atomic_write(session.note_path, changed)
            current_log = read_text(session.log_path)
            atomic_write(
                session.log_path,
                replace_frontmatter(current_log, {"status": next_status}),
            )
        return "REPAIR_REQUIRED" if assessment["outcome"] == "ungradable" else "RECORDED"


def validate_retrieval_completion(note_path: Path, log_path: Path) -> list[str]:
    """Return completion invariant errors; designed for teach's validator import."""
    errors: list[str] = []
    try:
        session = open_session(note_path, allow_legacy=False)
    except RetrievalError as error:
        return [str(error)]
    if session.log_path.resolve() != log_path.resolve():
        return ["session log path does not match session-note link"]
    errors.extend(canonical_errors(session))
    if session.stage != "complete":
        errors.append("retrieval-stage must be complete")
        return errors
    try:
        start = as_date(session.meta.get("retrieval-started", ""), "retrieval-started")
    except RetrievalError as error:
        return errors + [str(error)]
    committed = events(session.log)
    passes = [event for event in committed if event.get("outcome") == "pass"]
    if len(passes) != 2:
        errors.append("completion requires exactly two committed pass events")
        return errors
    if [event.get("stage") for event in passes] != ["initial", "interleaved"]:
        errors.append("completion passes must be initial then interleaved")
    for event in passes:
        try:
            if as_date(str(event.get("presented", "")), "pass presented date") <= start:
                errors.append("each completion pass must be presented after retrieval-started")
        except RetrievalError as error:
            errors.append(str(error))
        current_prompt = prompt_from_note(session.note, str(event.get("stage")))
        if event.get("fingerprint") != prompt_fingerprint(current_prompt):
            errors.append("committed pass prompt fingerprint does not match canonical prompt")
    try:
        desired = desired_after(committed, session)
        observed = (session.stage, int(session.meta.get("retrieval-passes", "-1")), session.due, session.meta.get("status", ""))
        if desired != observed:
            errors.append("main retrieval state does not match committed sidecar events")
    except RetrievalError as error:
        errors.append(str(error))
    return errors


def recovery(note_path: Path) -> str:
    with session_lock(note_path.resolve()):
        session = migrate(open_session(note_path))
        errors = canonical_errors(session)
        if errors:
            raise RetrievalError("; ".join(errors))
        sync_from_events(session)
    return "RECOVERED"


def discovery(vault: Path, now: str | None) -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = {key: [] for key in ("due", "future", "blocked", "invalid", "excluded")}
    for path in sorted(vault.rglob("*.md"), key=lambda item: item.as_posix().casefold()):
        try:
            text = read_text(path)
            meta, _, _ = parse_frontmatter(text, path)
        except (OSError, RetrievalError):
            continue
        if meta.get("type") != "learning-session":
            continue
        relative = path.relative_to(vault).as_posix()
        if meta.get("interaction-mode") == "synthetic-harness":
            result["excluded"].append({"path": relative, "reason": "interaction-mode synthetic-harness"})
            continue
        if meta.get("retrieval-enabled", "").casefold() == "false":
            result["excluded"].append({"path": relative, "reason": "retrieval-enabled false"})
            continue
        if meta.get("status") not in {"awaiting-retrieval", "complete"}:
            result["excluded"].append(
                {"path": relative, "reason": f"status {meta.get('status', '<missing>')}"}
            )
            continue
        try:
            session = open_session(path)
        except RetrievalError as error:
            result["invalid"].append({"path": relative, "reason": str(error)})
            continue
        if session.legacy:
            if session.meta.get("protocol-version") != "2026-08-25.6":
                result["invalid"].append({"path": relative, "reason": "legacy migration supports only protocol-version 2026-08-25.6"})
                continue
            if legacy_prompts(session.note) and closeout_date(session.log):
                result["blocked"].append({"path": relative, "reason": "legacy session is migratable; run prepare or recover"})
            else:
                result["blocked"].append({"path": relative, "reason": "legacy session needs repair: no evidenced retrieval-started"})
            continue
        errors = (
            validate_retrieval_completion(session.note_path, session.log_path)
            if session.meta.get("status") == "complete"
            else canonical_errors(session)
        )
        if errors:
            result["invalid"].append({"path": relative, "reason": "; ".join(errors)})
            continue
        if session.stage == "complete":
            result["excluded"].append({"path": relative, "reason": "retrieval complete"})
            continue
        if pending(session.log):
            result["blocked"].append({"path": relative, "reason": "prepared retrieval attempt awaiting answer or record"})
            continue
        today = local_date(now, session.zone)
        due = as_date(session.due, "next-retrieval")
        item = {"path": relative, "due": session.due, "timezone": session.meta["retrieval-timezone"]}
        result["due" if due <= today else "future"].append(item)
    for key in ("due", "future"):
        result[key].sort(key=lambda item: (item["due"], item["path"].casefold()))
    for key in ("blocked", "invalid", "excluded"):
        result[key].sort(key=lambda item: item["path"].casefold())
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    discover = commands.add_parser("discover")
    discover.add_argument("vault_root", type=Path)
    discover.add_argument("--now")
    discover.add_argument("--json", action="store_true")
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("session_note", type=Path)
    prepare_parser.add_argument("--now")
    record_parser = commands.add_parser("record")
    record_parser.add_argument("session_note", type=Path)
    record_parser.add_argument("--attempt-id", required=True)
    record_parser.add_argument("--answer-file", required=True, type=Path)
    record_parser.add_argument("--assessment-file", required=True, type=Path)
    record_parser.add_argument("--now")
    recover_parser = commands.add_parser("recover")
    recover_parser.add_argument("session_note", type=Path)
    recover_parser.add_argument("--now")
    validate_parser = commands.add_parser("validate")
    validate_parser.add_argument("session_note", type=Path)
    validate_parser.add_argument("session_log", type=Path)
    validate_parser.add_argument("--now")
    validate_parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "discover":
            payload = discovery(args.vault_root.resolve(), args.now)
            if args.json:
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                for category, items in payload.items():
                    for item in items:
                        print(f"{category.upper()}: {item['path']} — {item.get('due', item['reason'])}")
        elif args.command == "prepare":
            attempt_id, prompt = prepare(args.session_note, args.now)
            print(f"ATTEMPT_ID: {attempt_id}")
            print("PROMPT_BEGIN")
            print(prompt)
            print("PROMPT_END")
        elif args.command == "record":
            print(record(args.session_note, args.attempt_id, args.answer_file, args.assessment_file, args.now))
        elif args.command == "recover":
            print(recovery(args.session_note))
        else:
            if args.require_complete:
                errors = validate_retrieval_completion(args.session_note, args.session_log)
            else:
                session = open_session(args.session_note, allow_legacy=False)
                errors = canonical_errors(session)
                if session.log_path.resolve() != args.session_log.resolve():
                    errors.append("session log path does not match session-note link")
            if errors:
                for error in errors:
                    print(f"ERROR: {error}", file=sys.stderr)
                return 1
            print(f"VALID: {args.session_note} ↔ {args.session_log}")
        return 0
    except (OSError, RetrievalError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
