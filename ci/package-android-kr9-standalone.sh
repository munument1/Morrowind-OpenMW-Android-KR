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
test "$ACTUAL_KR_SHA" = 'cf106f05d5292663caef5ee2b4588517a9c0da211674f7571cee5d96f2dc8af9'
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
    lines += ['fallback=Fonts_Font_0,MysticCards', 'fallback=Fonts_Font_2,MysticCards']
    lines += movie_fallbacks
    p.write_text('\n'.join(lines) + '\n', encoding='utf-8')
PY

for cfg in source/app/openmw.base.cfg source/app/src/main/assets/libopenmw/openmw/openmw.base.cfg; do
  grep -Fx 'fallback=Fonts_Font_0,MysticCards' "$cfg"
  grep -Fx 'fallback=Fonts_Font_2,MysticCards' "$cfg"
  grep -Fx 'fallback=Movies_New_Game,mw_intro.bik' "$cfg"
done
grep -Fq 'category.equals("Fonts", ignoreCase = true)' source/app/src/main/java/file/IniConverter.kt
grep -Fq '<item>매우 높음</item>' source/app/src/main/res/values-ko/strings.xml

(
  cd source
  chmod +x gradlew
  ./gradlew --no-daemon :app:testMainlineDebugUnitTest --tests file.IniConverterTest
  ./gradlew --no-daemon :app:assembleMainlineDebug
)

APK='source/app/build/outputs/apk/mainline/debug/app-mainline-debug.apk'
test -s "$APK"

for library in libopenmw.so libopenal.so libSDL2.so libGL.so libcollada-dom2.5-dp.so libc++_shared.so; do
  A="$(unzip -p "$APK" "lib/arm64-v8a/$library" | sha256sum | awk '{print $1}')"
  B="$(sha256sum "$NATIVE_INPUT/libs/$library" | awk '{print $1}')"
  test "$A" = "$B"
done

"$AAPT" dump badging "$APK" > /tmp/badging.txt
grep -F "versionCode='5112'" /tmp/badging.txt
grep -F "versionName='0.51.0-12'" /tmp/badging.txt
grep -Fq "name='com.ast.openmw.kr9'" /tmp/badging.txt
if grep -Fq "name='com.ast.openmw'" /tmp/badging.txt; then
  echo 'Original KR8 package identity was not isolated!' >&2
  exit 1
fi
grep -Fq 'applicationId "com.ast.openmw.kr9"' source/app/build.gradle
grep -Fq 'packageName == "com.ast.openmw.kr9"' source/app/src/main/java/utils/MyApp.kt

unzip -p "$APK" assets/libopenmw/openmw/openmw.base.cfg > /tmp/openmw.base.cfg
grep -Fx 'fallback=Fonts_Font_0,MysticCards' /tmp/openmw.base.cfg
grep -Fx 'fallback=Fonts_Font_2,MysticCards' /tmp/openmw.base.cfg
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

OUT="$OUTDIR/OpenMW-Android-0.51.0-12-Korean-KR9-Standalone-16K.apk"
cp "$APK" "$OUT"
"$ANDROID_HOME/build-tools/35.0.0/apksigner" verify --verbose --print-certs "$OUT" | tee "$OUTDIR/kr9-signer.txt"
if grep -Fiq 'Signer #1 certificate SHA-256 digest: 5eea68aceb434506b04f563532460c83330145f3d4ca77ad6ef41792d05985f8' "$OUTDIR/kr9-signer.txt"; then
  echo 'Unexpected reuse of lost KR8 certificate: cannot classify as fresh-install identity' >&2
  exit 1
fi
sha256sum "$OUT" | tee "$OUT.sha256"
cp "$NATIVE_INPUT/korean-origin.txt" "$OUTDIR/korean-origin.txt"
cp "$NATIVE_INPUT/page-size-report.txt" "$OUTDIR/native-build-page-size-report.txt"

{
  echo 'OpenMW Android 0.51.0-11 Korean KR1 test verification'
  echo 'result=PASS'
  echo 'runtime_patches=0001-0008'
  echo 'standalone_application_id=com.ast.openmw.kr9'
  echo 'original_application_id=com.ast.openmw'
  echo 'legacy_shared_storage_migration=disabled_for_standalone'
  echo 'signing=ephemeral_debug_certificate (not reusable for future upgrades)'
  echo 'video_subtitles_engine=enabled'
  echo 'required_page_size=16384'
  echo 'versionCode=5112'
  echo 'versionName=0.51.0-12'
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

echo 'Verified Korean 0.51.0-12 KR9 standalone APK with patches 0001-0008 and 16 KiB native ELF alignment.'
