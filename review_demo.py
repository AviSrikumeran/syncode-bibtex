"""Serve the reviewer demonstration on localhost without extra dependencies."""

import argparse
import ast
import hashlib
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
from time import perf_counter

from lark import Tree, UnexpectedInput

from bibtex_syncode import ROOT, load_parser, validate
from evaluate_bounds import cases


REVISION = '7ae557604adf67be50417f59c2c2f167def9a775'
ASSETS = ROOT / 'reviewer'
REQUIREMENTS = {
    'R1': 'Standard BibTeX entry types',
    'R2': 'Nested brace groups',
    'R3': 'Special characters, LaTeX, and Unicode content',
    'R4': 'Quoted/braced values and field syntax',
    'R5': 'Multiple entries and document structure',
    'R6': 'Robustness extension: reject malformed or incomplete responses',
    'S1': 'Semantic boundary: syntax does not verify citation facts',
    'S2': 'Declared scope: BibTeX features outside the citation subset',
}
CASE_GROUPS = {
    'provided-assignment': 'The exact BibTeX input from an original assignment test; it must parse. Test bodies and assertions are unchanged.',
    'regression-valid': 'Curated valid examples must parse; bibliography facts are not part of this assertion.',
    'regression-invalid': 'Malformed or disallowed whole responses must be rejected, not crash the parser.',
    'nesting-valid': 'Balanced groups at the named depth must parse.',
    'nesting-invalid': 'The matching nested example with its final closing brace removed must be rejected.',
    'document-size-valid': 'All entries in the named document size must parse.',
    'document-size-invalid': 'Removing the last closing brace leaves the final entry incomplete and must be rejected.',
    'value-length-valid': 'A quoted value with the named character count must parse, including an empty value.',
    'value-length-invalid': 'The matching long value without its closing quote must be rejected.',
    'feature-interactions': 'Combines 4 nesting depths, 3 value formats, 2 outer delimiters, and 2 trailing-comma choices.',
    'every-prefix-truncation': 'Every incomplete prefix of one 58-character entry is rejected; none contains a complete earlier entry.',
    'semantic-limits-accepted': 'Syntactically valid input is accepted even when facts, required fields, or macro definitions are questionable.',
    'documented-out-of-scope': 'These are legitimate general BibTeX constructs outside this supported subset; rejection records scope, not invalid BibTeX.',
    'lexical-boundary': 'ASCII whitespace must not silently split a citation key or field name.',
    'unicode-content': 'Non-breaking and thin spaces inside a field value are literal content and must be accepted.',
}


def case_requirements(category, name, expected):
    if category == 'provided-assignment':
        tags = ['R1', 'R4']
        if name in ('test_with_special_characters', 'test_provided_examples'):
            tags.extend(['R2', 'R3'])
        if name == 'test_complex_author_list':
            tags.append('R3')
        if name in ('test_multiple_entries_and_types', 'test_provided_examples'):
            tags.append('R5')
        return tags
    if category == 'semantic-limits-accepted':
        return ['S1']
    if category == 'documented-out-of-scope':
        return ['S2']
    tags = []
    if not expected:
        tags.append('R6')
    if name.startswith('type_'):
        tags.append('R1')
    if 'nesting' in category or name in ('deep_nesting', 'quoted_nested'):
        tags.append('R2')
    if category == 'unicode-content' or name in ('unicode', 'unicode_spacing', 'latex', 'punctuation', 'inner_delimiters'):
        tags.append('R3')
    if category.startswith('document-size') or name in ('adjacent_entries', 'duplicate_keys'):
        tags.append('R5')
    if category == 'feature-interactions':
        tags.extend(['R2', 'R3', 'R4'])
    return tags or ['R4']


def provided_cases():
    module = ast.parse((ROOT / 'test.py').read_text(encoding='utf-8'))
    for node in ast.walk(module):
        if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
            assignment = next((statement for statement in node.body if isinstance(statement, ast.Assign)
                               and any(isinstance(target, ast.Name) and target.id == 'bibtex' for target in statement.targets)), None)
            if assignment is None:
                raise ValueError(f'Cannot locate the BibTeX fixture in {node.name}.')
            source = ast.literal_eval(assignment.value)
            if not isinstance(source, str):
                raise ValueError(f'Expected a literal string fixture in {node.name}.')
            yield 'provided-assignment', node.name, source, True


