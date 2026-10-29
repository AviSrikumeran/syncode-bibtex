const $ = id => document.getElementById(id);
const recordedSite = document.documentElement.dataset.mode === 'recorded';
async function apiFetch(path, options = {}) {
  if (!recordedSite) return fetch(path, options);
  if (!options.method || options.method === 'GET') {
    return fetch(`./data/${path.split('/').pop()}.json`);
  }
  const payload = JSON.parse(options.body || '{}');
  const response = await fetch('./data/results.json');
  const results = await response.json();
  if (path === '/api/run-case') return {ok: true, json: async () => results.find(item => item.case_id === payload.case_id)};
  if (path === '/api/run-group') {
    const rows = results.filter(item => payload.group === '*' || item.category === payload.group);
    return {ok: true, json: async () => ({results: rows, total: rows.length, matched: rows.filter(item => item.matched_expectation).length})};
  }
  throw Error('Fresh parsing and generation require the local Python demo. See Reproduce.');
}
document.querySelectorAll('pre[data-copy-commands]').forEach(block => {
  const controls = document.createElement('div'); controls.className = 'toolbar';
  const commands = block.textContent.trim().split(/\r?\n/).filter(line => line.trim());
  const status = document.createElement('span'); status.setAttribute('role', 'status');
  [block.textContent.trim()].forEach((command, index) => {
    const button = document.createElement('button');
    button.textContent = commands.length === 1 ? 'Copy command' : 'Copy all commands';
    button.title = command;
    button.onclick = async () => {
      try { await navigator.clipboard.writeText(command); status.textContent = 'Commands copied.'; }
      catch (error) { status.textContent = 'Clipboard unavailable. Select the command and press Ctrl+C.'; }
    };
    controls.append(button);
  });
  controls.append(status); block.after(controls);
});
$('copy-citation').onclick = async () => {
  try {
    await navigator.clipboard.writeText($('walkthrough-citation').textContent);
    $('copy-citation-status').textContent = 'Citation copied.';
  } catch (error) {
    $('copy-citation-status').textContent = 'Clipboard unavailable. Select the example text and press Ctrl+C, or use Load into validator.';
  }
};
$('use-citation').onclick = () => {
  $('bibtex-input').value = $('walkthrough-citation').textContent;
  $('validation-status').textContent = '';
  $('validation-detail').textContent = 'Example loaded. Predict the result, then click Validate with Lark.';
  $('bibtex-input').focus();
};
let report;
let prompts = [];
apiFetch('/api/grammar').then(async response => {
  const value = await response.json(); if (!response.ok) throw Error(value.error || 'Could not load grammar.');
  $('grammar-source').textContent = value.source;
  $('copy-grammar').disabled = false;
}).catch(error => { $('grammar-source').textContent = error.message; });
$('copy-grammar').onclick = async () => {
  try { await navigator.clipboard.writeText($('grammar-source').textContent); $('grammar-copy-status').textContent = 'Grammar copied.'; }
  catch (error) { $('grammar-copy-status').textContent = 'Select the grammar text and press Ctrl+C.'; }
};
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
  $('comparison-summary').textContent = `Qwen alone: ${counts('unconstrained')}. Qwen + SynCode: ${counts('constrained')}. These results describe the selected prompts and settings.`;
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
  $('prompt-overview').replaceChildren();
  prompts.forEach((prompt, index) => {
    const row = document.createElement('tr'); cell(row, prompt);
    for (const mode of ['unconstrained', 'constrained']) {
      const record = recordFor(index, mode);
      cell(row, record ? (record.assessment.raw_valid ? 'Raw text parses' : 'Raw text does not parse') : 'No result');
    }
    const button = document.createElement('button'); button.textContent = 'Show outputs';
    button.onclick = () => { $('prompt-select').value = String(index); renderComparison(); $('selected-prompt').scrollIntoView({block: 'nearest'}); };
    const action = document.createElement('td'); action.append(button); row.append(action); $('prompt-overview').append(row);
  });
  for (const id of ['prompt-select', 'trace-prompt']) {
    $(id).replaceChildren(...prompts.map((prompt, index) => { const option = document.createElement('option'); option.value = index; option.textContent = `${index + 1}. ${['Article', 'Conference paper', 'Book'][index] || 'Custom prompt'}`; return option; }));
  }
  $('evidence-label').textContent = `${label} · ${report.evidence_file} · ${report.created_at_utc || 'Timestamp not recorded in this older run'}`;
  if (report.grammar_matches_recorded === false) $('evidence-label').textContent += ' · Archived grammar differs from the current validator';
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
document.querySelectorAll('[data-example]').forEach(button => button.onclick = async () => {
  $('bibtex-input').value = examples[button.dataset.example];
  if (!recordedSite) { $('validate').click(); return; }
  try {
    const response = await apiFetch('/api/examples');
    if (!response.ok) throw Error('Could not load saved example results.');
    const record = (await response.json())[button.dataset.example];
    $('bibtex-input').value = record.source;
    $('validation-status').textContent = 'Recorded example result: ' + (record.raw_valid ? 'accepted by Lark' : 'rejected by Lark');
    $('validation-detail').textContent = record.raw_valid ? record.tree : record.raw_error;
  } catch (error) { $('validation-status').textContent = error.message; }
});
$('validate').onclick = async () => {
  try {
    const response = await apiFetch('/api/validate', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({source: $('bibtex-input').value})});
    const value = await response.json(); if (!response.ok) throw Error(value.error);
    $('validation-status').textContent = value.raw_valid ? 'Accepted by Lark' : 'Rejected by Lark';
    $('validation-status').className = value.raw_valid ? 'success-text' : 'failure-text';
    $('validation-detail').textContent = value.raw_valid ? value.tree : value.raw_error;
  } catch (error) { $('validation-status').textContent = error.message; }
};
async function pollRun() {
  try {
    const response = await apiFetch('/api/job'); const job = await response.json();
    $('live-log').textContent = job.log_tail || 'Loading the local model. This can take a few minutes…';
    $('live-run').textContent = job.status === 'running' ? 'Running all 3 prompts…' : 'Run all 3 prompts locally';
    $('run-status').textContent = job.status === 'running' ? 'Fresh generation in progress. Existing displayed results remain saved evidence until this run finishes.' :
      job.status === 'complete' ? 'Fresh run completed. The table and outputs now show this run.' : 'Run ended with failures. Inspect the logs and any available outputs.';
    if (job.status === 'running') { setTimeout(pollRun, 1500); return; }
    $('live-run').disabled = false;
    if (job.report) loadReport(job.report, job.status === 'complete' ? 'Fresh live run completed' : 'Live run finished with failures');
    if (job.error) $('live-log').textContent += '\n' + job.error;
  } catch (error) { $('live-log').textContent = error.message; $('live-run').disabled = false; }
}
$('live-run').onclick = async () => {
  $('live-run').disabled = true;
  $('run-status').textContent = 'Starting the local three-prompt comparison…';
  try { const response = await apiFetch('/api/run', {method: 'POST'}); if (![202, 409].includes(response.status)) throw Error('Could not start the run.'); pollRun(); }
  catch (error) { $('live-log').textContent = error.message; $('live-run').disabled = false; }
};
showComponent('syncode'); $('bibtex-input').value = examples.nested;
apiFetch('/api/evidence').then(response => { if (!response.ok) throw Error('Could not load the saved evidence.'); return response.json(); }).then(value => loadReport(value, 'Recorded real experiment')).catch(error => { $('evidence-label').textContent = error.message; });

