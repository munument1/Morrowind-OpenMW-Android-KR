#!/usr/bin/env python3
"""Build Android KR12.6 DATA ONLY from immutable public KR12.5 Android/KR12.6 Windows archives.

The Windows KR12.6 ESP/TOP are copied exactly; this script never edits an APK,
original Morrowind masters, the source archives, scripts or quest conditions.
"""
import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from patch_kr12_quest_entry_topics import chunks, fields, decoded

ANDROID_ZIP_SHA = "5f57f7a8d99d12105ca86202a2efe8aca0debb3aba3454b6bf42bf687c414634"
WINDOWS_ZIP_SHA = "2f4bb6b9cfd5916fd9574b6207628e4bb16f8bdc4f1c68fc1ef7581c970989e9"
OLD_ESP_SHA = "04d6579f56049c7eabc08a3ad13712c9b74ceb8479e94eba3a0c183f76b5f0fd"
NEW_ESP_SHA = "c52a5355752ef0be93fadeca9c95ca00d7cad808f713ce92a624a67d0cc277df"
NEW_TOP_SHA = "d14b96aaa3fc09aba193cd2c763787632073b630be4ca0cac5ee2e390b445235"
STEM = "Morrowind_Korean_ReTranslation"
ANDROID = STEM + "/"
WINDOWS = "payload/mods/" + STEM + "/"
TARGET = "제국 교단에 가입"
EXPECTED_JOIN_IDS = ("26689110631261324944", "24205752258151922")
LINK = re.compile(r"@([^@#]+)#")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def visible(data):
    return LINK.sub(lambda m: m.group(1).replace("\x7f", ""), decoded(data)).replace("\x7f", "")


def parse_sidecar(raw):
    rows = []
    for line in raw.decode("utf-8-sig").splitlines():
        if "\t" in line:
            key, value = line.split("\t", 1)
            rows.append((key, value))
    return rows


def inspect_esp(old_bytes, new_bytes):
    a = list(chunks(old_bytes, 16))
    b = list(chunks(new_bytes, 16))
    if len(a) != 48146 or len(a) != len(b):
        raise ValueError("Unpinned TES3 record count")
    changed_ids = []
    topic_names = set()
    joining = []
    relevant = []
    parent = None
    parent_kind = None
    for index, ((tag, h, payload), (tag2, h2, payload2)) in enumerate(zip(a, b)):
        if tag != tag2 or h[8:] != h2[8:]:
            raise ValueError("TES3 record headers changed")
        if tag == b"DIAL":
            f = dict(fields(payload2))
            parent = decoded(f.get(b"NAME", b""))
            parent_kind = f.get(b"DATA", b"\xff")[:1].hex()
            if f.get(b"DATA", b"\xff")[:1] == b"\0" and b"DELE" not in f:
                topic_names.add(parent)
        if payload != payload2:
            if tag != b"INFO":
                raise ValueError("A non-INFO record changed: " + repr(tag))
            af, bf = fields(payload), fields(payload2)
            if len(af) != len(bf):
                raise ValueError("INFO subrecord count drift")
            changed = []
            for (name, value), (name2, value2) in zip(af, bf):
                if name != name2:
                    raise ValueError("INFO subrecord type/order drift")
                if value != value2:
                    if name != b"NAME" or visible(value) != visible(value2):
                        raise ValueError("Non-display or non-NAME INFO changed")
                    changed.append(name)
            if changed != [b"NAME"]:
                raise ValueError("Unexpected INFO field changes")
            changed_ids.append((parent, decoded(dict(af).get(b"INAM", b""))))
        if tag == b"INFO":
            f = dict(fields(payload2))
            text = decoded(f.get(b"NAME", b""))
            info_id = decoded(f.get(b"INAM", b""))
            if (TARGET in visible(f.get(b"NAME", b""))
                    or info_id in EXPECTED_JOIN_IDS
                    or (parent and "제국 교단" in parent and "가입" in parent)):
                entry = {
                    "INAM": info_id, "DIAL": parent, "dial_kind_hex": parent_kind,
                    "ONAM_actor": decoded(f.get(b"ONAM", b"")),
                    "FNAM_faction": decoded(f.get(b"FNAM", b"")),
                    "RNAM_race": decoded(f.get(b"RNAM", b"")),
                    "CNAM_class": decoded(f.get(b"CNAM", b"")),
                    "ANAM_cell": decoded(f.get(b"ANAM", b"")),
                    "SCVR_hex": [value.hex() for key, value in fields(payload2) if key == b"SCVR"],
                    "result_script": decoded(f.get(b"BNAM", b"")),
                    "text": text,
                    "explicit_target_link": ("@" + TARGET + "#") in text,
                    "visible": visible(f.get(b"NAME", b"")),
                    "record_index": index
                }
                relevant.append(entry)
                if info_id in EXPECTED_JOIN_IDS:
                    joining.append(entry)
    if len(changed_ids) != 230 or len(set(changed_ids)) != 230:
        raise ValueError(f"KR12.6 expected 230 unique INFO.NAME updates; actual records={len(changed_ids)}, unique_INFO_IDs={len(set(changed_ids))}, sample={changed_ids[:10]}")
    if TARGET not in topic_names:
        raise ValueError("Imperial Cult join target DIAL does not exist")
    if {x["INAM"] for x in joining} != set(EXPECTED_JOIN_IDS):
        raise ValueError("Original English-verified join INFO IDs are missing")
    if not all(x["explicit_target_link"] for x in joining):
        raise ValueError("A previously repaired Imperial Cult join INFO lost its link")
    return {
        "total_records": len(a), "changed_INFO_NAME": len(changed_ids),
        "changed_INFO_ids": changed_ids,
        "all_other_TES3_fields_byte_identical": True,
        "all_visible_Korean_unchanged": True,
        "imperial_cult": {
            "target_dial": TARGET,
            "dial_exists": True,
            "previously_repaired_info": joining,
            "relevant_info_count": len(relevant),
            "relevant_infos": relevant,
            "limitations": [
                "The existence of two explicit links does not prove their NPC GREETING is reachable.",
                "SCVR, quest-journal state, active mods, NPC availability and runtime filter evaluation are not simulated.",
                "Reported screenshot and actual reporter save/ESP are not inspected.",
            ],
        },
    }


