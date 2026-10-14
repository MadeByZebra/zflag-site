"""Reset ClientAppSettings locally with a backup; never touch Roblox memory."""
import os
import sys
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
import zflag_supported


class TestLocalReset(TestCase):
    def test_reset_preserves_exact_content_in_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)/"Roblox"/"Versions"/"version-test"/"ClientSettings"/"ClientAppSettings.json"
            target.parent.mkdir(parents=True,exist_ok=True)
            original = b'{"FFlagHandleAltEnterFullscreenManually":"False"}\n'
            target.write_bytes(original)
            with patch.dict(os.environ, {"LOCALAPPDATA": directory}), patch.object(zflag_supported,"target_json",return_value=target):
                result=zflag_supported.reset_local_settings()
            self.assertTrue(result["ok"])
            self.assertTrue(result["removed"])
            self.assertFalse(target.exists())
            self.assertTrue(Path(result["backup"]).exists())
            self.assertEqual(Path(result["backup"]).read_bytes(),original)

    def test_reset_when_no_local_flags_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/"Roblox"/"Versions"/"version-test"/"ClientSettings"/"ClientAppSettings.json"
            with patch.dict(os.environ, {"LOCALAPPDATA": directory}), patch.object(zflag_supported,"target_json",return_value=target):
                result=zflag_supported.reset_local_settings()
            self.assertTrue(result["ok"])
            self.assertFalse(result["removed"])

    def test_symlink_target_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            actual=Path(directory)/"actual.json"
            actual.write_text('{"anything": true}')
            directory2=Path(directory)/"ClientSettings"
            directory2.mkdir()
            path=directory2/"ClientAppSettings.json"
            try: path.symlink_to(actual)
            except (OSError,NotImplementedError): self.skipTest("Symlinks unavailable without Windows developer mode")
            with patch.object(zflag_supported,"target_json",return_value=path):
                result=zflag_supported.reset_local_settings()
            self.assertFalse(result["ok"])
            self.assertTrue(actual.exists())


if __name__ == "__main__":
    import unittest
    unittest.main()
