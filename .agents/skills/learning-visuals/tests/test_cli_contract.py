import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


SKILL = Path(__file__).resolve().parents[1]
CLI = SKILL / "scripts" / "visual_pipeline.mjs"
FIXTURE = SKILL / "fixtures" / "vector-balance.svg"


class CliContractTests(unittest.TestCase):
    def run_cli(self, *args, expected=0):
        result = subprocess.run(
            ["node", str(CLI), *map(str, args)],
            check=False,
            capture_output=True,
            text=True,
            timeout=40,
        )
        self.assertEqual(result.returncode, expected, result.stderr)
        stream = result.stdout if expected == 0 else result.stderr
        return json.loads(stream)

    def test_json_stage_publish_contract_and_hash(self):
        with tempfile.TemporaryDirectory(prefix="learning-visual-cli-") as directory:
            workspace = Path(directory).resolve()
            source = workspace / "visual.svg"
            shutil.copyfile(FIXTURE, source)
            cache = workspace / ".cache"
            staged = self.run_cli(
                "stage", "--kind", "svg", "--source", source, "--name", "cli-visual",
                "--workspace", workspace, "--cache-dir", cache,
            )
            self.assertTrue(staged["ok"])
            preview = Path(staged["previewPath"]).read_bytes()
            self.assertEqual(hashlib.sha256(preview).hexdigest(), staged["previewSha256"])
            published = self.run_cli(
                "publish", "--receipt", staged["receiptPath"],
                "--approved-preview-sha256", staged["previewSha256"], "--workspace", workspace,
            )
            self.assertEqual(Path(published["pngPath"]).read_bytes(), preview)
            self.assertEqual(published["receipt"]["status"], "published")

    def test_failures_are_machine_readable_and_nonzero(self):
        payload = self.run_cli("unknown", expected=1)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "BAD_COMMAND")


if __name__ == "__main__":
    unittest.main()
