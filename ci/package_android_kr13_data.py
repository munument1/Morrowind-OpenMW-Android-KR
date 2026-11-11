#!/usr/bin/env python3
"""Repackage public Android KR12.6 data with the pinned Windows KR13 translation.

This is a DATA-ONLY update. The original Android ZIP supplies all existing members
and metadata; only the Korean ESP/TOP and any independently changed ko.yaml
sidecars are eligible for replacement. No APK, commercial masters, or saves are
read or modified.
"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from patch_kr12_quest_entry_topics import chunks, decoded, fields

ANDROID_ZIP_SHA = "a1c718740f740cd42fbc0650e54b5bc557aa0a74d40d5a85d95763a84ee7ad3c"
WINDOWS_ZIP_SHA = "40da1be66a346c86baa2a3024346b300284c68a73379c64c4e1647744158ac31"
OLD_ESP_SHA = "c52a5355752ef0be93fadeca9c95ca00d7cad808f713ce92a624a67d0cc277df"
NEW_ESP_SHA = "9f94b1c96b10a491cec00d4931123ef1e0f52f52c6095da6b9b380eb9a617b1c"
OLD_TOP_SHA = "d14b96aaa3fc09aba193cd2c763787632073b630be4ca0cac5ee2e390b445235"
NEW_TOP_SHA = "928ace2d7245edd01f8085737e76d4fc6e9d1343b1477e7c5ed9eebf78cc6f0b"

STEM = "Morrowind_Korean_ReTranslation"
ANDROID_DIR = STEM + "/"
WINDOWS_DIR = "payload/mods/" + ANDROID_DIR
ESP = STEM + ".esp"
TOP = STEM + ".top"
UPGRADE_README = "KR13-ANDROID-UPGRADE.txt"
UPGRADE_TEXT = """OpenMW Android 한국어 KR13 데이터 업데이트

이 파일은 KR13 데이터 전용 ZIP의 안내입니다. 기존 README-ANDROID-KO.txt는
이전 KR12 설치 자료를 보존한 역사적 문서입니다.

KR13의 대화 주제 처리(특히 지역 확장/가입 주제)에는 Android KR13 네이티브 엔진
업데이트와 이 KR13 데이터가 모두 필요합니다. KR12.4 서명 APK에는 Windows KR13의
엔진 패치 0017이 들어 있지 않으므로, 데이터 ZIP만 교체해서 동일한 동작을
기대하지 마세요.

1. 공식 Android KR13 서명 APK의 배포 여부와 서명/앱 ID를 확인하세요.
2. 기존 게임 데이터와 세이브를 백업하세요.
3. ZIP의 Morrowind_Korean_ReTranslation 폴더를 기존 한국어 데이터에 갱신하세요.
4. OpenMW Android의 데이터 디렉터리와 Morrowind_Korean_ReTranslation.esp
   활성화 및 모드 로드 순서를 확인하세요.
5. 공식 Android KR13 APK를 설치한 뒤 새 대화 주제/지역 모드를 게임에서 확인하세요.

