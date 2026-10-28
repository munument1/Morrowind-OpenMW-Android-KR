# Android KR11 native update

KR11 adds Windows KR10 patches 0009 (honorific particles) and 0010 (validated
legacy known-topic and journal-topic recovery) to the existing Android Korean
patch chain. The patch files are fetched from the pinned Windows source commit
22410f633d4de10aaeb8345238a15d45a7f24ca3 and verified by Git blob SHA.

The APK uses the previously prepared, unpublished stable app ID
`com.ast.openmw.korean`, a non-debuggable release build and versionCode 5113.
It coexists with KR8 `com.ast.openmw` and the first KR9 `com.ast.openmw.kr9`;
shared save migration remains disabled. Existing apps and saves are not deleted.

Signing uses a newly backed-up permanent certificate because the old proposed
509d... identity was never released and its private backup was unavailable here.
Public certificate SHA-256:
`ebf75015d1b61b14ffa2a3539d8981434c30272219eb6b0ae0c3de16bb2228f2`.
The encrypted private backup and its recovery key are separate GitHub Secrets;
private material is excluded from source, Actions artifacts and release assets.
Future updates must retain this certificate/package and increase versionCode.

The KR11 data ZIP enables U+2160–U+217F Roman numerals in MysticCards. It keeps
the released Android ESP, sidecars, TTF and subtitles unchanged. Install both
the APK and data update; an APK-only native update does not replace data files.

The Daedric font slot (`Fonts_Font_2`) is restored to `DemonicLetters`, preserving
the upstream Daedric font definition, glyph font and license byte-for-byte.
`Fonts_Font_0` remains `MysticCards` for ordinary Korean prose. Daedric inscriptions
must retain their Latin input text so that the font renders Daedric glyphs.

CI checks the full native patch chain, host C++ topic recovery/index regressions,
Gradle unit tests, APK application identity, non-debuggable status, permanent
signature and 16 KiB native ELF/ZIP alignment. Android hardware gameplay is not
claimed without separate device evidence. Rebirth data is excluded.
