from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from session_fixtures import ACTIVE_CHECK, session_log, session_note, write_closed_session


VALIDATOR = Path(__file__).resolve().parents[1] / "scripts" / "validate_session.py"
SPEC = importlib.util.spec_from_file_location("teach_validate_session", VALIDATOR)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = validator
SPEC.loader.exec_module(validator)


class SessionValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_validator(self, note: Path, log: Path, *flags: str, success: bool = True):
        run = subprocess.run(
            [sys.executable, str(VALIDATOR), str(note), str(log), *flags],
            text=True,
            capture_output=True,
        )
        if success:
            self.assertEqual(run.returncode, 0, run.stderr)
        return run

    def test_valid_closeout_requires_resolvable_source_and_exact_initial_due(self) -> None:
        note, log = write_closed_session(self.root)
        self.run_validator(note, log, "--require-closeout")

        note.write_text(
            note.read_text(encoding="utf-8").replace('source-note: "[[Source]]"', 'source-note: "[[Missing]]"'),
            encoding="utf-8",
        )
        missing = self.run_validator(note, log, "--require-closeout", success=False)
        self.assertIn("source-note must link to an existing Markdown note", missing.stderr)

        note.write_text(session_note("Lifecycle", due="2026-01-04"), encoding="utf-8")
        wrong_due = self.run_validator(note, log, "--require-closeout", success=False)
        self.assertIn("retrieval-started + 2 calendar days", wrong_due.stderr)

    def test_active_check_allows_outer_trim_only(self) -> None:
        (self.root / "Source.md").write_text("# Source\n", encoding="utf-8")
        note = self.root / "Active.md"
        log = self.root / "Active — Session Log.md"
        note.write_text(session_note("Active", status="teaching"), encoding="utf-8")
        log.write_text(session_log("Active", status="active", pending=True), encoding="utf-8")
        valid = self.run_validator(note, log, "--require-active-check")
        self.assertIn(ACTIVE_CHECK, valid.stdout)

        log.write_text(
            log.read_text(encoding="utf-8").replace("one invariant", "one  invariant"),
            encoding="utf-8",
        )
        changed = self.run_validator(note, log, "--require-active-check", success=False)
        self.assertIn("differs from the canonical lesson", changed.stderr)

    def test_source_link_resolves_vault_paths_anchors_and_unique_basenames(self) -> None:
        source_dir = self.root / "Sources"
        session_dir = self.root / "Sessions"
        source_dir.mkdir()
        session_dir.mkdir()
        source = source_dir / "Primary Source.md"
        source.write_text("# Primary source\n", encoding="utf-8")
        note = session_dir / "Session.md"

        self.assertEqual(
            validator.linked_markdown_path(
                note, "[[Sources/Primary Source#Relevant claim]]", self.root
            ),
            source.resolve(),
        )
        self.assertEqual(
            validator.linked_markdown_path(note, "[[Primary Source]]", self.root),
            source.resolve(),
        )
        duplicate_dir = self.root / "Other"
        duplicate_dir.mkdir()
        (duplicate_dir / source.name).write_text("# Duplicate\n", encoding="utf-8")
        self.assertIsNone(
            validator.linked_markdown_path(note, "[[Primary Source]]", self.root)
        )


if __name__ == "__main__":
    unittest.main()
