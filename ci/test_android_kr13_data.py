#!/usr/bin/env python3
"""Regression tests for the immutable Android KR13 data-only builder."""

import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import package_android_kr13_data as kr13


def subrecord(tag, data):
    return tag + struct.pack("<I", len(data)) + data


def record(tag, data):
    return tag + struct.pack("<I", len(data)) + b"\0" * 8 + data


def sample_esp(text=b"hello topic", script=b"set x to 1", condition=b"known"):
    top = record(b"TES3", b"")
    dial = record(b"DIAL", subrecord(b"NAME", b"topic") + subrecord(b"DATA", b"\0"))
    info = record(b"INFO", (
        subrecord(b"INAM", b"42") + subrecord(b"SCVR", condition) +
        subrecord(b"NAME", text) + subrecord(b"BNAM", script)
    ))
    return top + dial + info


class AndroidKR13DataTests(unittest.TestCase):
    def test_visible_text_ignores_topic_markup_and_hidden_separator(self):
        self.assertEqual(kr13.visible("go @topic\x7f#"), "go topic")
        self.assertEqual(kr13.visible("go @topic#"), "go topic")

    def test_name_only_link_update_preserves_all_other_fields(self):
        with patch.dict(kr13.ALLOWED_VISIBLE_CORRECTIONS, {}, clear=True):
            report, topics = kr13.inspect_esp(sample_esp(), sample_esp(b"hello @topic#"))
        self.assertEqual(report["changed_INFO_NAME"], 1)
        self.assertEqual(report["visible_equivalent_changes"], 1)
        self.assertTrue(report["all_INFO_non_NAME_fields_byte_identical"])
        self.assertEqual(topics, {"topic"})
        kr13.validate_links(report, topics, {})
        self.assertTrue(report["changed_INFO_links_resolve_to_DIAL_or_TOP"])

    def test_rejects_changed_script(self):
        with patch.dict(kr13.ALLOWED_VISIBLE_CORRECTIONS, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "scripts"):
                kr13.inspect_esp(sample_esp(), sample_esp(b"hello @topic#", script=b"set x to 2"))

    def test_rejects_changed_conditions(self):
        with patch.dict(kr13.ALLOWED_VISIBLE_CORRECTIONS, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "non-display"):
                kr13.inspect_esp(sample_esp(), sample_esp(b"hello @topic#", condition=b"different"))

    def test_rejects_unreviewed_visible_change(self):
        with patch.dict(kr13.ALLOWED_VISIBLE_CORRECTIONS, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "Unreviewed visible"):
                kr13.inspect_esp(sample_esp(), sample_esp(b"different words"))

    def test_rejects_other_record_changes(self):
        old = sample_esp()
        revised = old.replace(b"topic", b"other", 1)
        with self.assertRaisesRegex(ValueError, "Non-INFO"):
            kr13.inspect_esp(old, revised)

    def test_rejects_unresolved_new_info_links(self):
        with patch.dict(kr13.ALLOWED_VISIBLE_CORRECTIONS, {}, clear=True):
            report, topics = kr13.inspect_esp(sample_esp(), sample_esp(b"hello @topic#"))
        with self.assertRaisesRegex(ValueError, "unresolved"):
            kr13.validate_links(report, set(), {})

    def test_top_parser_rejects_extra_blank_lines(self):
        self.assertEqual(kr13.parse_top(b"a\tA\nb\tB\n"), [("a", "A"), ("b", "B")])
        self.assertEqual(kr13.parse_top(b"a\tA\n\nb\tB\n", expected_blank_line=2),
                         [("a", "A"), ("b", "B")])
        for bad in (b"a\tA\n\nb\tB", b"a\tA\n\n\nb\tB", b"a\tA\nmissing"):
            with self.assertRaises(ValueError):
                kr13.parse_top(bad)

    def test_top_parser_rejects_duplicate_keys(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            kr13.parse_top(b"a\tA\na\tB")

    def test_top_inspection_accepts_only_pinned_external_english_targets(self):
        source = b"existing\ttopic\n"
        new_rows = [source.decode("ascii")]
        new_rows += [f"alias{i}\ttopic\n" for i in range(5992)]
        new_rows += ["\n"]
        for key, value in sorted(kr13.KNOWN_EXTERNAL_TOP_TARGETS):
            new_rows.append(f"{key}\t{value}\n")
        target = "".join(new_rows).encode("utf-8")
        report, aliases = kr13.inspect_top(source, target, {"topic"})
        self.assertEqual(len(report["known_external_topic_targets"]), 4)
        self.assertEqual(report["added_alias_count"], 5996)
        self.assertEqual(aliases["existing"], "topic")
        malicious = target + b"untrusted\tunknown goal\n"
        with self.assertRaisesRegex(ValueError, "dangling"):
            kr13.inspect_top(source, malicious, {"topic"})

    def test_refuse_unpinned_sources_and_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            android, windows = base / "a.zip", base / "w.zip"
            output, report = base / "out.zip", base / "report.json"
            android.write_bytes(b"invalid source")
            windows.write_bytes(b"invalid windows")
            with self.assertRaisesRegex(ValueError, "Unpinned"):
                kr13.build(android, windows, output, report)
            self.assertFalse(output.exists())
            output.write_bytes(b"pre-existing data")
            with self.assertRaises(FileExistsError):
                kr13.build(android, windows, output, report)
            self.assertEqual(output.read_bytes(), b"pre-existing data")

    @unittest.skipUnless(os.getenv("ANDROID_KR13_TEST_ANDROID_ZIP") and
                         os.getenv("ANDROID_KR13_TEST_WINDOWS_ZIP"),
                         "Set both source ZIP env vars for reproducible integration test")
    def test_real_pinned_zips_build_deterministically(self):
        android = Path(os.environ["ANDROID_KR13_TEST_ANDROID_ZIP"])
        windows = Path(os.environ["ANDROID_KR13_TEST_WINDOWS_ZIP"])
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "first" / "data.zip"
            second = Path(tmp) / "second" / "data.zip"
            a = kr13.build(android, windows, first, first.with_suffix(".json"))
            b = kr13.build(android, windows, second, second.with_suffix(".json"))
            self.assertEqual(a["output_sha256"], b["output_sha256"])
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(a["record_verification"]["total_records"], 48146)
            self.assertEqual(a["record_verification"]["changed_INFO_NAME"], 224)
            self.assertEqual(a["record_verification"]["visible_equivalent_changes"], 222)
            self.assertEqual(a["top_verification"]["added_alias_count"], 2202)
            self.assertEqual(a["unchanged_android_member_count"], 40)
            with ZipFile(android) as src, ZipFile(first) as new:
                self.assertEqual(new.namelist(), src.namelist() + [kr13.UPGRADE_README])
                for name in src.namelist():
                    if name not in a["updated_android_members"]:
                        self.assertEqual(src.read(name), new.read(name), name)


if __name__ == "__main__":
    unittest.main()