apiFetch('/api/bounds').then(async response => {
  const value = await response.json(); if (!response.ok) throw Error(value.error);
  const rows = value.after.cases;
  const matched = rows.filter(row => row.matched_expectation).length;
  $('bounds-status').textContent = `${matched}/${rows.length} documented expectations matched. ${value.after.repeats} repetitions per case. Report: ${value.after.created_at_utc}.`;
  if (value.after.grammar_sha256 !== value.active_grammar_sha256) $('bounds-status').textContent += ' WARNING: report grammar differs from the active grammar.';
  const groups = new Map();
  for (const record of rows) {
    if (!groups.has(record.category)) groups.set(record.category, []);
    groups.get(record.category).push(record);
    const row = document.createElement('tr');
    const details = document.createElement('details'); const summary = document.createElement('summary');
    summary.textContent = record.category + ' / ' + record.name;
    const preview = document.createElement('pre');
    preview.textContent = `Characters: ${record.characters}\nInput SHA-256: ${record.source_sha256}\nPreview (first 400 characters):\n${record.preview}\n\n${record.error || ''}`;
    details.append(summary, preview); const nameCell = document.createElement('td'); nameCell.append(details); row.append(nameCell);
    cell(row, record.expected_accept ? 'Accept' : 'Reject'); cell(row, record.actual_accept ? 'Accepted' : 'Rejected');
    cell(row, record.matched_expectation ? 'Yes' : 'NO'); cell(row, record.median_ms.toFixed(4)); $('bounds-cases').append(row);
    if (['nesting-valid', 'document-size-valid', 'value-length-valid'].includes(record.category)) {
      const scale = document.createElement('tr'); cell(scale, record.name); cell(scale, record.characters);
      cell(scale, record.actual_accept ? 'Yes' : 'No'); cell(scale, record.median_ms.toFixed(4)); $('bounds-scale').append(scale);
    }
  }
  for (const [category, records] of groups) {
    const times = records.map(record => record.median_ms).sort((a, b) => a - b);
    const middle = Math.floor(times.length / 2);
    const median = times.length % 2 ? times[middle] : (times[middle - 1] + times[middle]) / 2;
    const row = document.createElement('tr'); cell(row, category);
    cell(row, `${records.filter(record => record.matched_expectation).length}/${records.length}`); cell(row, median.toFixed(4)); $('bounds-groups').append(row);
  }
  const failures = value.before?.cases.filter(record => !record.matched_expectation) || [];
  $('bounds-defect').textContent = failures.length ?
    'Preserved before-fix failure: ' + failures.map(record => `${record.category}/${record.name} expected acceptance=${record.expected_accept}, observed acceptance=${record.actual_accept} (${record.error_type})`).join('; ') + '. The after-fix report includes the regression case.' : 'No before-fix report available.';
}).catch(error => { $('bounds-status').textContent = error.message; });