def tree_preview(tree):
    lines, stack = [], [(tree, 0)]
    while stack and len(lines) < 100:
        node, depth = stack.pop()
        if isinstance(node, Tree):
            lines.append('  ' * depth + str(node.data))
            if depth < 8:
                stack.extend((child, depth + 1) for child in reversed(node.children))
            elif node.children:
                lines.append('  ' * (depth + 1) + '[deeper nodes omitted from preview]')
        else:
            value = str(node)
            lines.append('  ' * depth + repr(value[:120]) + (' [truncated token]' if len(value) > 120 else ''))
    if stack:
        lines.append('[remaining nodes omitted from preview]')
    return '\n'.join(lines)


def analyze_output(parser, source):
    raw_valid, error = validate(parser, source)
    fence = re.fullmatch(r'\s*```(?:bibtex)?[ \t]*\r?\n(.*?)\r?\n```\s*', source, re.S | re.I)
    extracted = fence.group(1) if fence else source
    return dict(raw_valid=raw_valid, raw_error=error, fence_removed=bool(fence),
                extracted_valid=validate(parser, extracted)[0])


def evidence(parser, path):
    report = json.loads(path.read_text(encoding='utf-8'))
    records = [dict(record, assessment=analyze_output(parser, record['output']))
               for record in report['generations']]
    current_hash = hashlib.sha256((ROOT / 'bibtex.lark').read_bytes()).hexdigest()
    return dict(report, generations=records, evidence_file=path.relative_to(ROOT).as_posix(),
                validation_grammar_sha256=current_hash,
                grammar_matches_recorded=current_hash == report.get('grammar_sha256'))


class ReviewServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, offline=False):
        super().__init__(address, ReviewHandler)
        self.parser = load_parser()
        self.case_fixtures = {
            category + '/' + name: dict(case_id=category + '/' + name, category=category,
                                        name=name, source=source, expected_accept=expected,
                                        requirements=case_requirements(category, name, expected))
            for category, name, source, expected in (*provided_cases(), *cases())
        }
        self.offline = offline
        self.job_lock = threading.Lock()
        self.job = dict(status='idle')
        self.process = None

    def run_case(self, fixture, include_tree=True):
        started = perf_counter()
        tree, error, crash = None, None, False
        try:
            tree = self.parser.parse(fixture['source'])
            accepted = True
        except UnexpectedInput as failure:
            accepted, error = False, str(failure)[:6000]
        except Exception as failure:
            accepted, error, crash = False, type(failure).__name__ + ': ' + str(failure), True
        elapsed = (perf_counter() - started) * 1000
        return dict(case_id=fixture['case_id'], category=fixture['category'], name=fixture['name'],
                    expected_accept=fixture['expected_accept'], actual_accept=accepted,
                    matched_expectation=accepted == fixture['expected_accept'] and not crash,
                    crash=crash, error=error, elapsed_ms=round(elapsed, 4),
                    characters=len(fixture['source']),
                    source_sha256=hashlib.sha256(fixture['source'].encode('utf-8')).hexdigest(),
                    tree=tree_preview(tree) if include_tree and tree is not None else None)

    def start_run(self):
        with self.job_lock:
            if self.job['status'] == 'running':
                return False
            run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            output = ROOT / 'results' / f'reviewer-live-{run_id}.json'
            log = output.with_suffix('.log')
            output.parent.mkdir(exist_ok=True)
            self.job = dict(status='running', run_id=run_id, output=str(output), log=str(log))
            threading.Thread(target=self.run_model, args=(output, log), daemon=True).start()
            return True

    def run_model(self, output, log):
        env = os.environ.copy()
        if self.offline:
            env['HF_HUB_OFFLINE'] = '1'
        command = [sys.executable, '-u', str(ROOT / 'bibtex_syncode.py'), '--compare',
                   '--trace-steps', '8', '--revision', REVISION, '--output', str(output)]
        try:
            with log.open('w', encoding='utf-8') as stream:
                self.process = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                                stdout=stream, stderr=subprocess.STDOUT,
                                                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                try:
                    code = self.process.wait(timeout=900)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()
                    raise RuntimeError('Model run exceeded the 15-minute limit.')
            with self.job_lock:
                self.job.update(status='complete' if code == 0 else 'failed', exit_code=code)
        except Exception as error:
            with self.job_lock:
                self.job.update(status='failed', error=str(error))


