"""Small, read-only contract regressions; no training or report regeneration."""
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("r0_baseline", ROOT / "tools/r0_baseline.py")
r0 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r0)


class BaselineTests(unittest.TestCase):
    def test_inventory_protects_data_but_excludes_mutable_live_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("models/model.bin", "data/raw/train.bin", "data/live/latest.json", "data/runtime/replay.db"):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"test fixture")
            before = r0.protected_inventory(root)
            self.assertEqual(set(before), {"models/model.bin", "data/raw/train.bin"})
            (root / "data/raw/train.bin").write_bytes(b"changed")
            self.assertEqual(r0.changes(before, r0.protected_inventory(root))["changed"], ["data/raw/train.bin"])

    def test_native_failure_cannot_reach_success_message(self):
        shell = shutil.which("powershell") or shutil.which("pwsh")
        if not shell:
            self.skipTest("PowerShell unavailable on this platform")
        helper = str(ROOT / "tools/verification_helpers.ps1").replace("'", "''")
        python = sys.executable.replace("'", "''")
        command = f"$ErrorActionPreference='Stop'; . '{helper}'; Invoke-CheckedCommand -Executable '{python}' -Arguments @('-c','import sys; sys.exit(17)'); Write-Output 'FALSE_SUCCESS'"
        result = subprocess.run([shell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command], capture_output=True, text=True, timeout=20)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("FALSE_SUCCESS", result.stdout)
        self.assertIn("exited with code 17", result.stderr)

    def test_inventory_detects_removed_and_added_files(self):
        result = r0.changes({"old": {"sha256": "a"}}, {"new": {"sha256": "b"}})
        self.assertEqual(result["missing"], ["old"])
        self.assertEqual(result["added"], ["new"])
