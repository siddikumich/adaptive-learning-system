from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from session_fixtures import session_log, session_note


TEACH_ROOT = Path(__file__).resolve().parents[1]
FACTORY = TEACH_ROOT / "scripts" / "session_factory.py"
VALIDATOR = TEACH_ROOT / "scripts" / "validate_session.py"
RETRIEVAL = TEACH_ROOT.parents[0] / "retrieve" / "scripts" / "retrieval_state.py"


class CurrentProtocolLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "Source.md"
        self.source.write_text("# Source\n\nThe scoped rule is grounded here.\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def command(self, *args: str, success: bool = True) -> subprocess.CompletedProcess[str]:
        run = subprocess.run(list(args), text=True, capture_output=True)
        if success:
            self.assertEqual(run.returncode, 0, run.stderr)
        return run

    def assess(self, note: Path, attempt_id: str, now: str) -> None:
        answer = self.root / f"answer-{attempt_id}.txt"
        assessment = self.root / f"assessment-{attempt_id}.json"
        answer.write_text("A source-grounded production answer.", encoding="utf-8")
        assessment.write_text(
            json.dumps(
                {
                    "outcome": "pass",
                    "source_lesson_basis": ["[[Source]]", "Node 1 — Scoped foundation"],
                    "rationale": "The response states and applies the scoped invariant.",
                    "corrective_feedback": "",
                }
            ),
            encoding="utf-8",
        )
        self.command(
            sys.executable,
            str(RETRIEVAL),
            "record",
            str(note),
            "--attempt-id",
            attempt_id,
            "--answer-file",
            str(answer),
            "--assessment-file",
            str(assessment),
            "--now",
            now,
        )

    def prepare(self, note: Path, now: str) -> str:
        run = self.command(
            sys.executable,
            str(RETRIEVAL),
            "prepare",
            str(note),
            "--now",
            now,
        )
        return run.stdout.split("ATTEMPT_ID: ", 1)[1].splitlines()[0]

    def test_factory_teaching_closeout_and_both_delayed_passes(self) -> None:
        created = self.command(
            sys.executable,
            str(FACTORY),
            "Lifecycle",
            "--output-dir",
            str(self.root),
            "--created",
            "2026-01-01",
            "--source-note",
            str(self.source),
        )
        self.assertIn("PROTOCOL_VERSION: 2026-08-26.1", created.stdout)
        note = self.root / "Lifecycle.md"
        log = self.root / "Lifecycle — Session Log.md"
        self.command(sys.executable, str(VALIDATOR), str(note), str(log))

        note.write_text(
            session_note("Lifecycle", status="teaching"), encoding="utf-8"
        )
        log.write_text(
            session_log("Lifecycle", status="active", pending=True), encoding="utf-8"
        )
        self.command(
            sys.executable,
            str(VALIDATOR),
            str(note),
            str(log),
            "--require-active-check",
        )

        note.write_text(session_note("Lifecycle"), encoding="utf-8")
        log.write_text(session_log("Lifecycle"), encoding="utf-8")
        self.command(
            sys.executable,
            str(VALIDATOR),
            str(note),
            str(log),
            "--require-closeout",
        )

        initial = self.prepare(note, "2026-01-03T09:00:00-05:00")
        self.assess(note, initial, "2026-01-03T09:05:00-05:00")
        interleaved = self.prepare(note, "2026-01-08T09:00:00-05:00")
        self.assess(note, interleaved, "2026-01-08T09:05:00-05:00")

        self.command(
            sys.executable,
            str(RETRIEVAL),
            "validate",
            str(note),
            str(log),
            "--require-complete",
        )
        self.command(
            sys.executable,
            str(VALIDATOR),
            str(note),
            str(log),
            "--require-closeout",
        )
        final = note.read_text(encoding="utf-8")
        self.assertIn("protocol-version: \"2026-08-26.1\"", final)
        self.assertIn("status: complete", final)
        self.assertIn("retrieval-passes: 2", final)


if __name__ == "__main__":
    unittest.main()