이 ZIP에는 APK, 상용 원본 ESM, 사용자 세이브, Windows 실행 파일이 없습니다.
자동 구조 검사는 Android 실기기에서의 게임 진행이나 퀘스트 접근을 증명하지 않습니다.
"""
LINK = re.compile(r"@([^@#]+)#")
VARIABLE = re.compile(r"%[A-Za-z][A-Za-z0-9]*")

# These are the two reviewed source-English/Korean semantic corrections present
# in the published KR13 ESP. All other changed INFO display text must remain
# identical after stripping explicit topic-link markup.
ALLOWED_VISIBLE_CORRECTIONS = {
    "1002529664882329219": (
        "dc7f913cba2de353829baa2afdbb55d95a6e6b4e547a4643d8fcf76d51dd293b",
        "c7042859bdbf90403ba199fc58c9b39276bbefedcbc5e3508e04f2322fd9a0d4",
    ),
    "119482303674158": (
        "fca15235cf19c27d55654fd7e1cf57b7ad9da7d9a4cb46dd61e122ffd6925388",
        "4d3dbe2d9d53ae5a54139cb78ed94fa2b3f89abb51f12f6e966624d1bb48bd5e",
    ),
}

# KR13 includes four explicit legacy-topic aliases pointing at English engine
# topic keys. They are intentionally not DIAL.NAME records in the translated ESP.
# Report them, and reject any other dangling TOP target.
KNOWN_EXTERNAL_TOP_TARGETS = {
    ("마법사 길드에 가입*", "join the Mages Guild"),
    ("전사 길드에 가입*", "join the Fighters Guild"),
    ("제국 교단에 가입*", "join the Imperial Cult"),
    ("텔바니 가문에 가입*", "join House Telvanni"),
}


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def visible(raw):
    text = decoded(raw) if isinstance(raw, bytes) else raw
    return LINK.sub(lambda match: match.group(1).replace("\x7f", ""), text).replace("\x7f", "")


def dialect_topics(esp_records):
    topics = set()
    for tag, _, payload in esp_records:
        if tag != b"DIAL":
            continue
        values = dict(fields(payload))
        if values.get(b"DATA", b"\xff")[:1] == b"\0" and b"DELE" not in values:
            topics.add(decoded(values[b"NAME"]))
    return topics


def inspect_esp(before, after):
    left = list(chunks(before, 16))
    right = list(chunks(after, 16))
    if not left or len(left) != len(right):
        raise ValueError("TES3 record count or order changed")
    if left[0][0] != b"TES3":
        raise ValueError("TES3 master header missing")

    changed = []
    corrected = {}
    parent = ""
    for index, ((tag, old_header, old_payload), (tag2, new_header, new_payload)) in enumerate(zip(left, right)):
        if tag != tag2 or old_header[8:] != new_header[8:]:
            raise ValueError(f"TES3 record type or metadata changed at index {index}")
        if tag == b"DIAL":
            parent = decoded(dict(fields(new_payload)).get(b"NAME", b""))
        if old_payload == new_payload:
            continue
        if tag != b"INFO":
            raise ValueError(f"Non-INFO TES3 record changed at index {index}: {tag!r}")
        old_parts = fields(old_payload)
        new_parts = fields(new_payload)
        if [key for key, _ in old_parts] != [key for key, _ in new_parts]:
            raise ValueError(f"INFO subrecord type/order changed at index {index}")
        old_values, new_values = dict(old_parts), dict(new_parts)
        info_id = decoded(old_values.get(b"INAM", b""))
        if not info_id or old_values.get(b"INAM") != new_values.get(b"INAM"):
            raise ValueError(f"INFO identity changed at index {index}")
        modified_keys = [key for (key, first), (_, second) in zip(old_parts, new_parts) if first != second]
        if modified_keys != [b"NAME"] or len([key for key, _ in old_parts if key == b"NAME"]) != 1:
            raise ValueError(f"INFO selectors, scripts, or non-display fields changed: {info_id}")
        old_name, new_name = old_values[b"NAME"], new_values[b"NAME"]
        old_text, new_text = decoded(old_name), decoded(new_name)
        if Counter(VARIABLE.findall(old_text)) != Counter(VARIABLE.findall(new_text)):
            raise ValueError(f"INFO substitution variables were modified: {info_id}")

        equivalent = visible(old_text) == visible(new_text)
        if not equivalent:
            hashes = (sha(old_name), sha(new_name))
            if ALLOWED_VISIBLE_CORRECTIONS.get(info_id) != hashes or info_id in corrected:
                raise ValueError(f"Unreviewed visible INFO text change: {info_id}")
            corrected[info_id] = {"record_index": index, "old_NAME_sha256": hashes[0],
                                  "new_NAME_sha256": hashes[1]}
        changed.append({
            "record_index": index, "INAM": info_id, "DIAL": parent,
            "visible_Korean_unchanged": equivalent,
            "old_NAME_sha256": sha(old_name), "new_NAME_sha256": sha(new_name),
            "new_explicit_links": [match.group(1).replace("\x7f", "") for match in LINK.finditer(new_text)],
        })

    if not changed:
        raise ValueError("KR13 ESP unexpectedly contains no changes")
    # Vanilla TES3 can reuse an INAM under different dialogue parents.
    if len({(entry["DIAL"], entry["INAM"]) for entry in changed}) != len(changed):
        raise ValueError("Ambiguous duplicate changed INFO identifiers within one dialogue")
    if set(corrected) != set(ALLOWED_VISIBLE_CORRECTIONS):
        raise ValueError("Expected two reviewed KR13 visible dialogue corrections missing")
    return {
        "total_records": len(left),
        "changed_INFO_NAME": len(changed),
        "visible_equivalent_changes": len(changed) - len(corrected),
        "reviewed_visible_corrections": corrected,
        "all_non_INFO_records_unchanged": True,
        "all_INFO_non_NAME_fields_byte_identical": True,
        "record_headers_and_order_preserved": True,
        "changed_INFO": changed,
    }, dialect_topics(right)


def parse_top(raw, expected_blank_line=None):
    rows = []
    blank_positions = []
    for number, line in enumerate(raw.decode("utf-8-sig").splitlines(), start=1):
        # The pinned KR13 TOP has exactly one separator at physical line 5994.
        if not line:
            blank_positions.append(number)
            continue
        if "\t" not in line:
            raise ValueError("Malformed TOP mapping")
        key, value = line.split("\t", 1)
        if not key or not value:
            raise ValueError("Empty TOP mapping key/target")
        rows.append((key, value))
    if len({key for key, _ in rows}) != len(rows):
        raise ValueError("Duplicate TOP alias key")
    if blank_positions != ([expected_blank_line] if expected_blank_line else []):
        raise ValueError(f"Unexpected TOP blank lines: {blank_positions}")
    return rows


def inspect_top(before, after, topics):
    original, latest = parse_top(before), parse_top(after, expected_blank_line=5994)
    new_pairs = set(latest)
    if not set(original) <= new_pairs:
        raise ValueError("KR12.6 TOP mapping altered or removed")
    ordered = iter(latest)
    if not all(any(row == expected for row in ordered) for expected in original):
        raise ValueError("KR12.6 TOP alias order changed")
    external = {(key, target) for key, target in latest if target not in topics}
    if external != KNOWN_EXTERNAL_TOP_TARGETS:
        raise ValueError("Unexpected dangling TOP target(s): " + repr(sorted(external ^ KNOWN_EXTERNAL_TOP_TARGETS)))
    return {
        "original_alias_count": len(original),
        "new_alias_count": len(latest),
        "added_alias_count": len(new_pairs - set(original)),
        "original_aliases_and_order_preserved": True,
        "TOP_targets_resolve_to_DIAL_except_known_external": True,
        "known_external_topic_targets": [
            {"alias": key, "target": target} for key, target in sorted(external)
        ],
    }, dict(latest)


def validate_links(info_report, topics, aliases):
    new_links = 0
    for entry in info_report["changed_INFO"]:
        for link in entry["new_explicit_links"]:
            new_links += 1
            if link not in topics and aliases.get(link) not in topics:
                raise ValueError(f"INFO has unresolved KR13 topic link: {entry['INAM']}: {link!r}")
    info_report["changed_INFO_link_count"] = new_links
    info_report["changed_INFO_links_resolve_to_DIAL_or_TOP"] = True


def build(android, windows, output, report):
    checksum = output.with_name(output.name + ".sha256")
    inputs_and_outputs = [android, windows, output, report, checksum]
    if len({file.resolve() for file in inputs_and_outputs}) != len(inputs_and_outputs):
        raise ValueError("Input/output paths overlap")
    if any(file.exists() for file in (output, report, checksum)):
        raise FileExistsError("Existing output/report/checksum must never be overwritten")
    if sha(android.read_bytes()) != ANDROID_ZIP_SHA or sha(windows.read_bytes()) != WINDOWS_ZIP_SHA:
        raise ValueError("Unpinned Android KR12.6 / Windows KR13 public release ZIP SHA256")

    with zipfile.ZipFile(android) as az, zipfile.ZipFile(windows) as wz:
        source_names = az.namelist()
        windows_names = wz.namelist()
        if (len(set(source_names)) != len(source_names) or
                len(set(windows_names)) != len(windows_names) or az.testzip() or wz.testzip()):
            raise ValueError("Missing, duplicated, or corrupt ZIP source member")
        updates = {}
        for member, expected_old, expected_new in (
            (ESP, OLD_ESP_SHA, NEW_ESP_SHA), (TOP, OLD_TOP_SHA, NEW_TOP_SHA),
        ):
            source_name = ANDROID_DIR + member
            windows_name = WINDOWS_DIR + member
            if source_names.count(source_name) != 1 or windows_names.count(windows_name) != 1:
                raise ValueError("Missing Korean payload " + member)
            old, new = az.read(source_name), wz.read(windows_name)
            if sha(old) != expected_old or sha(new) != expected_new:
                raise ValueError("Korean ESP/TOP member hash mismatch: " + member)
            updates[source_name] = new

        esp_report, topics = inspect_esp(az.read(ANDROID_DIR + ESP), updates[ANDROID_DIR + ESP])
        top_report, aliases = inspect_top(az.read(ANDROID_DIR + TOP), updates[ANDROID_DIR + TOP], topics)
        validate_links(esp_report, topics, aliases)

        sidecar_changes = []
        for member in source_names:
            if not (member.startswith(ANDROID_DIR + "l10n/") and member.endswith("/ko.yaml")):
                continue
            expected = "payload/mods/" + member
            if windows_names.count(expected) != 1:
                raise ValueError("Missing Windows KR13 translation sidecar: " + expected)
            old, new = az.read(member), wz.read(expected)
            old.decode("utf-8-sig")
            new.decode("utf-8-sig")
            if new != old:
                updates[member] = new
                sidecar_changes.append({"member": member, "old_sha256": sha(old), "new_sha256": sha(new)})

        # Keep archive entry ordering and each original ZipInfo (timestamps,
        # compression, attributes, extra fields, and comments) intact.
        output.parent.mkdir(parents=True, exist_ok=True)
        if UPGRADE_README in source_names or UPGRADE_README in windows_names:
            raise ValueError("New documentation member name unexpectedly exists in input ZIP")
        with zipfile.ZipFile(output, mode="x", allowZip64=True) as result:
            result.comment = az.comment
            for item in az.infolist():
                result.writestr(item, updates.get(item.filename, az.read(item.filename)))
            doc = zipfile.ZipInfo(UPGRADE_README, date_time=(2026, 11, 12, 0, 0, 0))
            doc.compress_type = zipfile.ZIP_DEFLATED
            doc.external_attr = 0o644 << 16
            result.writestr(doc, UPGRADE_TEXT.encode("utf-8"))

    with zipfile.ZipFile(android) as original, zipfile.ZipFile(output) as candidate:
        if candidate.testzip() or candidate.namelist() != original.namelist() + [UPGRADE_README]:
            raise ValueError("Packaged Android ZIP integrity/order mismatch")
        if candidate.read(UPGRADE_README) != UPGRADE_TEXT.encode("utf-8"):
            raise ValueError("KR13 upgrade documentation missing/corrupted")
        for name in original.namelist():
            if candidate.read(name) != updates.get(name, original.read(name)):
                raise ValueError("Candidate ZIP bytes mismatch for member: " + name)
            old_info, new_info = original.getinfo(name), candidate.getinfo(name)
            for attr in ("date_time", "compress_type", "comment", "extra",
                         "external_attr", "internal_attr", "create_system"):
                if getattr(old_info, attr) != getattr(new_info, attr):
                    raise ValueError(f"ZIP member metadata drift: {name}: {attr}")
        if original.comment != candidate.comment:
            raise ValueError("ZIP archive comment changed")

    result_report = {
        "status": "ANDROID_KR13_DATA_ONLY_STATIC_QA_PASS",
        "version": "KR13",
        "release_tag": "android-korean-0.51.0-12-kr13-data-only",
        "android_kr12_6_source_sha256": ANDROID_ZIP_SHA,
        "windows_kr13_source_sha256": WINDOWS_ZIP_SHA,
        "old_esp_sha256": OLD_ESP_SHA, "new_esp_sha256": NEW_ESP_SHA,
        "old_top_sha256": OLD_TOP_SHA, "new_top_sha256": NEW_TOP_SHA,
        "output_sha256": sha(output.read_bytes()),
        "record_verification": esp_report,
        "top_verification": top_report,
        "changed_l10n_sidecars": sidecar_changes,
        "unchanged_android_member_count": len(source_names) - len(updates),
        "updated_android_members": sorted(updates),
        "new_documentation_member": UPGRADE_README,
        "new_documentation_sha256": sha(UPGRADE_TEXT.encode("utf-8")),
        "android_members_and_metadata_preserved": True,
        "apk_rebuilt": False, "saved_games_modified": False, "in_game_verified": False,
        "known_limitations": [
            "Static ZIP/TES3/TOP checks do not prove OpenMW Android runtime topic reachability.",
            "Four published TOP aliases point to external English join-topic keys rather than ESP DIAL names.",
            "The KR13 Windows native executable changes are not part of this Android DATA ONLY ZIP.",
        ],
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    with report.open("x", encoding="utf-8") as handle:
        json.dump(result_report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    with checksum.open("x", encoding="ascii") as handle:
        handle.write(result_report["output_sha256"] + "  " + output.name + "\n")
    return result_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("android", "windows", "output", "report"):
        parser.add_argument("--" + arg, type=Path, required=True)
    args = parser.parse_args()
    result = build(args.android, args.windows, args.output, args.report)
    print(json.dumps({
        "status": "PASS",
        "output_sha256": result["output_sha256"],
        "changed_INFO_NAME": result["record_verification"]["changed_INFO_NAME"],
        "reviewed_visible_corrections": len(result["record_verification"]["reviewed_visible_corrections"]),
        "new_TOP_aliases": result["top_verification"]["added_alias_count"],
        "changed_l10n_sidecars": len(result["changed_l10n_sidecars"]),
        "unchanged_android_members": result["unchanged_android_member_count"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
