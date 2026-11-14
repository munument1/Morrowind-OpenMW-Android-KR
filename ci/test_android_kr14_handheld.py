"""Static guardrails for the unreleased Android 0.51.0-14 handheld port.

The native ARM64 ABI, OpenMW symbols and on-device gamepad interactions still
require a signed-build/device QA run; these checks do not claim otherwise.
"""

from __future__ import annotations

import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "source/app"
MAIN = APP / "src/main"
RADIAL = MAIN / "handheld-assets/handheld"


def yaml_keys(path: Path) -> list[str]:
    # RadialMenu's simple top-level YAML maps have no nested keys.
    return re.findall(r"^([A-Za-z][A-Za-z0-9_]*):", path.read_text(encoding="utf-8"), re.M)


class HandheldPortTests(unittest.TestCase):
    def test_korean_l10n_and_english_fallback_match(self) -> None:
        directory = RADIAL / "l10n/OMWRadialMenu"
        english = yaml_keys(directory / "en.yaml")
        korean = yaml_keys(directory / "ko.yaml")
        self.assertEqual(len(english), 24)
        self.assertEqual(len(set(english)), len(english))
        self.assertEqual(len(set(korean)), len(korean))
        self.assertEqual(set(english), set(korean))
        self.assertRegex((directory / "ko.yaml").read_text(encoding="utf-8"), "[가-힣]")

    def test_handheld_script_manifest_targets_real_assets(self) -> None:
        source = (MAIN / "java/ui/activity/HandheldController.kt").read_text(encoding="utf-8")
        match = re.search(r'private const val SCRIPTS = """(.*?)"""', source, re.S)
        self.assertIsNotNone(match)
        for line in match.group(1).strip().splitlines():
            _modes, file_path = line.split(": ", 1)
            self.assertTrue((RADIAL / file_path).is_file(), file_path)
        self.assertIn('content=${HandheldController.CONTENT_FILE}', (
            MAIN / "java/ui/activity/MainActivity.kt").read_text(encoding="utf-8"))

    def test_android_settings_have_korean_labels(self) -> None:
        for path in [
            MAIN / "AndroidManifest.xml",
            MAIN / "res/xml/settings.xml",
            MAIN / "res/xml/gs_interface.xml",
            MAIN / "res/values/strings.xml",
            MAIN / "res/values-ko/strings.xml",
        ]:
            ET.parse(path)
        english = {s.attrib.get("name") for s in ET.parse(MAIN / "res/values/strings.xml").getroot()}
        korean = {s.attrib.get("name") for s in ET.parse(MAIN / "res/values-ko/strings.xml").getroot()}
        for key in [
            "pref_handheld_mode_title",
            "pref_handheld_mode_summary",
            "pref_font_size",
            "pref_truetype_fonts_title",
            "pref_truetype_fonts_summary",
        ]:
            self.assertIn(key, english)
            self.assertIn(key, korean)
        # The existing Gradle verifyOpenMwPayload gate checks these languages too.
        # Importing the new strings only into KO silently breaks that gate.
        for locale in ("de", "fr", "pl", "ru", "sv"):
            strings = {
                s.attrib.get("name")
                for s in ET.parse(MAIN / f"res/values-{locale}/strings.xml").getroot()
            }
            for key in (
                "pref_handheld_mode_title",
                "pref_handheld_mode_summary",
                "pref_font_size",
                "pref_truetype_fonts_title",
                "pref_truetype_fonts_summary",
            ):
                self.assertIn(key, strings, f"{locale} missing {key}")

    def test_upgrade_keeps_app_identity_and_16k_jni(self) -> None:
        gradle = (APP / "build.gradle").read_text(encoding="utf-8")
        native = (MAIN / "cpp/Android.mk").read_text(encoding="utf-8")
        self.assertIn('applicationId "com.ast.openmw.korean"', gradle)
        self.assertIn('openMwVersionCode = 5119', gradle)
        self.assertIn("0.51.0-14-KR14-dev", gradle)
        self.assertIn("ndkVersion '27.3.13750724'", gradle)
        self.assertIn("max-page-size=16384", native)
        self.assertIn("common-page-size=16384", native)
        self.assertNotIn("<<<<<<<", gradle)

    def test_powervr_and_cursor_bridge_are_present(self) -> None:
        cmake = (ROOT / "source/buildscripts/CMakeLists.txt").read_text(encoding="utf-8")
        self.assertIn('apply-powervr-packed-depth-stencil.py', cmake)
        self.assertTrue((ROOT / "source/buildscripts/patches/gl4es/apply-powervr-packed-depth-stencil.py").is_file())
        bridge = (MAIN / "cpp/handheld.c").read_text(encoding="utf-8")
        self.assertIn("Java_cursor_EngineCursor_nativeIsMenuOpen", bridge)
        self.assertIn("Java_cursor_EngineCursor_nativeSetVisible", bridge)
        self.assertIn('dlopen("libopenmw.so"', bridge)


if __name__ == "__main__":
    unittest.main()
