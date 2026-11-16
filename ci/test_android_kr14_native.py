import unittest

from verify_handheld_native import SYMBOLS, verify_layout, verify_symbols


class CursorAbiTests(unittest.TestCase):
    def test_layout_rejects_shifted_window_manager(self):
        fields = ['mWorld', 'mWorldModel', 'mWorldScene', 'mESMStore',
                  'mSoundManager', 'mScriptManager', 'mWindowManager']
        header = 'class Environment {\nstatic Environment* sThis;\n' + ''.join(
            f'World* {name} = nullptr;\n' for name in fields) + '\n public:'
        verify_layout(header)
        with self.assertRaises(ValueError):
            verify_layout(header.replace('World* mWorld ', 'int newField; World* mWorld '))

    def test_only_defined_dynamic_symbols_pass(self):
        symbols = '\n'.join(f'1: 00001 10 FUNC GLOBAL DEFAULT 12 {name}' for name in SYMBOLS)
        verify_symbols(symbols)
        with self.assertRaises(ValueError):
            verify_symbols(symbols.replace('DEFAULT 12', 'DEFAULT UND', 1))
        with self.assertRaises(ValueError):
            verify_symbols(symbols.replace(SYMBOLS[0], 'different_symbol'))


if __name__ == '__main__':
    unittest.main()
