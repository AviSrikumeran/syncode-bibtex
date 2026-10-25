const $ = id => document.getElementById(id);
let report;
let prompts = [];
const components = {
  tokenizer: ['TEXT INTO MODEL INPUT', 'A token is a piece of text, not always a word.', 'The tokenizer converts the prompt into token IDs and converts generated IDs back into text. A single token can span punctuation and letters, so grammar constraints must operate correctly across token boundaries.', 'The tokenizer does not know whether a paper exists or a citation is valid.', 'Prompt text → [token IDs] → Qwen\nGenerated IDs → text'],
  qwen: ['THE LANGUAGE MODEL', 'Qwen scores what could come next.', 'We use Qwen2.5-0.5B-Instruct on the CPU. For each step it produces a score for each possible next token. Greedy decoding chooses the highest remaining score. The same model and prompts are used in both comparison arms.', 'A likely token is not necessarily structurally valid, relevant, or factually true.', 'Prompt + generated prefix\n        ↓\nScores for the next token\n        ↓\nChoose highest score'],
  syncode: ['CONSTRAINT DURING GENERATION', 'The grammar changes the available choices.', 'SynCode tracks the partial output against the grammar and masks disallowed tokens before the next token is selected. We use grammar_mask, then validate the finished output. This constrains the generation process instead of repairing the response afterward.', 'grammar_mask can overapproximate valid continuations. A token budget can still end a response before it is complete.', 'Qwen scores\n    ↓\nSynCode + bibtex.lark\n    ↓\nMasked scores\n    ↓\nNext token → repeat'],
  lark: ['INDEPENDENT FINAL CHECK', 'The completed response must parse.', 'Lark uses the LALR grammar to parse the whole response. The recursive braced rule balances nested groups. Missing delimiters and malformed field assignments are rejected. The parse tree shows the structure that was recognized.', 'Parsing checks syntax. It does not validate authors, publication facts, required bibliographic fields, or topic relevance.', 'braced: "{" (text | "\\\"" | braced)* "}"\n\n@article{key,\n  title = {A {nested} title}\n}']
};
function showComponent(name) {
  const [label, title, description, limit, example] = components[name];
  $('component-label').textContent = label; $('component-title').textContent = title;
  $('component-description').textContent = description; $('component-limit').textContent = limit;
  $('component-example').textContent = example;
  document.querySelectorAll('[data-component]').forEach(button => button.classList.toggle('selected', button.dataset.component === name));
}
document.querySelectorAll('[data-component]').forEach(button => button.onclick = () => showComponent(button.dataset.component));
document.querySelectorAll('[data-tab]').forEach(button => button.onclick = () => {
  document.querySelectorAll('.panel').forEach(panel => panel.hidden = panel.id !== button.dataset.tab);
  document.querySelectorAll('[data-tab]').forEach(tab => tab.classList.toggle('active', tab === button));
});
function cell(row, text) { const td = document.createElement('td'); td.textContent = text; row.append(td); return td; }
function recordFor(index, mode) { return report.generations.find(record => record.prompt === prompts[index] && record.mode === mode); }
function renderComparison() {
  const index = Number($('prompt-select').value || 0);
  $('selected-prompt').textContent = prompts[index];
  for (const mode of ['unconstrained', 'constrained']) {
    const record = recordFor(index, mode);
    $(mode + '-output').textContent = record?.output || 'No output in this evidence file.';
    const badge = $(mode + '-badge');
    badge.textContent = record ? (record.assessment.raw_valid ? 'RAW SYNTAX PASS' : 'RAW SYNTAX FAIL') : 'NOT RUN';
    badge.className = 'badge ' + (record?.assessment.raw_valid ? 'pass' : 'fail');
    $(mode + '-assessment').textContent = record ?
      (record.assessment.fence_removed ? 'After removing only the outer Markdown fence: ' + (record.assessment.extracted_valid ? 'syntax passes.' : 'syntax still fails.') : 'No outer Markdown fence removed.') +
      (record.new_tokens ? ` ${record.new_tokens} tokens.` : '') +
      (record.elapsed_seconds ? ` Generation: ${record.elapsed_seconds}s (not a controlled speed benchmark).` : '') : '';
  }
  const counts = mode => {
    const records = report.generations.filter(record => record.mode === mode);
    return `${records.filter(record => record.assessment.raw_valid).length}/${records.length} raw; ${records.filter(record => record.assessment.extracted_valid).length}/${records.length} after fence removal`;
  };
  $('comparison-summary').textContent = `Qwen alone: ${counts('unconstrained')}. Qwen + SynCode: ${counts('constrained')}. Three prompts demonstrate behavior; they do not establish a general reliability rate or that SynCode is always necessary. A fence extractor is a simpler alternative for these particular baseline failures.`;
}
function renderTrace() {
  const record = recordFor(Number($('trace-prompt').value || 0), 'constrained');
  const steps = record?.token_trace || [];
  $('trace-step').max = Math.max(1, steps.length); $('trace-step').disabled = !steps.length;
  const index = Math.min(Number($('trace-step').value) - 1, steps.length - 1);
  $('step-label').textContent = steps.length ? `${index + 1} / ${steps.length}` : 'No trace';
  const trace = steps[index];
  $('trace-prefix').textContent = trace ? (trace.prefix || '(empty output—choosing the first token)') : 'This older report contains no token trace. Run the model again to record real decisions.';
  $('token-candidates').replaceChildren(); $('token-allowed').replaceChildren();
  for (const candidate of trace?.model_top_choices || []) {
    const row = document.createElement('tr'); cell(row, JSON.stringify(candidate.text)); cell(row, candidate.score.toFixed(3));
    cell(row, candidate.allowed ? 'Allowed' : 'Blocked').className = candidate.allowed ? 'success-text' : 'failure-text'; $('token-candidates').append(row);
  }
  for (const candidate of trace?.allowed_top_choices || []) {
    const row = document.createElement('tr'); cell(row, JSON.stringify(candidate.text)); cell(row, candidate.score.toFixed(3)); $('token-allowed').append(row);
  }
  $('selected-token').textContent = trace ? JSON.stringify(trace.selected_token) : 'No trace';
}
function loadReport(value, label) {
  report = value; prompts = [...new Set(report.generations.map(record => record.prompt))];
  for (const id of ['prompt-select', 'trace-prompt']) {
    $(id).replaceChildren(...prompts.map((prompt, index) => { const option = document.createElement('option'); option.value = index; option.textContent = `${index + 1}. ${['Article', 'Conference paper', 'Book'][index] || 'Custom prompt'}`; return option; }));
  }
  $('evidence-label').textContent = `${label} · ${report.evidence_file} · ${report.created_at_utc || 'Timestamp not recorded in this older run'}`;
  const metadata = {
    'Model': report.model, 'Model revision': report.revision, 'Grammar SHA-256': report.grammar_sha256,
    'Source SHA-256': report.source_sha256 || 'Not recorded in this older run',
    'Git base commit': report.git_commit || 'Not recorded in this older run',
    'Environment': JSON.stringify(report.environment || report.versions), 'Dependencies': JSON.stringify(report.versions),
    'Decoding': `Greedy; seed ${report.seed}; ${report.max_new_tokens} token limit; ${report.mode || 'grammar_strict (archived run)'}`
  };
  $('provenance').replaceChildren();
  for (const [key, value] of Object.entries(metadata)) { const dt = document.createElement('dt'); dt.textContent = key; const dd = document.createElement('dd'); dd.textContent = value; $('provenance').append(dt, dd); }
  renderComparison(); renderTrace();
}
$('prompt-select').onchange = renderComparison;
$('trace-prompt').onchange = () => { $('trace-step').value = 1; renderTrace(); };
$('trace-step').oninput = renderTrace;
const examples = {
  nested: '@article{review2026,\n  title = {A {deeply {nested}} title},\n  author = {Example Author},\n  year = 2026\n}',
  broken: '@article{broken,\n  title = {Missing the outer closing brace}\n',
  empty: '@misc{empty,\n  title = {},\n  note = ""\n}',
  semantic: '@article{invented,\n  author = {Imaginary Researcher},\n  title = {A Made-Up Paper in a Nonexistent Journal},\n  journal = {This Journal Does Not Exist},\n  year = 9999\n}'
};
document.querySelectorAll('[data-example]').forEach(button => button.onclick = () => { $('bibtex-input').value = examples[button.dataset.example]; $('validate').click(); });
$('validate').onclick = async () => {
  try {
    const response = await fetch('/api/validate', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({source: $('bibtex-input').value})});
    const value = await response.json(); if (!response.ok) throw Error(value.error);
    $('validation-status').textContent = value.raw_valid ? 'Accepted by Lark' : 'Rejected by Lark';
    $('validation-status').className = value.raw_valid ? 'success-text' : 'failure-text';
    $('validation-detail').textContent = value.raw_valid ? value.tree : value.raw_error;
  } catch (error) { $('validation-status').textContent = error.message; }
};
async function pollRun() {
  try {
    const response = await fetch('/api/job'); const job = await response.json();
    $('live-log').textContent = job.log_tail || 'Loading the local model. This can take a few minutes…';
    $('live-run').textContent = job.status === 'running' ? 'Qwen is running…' : 'Run Qwen again locally';
    if (job.status === 'running') { setTimeout(pollRun, 1500); return; }
    $('live-run').disabled = false;
    if (job.report) loadReport(job.report, job.status === 'complete' ? 'Fresh live run completed' : 'Live run finished with failures');
    if (job.error) $('live-log').textContent += '\n' + job.error;
  } catch (error) { $('live-log').textContent = error.message; $('live-run').disabled = false; }
}
$('live-run').onclick = async () => {
  $('live-run').disabled = true;
  try { const response = await fetch('/api/run', {method: 'POST'}); if (![202, 409].includes(response.status)) throw Error('Could not start the run.'); pollRun(); }
  catch (error) { $('live-log').textContent = error.message; $('live-run').disabled = false; }
};
showComponent('syncode'); $('bibtex-input').value = examples.nested;
fetch('/api/evidence').then(response => { if (!response.ok) throw Error('Could not load the saved evidence.'); return response.json(); }).then(value => loadReport(value, 'Recorded real experiment')).catch(error => { $('evidence-label').textContent = error.message; });
