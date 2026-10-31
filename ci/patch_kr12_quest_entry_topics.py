#!/usr/bin/env python3
"""Produce a NEW candidate ESP containing exact, evidence-backed quest-entry tags.

Read-only on the pinned KR12.2 release. Never modifies the original zip/ESP or
its scripts/quest conditions. Review and gameplay QA required before release.
"""
import argparse
import hashlib
import json
import re
import struct
import zipfile
from pathlib import Path

BASE_SHA = "0f04a21d69ecae16a1c2ae3bb0b739ac4e71cdb59054c809fc844128e2c12327"
STEM = "Morrowind_Korean_ReTranslation.esp"
# (INFO INAM, source DIAL, original ONAM, original phrase, new tagged phrase, target DIAL)
CASES = (
    ("6986172382590219429", "명령", "persius mercius",
     "바스라는 강령술사 소굴", "@바스#라는 강령술사 소굴", "바스"),
    ("499230085676914328", "일거리", "stacey",
     "나빌과 라네스 이에니스야", "나빌과 라네스 @이에니스#야", "이에니스"),
    ("20813494252707603", "소환 명령", "caius cosades",
     "공작원으로 승진시키는", "@공작원으로 승진#시키는", "공작원으로 승진"),
    ("187538034100124510", "임무", "falco galenus",
     "결정하셨습니까", "@결정#하셨습니까", "결정"),
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def chunks(blob, head):
    offset = 0
    while offset < len(blob):
        if offset + head > len(blob):
            raise ValueError("truncated TES3 record")
        tag, size = struct.unpack_from("<4sI", blob, offset)
        end = offset + head + size
        if end > len(blob):
            raise ValueError("record out of bounds")
        yield tag, blob[offset:offset + head], blob[offset + head:end]
        offset = end


def decoded(data):
    return data.rstrip(b"\0").decode("utf-8")


def fields(payload):
    return [(tag, value) for tag, _, value in chunks(payload, 8)]


def pack(tag, header, payload):
    return tag + struct.pack("<I", len(payload)) + header[8:] + payload


def rewrite(original, verify_sha=True):
    if verify_sha and sha(original) != BASE_SHA:
        raise ValueError("unexpected KR12.2 ESP SHA-256; source not patched")
    source = list(chunks(original, 16))
    real_topics = set()
    for tag, _, payload in source:
        if tag == b"DIAL":
            f = dict(fields(payload))
            if f.get(b"DATA", b"\xff")[:1] == b"\0" and b"DELE" not in f:
                real_topics.add(decoded(f[b"NAME"]))
    if not {case[-1] for case in CASES} <= real_topics:
        raise ValueError("requested target DIAL missing in source")

    changed = []
    out = []
    parent = None
    for tag, header, payload in source:
        if tag == b"DIAL":
            parent = decoded(dict(fields(payload))[b"NAME"])
        if tag != b"INFO":
            out.append(header + payload)
            continue
        parts = fields(payload)
        f = dict(parts)
        iid = decoded(f.get(b"INAM", b""))
        actor = decoded(f.get(b"ONAM", b"")).lower()
        matching = [c for c in CASES if (iid, parent, actor) == (c[0], c[1], c[2])]
        if not matching:
            out.append(header + payload)
            continue
        if len(matching) != 1:
            raise ValueError("duplicate candidate specification")
        task = matching[0]
        old_value = f[b"NAME"]
        before = decoded(old_value)
        if before.count(task[3]) != 1 or task[4].replace("@"+task[-1]+"#", task[-1]) != task[3]:
            raise ValueError("invalid original text/visible text: " + iid)
        after = before.replace(task[3], task[4])
        new_value = after.encode("utf-8") + old_value[len(old_value.rstrip(b"\0")):]
        rebuilt = b"".join(
            struct.pack("<4sI", name, len(new_value if name == b"NAME" else value))
            + (new_value if name == b"NAME" else value)
            for name, value in parts
        )
        out.append(pack(tag, header, rebuilt))
        changed.append({
            "INFO":iid, "DIAL":parent, "actor":actor, "target":task[-1],
            "source_name_sha256":sha(old_value), "patched_name_sha256":sha(new_value),
            "visible_text_unchanged":after.replace("@"+task[-1]+"#", task[-1]) == before
        })
    if sorted(x["INFO"] for x in changed) != sorted(c[0] for c in CASES):
        raise ValueError("not all four intended INFO records were patched")
    patched = b"".join(out)

    # Independent post-rebuild parity: preserve all other records and all fields,
    # particularly INFO selector conditions and BNAM result scripts.
    newer = list(chunks(patched, 16))
    if len(newer) != len(source):
        raise ValueError("record count drift")
    changed_ids = {c[0] for c in CASES}
    for (tag, h, v), (t2, h2, v2) in zip(source, newer):
        if tag != t2 or h[8:] != h2[8:]:
            raise ValueError("record header changed unexpectedly")
        if tag != b"INFO":
            if h + v != h2 + v2:
                raise ValueError("non-INFO changed")
            continue
        oldparts, newparts = fields(v), fields(v2)
        if len(oldparts) != len(newparts):
            raise ValueError("INFO subrecord count drift")
        iid = decoded(dict(oldparts).get(b"INAM", b""))
        for (k, old), (k2, new) in zip(oldparts, newparts):
            if k != k2 or (old != new and (iid not in changed_ids or k != b"NAME")):
                raise ValueError("non-target subrecord changed: " + iid)
    return patched, {
        "status":"CANDIDATE_NOT_RELEASED_GAMEPLAY_QA_REQUIRED",
        "source_esp_sha256":sha(original),
        "candidate_esp_sha256":sha(patched),
        "changed_info_count":len(changed),
        "all_other_records_and_fields_unchanged":True,
        "changes":changed,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-zip", type=Path, required=True)
    p.add_argument("--output-esp", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    args = p.parse_args()
    if args.output_esp.exists() or args.report.exists():
        raise ValueError("outputs must be new files")
    with zipfile.ZipFile(args.source_zip) as archive:
        names = [n for n in archive.namelist() if n.endswith("/"+STEM)]
        if len(names) != 1:
            raise ValueError("expected exactly one KR12.2 translation ESP")
        original = archive.read(names[0])
    patched, report = rewrite(original)
    args.output_esp.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.output_esp.write_bytes(patched)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
