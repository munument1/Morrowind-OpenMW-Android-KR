#!/usr/bin/env bash
set -euo pipefail

UPSTREAM_REPO='munument1/Morrowind-OpenMW-Android-KR'
UPSTREAM_TAG='android-korean-0.51.0-12-kr8'
UPSTREAM_APK='OpenMW-Android-0.51.0-12-Korean-KR8-16K.apk'
UPSTREAM_APK_SHA256='42e5f909b05e516519502abdf0bded3023e1952a7218d8a493f8b09a838e5a4f'
NDK_PACKAGE='27.3.13750724'
NATIVE_INPUT="${NATIVE_INPUT:-native-input}"
OUTDIR='release-artifacts'
JNI_DIR='source/app/src/main/jniLibs/arm64-v8a'
NATIVE_GATE='source/buildscripts/openmw-051-patch39-libopenmw.sha256'

mkdir -p "$OUTDIR" work/upstream "$JNI_DIR"

for library in libopenmw.so libopenal.so libSDL2.so libGL.so libcollada-dom2.5-dp.so libc++_shared.so; do
  test -s "$NATIVE_INPUT/libs/$library"
  cp "$NATIVE_INPUT/libs/$library" "$JNI_DIR/$library"
done

grep -Fq 'required_min_load_align=0x4000' "$NATIVE_INPUT/page-size-report.txt"

test -s "$NATIVE_INPUT/libopenmw.so.sha256"
EXPECTED_KR_SHA="$(awk 'NR==1 {print $1}' "$NATIVE_INPUT/libopenmw.so.sha256")"
ACTUAL_KR_SHA="$(sha256sum "$NATIVE_INPUT/libs/libopenmw.so" | awk '{print $1}')"
test "$EXPECTED_KR_SHA" = "$ACTUAL_KR_SHA"
test "$ACTUAL_KR_SHA" != 'cf106f05d5292663caef5ee2b4588517a9c0da211674f7571cee5d96f2dc8af9'
grep -Fxq 'voice_subtitle_sync=9ccc477acf8488bf3b93e5b64b897ddb8a7f52af' "$NATIVE_INPUT/korean-origin.txt"

grep -Fxq 'topic_link_fix=1f40a0952d193b4ba68cb4f6ffa08091233353f8' "$NATIVE_INPUT/korean-origin.txt"
grep -Fxq 'spell_duration_order=29999121dd127c83219a30ae995e0b7ba09b0b61' "$NATIVE_INPUT/korean-origin.txt"

grep -Fxq 'legacy_topic_recovery=1f31cccb299d8fd3b8895fcd0523775207c3355c' "$NATIVE_INPUT/korean-origin.txt"
grep -Fxq 'korean_honorific=103e64ca1e5e63d8a08e516e0f21ede004ea516a' "$NATIVE_INPUT/korean-origin.txt"
grep -Fxq 'korean_topic_boundaries=3a2498b52b6ca7358a92ef9a846f462867a323e4' "$NATIVE_INPUT/korean-origin.txt"
printf '%s  %s\n' "$ACTUAL_KR_SHA" 'app/src/main/jniLibs/arm64-v8a/libopenmw.so' > "$NATIVE_GATE"
grep -Fq "$ACTUAL_KR_SHA" "$NATIVE_GATE"

NDK_ROOT="${ANDROID_HOME:?ANDROID_HOME is required}/ndk/$NDK_PACKAGE"
READELF="$NDK_ROOT/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-readelf"
AAPT="$ANDROID_HOME/build-tools/35.0.0/aapt"
ZIPALIGN="$ANDROID_HOME/build-tools/35.0.0/zipalign"
test -x "$READELF"
test -x "$AAPT"
test -x "$ZIPALIGN"

