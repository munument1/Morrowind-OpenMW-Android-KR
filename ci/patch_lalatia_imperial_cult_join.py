#!/usr/bin/env python3
"""Build an isolated, UNRELEASED Lalatia Varian join-topic candidate from Android KR12.6.

One INFO.NAME explicit hyperlink only. No source ZIP/ESP, native code, sidecar,
original master, installed game or save is changed.
"""
import argparse
import hashlib
import json
import re
import struct
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from patch_kr12_quest_entry_topics import chunks, fields, decoded, pack

SOURCE_ZIP_SHA = "a1c718740f740cd42fbc0650e54b5bc557aa0a74d40d5a85d95763a84ee7ad3c"
SOURCE_ESP_SHA = "c52a5355752ef0be93fadeca9c95ca00d7cad808f713ce92a624a67d0cc277df"
MEMBER = "Morrowind_Korean_ReTranslation/Morrowind_Korean_ReTranslation.esp"
TARGET_INFO = "1341756011233729353"
TARGET_DIAL = "평신도 회원"
CLICK_DIAL = "제국 교단에 가입"
BEFORE = "제국 교단에 가입하시겠습니까?"
AFTER = "@제국 교단에 가입#하시겠습니까?"
ENTRY_INFO = "246142351970125790"
ENTRY_DIAL = "Greeting 6"
ENTRY_MARKUP = "@평신도가#"
TAG = re.compile(r"@([^@#]+)#")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def visible(s):
    return TAG.sub(lambda m: m.group(1).replace("\x7f", ""), s).replace("\x7f", "")


def analyze(original):
    source = list(chunks(original, 16))
    out = []
    topics = set()
    active_dial = None
    matches = []
    entry_seen = 0
    for index, (tag, header, payload) in enumerate(source):
        data = dict(fields(payload))
        if tag == b"DIAL":
            active_dial = decoded(data.get(b"NAME", b""))
            if data.get(b"DATA", b"\xff")[:1] == b"\x00" and b"DELE" not in data:
                topics.add(active_dial)
        if tag != b"INFO":
            out.append(header + payload)
            continue
        info_id = decoded(data.get(b"INAM", b""))
        response = decoded(data.get(b"NAME", b""))
        if info_id == ENTRY_INFO and active_dial == ENTRY_DIAL:
            if ENTRY_MARKUP not in response:
                raise ValueError("Lay member entry hyperlink has unexpectedly changed")
            entry_seen += 1
        if info_id != TARGET_INFO or active_dial != TARGET_DIAL:
            out.append(header + payload)
            continue
        if response.count(BEFORE) != 1 or visible(AFTER) != BEFORE:
            raise ValueError("The exact expected response phrase does not match pinned release")
        if BEFORE in response and AFTER in response:
            raise ValueError("Already patched")
        changed_text = response.replace(BEFORE, AFTER)
        if visible(response) != visible(changed_text):
            raise ValueError("Displayed dialogue drift")
        parts = fields(payload)
        raw = data[b"NAME"]
        nulls = raw[len(raw.rstrip(b"\x00")):]
        new_raw = changed_text.encode("utf-8") + nulls
        rebuilt = b"".join(
            tag2 + struct.pack("<I", len(new_raw if tag2 == b"NAME" else raw2))
            + (new_raw if tag2 == b"NAME" else raw2)
            for tag2, raw2 in parts
        )
        out.append(pack(tag, header, rebuilt))
        matches.append({
            "record_index": index,
            "parent_DIAL": active_dial,
            "INFO_INAM": info_id,
            "NPC_actor": decoded(data.get(b"ONAM", b"")),
            "faction": decoded(data.get(b"FNAM", b"")),
            "before": response,
            "after": changed_text,
            "source_NAME_sha256": sha(raw),
            "candidate_NAME_sha256": sha(new_raw),
            "visible_text_unchanged": True,
            "SCVR_unchanged": True,
            "BNAM_result_script_unchanged": True,
        })
    if len(matches) != 1 or entry_seen != 1 or CLICK_DIAL not in topics:
        raise ValueError(f"Expected one lay member INFO and one GREETING and join DIAL, got {len(matches)} and {entry_seen}")
    candidate = b"".join(out)
    if len(source) != 48146 or len(list(chunks(candidate, 16))) != 48146:
        raise ValueError("TES3 record count drift")
    differences = 0
    for (t1, h1, p1), (t2, h2, p2) in zip(source, chunks(candidate, 16)):
        if t1 != t2 or h1[8:] != h2[8:]:
            raise ValueError("TES3 record metadata drift")
        if p1 == p2:
            continue
        if t1 != b"INFO":
            raise ValueError("Non-INFO changes")
        a = fields(p1)
        b = fields(p2)
        old = dict(a)
        if active_dial is None or decoded(old.get(b"INAM", b"")) != TARGET_INFO:
            raise ValueError("Wrong INFO changed")
        if len(a) != len(b):
            raise ValueError("INFO subrecords changed")
        changed_fields = []
        for (name, value), (name2, value2) in zip(a, b):
            if name != name2:
                raise ValueError("INFO order drift")
            if value != value2:
                if name != b"NAME" or visible(decoded(value)) != visible(decoded(value2)):
                    raise ValueError("Unexpected changed INFO field")
                changed_fields.append(name)
        if changed_fields != [b"NAME"]:
            raise ValueError("Only INFO.NAME must change")
        differences += 1
    if differences != 1:
        raise ValueError("Candidate must have one changed INFO.NAME")
    return candidate, {
        "status": "CANDIDATE_ONLY_NOT_RELEASED",
        "original_esp_sha256": sha(original),
        "candidate_esp_sha256": sha(candidate),
        "source_record_count": 48146,
        "changed_info_count": differences,
        "non_target_records_and_fields_byte_identical": True,
        "displayed_text_unchanged": True,
        "join_DIAL_exists": True,
        "entry_Greeting6_explicit_lay_member_link_exists": True,
        "changes": matches,
        "limitation": "Static source-proof only; no save-state or NPC-filter gameplay QA",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source-zip", required=True, type=Path)
    p.add_argument("--output-esp", required=True, type=Path)
    p.add_argument("--report", required=True, type=Path)
    args = p.parse_args()
    if len({x.resolve() for x in (args.source_zip, args.output_esp, args.report)}) != 3:
        raise ValueError("Source/output paths overlap")
    if args.output_esp.exists() or args.report.exists():
        raise ValueError("Refuse existing output")
    raw = args.source_zip.read_bytes()
    if sha(raw) != SOURCE_ZIP_SHA:
        raise ValueError("Expected unchanged Android KR12.6 source ZIP")
    with zipfile.ZipFile(args.source_zip) as archive:
        original = archive.read(MEMBER)
    if sha(original) != SOURCE_ESP_SHA:
        raise ValueError("Expected unchanged Android/Windows KR12.6 source ESP")
    patched, report = analyze(original)
    args.output_esp.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.output_esp.write_bytes(patched)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("LALATIA_JOIN_CANDIDATE=" + json.dumps({
        "status": report["status"], "info": TARGET_INFO, "dial": TARGET_DIAL,
        "source_esp": SOURCE_ESP_SHA, "candidate_esp": report["candidate_esp_sha256"],
        "change_count": report["changed_info_count"],
        "visible_text_unchanged": report["displayed_text_unchanged"],
        "entry_info": ENTRY_INFO, "entry_link": ENTRY_MARKUP,
        "candidate_phrase": AFTER,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
