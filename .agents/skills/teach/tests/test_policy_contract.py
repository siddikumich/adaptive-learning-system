from __future__ import annotations

import unittest
from pathlib import Path


TEACH_ROOT = Path(__file__).resolve().parents[1]
VAULT_ROOT = TEACH_ROOT.parents[2]


class TeachPolicyContractTests(unittest.TestCase):
    def test_teach_remains_explicit_only(self) -> None:
        metadata = (TEACH_ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        skill = (TEACH_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("allow_implicit_invocation: false", metadata)
        self.assertIn("only when Farhan explicitly invokes `$teach`", skill)

    def test_answer_hidden_tool_contract_is_complete(self) -> None:
        skill = (TEACH_ROOT / "SKILL.md").read_text(encoding="utf-8")
        verifier = (VAULT_ROOT / ".codex" / "agents" / "learning-verifier.toml").read_text(
            encoding="utf-8"
        )
        for tool in ("register_quiz", "present_quiz", "submit_quiz"):
            self.assertIn(tool, skill)
        self.assertIn("returns only its opaque `quiz_id`", skill)
        self.assertIn("Return only `VERIFIED` and the opaque `quiz_id`", verifier)
        self.assertIn("ISOLATION_UNAVAILABLE", verifier)

    def test_visual_contract_fails_closed_and_requires_both_inspections(self) -> None:
        skill = (TEACH_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("visual_pipeline.mjs stage", skill)
        self.assertIn("approved-preview-sha256", skill)
        self.assertGreaterEqual(skill.count("`view_image`"), 3)
        self.assertIn("Fail closed", skill)


if __name__ == "__main__":
    unittest.main()
