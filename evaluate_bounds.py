"""Measure selected grammar boundaries with deterministic, documented cases."""

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
from itertools import product
import json
from pathlib import Path
from statistics import median
from time import perf_counter

from lark import UnexpectedInput

from bibtex_syncode import GRAMMAR_PATH, ROOT, load_parser
from tests.test_edge_cases import INVALID, VALID


def cases():
    for name, source in VALID.items():
        yield 'regression-valid', name, source, True
    for name, source in INVALID.items():
        yield 'regression-invalid', name, source, False
    for depth in (0, 1, 2, 8, 40, 100, 500, 1000):
        source = '@misc{k,title={' + '{' * depth + 'x' + '}' * depth + '}}'
        yield 'nesting-valid', f'depth-{depth}', source, True
        yield 'nesting-invalid', f'depth-{depth}-missing-close', source[:-1], False
    for count in (1, 10, 100, 1000):
        source = '\n'.join(f'@misc{{key{i},title={{Entry {i}}}}}' for i in range(count))
        yield 'document-size-valid', f'entries-{count}', source, True
        yield 'document-size-invalid', f'entries-{count}-truncated', source[:-1], False
    for length in (0, 1, 100, 10000, 100000):
        source = '@misc{k,title="' + 'x' * length + '"}'
        yield 'value-length-valid', f'characters-{length}', source, True
        yield 'value-length-invalid', f'characters-{length}-unclosed-quote', source[:-2] + '}', False
    for depth, formatting, delimiter, trailing in product((0, 1, 4, 12), ('braced', 'quoted', 'concat'), ('brace', 'paren'), (False, True)):
        text = '{' * depth + 'Müller, $x_1$ @ # =' + '}' * depth
        value = '"' + text + '"' if formatting == 'quoted' else '{' + text + '}'
        if formatting == 'concat':
            value += ' # " tail"'
        opening, closing = ('{', '}') if delimiter == 'brace' else ('(', ')')
        source = '@misc' + opening + 'k,title=' + value + (',' if trailing else '') + closing
        yield 'feature-interactions', f'{depth}-{formatting}-{delimiter}-trailing-{trailing}', source, True
    complete = '@article{k,title={A {nested} title},note="Text",year=2026}'
    for cut in range(len(complete)):
        yield 'every-prefix-truncation', f'cut-{cut}-of-{len(complete)}', complete[:cut], False
    semantics = {
        'invented-publication': '@article{k,title={A made-up paper},journal={An invented journal}}',
        'missing-bibliographic-fields': '@article{k,note={No author, title, or year}}',
        'undefined-macro': '@misc{k,title=undefinedmacro}',
        'duplicate-keys': '@misc{k,title={One}}@misc{k,title={Two}}',
        'non-numeric-year': '@misc{k,year={Not a year}}',
    }
    for name, source in semantics.items():
        yield 'semantic-limits-accepted', name, source, True
    unsupported = {
        'string-definition': '@string{publisher = "Example Press"}',
        'preamble': '@preamble{"Example"}',
        'comment-block': '@comment{This is a comment}',
        'free-text-between-entries': '@misc{k,title={One}} explanatory text @misc{b,title={Two}}',
    }
    for name, source in unsupported.items():
        yield 'documented-out-of-scope', name, source, False
    yield 'lexical-boundary', 'split-field-name', '@misc{k,ti tle={x}}', False
    yield 'lexical-boundary', 'spaces-in-key', '@misc{two keys,title={x}}', False
    yield 'unicode-content', 'nonbreaking-and-thin-spaces', '@misc{k,title={non\u00a0breaking\u2009space}}', True


def evaluate(repeats):
    started = perf_counter()
    parser = load_parser()
    build_ms = (perf_counter() - started) * 1000
    rows = []
    for category, name, source, expected in cases():
        times = []
        accepted, error_type, error = False, None, None
        for _ in range(repeats):
            started = perf_counter()
            try:
                parser.parse(source)
                accepted, error_type, error = True, None, None
            except UnexpectedInput as failure:
                accepted, error_type, error = False, type(failure).__name__, str(failure)[:300]
            except Exception as failure:
                accepted, error_type, error = False, 'CRASH:' + type(failure).__name__, str(failure)[:300]
            times.append((perf_counter() - started) * 1000)
        rows.append(dict(category=category, name=name, expected_accept=expected, actual_accept=accepted,
                         matched_expectation=accepted == expected and not (error_type or '').startswith('CRASH:'),
                         characters=len(source), source_sha256=hashlib.sha256(source.encode('utf-8')).hexdigest(),
                         preview=source[:400], median_ms=round(median(times), 4),
                         error_type=error_type, error=error))
    return dict(created_at_utc=datetime.now(timezone.utc).isoformat(),
                grammar_sha256=hashlib.sha256(GRAMMAR_PATH.read_bytes()).hexdigest(),
                fixture_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                repeats=repeats, parser_build_ms=round(build_ms, 4), cases=rows)


def summary(report):
    groups = defaultdict(list)
    for row in report['cases']:
        groups[row['category']].append(row)
    lines = ['# Measured test spectrum', '', '| Category | Expectations met | Median case time (ms) |',
             '| --- | --- | --- |']
    for category, rows in groups.items():
        lines.append(f'| {category} | {sum(row["matched_expectation"] for row in rows)}/{len(rows)} | {median(row["median_ms"] for row in rows):.4f} |')
    lines += ['', '## Scaling observations', '', '| Case | Characters | Accepted | Median ms |', '| --- | --- | --- | --- |']
    for row in report['cases']:
        if row['category'] in ('nesting-valid', 'document-size-valid', 'value-length-valid'):
            lines.append(f'| {row["name"]} | {row["characters"]} | {row["actual_accept"]} | {row["median_ms"]:.4f} |')
    failures = [row for row in report['cases'] if not row['matched_expectation']]
    lines += ['', f'Unexpected outcomes: {len(failures)}.', '']
    for row in failures:
        lines.append(f'- {row["category"]}/{row["name"]}: expected acceptance {row["expected_accept"]}; observed {row["actual_accept"]}; {row["error_type"]}.')
    lines += ['', 'Timings describe this machine and run, not a controlled performance benchmark.',
              'The largest case tested is not a proven maximum. This is selected boundary coverage, not exhaustive BibTeX conformance.',
              'Out-of-scope rejection does not mean those BibTeX features are invalid. Semantic-limit cases are intentionally accepted.',
              'Model-generation reliability is a separate experiment; parser-case counts are not model success rates.']
    return '\n'.join(lines) + '\n'


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--repeats', type=int, choices=range(1, 11), default=3, metavar='1..10')
    cli.add_argument('--output', type=Path, default=ROOT / 'results' / 'boundary-report.json')
    cli.add_argument('--markdown', type=Path, default=ROOT / 'results' / 'boundary-report.md')
    args = cli.parse_args()
    report = evaluate(args.repeats)
    text = summary(report)
    for path in (args.output, args.markdown):
        path.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding='utf-8')
    args.markdown.write_text(text, encoding='utf-8')
    print(text)
    return 0 if all(row['matched_expectation'] for row in report['cases']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
