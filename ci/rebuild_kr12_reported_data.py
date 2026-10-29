#!/usr/bin/env python3
"""Rebuild Windows/Android KR12 data from pinned released archives (issue #27).

This updates translation data, not the native OpenMW binary or the original
Bethesda Siege at Firemoth plugin. No source ESP is committed to Git.
"""
import argparse
import hashlib
import json
import pathlib
import struct
import zipfile

STEM = "Morrowind_Korean_ReTranslation"
PREFIX = {
    "windows": f"payload/mods/{STEM}/",
    "android": f"{STEM}/",
}
BASE_SHA256 = {
    "windows": "4c1ab3d6163391e7592957552292f4fc5aff22ad0d14020130062ad2ae5c135c",
    "android": "40cccc48303794f77af007206191323bceff9be0e04de4713ca917969ceacb3e",
}
ESP_SHA256 = "bbedecb7ee1cfc6f9f0730095fd7951591315ae0124d90dfa3e1e7c926d6bab7"
OLD_ORDER = "카짓 하나에게 현상금이 걸렸어. 이름은 드로'사카르야."
NEW_ORDER = "카짓 하나에게 현상금이 걸렸어. 이름은 @드로'사카르#야."
FIREMOTH_CELLS = (
    ("Firemoth, Keep", "파이어모스, 성채"),
    ("Firemoth, Great Hall", "파이어모스, 대전당"),
    ("Firemoth, Upper Chambers", "파이어모스, 상층 방"),
    ("Firemoth, Guard Quarters", "파이어모스, 경비병 숙소"),
    ("Firemoth, Dungeon", "파이어모스, 지하 감옥"),
    ("Firemoth, Lower Cavern", "파이어모스, 하층 동굴"),
    ("Firemoth, Tomb", "파이어모스, 무덤"),
    ("Firemoth, Guard Towers", "파이어모스, 감시탑"),
    ("Firemoth, Upper Cavern", "파이어모스, 상층 동굴"),
    ("Firemoth, Mine", "파이어모스, 광산"),
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fields(blob):
    pos = 0
    while pos < len(blob):
        if pos + 8 > len(blob):
            raise ValueError("Truncated subrecord")
        kind, size = struct.unpack_from("<4sI", blob, pos)
        start = pos + 8
        end = start + size
        if end > len(blob):
            raise ValueError("Subrecord crosses record boundary")
        yield kind, blob[start:end]
        pos = end


def records(blob):
    pos = 0
    while pos < len(blob):
        if pos + 16 > len(blob):
            raise ValueError("Truncated TES3 record")
        kind, size = struct.unpack_from("<4sI", blob, pos)
        end = pos + 16 + size
        if end > len(blob):
            raise ValueError("TES3 record crosses file boundary")
        yield kind, blob[pos:pos+16], list(fields(blob[pos+16:end]))
        pos = end


def as_text(data):
    return data.rstrip(b"\0").decode("utf-8")


def rewrite(raw):
    if digest(raw) != ESP_SHA256:
        raise ValueError("Unexpected KR12 translation ESP SHA-256")
    out = bytearray()
    current_dial = None
    edits = []
    count = 0
    for kind, header, parts in records(raw):
        count += 1
        before = {tag: value for tag, value in parts}
        if kind == b"DIAL":
            current_dial = as_text(before[b"NAME"])
        changed = []
        if kind == b"GMST" and as_text(before.get(b"NAME", b"")) == "sfor":
            if as_text(before[b"STRV"]) != "동안":
                raise ValueError("Duration marker changed since pinned baseline")
            changed.append((b"STRV", "동안", "지속:"))
        if kind == b"GMST" and as_text(before.get(b"NAME", b"")).lower() == "sonword":
            if as_text(before[b"STRV"]) != "적용":
                raise ValueError("Application range label changed since pinned baseline")
            changed.append((b"STRV", "적용", "적용:"))
        if kind == b"GMST" and as_text(before.get(b"NAME", b"")) == "sEffectLight":
            if as_text(before[b"STRV"]) != "경량":
                raise ValueError("Light text changed since pinned baseline")
            changed.append((b"STRV", "경량", "빛"))
        if kind == b"INFO" and current_dial == "명령":
            if (as_text(before.get(b"INAM", b"")) == "5257862417724508"
                and as_text(before.get(b"ONAM", b"")) == "lorbumol gro-aglakh"):
                if as_text(before[b"NAME"]) != OLD_ORDER:
                    raise ValueError("Dro'Sakhar quest dialogue changed")
                changed.append((b"NAME", OLD_ORDER, NEW_ORDER))
        if changed:
            for tag, old, new in changed:
                if sum(k == tag for k, _ in parts) != 1 or as_text(before[tag]) != old:
                    raise ValueError("Ambiguous target field")
                value = before[tag]
                nul = value[len(value.rstrip(b"\0")):]
                replacement = new.encode("utf-8") + nul
                parts = [(k, replacement if k == tag else v) for k, v in parts]
                edits.append({"record_type": kind.decode(), "field": tag.decode(),
                              "before": old, "after": new})
            body = b"".join(k + struct.pack("<I", len(v)) + v for k, v in parts)
            out += header[:4] + struct.pack("<I", len(body)) + header[8:] + body
        else:
            body = b"".join(k + struct.pack("<I", len(v)) + v for k, v in parts)
            if len(body) != struct.unpack_from("<I", header, 4)[0]:
                raise AssertionError("Invalid original record")
            out += header + body
    if [(e["record_type"], e["field"]) for e in edits] != [
        ("GMST", "STRV"), ("GMST", "STRV"), ("GMST", "STRV"), ("INFO", "NAME")
    ]:
        raise AssertionError("Expected exactly four targeted record edits")
    rewritten = bytes(out)
    old_records = list(records(raw))
    new_records = list(records(rewritten))
    if len(old_records) != len(new_records) or len(old_records) != count:
        raise AssertionError("Record count changed")
    changed_count = 0
    for (a, ah, af), (b, bh, bf) in zip(old_records, new_records):
        if a != b or ah[:4] + ah[8:] != bh[:4] + bh[8:] or len(af) != len(bf):
            raise AssertionError("Record structure/metadata changed")
        for (ak, av), (bk, bv) in zip(af, bf):
            if ak != bk:
                raise AssertionError("Subrecord type/order changed")
            if av != bv:
                changed_count += 1
                if not ((a == b"GMST" and ak == b"STRV"
                         and as_text(dict(af)[b"NAME"]).lower() in ("seffectlight", "sfor", "sonword"))
                        or (a == b"INFO" and ak == b"NAME"
                            and as_text(dict(af)[b"INAM"]) == "5257862417724508")):
                    raise AssertionError("Unexpected field changed")
    if changed_count != 4:
        raise AssertionError("Unexpected changed field count")
    return rewritten, edits, count


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--platform", choices=tuple(PREFIX), required=True)
    ap.add_argument("--source", type=pathlib.Path, required=True)
    ap.add_argument("--output", type=pathlib.Path, required=True)
    ap.add_argument("--report", type=pathlib.Path, required=True)
    args = ap.parse_args()
    if args.source.resolve() == args.output.resolve():
        ap.error("Output must differ from original release ZIP")
    original_zip = args.source.read_bytes()
    if digest(original_zip) != BASE_SHA256[args.platform]:
        raise ValueError("Not the pinned public KR12 " + args.platform + " release")
    prefix = PREFIX[args.platform]
    esp_name = prefix + STEM + ".esp"
    cel_name = prefix + "Siege at Firemoth.cel"
    cel = b"\xef\xbb\xbf" + "".join(
        english + "\t" + korean + "\r\n" for english, korean in FIREMOTH_CELLS
    ).encode("utf-8")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.source) as zin:
        names = zin.namelist()
        if names.count(esp_name) != 1 or cel_name in names:
            raise ValueError("Missing/duplicate ESP or conflicting Firemoth alias")
        original_esp = zin.read(esp_name)
        patched_esp, edits, total_records = rewrite(original_esp)
        with zipfile.ZipFile(args.output, "w") as zout:
            for entry in zin.infolist():
                zout.writestr(entry, patched_esp if entry.filename == esp_name
                              else zin.read(entry.filename))
            zout.writestr(cel_name, cel, compress_type=zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(args.source) as baseline, zipfile.ZipFile(args.output) as built:
        if built.testzip() is not None or built.namelist() != names + [cel_name]:
            raise AssertionError("ZIP contents/CRC invalid")
        for name in names:
            if name != esp_name and baseline.read(name) != built.read(name):
                raise AssertionError("Unrelated ZIP member changed: " + name)
        if built.read(esp_name) != patched_esp or built.read(cel_name) != cel:
            raise AssertionError("Patch payload mismatch")
    report = {
        "platform": args.platform,
        "source_zip_sha256": digest(original_zip),
        "source_esp_sha256": digest(original_esp),
        "patched_zip_sha256": digest(args.output.read_bytes()),
        "patched_esp_sha256": digest(patched_esp),
        "record_count_unchanged": total_records,
        "changed_subrecords": edits,
        "duration_label": "지속: N초",
        "application_range_label": "적용: 자신/접촉/대상",
        "new_firemoth_cell_aliases": len(FIREMOTH_CELLS),
        "other_zip_members_byte_identical": True,
        "pillow_shipment_vanilla_condition_changed": False,
        "duration_formatting_changed": False,
        "engine_rebuilt": False,
        "in_game_verified": False,
        "release_published": False,
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