class ReviewHandler(BaseHTTPRequestHandler):
    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=True).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == '/api/grammar':
            return self.send_json(200, dict(source=(ROOT / 'bibtex.lark').read_text(encoding='utf-8'),
                                            filename='bibtex.lark'))
        if self.path == '/api/cases':
            catalog = []
            for fixture in self.server.case_fixtures.values():
                source = fixture['source']
                catalog.append(dict(fixture, source=source if len(source) <= 20000 else None,
                                    preview=source[:400], characters=len(source),
                                    source_sha256=hashlib.sha256(source.encode('utf-8')).hexdigest()))
            return self.send_json(200, dict(cases=catalog, groups=CASE_GROUPS, requirements=REQUIREMENTS))
        if self.path == '/api/bounds':
            path = ROOT / 'results' / 'boundary-report.json'
            if not path.exists():
                return self.send_json(503, dict(error='Run evaluate_bounds.py to create the measured report.'))
            before = ROOT / 'results' / 'boundary-before.json'
            return self.send_json(200, dict(
                after=json.loads(path.read_text(encoding='utf-8')),
                before=json.loads(before.read_text(encoding='utf-8')) if before.exists() else None,
                active_grammar_sha256=hashlib.sha256((ROOT / 'bibtex.lark').read_bytes()).hexdigest()))
        if self.path == '/api/evidence':
            path = ROOT / 'results' / 'reviewer-run.json'
            if not path.exists():
                path = ROOT / 'results' / 'generation.json'
            return self.send_json(200, evidence(self.server.parser, path))
        if self.path == '/api/job':
            with self.server.job_lock:
                job = self.server.job.copy()
            if 'log' in job:
                path = Path(job.pop('log'))
                job['log_tail'] = path.read_text(encoding='utf-8', errors='replace')[-6000:] if path.exists() else ''
            if 'output' in job:
                path = Path(job.pop('output'))
                if job['status'] != 'running' and path.exists():
                    job['report'] = evidence(self.server.parser, path)
            return self.send_json(200, job)
        assets = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'),
                  '/styles.css': ('styles.css', 'text/css')}
        if self.path not in assets:
            return self.send_json(404, dict(error='Not found'))
        name, content_type = assets[self.path]
        body = (ASSETS / name).read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', content_type + '; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        origin = self.headers.get('Origin')
        if origin and origin not in (f'http://127.0.0.1:{self.server.server_port}',
                                     f'http://localhost:{self.server.server_port}'):
            return self.send_json(403, dict(error='Use the local demonstration page.'))
        if self.path == '/api/run':
            started = self.server.start_run()
            return self.send_json(202 if started else 409, dict(started=started))
        if self.path not in ('/api/validate', '/api/run-case', '/api/run-group'):
            return self.send_json(404, dict(error='Not found'))
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 64000:
                raise ValueError('Provide a JSON request smaller than 64 KB.')
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError('Provide a JSON object.')
            if self.path == '/api/run-case':
                case_id = payload.get('case_id')
                fixture = self.server.case_fixtures.get(case_id) if isinstance(case_id, str) else None
                if fixture is None:
                    return self.send_json(404, dict(error='Unknown case ID.'))
                return self.send_json(200, self.server.run_case(fixture))
            if self.path == '/api/run-group':
                group = payload.get('group')
                if group != '*' and (not isinstance(group, str) or group not in CASE_GROUPS):
                    return self.send_json(404, dict(error='Unknown group.'))
                fixtures = [case for case in self.server.case_fixtures.values() if group == '*' or case['category'] == group]
                results = [self.server.run_case(case, include_tree=False) for case in fixtures]
                return self.send_json(200, dict(group=group, results=results,
                                               matched=sum(row['matched_expectation'] for row in results), total=len(results)))
            source = payload.get('source') if isinstance(payload, dict) else None
            if not isinstance(source, str) or len(source) > 20000:
                raise ValueError('source must be text of at most 20,000 characters.')
        except (ValueError, UnicodeDecodeError) as error:
            return self.send_json(400, dict(error=str(error)))
        assessment = analyze_output(self.server.parser, source)
        tree = tree_preview(self.server.parser.parse(source)) if assessment['raw_valid'] else None
        return self.send_json(200, dict(assessment, tree=tree))


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--port', type=int, default=8765)
    cli.add_argument('--offline', action='store_true', help='Use already downloaded model files only')
    args = cli.parse_args()
    server = ReviewServer(('127.0.0.1', args.port), offline=args.offline)
    print(f'Reviewer demonstration: http://127.0.0.1:{server.server_port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if server.process and server.process.poll() is None:
            server.process.terminate()
            server.process.wait()
        server.server_close()


if __name__ == '__main__':
    main()
