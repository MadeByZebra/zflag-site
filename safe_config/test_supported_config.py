"""Offline unit tests: backed-up Roblox allowlisted config staging."""
import json
import tempfile
import unittest
from pathlib import Path
from zflag_supported_config import (
    ALLOWED, config_target, discover_roblox, get_existing,
    normalize_preset, normalize_value, restore_backup, write_verified,
)

class SupportedConfigTests(unittest.TestCase):
    def test_published_initial_list_has_18_names(self):
        self.assertEqual(len(ALLOWED), 18)
        self.assertIn("FFlagHandleAltEnterFullscreenManually", ALLOWED)
        self.assertNotIn("DFIntServerTickRate", ALLOWED)

    def test_boolean_normalization(self):
        self.assertEqual(normalize_value("FFlagHandleAltEnterFullscreenManually", True), "True")
        self.assertEqual(normalize_value("DFFlagDisableDPIScale", "false"), "False")
        self.assertEqual(normalize_value("FFlagDebugSkyGray", "1"), "True")
        with self.assertRaises(ValueError):
            normalize_value("FFlagDebugSkyGray", "maybe")

    def test_integer_normalization(self):
        self.assertEqual(normalize_value("DFIntTextureQualityOverride", " 02 "), "2")
        self.assertEqual(normalize_value("FIntDebugForceMSAASamples", 4), "4")
        with self.assertRaises(ValueError):
            normalize_value("DFIntTextureQualityOverride", False)
        with self.assertRaises(ValueError):
            normalize_value("DFIntTextureQualityOverride", "3.2")
        with self.assertRaises(ValueError):
            normalize_value("DFIntTextureQualityOverride", 2**45)

    def test_unsupported_flags_not_staged(self):
        selected, stats = normalize_preset({
            "FFlagHandleAltEnterFullscreenManually": True,
            "DFIntTextureQualityOverride": 2,
            "DFIntServerTickRate": 9999,
            "FFlagDebugSkyGray": "not bool",
        })
        self.assertEqual(selected, {
            "FFlagHandleAltEnterFullscreenManually": "True",
            "DFIntTextureQualityOverride": "2",
        })
        self.assertEqual(stats, {"accepted": 2, "unsupported": 1, "invalid": 1})

    def test_nested_ffm_flags_object(self):
        selected, stats = normalize_preset({"flags": {
            "DFIntTextureQualityOverride": 1,
            "FFlagDebugGraphicsPreferVulkan": "False",
            "DFFlagDebugForceFutureIsBrightPhase3": True
        }})
        self.assertEqual(len(selected), 2)
        self.assertEqual(stats["unsupported"], 1)

    def test_file_staging_backup_and_restore(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            version = root / "Roblox" / "Versions" / "version-aa1122"
            version.mkdir(parents=True)
            exe = version / "RobloxPlayerBeta.exe"
            exe.write_bytes(b"test only")
            self.assertEqual(discover_roblox(root), [exe])
            target = config_target(exe, root)
            target.parent.mkdir()
            original = {"FFlagHandleAltEnterFullscreenManually": "False",
                        "MyUnlistedSetting": "preserve via backup"}
            target.write_text(json.dumps(original), encoding="utf-8")
            replacement = {"FFlagHandleAltEnterFullscreenManually": "True",
                           "DFIntTextureQualityOverride": "2"}
            backup = write_verified(target, replacement)
            self.assertIsNotNone(backup)
            self.assertEqual(get_existing(target), replacement)
            self.assertEqual(json.loads(backup.read_text()), original)
            restore_backup(target, backup)
            self.assertEqual(get_existing(target), original)

    def test_reject_arbitrary_executable_path(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            exe = root / "RobloxPlayerBeta.exe"
            exe.write_bytes(b"dummy")
            with self.assertRaises(ValueError):
                config_target(exe, root)

    def test_corrupt_existing_config_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "ClientAppSettings.json"
            target.write_text("{not valid json", encoding="utf-8")
            with self.assertRaises(ValueError):
                write_verified(target, {"FFlagDebugSkyGray": "True"})
            self.assertEqual(target.read_text(encoding="utf-8"), "{not valid json")

    def test_empty_or_invalid_preset_cannot_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "ClientAppSettings.json"
            with self.assertRaises(ValueError):
                write_verified(target, {})
            with self.assertRaises(ValueError):
                write_verified(target, {"DFIntServerTickRate": "100"})

if __name__ == "__main__":
    unittest.main()
