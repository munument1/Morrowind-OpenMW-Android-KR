import struct
import unittest

from package_issue71_android_data import verify_scripts


def sub(key, value):
    return key + struct.pack('<I', len(value)) + value


def plugin(text, audio=b'voice.wav', condition=b'condition'):
    output = b''
    for name, count in ((b'VampireMolag', 5), (b'playScript', 6)):
        script = condition + b'\n' + (b'Player->Say "' + audio + b'", "' + text + b'"\n') * count
        body = sub(b'SCHD', name.ljust(52, b'\0')) + sub(b'SCDT', b'bytecode') + sub(b'SCTX', script)
        output += b'SCPT' + struct.pack('<I', len(body)) + b'\0' * 8 + body
    return output


class AndroidDataTests(unittest.TestCase):
    def test_subtitles_can_change_but_audio_conditions_and_bytecode_cannot(self):
        before = plugin(b'Hello')
        after = plugin('안녕'.encode())
        self.assertEqual(verify_scripts(before, after)['changed_subtitles'], {'VampireMolag': 5, 'playScript': 6})
        for bad in (plugin(b'Hello', audio=b'other.wav'), plugin(b'Hello', condition=b'bad'),
                    after.replace(b'bytecode', b'bad_code'), after[:-1]):
            with self.assertRaises(ValueError):
                verify_scripts(before, bad)


if __name__ == '__main__':
    unittest.main()
