# BibTeX assignment: implementation and demonstration

For the expanded reviewer interface, fair comparison analysis, and current
87-test suite, see [REVIEWER.md](REVIEWER.md). The historical runs below are
preserved as evidence of the original implementation and its limitations.

The working copy is based on upstream commit
`a91952e657ff94d296fdd196f32ce247731cb12a`. The original assignment text
is retained below the implementation instructions in README.md.

## Run on this machine

For a beginner-friendly run, double-click `RUN_DEMO.cmd` in File Explorer.
It runs the tests and three constrained generations using the existing environment and
cached model, saves `results/latest-demo.json`, and keeps the terminal open so
you can read the results. This launcher uses offline mode; initial setup is
already complete on this machine.

Codex can run the entire workflow directly in its shell using
`cmd.exe /c RUN_DEMO.cmd --no-pause`. There is no need to move commands or output
between VS Code and chat. The launcher saves `results/latest-tests.log`,
`results/latest-generation.log`, and `results/latest-demo.json`, which Codex
can inspect directly.

An ordinary-terminal run exposed a missing Windows C++ runtime dependency that
Codex's injected PATH had masked. The local `.venv/Library/bin` now contains
Microsoft-signed runtime DLLs copied from the bundled runtime. PyTorch searches
this directory automatically. This repair is confined to the ignored virtual
environment; no global PATH or system files were changed. Verification uses a
clean PATH containing only Windows system directories. On another Windows
machine, install the Microsoft Visual C++ x64 runtime as part of environment
setup rather than relying on Codex's process environment.

Open a PowerShell terminal in this folder. The isolated `.venv` is ready:

```powershell
.\.venv\Scripts\python.exe run_tests.py
.\.venv\Scripts\python.exe bibtex_syncode.py --parse-only
.\.venv\Scripts\python.exe bibtex_syncode.py --compare --output results/generation.json
```

The first command prints individual failures, separate group totals, and an
overall status; it exits nonzero on failure. The second needs only Lark. The
third performs real CPU inference with Qwen2.5-0.5B-Instruct, downloading about
1 GB of weights on first use. Model files and SynCode masks are cached in
`.cache/`. It exits nonzero if a constrained output fails validation;
unconstrained failures are expected comparison results.

For a new environment, use **Python 3.12** to create a virtual environment,
then run its Python with `-m pip install -r requirements-lock.txt`. The lock
records the tested Windows environment; `requirements.txt` specifies the two
direct dependencies. Do not install both `lark-parser` and `lark`, which share
the same Python import name. Python 3.14 is not supported by this SynCode version.

For offline inference after downloading the model, set `HF_HUB_OFFLINE=1` in
the shell before running. For repeatable model selection, pass
`--revision <commit hash>` using the `revision` saved in a generation report.
`--model`, `--mode`, `--max-new-tokens`, `--seed`, and `--threads` are configurable.

## How the grammar works

`start` accepts one or more entries with optional surrounding whitespace.
Each entry contains its type, a citation key, and optional comma-separated
fields. Entries can use braces or parentheses as their outer delimiters.
Entry types and field names are general identifiers, allowing all 14 standard
entry types and custom types without a separate rule for every bibliography style.

`value` accepts braced text, quoted text, unsigned integers, and bare macro
names. `#` joins these value components syntactically; this parser does not
evaluate macros or concatenate strings into a bibliography data model.

`braced` contains itself recursively, so each opening group must have a
matching closing group. Nested groups can occur inside quoted values too.
Quotes inside braced groups are ordinary content. `ESCAPE` consumes a
backslash and the following non-newline character together, including escaped
quotes and braces. LaTeX commands and math remain text; no TeX rendering occurs.

The lexer separates letters, numbers, punctuation, whitespace, escapes, and
structural delimiters into nonoverlapping terminal classes. Whitespace is
explicit instead of globally ignored, so `two words` cannot accidentally
become a bare macro name. This also preserves whitespace in field values.
Both standalone Lark and SynCode's vendored parser use LALR parsing with the
basic lexer for the integration path.

## Supplied harness correction

The original `test.py` requests `start='bibTex'`. Lark rule names cannot contain
uppercase letters, so that spelling cannot be declared in a valid grammar.
The only change to the supplied file is `start='start'`. All seven test bodies,
inputs, and assertions are preserved. Comparing `test.py` against the upstream
commit above shows this correction.

