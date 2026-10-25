# BibTeX Grammar for Constrained LLM Generation with SynCode

This repository implements the [UIUC ARC BibTeX assignment](https://github.com/uiuc-arc/syncode-bibtex)
with a Lark LALR grammar, SynCode generation, and automated syntax tests.

## Reviewer demonstration

Read [REVIEWER.md](REVIEWER.md) for the experimental claim, alternatives,
limitations, and reproduction procedure. After installation, run
`.venv\Scripts\python.exe review_demo.py` and open `http://127.0.0.1:8765`.
The local page shows real side-by-side model outputs, recorded next-token
scores before and after SynCode masking, an editable Lark parser, and a button
to perform a fresh model run.

The fair comparison reports both raw-output syntax and syntax after removing
only a surrounding Markdown fence. Three prompts demonstrate behavior; they
are not a reliability benchmark or proof of factual citation accuracy.

## Run the implementation

Use **Python 3.12**. On Windows, install the Microsoft Visual C++ x64 runtime
if PyTorch reports a missing DLL.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run_tests.py
.\.venv\Scripts\python.exe bibtex_syncode.py --parse-only
.\.venv\Scripts\python.exe bibtex_syncode.py --compare --revision 7ae557604adf67be50417f59c2c2f167def9a775 --output results/reproduction.json
```

On macOS/Linux, create the environment with `python3.12 -m venv .venv` and use
`.venv/bin/python` in place of `.venv\Scripts\python.exe`. Windows is the tested platform.
The model demonstration downloads approximately 1 GB on its first run.
`RUN_DEMO.cmd` is an offline Windows launcher for an already prepared environment.

Verified results: **7 supplied tests, 40 additional valid cases, 24 invalid
cases, 2 SynCode compatibility tests, and 8 reviewer-demo tests passed** (81 total). The final constrained
generation run produced **3/3 outputs that parsed successfully**. The supplied
test harness has one documented correction: `bibTex` to `start`; all seven test
bodies remain unchanged.

See [IMPLEMENTATION.md](IMPLEMENTATION.md) for the design, scope, test details,
and honest comparison results. Actual successful and failed runs are preserved
in [results/](results/). Syntax validation does not verify publication facts.

---

The original assignment text follows.

## Assignment Overview
Create a Lark LR grammar for BibTeX citation format and use it with SynCode to constrain LLM outputs. This demonstrates how formal grammars can be used to ensure structured output generation from LLMs.

## Timeframe
One week

## Requirements
- Lark parser (`pip install lark-parser`)
- SynCode library (https://github.com/structuredllm/syncode, `pip install syncode`)
- Python 3.8+

## Tasks

### 1. Implement BibTeX Grammar
Create a Lark LALR(1) grammar that:
- Handles all standard BibTeX entry types
- Supports nested braces in field values
- Correctly processes special characters and LaTeX commands
- Is compatible with SynCode's grammar requirements

### 2. Test Grammar
A unit test file will be provided to verify your grammar implementation. The tests include various complex BibTeX examples:

- Nested braces in field values
- Special characters and LaTeX commands
- Mixed quote/brace formatting

Please see a similar ANTLR grammar here: https://github.com/antlr/grammars-v4/tree/master/bibtex (Note: This grammar is not in the Lark format)

### 3. Integrate with SynCode
Create a script that:
- Use your grammar with 
- Tests with at least 3 different prompts asking for BibTeX citations
- Example prompts:
  - "Generate a BibTeX entry for a 3 recent paper on LLM security"
  - "Create a BibTeX citation for a conference paper by authors Smith and Johnson"
  - "Provide the BibTeX entry for RL book Barto and Sutton"

## Deliverables
- `bibtex.lark` - Your Lark grammar file
- `bibtex_syncode.py` - Script for SynCode integration
