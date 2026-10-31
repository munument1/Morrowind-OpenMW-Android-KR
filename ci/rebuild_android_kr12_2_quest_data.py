#!/usr/bin/env python3
"""Build Android KR12.2 data from verified KR12.1 ZIP, changing four INFO.NAME only."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
from patch_kr12_quest_entry_topics import rewrite, CASES

BASE_SHA="f00cf86fc0083377cdabab5deb3929204f01686d6814be5de5b037cd0848c4ee"
ESP_SHA="0f04a21d69ecae16a1c2ae3bb0b739ac4e71cdb59054c809fc844128e2c12327"
ESP="Morrowind_Korean_ReTranslation/Morrowind_Korean_ReTranslation.esp"
def digest(x): return hashlib.sha256(x).hexdigest()
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for n in ("source","output","report"): ap.add_argument("--"+n,type=Path,required=True)
    a=ap.parse_args()
    if len({a.source.resolve(),a.output.resolve(),a.report.resolve()})!=3 or a.output.exists() or a.report.exists():
        raise ValueError("Input/output overlap or existing output")
    if digest(a.source.read_bytes())!=BASE_SHA: raise ValueError("Source not the official Android KR12.1 ZIP")
    with zipfile.ZipFile(a.source) as src:
        names=src.namelist()
        if names.count(ESP)!=1 or src.testzip() is not None: raise ValueError("Invalid input ZIP")
        old=src.read(ESP)
        if digest(old)!=ESP_SHA: raise ValueError("Unexpected Android ESP hash")
        newer,proof=rewrite(old)
        if proof["changed_info_count"]!=4 or not proof["all_other_records_and_fields_unchanged"]:
            raise ValueError("Unexpected rewritten records")
        a.output.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(a.output,"w") as dst:
            for member in src.infolist():
                dst.writestr(member,newer if member.filename==ESP else src.read(member.filename))
    with zipfile.ZipFile(a.source) as original,zipfile.ZipFile(a.output) as built:
        if built.testzip() is not None or built.namelist()!=names: raise ValueError("ZIP structure changed")
        for n in names:
            if n!=ESP and built.read(n)!=original.read(n): raise ValueError("Unrelated member modified: "+n)
    proof.update({"source_release":"android-korean-0.51.0-12-kr12.1-permanent",
       "source_zip_sha256":BASE_SHA,"patched_zip_sha256":digest(a.output.read_bytes()),
       "changed_INFO_inam":sorted(c[0] for c in CASES),
       "unchanged_android_zip_members_byte_identical":True,
       "modified_quest_selectors_or_scripts":False,
       "android_hardware_gameplay_verified":False,"release_published":False})
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print(json.dumps(proof,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