## How generation works

The script loads a Hugging Face instruction model and passes a real
`SyncodeLogitsProcessor` to `model.generate`. The processor receives the same
grammar through SynCode's `Grammar` object and uses `grammar_mask` mode.
`parse_output_only=True` keeps the natural-language prompt outside the grammar.
At each decoding step, SynCode masks tokens that its parser and finite-state
machinery disallow. It resets its state for every new prompt.

The demonstration uses three prompts: an article about LLM security, a
conference citation, and a reinforcement-learning book. Both constrained and
unconstrained runs get the same prompts, greedy decoding, token budget, and
stopping criterion. The script stops once the generated text parses as a
complete citation, or when generation ends or reaches its token limit.
Every output is independently reparsed by standalone Lark. The text is not
repaired or replaced with a canned citation.

Grammar constraints restrict syntax; they cannot force a model to finish
before a token limit or provide accurate bibliographic content. The JSON
report retains raw output and parse errors, as well as the model commit,
dependency versions, seed, token budget, grammar hash, and decoding mode.

The more restrictive `grammar_strict` mode can block valid model tokens that
cross several terminal boundaries. It is available through `--mode`, but the
demonstration defaults to `grammar_mask` to retain more of the model's choices.
This mode can overapproximate valid continuations, making final independent
validation essential.

## Tests and evidence

- `test.py`: seven supplied examples, with the start-name correction above.
- `tests/test_edge_cases.py`: 40 valid cases and 24 invalid cases. Valid cases
  cover every standard type, nesting, Unicode, LaTeX, empty and mixed values,
  concatenation, punctuation, whitespace, and multiple entries. Negative cases
  must raise `lark.UnexpectedInput`; unrelated exceptions fail the test.
- `tests/test_syncode.py`: two compatibility tests check all 64 additional
  cases against SynCode's actual vendored parser, independently of standalone Lark.
- `results/test-results.txt`: actual test runner output.
- `results/parsing.json`: actual parser-only demonstration results.
- `results/generation-smollm.json`: preserved first model attempt. The 135M
  model completed only 1/3 constrained citations; 0/3 unconstrained outputs
  parsed. The two unfinished constrained outputs were not counted as successes.
- `results/generation-qwen-strict.json`: preserved larger-model strict-mode
  attempt. All three constrained outputs hit the token limit without completing.
- `results/generation.json`: results of the larger model with `grammar_mask`.

Verified on October 25, 2026 with Python 3.12.14:

| Check | Result |
| --- | --- |
| Supplied cases (start-name correction only) | 7/7 passed |
| Additional valid inputs | 40/40 passed |
| Malformed inputs rejected | 24/24 passed |
| SynCode parser compatibility tests | 2/2 passed, covering all 64 additional inputs |
| Parser demonstration | 5/5 expected outcomes |
| Qwen constrained generation, `grammar_mask` | 3/3 parsed |
| Qwen unconstrained generation, raw output | 0/3 parsed |

The unconstrained Qwen outputs contain Markdown fences. This comparison checks
the raw output contract, not whether a citation could be extracted by removing
those fences. The constrained article also discusses LSTM security rather than
LLM security: syntactic success does not establish prompt compliance or factual
accuracy. None of these generated publication details have been independently
verified.

To reproduce the successful model revision explicitly:

```powershell
.\.venv\Scripts\python.exe bibtex_syncode.py --compare --revision 7ae557604adf67be50417f59c2c2f167def9a775 --output results/reproduction.json
```

## Scope and limitations

This is a citation-entry grammar, not a complete BibTeX processor. It does not
implement `@string` definitions, `@preamble`, `@comment` blocks, free text between
entries, or source comments outside field values. These are unsupported forms,
not claims that such BibTeX features are invalid. A document must contain at
least one entry; empty input is intentionally rejected for the generation task.

It does not check required fields, author-name structure, duplicate citation
keys, macro definitions, DOI correctness, or publication existence. Custom entry
types are accepted. Bibliographically incomplete citations may parse correctly.
Nested braces have no fixed grammar depth limit, but runtime resources remain
finite. Successful examples provide evidence for these runs, not a guarantee
that every future generation will complete successfully.
