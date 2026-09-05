from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from session_fixtures import session_log, session_note
from test_validate_session import validator


class DiagnosticVisualContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.note = self.root / "Review.md"
        self.log = self.root / "Review — Session Log.md"
        note = session_note("Review", status="teaching").replace(
            'protocol-version: "2026-08-26.1"',
            'protocol-version: "2026-08-26.1"\ndiagnostic-coverage: "1"\nlesson-visuals: "1"',
        ).replace(
            "## Dependency plan",
            "### Diagnostic coverage\n\n"
            "| Strand | Goal relevance | Evidence | Boundary | Coverage | Next action |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            "| Rule | Select legal moves | [[Review — Session Log#Probe 1]] | Goal-level construction succeeds | bounded | none — boundary mapped |\n\n"
            "Diagnostic scope: full-goal\n\n## Dependency plan",
        ).replace(
            "## Lessons",
            "### Lesson visual plan\n\n"
            "| Node | Relationship to explain | Form |\n| --- | --- | --- |\n"
            "| Scoped foundation | Legal versus illegal move | table |\n\n## Lessons",
        ).replace(
            "> **Advance when:**",
            "> **Visual:** alternative — the paired legal/illegal cases express the rule directly\n> **Advance when:**",
        )
        self.note.write_text(note, encoding="utf-8")
        self.log.write_text(
            session_log("Review", status="active", pending=True)
            + "\n### Probe 1\n\nPrompt: Select a legal move.\nResponse: Preserves the invariant.\nAssessment: correct construction.\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def replace(self, old: str, new: str) -> None:
        self.note.write_text(self.note.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")

    def errors(self) -> str:
        return "\n".join(validator.validate(self.note, self.log, True)[0])

    def test_populated_coverage_and_visual_decision_preserve_active_check(self) -> None:
        self.assertEqual(self.errors(), "")

    def test_review_contract_survives_same_day_closeout(self) -> None:
        self.replace("status: teaching", "status: awaiting-retrieval")
        (self.root / "Source.md").write_text("# Source\n", encoding="utf-8")
        self.log.write_text(
            session_log("Review") + "\n### Probe 1\n\nAssessment: correct construction.\n",
            encoding="utf-8",
        )
        errors, _ = validator.validate(self.note, self.log, False, require_closeout=True)
        self.assertEqual(errors, [])

    def test_first_node_ready_does_not_hide_unprobed_strand(self) -> None:
        self.replace("Diagnostic scope: full-goal", "| Implementation | Write runnable code | none | unknown | unprobed | cold code probe |\n\nDiagnostic scope: full-goal")
        self.assertIn("remains 'unprobed'", self.errors())

    def test_deferred_strand_requires_visible_partial_scope(self) -> None:
        self.replace("| bounded | none — boundary mapped |", "| deferred | cap reached; probe construction next session |")
        self.assertIn("Diagnostic scope must be 'partial'", self.errors())
        self.replace("Diagnostic scope: full-goal", "Diagnostic scope: partial")
        self.assertEqual(self.errors(), "")

    def test_unsupported_evidence_anchor_fails(self) -> None:
        self.replace("#Probe 1", "#Invented probe")
        self.assertIn("resolvable sidecar evidence", self.errors())

    def test_evidence_aliases_resolve_but_invented_directories_do_not(self) -> None:
        self.replace("#Probe 1]]", "#Probe 1|production]]")
        self.assertEqual(self.errors(), "")
        self.replace("[[Review — Session Log#", "[[missing/Review — Session Log#")
        self.assertIn("resolvable sidecar evidence", self.errors())

    def test_empty_inventory_and_floor_only_do_not_pass(self) -> None:
        self.replace("| bounded |", "| floor-only |")
        self.assertIn("remains 'floor-only'", self.errors())
        self.replace("### Diagnostic coverage", "### Unrelated table")
        self.assertIn("requires exactly one '### Diagnostic coverage'", self.errors())

    def test_planning_diagram_cannot_satisfy_lesson_embed(self) -> None:
        self.replace("alternative — the paired legal/illegal cases express the rule directly", "embedded — the rule's geometry")
        self.assertIn("no local explanatory PNG", self.errors())
        self.replace("#### Active check", "![[example.png]]\n\n#### Active check")
        self.assertIn("no local explanatory PNG", self.errors())
        # Existence is all this structural check proves, not valid image bytes.
        (self.root / "example.png").write_bytes(b"fixture")
        self.assertEqual(self.errors(), "")

    def test_active_check_input_picture_is_not_explanatory_visual(self) -> None:
        self.replace("alternative — the paired legal/illegal cases express the rule directly", "embedded — the rule's geometry")
        self.replace("#### Active check", "#### Active check\n\n![[example.png]]")
        (self.root / "example.png").write_bytes(b"fixture")
        self.assertIn("no local explanatory PNG", self.errors())

    def test_visual_fallback_requires_a_reason_and_plan_covers_taught_node(self) -> None:
        self.replace("alternative — the paired legal/illegal cases express the rule directly", "incomplete — renderer unavailable; use the paired cases")
        self.assertEqual(self.errors(), "")
        self.replace("incomplete — renderer unavailable; use the paired cases", "incomplete")
        self.assertIn("Visual callout decision", self.errors())
        self.replace("| Scoped foundation | Legal", "| Unrelated node | Legal")
        self.assertIn("missing from Lesson visual plan", self.errors())


if __name__ == "__main__":
    unittest.main()
