"""An independent terminal walkthrough for demonstrations and review."""

import argparse
from datetime import datetime, timezone
import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys

from bibtex_syncode import GRAMMAR_PATH, ROOT, load_parser, validate
from review_demo import analyze_output


REVISION = '7ae557604adf67be50417f59c2c2f167def9a775'


def overview():
    print('\nWHAT EACH COMPONENT DOES')
    print('Tokenizer: converts text to model token IDs and back.')
    print('Qwen: scores possible next tokens.')
    print('SynCode: applies the grammar mask before choosing the next token.')
    print('Lark: independently parses the completed output.')
    print('Qwen -> SynCode repeats for every generated token.\n')
    print('ACTUAL GRAMMAR: bibtex.lark\n')
    print(GRAMMAR_PATH.read_text(encoding='utf-8'))
    print('The braced rule refers to itself: that is how nested groups are balanced.')


def show_report(path, show_outputs=True):
    report = json.loads(path.read_text(encoding='utf-8'))
    parser = load_parser()
    print(f'\nSAVED EVIDENCE: {path}')
    print('This view inspects a recorded run; it does not perform new inference.')
    print(f'Model: {report["model"]}\nModel revision: {report["revision"]}')
    print('Recorded grammar SHA-256:', report['grammar_sha256'])
    if report['grammar_sha256'] != hashlib.sha256(GRAMMAR_PATH.read_bytes()).hexdigest():
        print('NOTE: This archived run used a different grammar. Syntax below is rechecked with the current grammar.')
    for record in report['generations']:
        assessment = analyze_output(parser, record['output'])
        print(f'\n{record["mode"].upper()}: {record["prompt"]}')
        if show_outputs:
            print(record['output'])
        print(f'Raw syntax: {"PASS" if assessment["raw_valid"] else "FAIL"}')
        print(f'After outer-fence removal: {"PASS" if assessment["extracted_valid"] else "FAIL"}')
        trace = record.get('token_trace', [])
        if not trace:
            continue
        if 'generated_token_ids' in record:
            if not all(step['selected_token_id'] == record['generated_token_ids'][index]
                       for index, step in enumerate(trace)):
                raise ValueError('Trace does not match the generated token IDs.')
        first = trace[0]
        print('First-token candidates at the SynCode boundary:')
        print(f'{"Token":<24} {"Score":>9}  Mask')
        for candidate in first['model_top_choices']:
            token = json.dumps(candidate['text'], ensure_ascii=True)
            verdict = 'allowed' if candidate['allowed'] else 'blocked'
            print(f'{token:<24} {candidate["score"]:>9.3f}  {verdict}')
        print('Selected:', json.dumps(first['selected_token'], ensure_ascii=True))
    print('\nScores are processed logits, not probabilities or private model reasoning.')
    print('Syntax validity does not prove factual accuracy or prompt compliance.')


def generate_live(args):
    prompt = args.prompt or input('\nType your own citation request: ').strip()
    if not prompt:
        print('No prompt supplied.')
        return 1
    output = args.output or ROOT / 'results' / ('terminal-run-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
    if not output.is_absolute():
        output = ROOT / output
    previous_mtime = output.stat().st_mtime_ns if output.exists() else None
    command = [sys.executable, '-u', str(ROOT / 'bibtex_syncode.py'), '--compare',
               '--trace-steps', '8', '--revision', REVISION, '--prompt', prompt,
               '--output', str(output)]
    env = os.environ.copy()
    if args.offline:
        env['HF_HUB_OFFLINE'] = '1'
    print('\nLIVE GENERATION: Qwen alone, then the same Qwen model with SynCode.')
    print('Command:', subprocess.list2cmdline(command), flush=True)
    result = subprocess.run(command, cwd=ROOT, env=env)
    if output.exists() and output.stat().st_mtime_ns != previous_mtime:
        show_report(output, show_outputs=False)
    print(f'\nGeneration process exit code: {result.returncode}')
    return result.returncode


def validate_input(args):
    if args.source:
        source = args.source.read_text(encoding='utf-8')
    else:
        print('\nPaste or type BibTeX. Finish with END on its own line.')
        lines = []
        while (line := input()) != 'END':
            lines.append(line)
        source = '\n'.join(lines)
    parser = load_parser()
    valid, error = validate(parser, source)
    print('\nLark:', 'ACCEPTED' if valid else 'REJECTED')
    print(parser.parse(source).pretty() if valid else error)
    print('This checks syntax, not whether the cited publication exists.')
    return 0 if valid else 1


def perform(action, args):
    if action == 'overview':
        overview()
        return 0
    if action == 'tests':
        return subprocess.run([sys.executable, str(ROOT / 'run_tests.py')], cwd=ROOT).returncode
    if action == 'generate':
        return generate_live(args)
    if action == 'validate':
        return validate_input(args)
    if action == 'bounds':
        return subprocess.run([sys.executable, str(ROOT / 'evaluate_bounds.py')], cwd=ROOT).returncode
    show_report(args.report)
    return 0


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--offline', action='store_true', help='Use the already downloaded model only')
    cli.add_argument('--action', choices=('overview', 'tests', 'generate', 'validate', 'report', 'bounds'))
    cli.add_argument('--prompt', help='A new prompt for a live comparison')
    cli.add_argument('--source', type=Path, help='A BibTeX file to validate')
    cli.add_argument('--output', type=Path, help='Where to save a new generation report')
    cli.add_argument('--report', type=Path, default=ROOT / 'results' / 'reviewer-run.json')
    args = cli.parse_args()
    if args.action:
        return perform(args.action, args)
    print('BIBTEX TERMINAL LAB\nWorking repository:', ROOT)
    actions = {'1': 'overview', '2': 'tests', '3': 'generate', '4': 'validate', '5': 'report', '6': 'bounds'}
    while True:
        print('\n1  Explain components and show grammar\n2  Run the automated tests\n3  Ask Qwen YOUR prompt (live comparison)\n4  Validate YOUR BibTeX\n5  Inspect saved outputs and token choices\n6  Measure the test spectrum and boundaries\n0  Exit')
        selection = input('Choose: ').strip()
        if selection == '0':
            return 0
        if selection not in actions:
            print('Choose a number from 0 to 6.')
            continue
        try:
            perform(actions[selection], args)
        except (OSError, ValueError) as error:
            print('Could not complete this step:', error)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (KeyboardInterrupt, EOFError):
        print('\nTerminal demonstration stopped.')
        raise SystemExit(130)
