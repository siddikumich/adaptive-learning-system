from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "retrieval_state.py"
sys.path.insert(0, str(SCRIPT.parent))
import retrieval_state as state  # noqa: E402


class RetrievalStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "Source.md").write_text("# Generic source\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def make_session(self, name: str = "Session", *, start: str = "2026-01-01", due: str | None = None, stage: str = "initial", passes: int = 0, status: str = "awaiting-retrieval", timezone: str = "America/Detroit", synthetic: bool = False, enabled: str = "true") -> tuple[Path, Path]:
        due = due if due is not None else (date.fromisoformat(start) + timedelta(days=2)).isoformat()
        if stage == "complete":
            due = ""
            passes = 2
            status = "complete"
        mode = "synthetic-harness" if synthetic else "obsidian-read-cli-answer"
        note = self.root / f"{name}.md"
        log = self.root / f"{name} Log.md"
        note.write_text(f'''---
type: learning-session
status: {status}
protocol-version: "2026-08-25.6"
source-note: "[[Source]]"
session-log: "[[{name} Log]]"
interaction-mode: {mode}
retrieval-schema: "1"
retrieval-enabled: {enabled}
retrieval-timezone: {timezone}
retrieval-started: {start}
retrieval-stage: {stage}
retrieval-required-passes: 2
retrieval-passes: {passes}
next-retrieval: "{due}"
---

# {name}

## Source pack

- [[Source]]

## Learner map

Current node: generic distinction

## Transfer and retrieval

### Delayed retrieval

- Completion criterion: Two committed delayed passes, in order (initial then interleaved), each presented after retrieval starts.
- Current stage: {stage}
- Next retrieval: {due}

#### Initial retrieval prompt

Explain the generic rule in one sentence.

#### Interleaved retrieval prompt

Distinguish the generic rule from a nearby alternative.

### Evidence boundary

Known: generic source fact.

Inference: generic learner interpretation.

Unknown: delayed retention.

To verify: delayed production.

Smallest next action: answer the scheduled prompt.
''', encoding="utf-8")
        log.write_text(f'''---
type: learning-session-log
status: awaiting-retrieval
session-note: "[[{name}]]"
---

# {name} Log
''', encoding="utf-8")
        return note, log

    def command(self, *arguments: str, success: bool = True) -> subprocess.CompletedProcess[str]:
        run = subprocess.run([sys.executable, str(SCRIPT), *arguments], text=True, capture_output=True)
        if success:
            self.assertEqual(run.returncode, 0, run.stderr)
        return run

    def prepare(self, note: Path, now: str = "2026-01-03T10:00:00-05:00") -> str:
        run = self.command("prepare", str(note), "--now", now)
        self.assertEqual(run.stdout.count("PROMPT_BEGIN"), 1)
        self.assertEqual(run.stdout.count("PROMPT_END"), 1)
        self.assertNotIn("Known:", run.stdout)
        return run.stdout.split("ATTEMPT_ID: ", 1)[1].splitlines()[0]

    def record(self, note: Path, attempt: str, outcome: str, now: str, answer: str = "generic answer") -> subprocess.CompletedProcess[str]:
        answer_path, assessment_path = self.root / "answer.txt", self.root / "assessment.json"
        answer_path.write_text(answer, encoding="utf-8")
        assessment_path.write_text(json.dumps({"outcome": outcome, "source_lesson_basis": ["[[Source]]", "generic lesson"], "rationale": "generic grounded judgment", "corrective_feedback": "generic feedback"}), encoding="utf-8")
        return self.command("record", str(note), "--attempt-id", attempt, "--answer-file", str(answer_path), "--assessment-file", str(assessment_path), "--now", now)

    def metadata(self, note: Path) -> dict[str, str]:
        return state.parse_frontmatter(note.read_text(encoding="utf-8"), note)[0]

    def test_discovery_due_future_and_order(self) -> None:
        self.make_session("Zeta", due="2026-01-05")
        self.make_session("Alpha", due="2026-01-03")
        self.make_session("Beta", due="2026-01-03")
        found = state.discovery(self.root, "2026-01-03T08:00:00-05:00")
        self.assertEqual([item["path"] for item in found["due"]], ["Alpha.md", "Beta.md"])
        self.assertEqual(found["future"][0]["path"], "Zeta.md")

    def test_late_pass_uses_assessment_date(self) -> None:
        note, _ = self.make_session(due="2026-01-03")
        attempt = self.prepare(note, "2026-01-07T23:30:00-05:00")
        self.record(note, attempt, "pass", "2026-01-07T23:30:00-05:00")
        metadata = self.metadata(note)
        self.assertEqual(metadata["retrieval-stage"], "interleaved")
        self.assertEqual(metadata["next-retrieval"], "2026-01-12")
        self.assertIn("- Scheduled date: 2026-01-03", (self.root / "Session Log.md").read_text(encoding="utf-8"))

    def test_partial_miss_retry_and_completion(self) -> None:
        note, log = self.make_session()
        first = self.prepare(note)
        self.record(note, first, "partial", "2026-01-03T09:00:00-05:00")
        self.assertEqual(self.metadata(note)["next-retrieval"], "2026-01-05")
        second = self.prepare(note, "2026-01-05T09:00:00-05:00")
        self.record(note, second, "miss", "2026-01-05T09:00:00-05:00")
        self.assertEqual(self.metadata(note)["next-retrieval"], "2026-01-06")
        third = self.prepare(note, "2026-01-06T09:00:00-05:00")
        self.record(note, third, "pass", "2026-01-06T09:00:00-05:00")
        fourth = self.prepare(note, "2026-01-11T09:00:00-05:00")
        self.record(note, fourth, "pass", "2026-01-11T09:00:00-05:00")
        self.assertEqual(self.metadata(note)["status"], "complete")
        self.assertEqual(self.metadata(log)["status"], "complete")
        final_note = note.read_text(encoding="utf-8")
        self.assertIn("Smallest next action: No scheduled retrieval remains", final_note)
        self.assertNotIn("Smallest next action: answer the scheduled prompt", final_note)
        self.assertEqual(state.validate_retrieval_completion(note, log), [])

    def test_ungradable_does_not_mutate_state(self) -> None:
        note, _ = self.make_session()
        before = self.metadata(note)
        attempt = self.prepare(note)
        result = self.record(note, attempt, "ungradable", "2026-01-03T09:00:00-05:00")
        self.assertIn("REPAIR_REQUIRED", result.stdout)
        after = self.metadata(note)
        for key in ("retrieval-stage", "retrieval-passes", "next-retrieval", "status"):
            self.assertEqual(after[key], before[key])

    def test_raw_answer_and_assessment_stay_in_sidecar(self) -> None:
        note, log = self.make_session()
        attempt = self.prepare(note)
        self.record(note, attempt, "pass", "2026-01-03T09:00:00-05:00", "RAW-UNIQUE-ANSWER")
        self.assertNotIn("RAW-UNIQUE-ANSWER", note.read_text(encoding="utf-8"))
        self.assertIn("RAW-UNIQUE-ANSWER", log.read_text(encoding="utf-8"))
        self.assertNotIn("generic grounded judgment", note.read_text(encoding="utf-8"))

    def test_prepare_and_record_are_idempotent(self) -> None:
        note, log = self.make_session()
        one = self.prepare(note)
        two = self.prepare(note)
        self.assertEqual(one, two)
        self.record(note, one, "pass", "2026-01-03T09:00:00-05:00")
        retry = self.record(note, one, "pass", "2026-01-03T09:00:00-05:00")
        self.assertIn("IDEMPOTENT", retry.stdout)
        self.assertEqual(len(state.events(log.read_text(encoding="utf-8"))), 1)
        answer_path = self.root / "answer.txt"
        answer_path.write_text("different answer", encoding="utf-8")
        conflict = self.command(
            "record", str(note), "--attempt-id", one,
            "--answer-file", str(answer_path),
            "--assessment-file", str(self.root / "assessment.json"),
            "--now", "2026-01-03T09:00:00-05:00", success=False,
        )
        self.assertIn("different answer", conflict.stderr)

    def test_future_prepare_is_blocked_and_frontmatter_is_preserved(self) -> None:
        note, _ = self.make_session(due="2026-01-05")
        text = note.read_text(encoding="utf-8").replace(
            "---\n\n# Session", "tags:\n  - learnings\n---\n\n# Session"
        )
        note.write_text(text, encoding="utf-8")
        early = self.command(
            "prepare", str(note), "--now", "2026-01-03T09:00:00-05:00", success=False
        )
        self.assertIn("not due until", early.stderr)
        attempt = self.prepare(note, "2026-01-05T09:00:00-05:00")
        self.record(note, attempt, "pass", "2026-01-05T09:00:00-05:00")
        self.assertIn("  - learnings", note.read_text(encoding="utf-8"))

    def test_lock_conflict_and_stale_lock_recovery(self) -> None:
        note, _ = self.make_session()
        lock = note.with_name(note.name + ".retrieval.lock")
        lock.write_text(json.dumps({"pid": os.getpid()}), encoding="utf-8")
        blocked = self.command("prepare", str(note), success=False)
        self.assertNotEqual(blocked.returncode, 0)
        lock.write_text(json.dumps({"pid": 99999999}), encoding="utf-8")
        self.prepare(note)
        self.assertFalse(lock.exists())

    def test_recover_syncs_interrupted_commit(self) -> None:
        note, log = self.make_session()
        attempt = self.prepare(note)
        session = state.open_session(note)
        prompt = state.prompt_from_note(session.note, "initial")
        event = {"schema": "1", "committed": True, "attempt_id": attempt, "stage": "initial", "scheduled": "2026-01-03", "presented": "2026-01-03", "fingerprint": state.prompt_fingerprint(prompt), "outcome": "pass", "next": "2026-01-08", "prompt": prompt}
        state.append_event(log, state.committed_markdown(event, "answer", {"outcome": "pass", "source_lesson_basis": "generic", "rationale": "generic", "corrective_feedback": ""}))
        self.assertEqual(self.metadata(note)["retrieval-stage"], "initial")
        self.command("recover", str(note))
        self.assertEqual(self.metadata(note)["retrieval-stage"], "interleaved")

    def test_invalid_metadata_and_exclusion(self) -> None:
        bad, _ = self.make_session("Bad", timezone="Not/AZone")
        bad_meta, _ = self.make_session("BadMeta")
        bad_meta.write_text(bad_meta.read_text(encoding="utf-8").replace("retrieval-passes: 0", "retrieval-passes: 4"), encoding="utf-8")
        synthetic, _ = self.make_session("Synthetic", synthetic=True)
        disabled, _ = self.make_session("Disabled", enabled="false")
        probing, _ = self.make_session("Probing")
        probing.write_text(
            probing.read_text(encoding="utf-8").replace(
                "status: awaiting-retrieval", "status: probing", 1
            ),
            encoding="utf-8",
        )
        found = state.discovery(self.root, "2026-01-03T09:00:00-05:00")
        self.assertTrue(any(item["path"] == bad.name for item in found["invalid"]))
        self.assertTrue(any(item["path"] == bad_meta.name for item in found["invalid"]))
        self.assertEqual(
            {item["path"] for item in found["excluded"]},
            {synthetic.name, disabled.name, probing.name},
        )

    def test_invalid_prompt_source_and_sidecar_link_are_reported(self) -> None:
        bad_prompt, _ = self.make_session("BadPrompt")
        bad_prompt.write_text(bad_prompt.read_text(encoding="utf-8").replace("Distinguish the generic rule from a nearby alternative.", ""), encoding="utf-8")
        bad_source, _ = self.make_session("BadSource")
        bad_source.write_text(bad_source.read_text(encoding="utf-8").replace("[[Source]]", "[[Missing source]]", 1), encoding="utf-8")
        bad_link, _ = self.make_session("BadLink")
        bad_link.write_text(bad_link.read_text(encoding="utf-8").replace("[[BadLink Log]]", "[[Missing Log]]"), encoding="utf-8")
        found = state.discovery(self.root, "2026-01-03T09:00:00-05:00")
        invalid = {item["path"]: item["reason"] for item in found["invalid"]}
        self.assertIn("interleaved", invalid[bad_prompt.name])
        self.assertIn("source-note", invalid[bad_source.name])
        self.assertIn("session-log", invalid[bad_link.name])

    def test_legacy_success_and_repair_required_failure(self) -> None:
        note, log = self.make_session("Legacy")
        legacy = note.read_text(encoding="utf-8")
        legacy = re_sub_many(legacy, [(r"retrieval-schema: \"1\"\n", ""), (r"retrieval-enabled: true\n", ""), (r"retrieval-timezone: America/Detroit\n", ""), (r"retrieval-started: 2026-01-01\n", ""), (r"retrieval-stage: initial\n", ""), (r"retrieval-required-passes: 2\n", ""), (r"retrieval-passes: 0\n", ""), (r"next-retrieval: \"2026-01-03\"\n", "")])
        legacy = legacy.replace("### Delayed retrieval", "- Retrieve on: 2026-01-03 — first generic prompt\n- Interleave/discriminate on: 2026-01-08 — second generic prompt\n\n### Legacy retrieval")
        note.write_text(legacy, encoding="utf-8")
        log.write_text(log.read_text(encoding="utf-8") + "\n## 2026-01-01 closeout\n", encoding="utf-8")
        found = state.discovery(self.root, "2026-01-03T09:00:00-05:00")
        self.assertTrue(any(item["path"] == note.name and "migratable" in item["reason"] for item in found["blocked"]))
        self.prepare(note)
        self.assertEqual(self.metadata(note)["retrieval-started"], "2026-01-01")
        no_date, _ = self.make_session("NoDate")
        text = no_date.read_text(encoding="utf-8").replace("retrieval-schema: \"1\"\n", "").replace("### Delayed retrieval", "- Retrieve on: 2026-01-03 — first\n- Interleave/discriminate on: 2026-01-08 — second\n\n### Legacy")
        no_date.write_text(text, encoding="utf-8")
        found = state.discovery(self.root, "2026-01-03T09:00:00-05:00")
        self.assertTrue(any(item["path"] == no_date.name and "repair" in item["reason"] for item in found["blocked"]))

    def test_digest_mismatch_and_wrong_order_fake_completion(self) -> None:
        note, log = self.make_session()
        attempt = self.prepare(note)
        note.write_text(note.read_text(encoding="utf-8").replace("Explain the generic rule in one sentence.", "Changed prompt."), encoding="utf-8")
        answer, assessment = self.root / "answer", self.root / "assessment"
        answer.write_text("answer", encoding="utf-8")
        assessment.write_text(json.dumps({"outcome": "pass", "source_lesson_basis": "generic", "rationale": "generic", "corrective_feedback": ""}), encoding="utf-8")
        self.assertNotEqual(self.command("record", str(note), "--attempt-id", attempt, "--answer-file", str(answer), "--assessment-file", str(assessment), success=False).returncode, 0)
        note2, log2 = self.make_session("Fake", stage="complete")
        session = state.open_session(note2)
        for attempt_id, stage in (("wrong-first", "interleaved"), ("wrong-second", "initial")):
            prompt = state.prompt_from_note(session.note, stage)
            event = {"schema": "1", "committed": True, "attempt_id": attempt_id, "stage": stage, "scheduled": "2026-01-04", "presented": "2026-01-04", "fingerprint": state.prompt_fingerprint(prompt), "outcome": "pass", "next": "", "prompt": prompt}
            state.append_event(log2, state.committed_markdown(event, "answer", {"outcome": "pass", "source_lesson_basis": "generic", "rationale": "generic", "corrective_feedback": ""}))
        errors = state.validate_retrieval_completion(note2, log2)
        self.assertTrue(any("initial then interleaved" in error for error in errors))

    def test_validate_rejects_same_day_completion(self) -> None:
        note, log = self.make_session(start="2026-01-03", stage="complete")
        session = state.open_session(note)
        for attempt_id, stage in (("same-day-initial", "initial"), ("same-day-interleaved", "interleaved")):
            prompt = state.prompt_from_note(session.note, stage)
            event = {
                "schema": "1", "committed": True, "attempt_id": attempt_id,
                "stage": stage, "scheduled": "2026-01-03", "presented": "2026-01-03",
                "assessed": "2026-01-03", "fingerprint": state.prompt_fingerprint(prompt),
                "outcome": "pass", "next": "", "prompt": prompt,
            }
            state.append_event(
                log,
                state.committed_markdown(
                    event, "answer",
                    {"outcome": "pass", "source_lesson_basis": "generic", "rationale": "generic", "corrective_feedback": ""},
                ),
            )
        errors = state.validate_retrieval_completion(note, log)
        self.assertTrue(any("after retrieval-started" in error for error in errors))


def re_sub_many(text: str, replacements: list[tuple[str, str]]) -> str:
    import re
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text)
    return text


if __name__ == "__main__":
    unittest.main()