let caseCatalog;
function selectedCase() { return caseCatalog.cases.find(item => item.case_id === $('case-select').value); }
function renderSelectedCase() {
  const item = selectedCase(); if (!item) return;
  $('case-reason').textContent = 'What this checks: ' + caseCatalog.groups[item.category];
  $('case-requirements').textContent = 'Requirement tags: ' + item.requirements.map(id => `${id} — ${caseCatalog.requirements[id]}`).join('; ');
  $('case-original-expectation').textContent = 'Original fixture expectation: ' + (item.expected_accept ? 'Accept' : 'Reject');
  $('case-source-info').textContent = `${item.characters} characters; SHA-256 ${item.source_sha256}` + (item.source === null ? '. Preview only: the original-fixture action parses the full generated input.' : '');
  $('case-input').value = item.source === null ? item.preview : item.source;
  $('case-input').readOnly = recordedSite || item.source === null;
  $('run-edited-case').disabled = recordedSite || item.source === null;
  $('case-edited-expected').value = String(item.expected_accept);
  $('case-run-status').textContent = recordedSite ? 'Select Show saved case result to inspect recorded evidence.' : 'Not run. The expectation above is not an execution result.';
  $('case-run-detail').textContent = '';
}
function filterCases() {
  const group = $('case-group').value;
  const items = caseCatalog.cases.filter(item => group === '*' || item.category === group);
  $('case-select').replaceChildren(...items.map(item => {
    const option = document.createElement('option'); option.value = item.case_id; option.textContent = item.name; return option;
  }));
  $('case-catalog-status').textContent = `${items.length} fixtures in this selection; ${caseCatalog.cases.length} in the complete catalog.`;
  $('case-group-results').replaceChildren(); $('case-group-status').textContent = '';
  renderSelectedCase();
}
function showCaseResult(result, label) {
  $('case-run-status').textContent = `${label}: ${result.crash ? 'PARSER CRASH' : result.actual_accept ? 'Accepted' : 'Rejected'}; expected ${result.expected_accept ? 'accept' : 'reject'}; ${result.matched_expectation ? 'expectation matched' : 'EXPECTATION NOT MATCHED'}.`;
  $('case-run-detail').textContent = `Input characters: ${result.characters}\nInput SHA-256: ${result.source_sha256 || '(edited input)'}\nParse time: ${result.elapsed_ms === undefined ? 'not measured' : result.elapsed_ms + ' ms'}\n\n${result.tree || result.error || 'No tree/error preview returned. Inspect this fixture individually for a tree.'}`;
}
async function caseRequest(path, payload) {
  const response = await apiFetch(path, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)});
  const result = await response.json(); if (!response.ok) throw Error(result.error); return result;
}
$('case-group').onchange = filterCases;
$('case-select').onchange = renderSelectedCase;
$('run-original-case').onclick = async () => {
  $('run-original-case').disabled = true;
  try { showCaseResult(await caseRequest('/api/run-case', {case_id: selectedCase().case_id}), recordedSite ? 'Recorded case result' : 'Original fixture run'); }
  catch (error) { $('case-run-status').textContent = error.message; }
  finally { $('run-original-case').disabled = false; }
};
$('run-edited-case').onclick = async () => {
  try {
    const source = $('case-input').value;
    const result = await caseRequest('/api/validate', {source});
    const expected = $('case-edited-expected').value === 'true';
    showCaseResult({actual_accept: result.raw_valid, expected_accept: expected, matched_expectation: result.raw_valid === expected,
      tree: result.tree, error: result.raw_error, characters: source.length}, 'Edited input run');
  } catch (error) { $('case-run-status').textContent = error.message; }
};
$('run-case-group').onclick = async () => {
  $('run-case-group').disabled = true; $('case-group-status').textContent = recordedSite ? 'Loading saved results…' : 'Running actual parser checks…';
  try {
    const batch = await caseRequest('/api/run-group', {group: $('case-group').value});
    $('case-group-results').replaceChildren();
    for (const result of batch.results) {
      const row = document.createElement('tr'); cell(row, result.name); cell(row, result.expected_accept ? 'Accept' : 'Reject');
      cell(row, result.crash ? 'CRASH' : result.actual_accept ? 'Accepted' : 'Rejected'); cell(row, result.matched_expectation ? 'Yes' : 'NO'); cell(row, result.elapsed_ms.toFixed(4));
      const td = document.createElement('td'); const inspect = document.createElement('button'); inspect.textContent = 'Inspect';
      inspect.onclick = () => { $('case-select').value = result.case_id; renderSelectedCase(); showCaseResult(result, 'Group-run result'); };
      td.append(inspect); row.append(td); $('case-group-results').append(row);
    }
    $('case-group-status').textContent = `${batch.matched}/${batch.total} expectations matched in ${recordedSite ? 'the recorded group results' : 'this fresh group run'}. These are parser checks, not model generations.`;
  } catch (error) { $('case-group-status').textContent = error.message; }
  finally { $('run-case-group').disabled = false; }
};
apiFetch('/api/cases').then(async response => {
  const value = await response.json(); if (!response.ok) throw Error(value.error); caseCatalog = value;
  const all = document.createElement('option'); all.value = '*'; all.textContent = 'All groups';
  $('case-group').replaceChildren(all, ...Object.keys(value.groups).map(group => {
    const option = document.createElement('option'); option.value = group; option.textContent = group; return option;
  }));
  $('case-group').value = 'provided-assignment'; filterCases();
  for (const [id, description] of Object.entries(value.requirements)) {
    const row = document.createElement('tr'); cell(row, id); cell(row, description);
    cell(row, value.cases.filter(item => item.requirements.includes(id)).length); $('case-requirement-map').append(row);
  }
}).catch(error => { $('case-catalog-status').textContent = error.message; });
if (recordedSite) {
  $('edited-case-controls').hidden = true;
  $('live-run').hidden = true;
  $('run-status').textContent = 'Published evidence viewer. Fresh Qwen generation requires the local setup in Reproduce.';
  $('validate').disabled = true;
  $('validate').hidden = true;
  $('bibtex-input').readOnly = true;
  $('use-citation').hidden = true;
  $('validation-status').textContent = 'Choose an example to see its saved validation result. New input can be tested in the local demo.';
  $('run-edited-case').hidden = true;
  $('run-original-case').textContent = 'Show saved case result';
  $('run-case-group').textContent = 'Show saved group results';
  $('case-edited-expected').disabled = true;
}