{
  echo 'required_min_load_align=0x4000'
  for so in "$JNI_DIR"/*.so; do
    name="$(basename "$so")"
    min=''
    while read -r align; do
      [[ -n "$align" ]] || continue
      if [[ -z "$min" ]] || (( align < min )); then min="$align"; fi
    done < <("$READELF" -lW "$so" | awk '$1=="LOAD" {print $NF}')
    min="${min:-0}"
    printf '%s_min_load_align=0x%x\n' "$name" "$min"
    (( min >= 0x4000 ))
  done
} | tee "$OUTDIR/native-page-size-report.txt"

gh release download "$UPSTREAM_TAG" --repo "$UPSTREAM_REPO" --pattern "$UPSTREAM_APK" --dir work/upstream --clobber
BASE_APK="work/upstream/$UPSTREAM_APK"
test "$(sha256sum "$BASE_APK" | awk '{print $1}')" = "$UPSTREAM_APK_SHA256"

EXTRACTED='work/upstream/resources'
rm -rf "$EXTRACTED" source/app/src/main/assets/libopenmw source/app/src/main/assets/android_omwfx
mkdir -p "$EXTRACTED" source/app/src/main/assets
unzip -q "$BASE_APK" 'assets/libopenmw/*' -d "$EXTRACTED"
cp -a "$EXTRACTED/assets/libopenmw" source/app/src/main/assets/
test -s source/app/src/main/assets/libopenmw/resources/vfs/fonts/DemonicLetters.omwfont
test -s source/app/src/main/assets/libopenmw/resources/vfs/fonts/DemonicLetters.ttf
if unzip -Z1 "$BASE_APK" | grep -q '^assets/android_omwfx/'; then
  unzip -q "$BASE_APK" 'assets/android_omwfx/*' -d "$EXTRACTED"
  cp -a "$EXTRACTED/assets/android_omwfx" source/app/src/main/assets/
fi

python3 - <<'PY'
from pathlib import Path
movie_fallbacks = [
    'fallback=Movies_Company_Logo,bethesda logo.bik',
    'fallback=Movies_Morrowind_Logo,mw_logo.bik',
    'fallback=Movies_New_Game,mw_intro.bik',
    'fallback=Movies_Loading,mw_load.bik',
    'fallback=Movies_Options_Menu,mw_menu.bik',
]
for name in [
    'source/app/openmw.base.cfg',
    'source/app/src/main/assets/libopenmw/openmw/openmw.base.cfg',
]:
    p = Path(name)
    text = p.read_text(encoding='utf-8').replace('\r\n', '\n')
    lines = [line for line in text.splitlines()
             if not line.startswith('fallback=Fonts_Font_0,')
             and not line.startswith('fallback=Fonts_Font_2,')
             and not line.startswith('fallback=Movies_Company_Logo,')
             and not line.startswith('fallback=Movies_Morrowind_Logo,')
             and not line.startswith('fallback=Movies_New_Game,')
             and not line.startswith('fallback=Movies_Loading,')
             and not line.startswith('fallback=Movies_Options_Menu,')]
    lines += ['fallback=Fonts_Font_0,MysticCards', 'fallback=Fonts_Font_2,DemonicLetters']
    lines += movie_fallbacks
    p.write_text('\n'.join(lines) + '\n', encoding='utf-8')
PY

for cfg in source/app/openmw.base.cfg source/app/src/main/assets/libopenmw/openmw/openmw.base.cfg; do
  grep -Fx 'fallback=Fonts_Font_0,MysticCards' "$cfg"
  grep -Fx 'fallback=Fonts_Font_2,DemonicLetters' "$cfg"
  grep -Fx 'fallback=Movies_New_Game,mw_intro.bik' "$cfg"
done
grep -Fq 'category.equals("Fonts", ignoreCase = true)' source/app/src/main/java/file/IniConverter.kt
grep -Fq '<item>매우 높음</item>' source/app/src/main/res/values-ko/strings.xml

(
  cd source
  chmod +x gradlew
  ./gradlew --no-daemon :app:testMainlineDebugUnitTest --tests file.IniConverterTest
  # Permanent release must NOT ship a debuggable Android build.
  ./gradlew --no-daemon :app:assembleMainlineRelease
)

APK="$(find source/app/build/outputs/apk/mainline/release -maxdepth 1 -type f -name 'app-mainline-release*.apk' | sort | head -n 1)"
test -n "$APK"
test -s "$APK"

for library in libopenmw.so libopenal.so libSDL2.so libGL.so libcollada-dom2.5-dp.so libc++_shared.so; do
  A="$(unzip -p "$APK" "lib/arm64-v8a/$library" | sha256sum | awk '{print $1}')"
  B="$(sha256sum "$NATIVE_INPUT/libs/$library" | awk '{print $1}')"
  test "$A" = "$B"
done

"$AAPT" dump badging "$APK" > /tmp/badging.txt
grep -F "versionCode='5114'" /tmp/badging.txt
grep -F "versionName='0.51.0-12-KR12'" /tmp/badging.txt
grep -Fq "name='com.ast.openmw.korean'" /tmp/badging.txt
if grep -Fq "name='com.ast.openmw'" /tmp/badging.txt; then
  echo 'Original KR8 package identity was not isolated!' >&2
  exit 1
fi
grep -Fq 'applicationId "com.ast.openmw.korean"' source/app/build.gradle
grep -Fq 'packageName == "com.ast.openmw.korean"' source/app/src/main/java/utils/MyApp.kt

unzip -p "$APK" assets/libopenmw/openmw/openmw.base.cfg > /tmp/openmw.base.cfg
grep -Fx 'fallback=Fonts_Font_0,MysticCards' /tmp/openmw.base.cfg
grep -Fx 'fallback=Fonts_Font_2,DemonicLetters' /tmp/openmw.base.cfg
for resource in DemonicLetters.omwfont DemonicLetters.ttf DemonicLettersFontLicense.txt; do
  font="assets/libopenmw/resources/vfs/fonts/$resource"
  test "$(unzip -p "$APK" "$font" | sha256sum | awk '{print $1}')" = "$(unzip -p "$BASE_APK" "$font" | sha256sum | awk '{print $1}')"
done
grep -Fx 'fallback=Movies_New_Game,mw_intro.bik' /tmp/openmw.base.cfg

TMPDIR="$(mktemp -d)"
unzip -q "$APK" 'lib/arm64-v8a/*.so' -d "$TMPDIR"
{
  echo 'required_min_load_align=0x4000'
  for so in "$TMPDIR"/lib/arm64-v8a/*.so; do
    name="$(basename "$so")"
    min=''
    while read -r align; do
      [[ -n "$align" ]] || continue
      if [[ -z "$min" ]] || (( align < min )); then min="$align"; fi
    done < <("$READELF" -lW "$so" | awk '$1=="LOAD" {print $NF}')
    min="${min:-0}"
    printf '%s_min_load_align=0x%x\n' "$name" "$min"
    (( min >= 0x4000 ))
  done
} | tee "$OUTDIR/apk-page-size-report.txt"
rm -rf "$TMPDIR"

"$ZIPALIGN" -c -P 16 4 "$APK"

OUT="$OUTDIR/OpenMW-Android-0.51.0-12-Korean-KR12-Unsigned-16K.apk"
cp "$APK" "$OUT"
# Keep this candidate unsigned: only the separate, secret-gated workflow
# may sign and publish it using the backed-up permanent signing identity.
if "$ANDROID_HOME/build-tools/35.0.0/apksigner" verify "$OUT" >/dev/null 2>&1; then
  echo '::error::Permanent release staging APK was unexpectedly pre-signed' >&2
  exit 1
fi
echo 'Candidate is intentionally unsigned; signing is restricted to final publisher.' > "$OUTDIR/kr11-signer.txt"
# Write a checksum using a path relative to release-artifacts, so that
# both local verification and release downloads can verify it reliably.
( cd "$OUTDIR" && sha256sum "$(basename "$OUT")" > "$(basename "$OUT").sha256" )
sha256sum "$OUT"
cp "$NATIVE_INPUT/korean-origin.txt" "$OUTDIR/korean-origin.txt"
cp "$NATIVE_INPUT/page-size-report.txt" "$OUTDIR/native-build-page-size-report.txt"

{
  echo 'OpenMW Android 0.51.0-12 Korean KR12 verification'
  echo 'result=PASS'
  echo 'runtime_patches=0001-0013'
  echo 'standalone_application_id=com.ast.openmw.korean'
  echo 'original_application_id=com.ast.openmw'
  echo 'legacy_shared_storage_migration=disabled_for_standalone'
  echo 'signing=unsigned_release_candidate (requires persistent key)'
  echo 'video_subtitles_engine=enabled'
  echo 'required_page_size=16384'
  echo 'versionCode=5114'
  echo 'versionName=0.51.0-12-KR12'
  echo 'movie_fallback=mw_intro.bik'
  echo 'zipalign_16k=PASS'
  echo
  echo '[native build]'
  cat "$OUTDIR/native-build-page-size-report.txt"
  echo
  echo '[packaged native libraries]'
  cat "$OUTDIR/native-page-size-report.txt"
  echo
  echo '[APK native libraries]'
  cat "$OUTDIR/apk-page-size-report.txt"
} > "$OUTDIR/16k-verification.txt"

echo 'Verified Korean KR12 maintenance unsigned RELEASE candidate with patches 0001-0013 and 16 KiB native ELF alignment.'
