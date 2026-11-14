# Android OpenMW 0.51.0-14 Handheld Mode — KR14 source candidate

**Draft/source integration only. No APK was built, signed, installed, or released.**

## Work consolidated

- Replayed the existing unmerged PowerVR 0.51.0-13 commits `06f31c7`, `bde229d` onto current Korean `main`.
- Replayed the existing unmerged Handheld 0.51.0-14 and Korean localization commits `18ad863`, `0eae603`, `c853144` onto current Korean `main`.
- Resolved only the conflicting `source/app/build.gradle` version identity, keeping `com.ast.openmw.korean` and using **development** versionCode `5119` (published KR12.4 is `5117`; prepared but unpublished KR13 is `5118`).
- Aligned the new `libhandheld.so` Android NDK build to **27.3.13750724** and explicitly requested 16 KiB ELF page alignment. The final APK alignment still requires binary validation.
- Restored the original 0.51.0-14 `OMWRadialMenu/en.yaml` fallback alongside the existing Korean `ko.yaml`. They contain the same 24 keys.
- Restored the five new Handheld/Sharp Fonts setting strings in upstream German, French, Polish, Russian and Swedish translations. This preserves the existing Gradle all-languages resource-key gate.
- Added a standalone Python source-level test and a read-only GitHub Actions CI guard.

## User-facing features being evaluated

Controller-oriented Handheld Mode, a radial item/spell menu, changed gamepad shortcuts, cursor behavior, font-size options and the preceding 0.51.0-13 PowerVR graphics fix. Original Android source and Korean translation assets are used; the game's official Morrowind files are not included.

## Essential release blockers

1. Current `ci/build-korean-native-kr13.sh` and `ci/package-android-kr13.sh` are pinned to the **0.51.0-12 KR13** input and target; they cannot generate a verified 0.51.0-14 KR14 APK simply by renaming a tag. A **separate pinned KR14 native and packaging workflow** must handle the 0.51.0-14 APK baseline, the Korean engine patch set, Gradle version and all resources.
2. The new C `libhandheld.so` bridge uses OpenMW C++ exported symbols and a layout-specific window-manager pointer offset. Confirm all three symbols from the **actual Korean ARM64 `libopenmw.so`** and test the in-game GUI cursor before shipping.
3. Validate permanent certificate SHA-256 `ebf75015d1b61b14ffa2a3539d8981434c30272219eb6b0ae0c3de16bb2228f2`, app ID `com.ast.openmw.korean`, 16 KiB `LOAD` alignment for every `.so`, zipalign, non-debuggable release, and upgrade from versionCode `5117`.
4. Run real-device gamepad checks (L1 radial menu; R1 journal; Select rest; L3 cursor; mouse/touch fallback), Korean/English fallback text, save/load, title fonts, PowerVR rendering and non-Handheld behavior.
5. The Android KR13 native 0017 workflow has not shipped a signed APK; Windows KR13.1 patches 0018–0019 require a separate Android rebase and compatibility tests. Do not claim either installed before a successful native build.

The previous published Android Korean data ZIP is **KR13 data-only**, while the latest published permanent signed APK remains **0.51.0-12 KR12.4**.
