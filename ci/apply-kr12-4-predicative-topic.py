#!/usr/bin/env python3
"""Apply Windows KR12.4 patch 0016 by an exact verified insertion anchor.

Android's patch 0015 has platform-specific surrounding context, so a plain
Windows unified-diff hunk can fail. Keep the SAME added lines as the reviewed
Windows 0016 patch; do not relax/alter semantic behavior or other code.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path

PATCH_GIT_BLOB_SHA1 = "710a0c1320c8aef66a88732a21e67392777bafbb"
SOURCE_PATH = Path("apps/openmw/mwdialogue/keywordsearch.cpp")
ANCHOR = "        // Plural nouns take case particles too: \"블레이드 교관들에\", \"길드원들에게\"."
PRECONDITIONS = (
    "constexpr std::string_view contextualNounEndings[] = {",
    "std::end(contextualNounEndings), suffix)",
    "return true;",
)
EXISTING = ("futureVerbEndings[]", "zeroCodaNounEndings[]")

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def extract_exact_addition(patch: bytes) -> str:
    if git_blob_sha(patch) != PATCH_GIT_BLOB_SHA1:
        raise ValueError("Windows 0016 patch blob SHA mismatch: refusing unreviewed source")
    data = patch.decode("utf-8")
    lines = data.splitlines(keepends=True)
    addition = "".join(line[1:] for line in lines if line.startswith("+") and not line.startswith("+++"))
    assert addition.startswith("        // A few translated topic keywords")
    assert "futureVerbEndings[]" in addition and "zeroCodaNounEndings[]" in addition
    assert len(addition) > 1200
    assert addition.endswith("\n\n")
    return addition

def integrate(source: str, addition: str) -> str:
    if any(x in source for x in EXISTING):
        raise ValueError("0016 keyword endings already exist or partially applied; refusing duplicate")
    if source.count(ANCHOR) != 1:
        raise ValueError("Android noun/plural anchor missing or not unique")
    pos = source.index(ANCHOR)
    # Verify patch 0015 is already installed immediately above the insertion.
    context = source[max(0, pos-900):pos]
    for x in PRECONDITIONS:
        if x not in context:
            raise ValueError("0015 contextual noun grammar not found near 0016 insertion: " + x)
    if source[pos-1] != "\n":
        raise ValueError("Insertion anchor not at a clean line boundary")
    return source[:pos] + addition + source[pos:]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("upstream_source", type=Path)
    parser.add_argument("verified_patch", type=Path)
    args = parser.parse_args()
    target = args.upstream_source / SOURCE_PATH
    patch = args.verified_patch.read_bytes()
    if not target.is_file():
        raise ValueError("Missing keywordsearch.cpp at " + str(target))
    add = extract_exact_addition(patch)
    original_bytes = target.read_bytes()
    original = original_bytes.decode("utf-8")
    if "\r\n" in original:
        raise ValueError("Unexpected Windows line endings in Android OpenMW source")
    newer = integrate(original, add)
    target.write_bytes(newer.encode("utf-8"))
    print("PASS: exact verified Windows 0016 implementation inserted into Android 0015 code")
    print("source_0016_sha256=" + hashlib.sha256(newer.encode()).hexdigest())
    print("windows_0016_git_blob=" + PATCH_GIT_BLOB_SHA1)

if __name__ == "__main__":
    main()
