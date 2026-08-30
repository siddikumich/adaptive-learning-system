from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "session_factory.py"
SPEC = importlib.util.spec_from_file_location("teach_session_factory", SCRIPT)
assert SPEC and SPEC.loader
factory = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = factory
SPEC.loader.exec_module(factory)


class SessionFactoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_creates_current_reciprocal_pair_with_source(self) -> None:
        source = self.root / "Source.md"
        source.write_text("# Source\n", encoding="utf-8")
        note, log = factory.create_session(
            self.root, "New Session", "2026-01-01", source
        )
        note_text = note.read_text(encoding="utf-8")
        log_text = log.read_text(encoding="utf-8")
        self.assertIn('protocol-version: "2026-08-26.1"', note_text)
        self.assertIn('session-log: "[[New Session — Session Log]]"', note_text)
        self.assertIn('source-note: "[[Source]]"', note_text)
        self.assertIn('session-note: "[[New Session]]"', log_text)
        self.assertNotIn("{{title}}", note_text + log_text)
        self.assertNotIn("{{date:YYYY-MM-DD}}", note_text + log_text)

    def test_refuses_partial_or_total_overwrite(self) -> None:
        (self.root / "Existing.md").write_text("mine", encoding="utf-8")
        with self.assertRaisesRegex(factory.FactoryError, "refusing to overwrite"):
            factory.create_session(self.root, "Existing", "2026-01-01")
        self.assertFalse((self.root / "Existing — Session Log.md").exists())

    def test_rejects_unsafe_title_and_missing_source(self) -> None:
        with self.assertRaises(factory.FactoryError):
            factory.create_session(self.root, "../escape", "2026-01-01")
        with self.assertRaises(factory.FactoryError):
            factory.create_session(
                self.root, "Missing Source", "2026-01-01", self.root / "no.md"
            )


if __name__ == "__main__":
    unittest.main()
