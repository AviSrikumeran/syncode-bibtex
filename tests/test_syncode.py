"""Check the vendored parser SynCode actually uses against our syntax cases."""

import unittest

from bibtex_syncode import GRAMMAR_PATH
from tests.test_edge_cases import INVALID, VALID


class SynCodeParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from syncode import Grammar
        from syncode.larkm.exceptions import UnexpectedInput
        from syncode.parsers import create_base_parser

        cls.unexpected_input = UnexpectedInput
        cls.parser = create_base_parser(Grammar(GRAMMAR_PATH.read_text(encoding='utf-8')))

    def test_valid_inputs(self):
        for name, source in VALID.items():
            with self.subTest(name=name):
                self.assertIsNotNone(self.parser.parse(source))

    def test_invalid_inputs(self):
        for name, source in INVALID.items():
            with self.subTest(name=name), self.assertRaises(self.unexpected_input):
                self.parser.parse(source)
