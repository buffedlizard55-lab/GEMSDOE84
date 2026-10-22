import tempfile
import unittest
from pathlib import Path

from scripts.check_readiness import REQUIRED, readiness


class ReadinessTests(unittest.TestCase):
    def test_empty_root_is_blocked_and_never_submission_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = readiness(Path(tmp))
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(len(result["missing"]), len(REQUIRED))
        self.assertFalse(result["submission_available"])

    def test_all_required_paths_present_is_only_pipeline_presence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for relpath, _ in REQUIRED:
                path = root / relpath
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"placeholder")
            result = readiness(root)
        self.assertEqual(result["status"], "READY_FOR_SHARED_PIPELINE")
        self.assertFalse(result["submission_available"])
        self.assertIn("still required", result["note"])


if __name__ == "__main__":
    unittest.main()
