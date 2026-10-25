import unittest

from lark import UnexpectedInput

from bibtex_syncode import load_parser


ENTRY_TYPES = (
    'article', 'book', 'booklet', 'conference', 'inbook', 'incollection',
    'inproceedings', 'manual', 'mastersthesis', 'misc', 'phdthesis',
    'proceedings', 'techreport', 'unpublished',
)

VALID = {
    **{f'type_{kind}': f'@{kind}{{key, title={{Example}}}}' for kind in ENTRY_TYPES},
    'deep_nesting': '@article{k,title={' + '{' * 40 + 'deep' + '}' * 40 + '}}',
    'empty_braced': '@misc{k,title={}}',
    'empty_quoted': '@misc{k,title=""}',
    'mixed_values': '@book{k,title="Quoted",author={Braced},year=2024}',
    'escaped_quotes': r'@misc{k,title="A \"quoted\" phrase"}',
    'quoted_nested': '@misc{k,title="A {group with "quotes"} here"}',
    'braced_quotes': '@misc{k,title={An "ordinary" quote}}',
    'latex': r'@article{k,author={M{\"u}ller},title={\textbf{Bold} $\sum_{i=1}^{n} x_i$}}',
    'escaped_braces': r'@misc{k,title={Literal \{ and \} symbols}}',
    'unicode': '@misc{k,title={日本語, naïve, García, Ελληνικά 🧪}}',
    'punctuation': '@misc{k,url={https://example.org/a?x=1&y=2#part},doi={10.1234/a_b:c}}',
    'inner_delimiters': '@misc{k,note={a,b=c @person (text) # % & $ _ ~}}',
    'multiline': '@misc{k,\n title = {First line\nSecond line},\n year = "2024"\n}',
    'whitespace': '\t\r\n@book \t{ k , TITLE = {x} , YEAR = 2024 , }\n',
    'trailing_comma': '@misc{k,title={x},}',
    'parentheses': '@article(k,title={x},year=2024)',
    'mixed_case': '@ArTiClE{k,TiTlE={x}}',
    'numeric_key': '@misc{2024,title={x}}',
    'key_punctuation': '@misc{smith:2024_a-b.c/2+,title={x}}',
    'custom_field': '@misc{k,my_custom_field={x}}',
    'bare_macro': '@misc{k,month=jan}',
    'concatenation': '@misc{k,title={Part} # " two" # suffix,year=2024}',
    'no_fields': '@misc{k,}',
    'bibliographic_incompleteness': '@article{k,note={No author, year, or title}}',
    'duplicate_keys': '@misc{k,title={one}} @misc{k,title={two}}',
    'adjacent_entries': '@misc{a,title={one}}@book(b,title="two")',
}

INVALID = {
    'empty_document': '',
    'missing_outer_brace': '@misc{k,title={x}',
    'missing_value_brace': '@misc{k,title={x',
    'extra_closing_brace': '@misc{k,title={x}}}',
    'unclosed_quote': '@misc{k,title="x}',
    'unmatched_nested_brace': '@misc{k,title={a {b}}',
    'missing_equals': '@misc{k,title {x}}',
    'missing_key': '@misc{,title={x}}',
    'missing_key_comma': '@misc{k title={x}}',
    'missing_field_comma': '@misc{k,title={x}year=2024}',
    'double_comma': '@misc{k,title={x},,year=2024}',
    'missing_value': '@misc{k,title=}',
    'extra_equals': '@misc{k,title=={x}}',
    'missing_type': '@{k,title={x}}',
    'missing_at': 'misc{k,title={x}}',
    'mismatched_entry_delimiters': '@misc(k,title={x}}',
    'unmatched_quote_group': '@misc{k,title="a {b"}',
    'bare_phrase': '@misc{k,title=two words}',
    'dangling_concatenation': '@misc{k,title={x} #}',
    'leading_concatenation': '@misc{k,title=# {x}}',
    'semicolon_separator': '@misc{k,title={x};year=2024}',
    'truncated_second_entry': '@misc{k,title={x}} @book{b,title=',
    'trailing_prose': '@misc{k,title={x}} Here is your citation.',
    'markdown_fence': '```bibtex\n@misc{k,title={x}}\n```',
}


def valid_case(source):
    def test(self):
        self.assertIsNotNone(self.parser.parse(source))
    return test


def invalid_case(source):
    def test(self):
        with self.assertRaises(UnexpectedInput):
            self.parser.parse(source)
    return test


class ValidInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parser = load_parser()


class InvalidInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parser = load_parser()


for name, source in VALID.items():
    setattr(ValidInputTests, f'test_{name}', valid_case(source))

for name, source in INVALID.items():
    setattr(InvalidInputTests, f'test_{name}', invalid_case(source))