def inspect_top(before, after, topics):
    old = parse_sidecar(before)
    new = parse_sidecar(after)
    if len(old) != 5848 or len(new) != 5934:
        raise ValueError("Unexpected KR12.5/KR12.6 TOP alias count")
    old_keys = [key for key, val in old]
    new_keys = [key for key, val in new]
    if len(set(old_keys)) != len(old_keys) or len(set(new_keys)) != len(new_keys):
        raise ValueError("Duplicate TOP alias key")
    old_set = set(old)
    new_set = set(new)
    if not old_set.issubset(new_set) or len(new_set - old_set) != 86:
        raise ValueError("Old TOP mapping changed or new alias count is not 86")
    # Existing row ordering must be preserved even if new entries were inserted.
    old_iter = iter(new)
    if not all(any(r == wanted for r in old_iter) for wanted in old):
        raise ValueError("Existing TOP alias order changed")
    if any(value not in topics for key, value in new):
        raise ValueError("TOP mapping has a target not defined by the translation ESP")
    # The target should resolve to itself when no alias is present.
    alias = dict(new)
    if alias.get(TARGET, TARGET) != TARGET:
        raise ValueError("Imperial Cult join text is redirected by TOP")
    return {"original_entries": len(old), "new_entries": len(new),
            "added_aliases": len(new_set - old_set),
            "existing_aliases_unchanged": True,
            "imperial_join_target_mapping": alias.get(TARGET, TARGET),
            "all_TOP_targets_exist_in_ESP": True}


