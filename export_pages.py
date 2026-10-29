"""Build a GitHub Pages evidence viewer; model execution stays local."""
from datetime import datetime, timezone
import ast
import hashlib
import json
import re
from pathlib import Path
from types import SimpleNamespace

from bibtex_syncode import ROOT, GRAMMAR_PATH, load_parser
from review_demo import CASE_GROUPS, REQUIREMENTS, ReviewServer, cases, evidence, provided_cases
from review_demo import case_requirements
from review_demo import analyze_output, tree_preview


def build():
    target = ROOT / 'docs'
    data = target / 'data'
    data.mkdir(parents=True, exist_ok=True)
    parser = load_parser()
    grammar_hash = hashlib.sha256(GRAMMAR_PATH.read_bytes()).hexdigest()
    example_block = (ROOT / 'reviewer/app.js').read_text(encoding='utf-8').split('const examples = {', 1)[1].split('\n};', 1)[0]
    examples = {}
    for name, literal in re.findall(r"(\w+): ('(?:\\.|[^'\\])*')", example_block):
        source = ast.literal_eval(literal)
        assessment = analyze_output(parser, source)
        examples[name] = dict(assessment, source=source,
                              tree=tree_preview(parser.parse(source)) if assessment['raw_valid'] else None)
    catalog, results = [], []
    for category, name, source, expected in (*provided_cases(), *cases()):
        fixture = dict(case_id=category + '/' + name, category=category, name=name,
                       source=source, expected_accept=expected,
                       requirements=[])
        fixture['requirements'] = case_requirements(category, name, expected)
        results.append(ReviewServer.run_case(SimpleNamespace(parser=parser), fixture))
        catalog.append(dict(fixture, source=source if len(source) <= 20000 else None,
                            preview=source[:400], characters=len(source),
                            source_sha256=hashlib.sha256(source.encode()).hexdigest()))
    payloads = {
        'grammar': dict(filename='bibtex.lark', source=GRAMMAR_PATH.read_text(encoding='utf-8')),
        'evidence': evidence(parser, ROOT / 'results/reviewer-run.json'),
        'bounds': dict(after=json.loads((ROOT / 'results/boundary-report.json').read_text(encoding='utf-8')),
                       before=json.loads((ROOT / 'results/boundary-before.json').read_text(encoding='utf-8')),
                       active_grammar_sha256=grammar_hash),
        'cases': dict(cases=catalog, groups=CASE_GROUPS, requirements=REQUIREMENTS),
        'results': results,
        'examples': examples,
    }
    for name, payload in payloads.items():
        (data / (name + '.json')).write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
    html = (ROOT / 'reviewer/index.html').read_text(encoding='utf-8')
    html = html.replace('<html lang="en">', '<html lang="en" data-mode="recorded">')
    style_version = hashlib.sha256((ROOT / 'reviewer/styles.css').read_bytes()).hexdigest()[:12]
    script_version = hashlib.sha256((ROOT / 'reviewer/app.js').read_bytes()).hexdigest()[:12]
    html = html.replace('href="/styles.css"', f'href="./styles.css?v={style_version}"').replace('src="/app.js"', f'src="./app.js?v={script_version}"')
    html = html.replace('Local execution. Recorded evidence is labeled. Publication facts are not verified.',
                        'Published evidence viewer. Results are recorded; fresh parsing and Qwen generation run in the local Python demo. See Reproduce.')
    html = html.replace('read directly from the local project', 'exported from the project')
    html = html.replace('Click <b>Run all 3 prompts locally</b> for fresh inference, then use <b>Show outputs</b> for each request.',
                        'Use <b>Show outputs</b> for each recorded request. To generate new results, follow Reproduce on your own machine.')
    html = html.replace('The local run button performs new inference;', 'The local Python demo performs new inference;')
    html = html.replace('This editor calls the local Lark parser. Maximum request: 20,000 characters.',
                        'Examples can be inspected here. Execute the local demo to validate new text.')
    html = html.replace('Run saved case', 'Show saved case result').replace('Run all saved cases in selected group', 'Show saved group results')
    html = html.replace('Run edited input', 'Local editing only')
    html = html.replace('Run selected group', 'Show saved group results')
    html = html.replace('Run it to obtain an actual parser result.', 'Inspect its recorded parser result; this public page does not execute Python.')
    html = html.replace('Selecting either does not execute a test. Run one saved case, test your edited text, or run every saved case in the selected group.',
                        'Select one saved case or inspect saved results for the whole group. Fresh execution is available in the local demo.')
    html = html.replace('to execute their inputs against the local parser', 'to inspect their recorded parser results')
    html = html.replace('Run original fixture', 'Show saved case result')
    html = html.replace('Input (editable when at most 20,000 characters)', 'Saved input (read-only)')
    html = html.replace('Change the edited-input expectation if your change alters the hypothesis. Original-fixture runs always use the stored full input and original expectation.',
                        'This page displays stored inputs and results. To change an input and execute the parser, run the local demo.')
    html = html.replace('Selecting All groups runs the entire', 'Selecting All groups displays the recorded results for the entire')
    html = html.replace('choose another group, inspect its expected acceptance or rejection, and run one fixture.',
                        'choose another group and inspect its expected acceptance or rejection and saved result.')
    (target / 'index.html').write_text(html, encoding='utf-8')
    for name in ('app.js', 'styles.css'):
        (target / name).write_bytes((ROOT / 'reviewer' / name).read_bytes())
    (target / '.nojekyll').write_text('', encoding='utf-8')
    (data / 'manifest.json').write_text(json.dumps(dict(exported_at_utc=datetime.now(timezone.utc).isoformat(),
        grammar_sha256=grammar_hash, cases=len(results), matched=sum(row['matched_expectation'] for row in results),
        mode='recorded evidence; no browser inference or Python validation')), encoding='utf-8')
    print(f'Exported {len(results)} recorded case results; {sum(row["matched_expectation"] for row in results)} match expectations.')


if __name__ == '__main__':
    build()
