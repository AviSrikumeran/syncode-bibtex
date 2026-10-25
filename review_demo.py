"""Serve the reviewer demonstration on localhost without extra dependencies."""

import argparse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading

from bibtex_syncode import ROOT, load_parser, validate


REVISION = '7ae557604adf67be50417f59c2c2f167def9a775'
ASSETS = ROOT / 'reviewer'


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
    return dict(report, generations=records, evidence_file=path.relative_to(ROOT).as_posix())


class ReviewServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, offline=False):
        super().__init__(address, ReviewHandler)
        self.parser = load_parser()
        self.offline = offline
        self.job_lock = threading.Lock()
        self.job = dict(status='idle')
        self.process = None

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
        if self.path != '/api/validate':
            return self.send_json(404, dict(error='Not found'))
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 64000:
                raise ValueError('Provide a JSON request smaller than 64 KB.')
            payload = json.loads(self.rfile.read(length))
            source = payload.get('source') if isinstance(payload, dict) else None
            if not isinstance(source, str) or len(source) > 20000:
                raise ValueError('source must be text of at most 20,000 characters.')
        except (ValueError, UnicodeDecodeError) as error:
            return self.send_json(400, dict(error=str(error)))
        assessment = analyze_output(self.server.parser, source)
        tree = self.server.parser.parse(source).pretty()[:20000] if assessment['raw_valid'] else None
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