def main():
    p = argparse.ArgumentParser()
    for key in ("android", "windows", "output", "report"):
        p.add_argument("--" + key, required=True, type=Path)
    x = p.parse_args()
    paths = (x.android, x.windows, x.output, x.report)
    if len(set(map(lambda y: y.resolve(), paths))) != 4:
        raise ValueError("Output and inputs overlap")
    if x.output.exists() or x.report.exists():
        raise ValueError("Refusing to overwrite existing output")
    android_bytes = x.android.read_bytes()
    windows_bytes = x.windows.read_bytes()
    if sha(android_bytes) != ANDROID_ZIP_SHA or sha(windows_bytes) != WINDOWS_ZIP_SHA:
        raise ValueError("Unpinned Android KR12.5 / Windows KR12.6 ZIP source SHA")
    with zipfile.ZipFile(x.android) as az, zipfile.ZipFile(x.windows) as wz:
        anames = az.namelist()
        if len(anames) != len(set(anames)) or az.testzip() or wz.testzip():
            raise ValueError("Invalid/duplicated ZIP source entries")
        esp_name, top_name = STEM + ".esp", STEM + ".top"
        for name in (esp_name, top_name):
            if anames.count(ANDROID + name) != 1 or wz.namelist().count(WINDOWS + name) != 1:
                raise ValueError("Missing/ambiguous Korean translation: " + name)
        old_esp = az.read(ANDROID + esp_name)
        new_esp = wz.read(WINDOWS + esp_name)
        old_top = az.read(ANDROID + top_name)
        new_top = wz.read(WINDOWS + top_name)
        if sha(old_esp) != OLD_ESP_SHA or sha(new_esp) != NEW_ESP_SHA or sha(new_top) != NEW_TOP_SHA:
            raise ValueError("ESP/TOP release source hash mismatch")
        esp_report = inspect_esp(old_esp, new_esp)
        topics = set()
        for tag, header, data in chunks(new_esp, 16):
            if tag == b"DIAL":
                f = dict(fields(data))
                if f.get(b"DATA", b"\xff")[:1] == b"\x00" and b"DELE" not in f:
                    topics.add(decoded(f[b"NAME"]))
        top_report = inspect_top(old_top, new_top, topics)
        updates = {ANDROID + esp_name: new_esp, ANDROID + top_name: new_top}
        x.output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(x.output, "w") as out:
            for item in az.infolist():
                out.writestr(item, updates.get(item.filename, az.read(item.filename)))
    with zipfile.ZipFile(x.android) as az, zipfile.ZipFile(x.output) as out:
        if out.testzip() or az.namelist() != out.namelist():
            raise ValueError("Output ZIP failed integrity or member-list parity")
        for name in az.namelist():
            if name not in updates and az.read(name) != out.read(name):
                raise ValueError("Unexpected non-translation Android member changed: " + name)
    report = {
        "status": "ANDROID_KR12_6_DATA_ONLY_STATIC_QA_NOT_GAMEPLAY",
        "version": "KR12.6", "android_source_sha256": ANDROID_ZIP_SHA,
        "windows_source_sha256": WINDOWS_ZIP_SHA,
        "old_esp_sha256": OLD_ESP_SHA, "new_esp_sha256": NEW_ESP_SHA,
        "new_top_sha256": NEW_TOP_SHA,
        "new_data_zip_sha256": sha(x.output.read_bytes()),
        "record_verification": esp_report,
        "top_verification": top_report,
        "other_android_zip_members_unchanged": True,
        "apk_rebuilt": False, "in_game_verified": False,
    }
    x.report.parent.mkdir(parents=True, exist_ok=True)
    x.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8")
    (x.output.parent / (x.output.name + ".sha256")).write_text(
        report["new_data_zip_sha256"] + "  " + x.output.name + "\n", "utf-8")
    print("ANDROID_KR12_6_PARITY=" + json.dumps({
        "status": "PASS", "zip_sha256": report["new_data_zip_sha256"],
        "info_changed": esp_report["changed_INFO_NAME"],
        "top_added": top_report["added_aliases"],
        "imperial_join_target": top_report["imperial_join_target_mapping"],
        "imperial_join_info": [
            {"INAM": z["INAM"], "DIAL": z["DIAL"], "actor": z["ONAM_actor"],
             "faction": z["FNAM_faction"], "explicit_link": z["explicit_target_link"],
             "text": z["text"][:550]} for z in esp_report["imperial_cult"]["previously_repaired_info"]
        ],
        "relevant_info_count": esp_report["imperial_cult"]["relevant_info_count"],
        "notes": "No actual quest/NPC runtime or installed-mod load-order verification"
    }, ensure_ascii=False))
    print("IMPERIAL_CULT_RELEVANT_INFO_SAMPLE=" + json.dumps(
        esp_report["imperial_cult"]["relevant_infos"][:30], ensure_ascii=False))


if __name__ == "__main__":
    main()
