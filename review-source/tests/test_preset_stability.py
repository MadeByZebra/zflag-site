"""Offline checks for huge FFlag presets. Never opens Roblox or writes to it."""
import sys
from pathlib import Path
from unittest import TestCase

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from zflag_supported import preflight, normalize, ALLOWED


class TestLargeSafePresets(TestCase):
    def test_1020_unknown_flags_are_not_eligible(self):
        config = {f"DFIntUnsupportedNetworkTweak{i}": "36420" for i in range(1019)}
        config["FFlagHandleAltEnterFullscreenManually"] = "False"
        result = preflight(config)
        self.assertTrue(result["ok"])
        self.assertEqual(result["total"], 1020)
        self.assertEqual(result["supported"], 1)
        self.assertEqual(result["unsupported"], 1019)
        self.assertEqual(result["invalid"], 0)
        self.assertEqual(len(result["entries"]), 1020)
        self.assertEqual(len([v for v in result["entries"] if v["valid"]]), 1)

    def test_bad_types_are_invalid_not_silently_converted(self):
        self.assertFalse(normalize("FFlagHandleAltEnterFullscreenManually", 1)[0])
        self.assertFalse(normalize("DFIntCSGLevelOfDetailSwitchingDistance", "9999999999999")[0])
        self.assertFalse(normalize("DFIntCSGLevelOfDetailSwitchingDistance", True)[0])
        self.assertTrue(normalize("FFlagHandleAltEnterFullscreenManually", "False")[0])

    def test_every_official_allowed_flag_is_classified_eligible_with_normal_type(self):
        self.assertIn("FFlagHandleAltEnterFullscreenManually", ALLOWED)
        self.assertIn("DFFlagTextureQualityOverrideEnabled", ALLOWED)
        self.assertNotIn("DFIntTaskSchedulerTargetFps", ALLOWED)


if __name__ == "__main__":
    import unittest
    unittest.main()
