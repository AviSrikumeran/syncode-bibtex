# My BibTeX Grammar and SynCode Solution

My solution to the [UIUC ARC BibTeX assignment](https://github.com/uiuc-arc/syncode-bibtex): a Lark LALR grammar, a script that applies it during language-model generation with SynCode, and executable tests. The implementation covers the three requested tasks: grammar construction, verification with the supplied tests, and citation generation from at least three different prompts.

**[Open the project website](https://avisrikumeran.github.io/syncode-bibtex/)** — inspect the grammar, recorded test results, three-prompt comparison, and captured token choices without installing anything.

The public website displays **recorded evidence**. The local Python console additionally validates new input, executes cases, and runs fresh Qwen inference. GitHub Pages does not execute the Python backend or the model.

## What my solution does

- **`bibtex.lark`** defines citation entries, keys, fields, quoted and braced values, recursive nested groups, and escaped characters used in LaTeX. Entry names are general identifiers, supporting standard citation types without a fixed whitelist.
- **`bibtex_syncode.py`** loads Qwen2.5-0.5B-Instruct on the CPU and uses the grammar with SynCode during generation. Lark checks the resulting text. Comparison runs use the same model, prompt, and decoding settings with and without constraints.
- **Tests and saved reports** make acceptance, rejection, model output, and token-mask decisions inspectable.

BibTeX, Lark, SynCode, and Qwen are existing projects. This repository supplies the citation grammar, integration code, evaluation, and demonstration tools. AI assisted development and explanation.

## Assignment requirements and evidence

| Requested work | Implementation and evidence |
| --- | --- |
| Lark LALR(1) grammar for standard citation types, nested braces, special characters, and LaTeX commands | [Grammar](bibtex.lark), [parser setup](bibtex_syncode.py), and acceptance/rejection tests |
| Verify the grammar with the supplied unit tests | **7/7 supplied tests pass** in [test.py](test.py) |
| Integrate the grammar with SynCode and test at least three citation prompts | [Generation script](bibtex_syncode.py) and [saved comparison](results/reviewer-run.json) |

The three implemented requests ask for an article about LLM security, a conference paper by Smith and Johnson, and a book citation for *Reinforcement Learning* by Sutton and Barto. These follow the assignment's example topics; they are not a verbatim replay of every example request.

## Results and additional investigation

The automated suite has **88 passing tests**: 7 supplied tests, 41 additional valid-input tests, 24 invalid-input tests, 2 SynCode compatibility tests, and 14 console tests. The supplied harness has one documented start-rule correction, `bibTex` to `start`; the seven original test bodies and assertions are unchanged.

In the saved three-prompt comparison, **3/3 constrained outputs parse directly**. Qwen alone returns Markdown-wrapped citations: **0/3 raw outputs parse, but 3/3 parse after removing the outer fences**. This establishes the observed format difference for these runs, not general model reliability. A syntactically valid citation can still contain invented facts or miss the requested topic.

Beyond the supplied examples, [evaluate_bounds.py](evaluate_bounds.py) measures **217 selected parser observations**, including existing regression cases. Explicit examples and deterministic generators probe nesting, document size, long values, feature combinations, and incomplete prefixes. These overlap the unit tests; they are not 217 model trials. The website catalog combines those observations with the seven supplied inputs: **224 cases total**.

The measured spectrum reaches 1,000 additional nested groups, 1,000 entries, and a 100,000-character field value. Each case is timed three times and its median is recorded. These are tested sizes, not proven maximums. A Unicode-spacing rejection found during evaluation is preserved in the [before-fix report](results/boundary-before.json), alongside the [after-fix report](results/boundary-report.json).

## Run locally

Windows with Python 3.12 is the verified setup. The first model run downloads model files; later runs can use the cache. No paid API or API key is required. Windows may require the Microsoft Visual C++ x64 runtime for PyTorch.

```powershell
git clone https://github.com/AviSrikumeran/syncode-bibtex.git
cd syncode-bibtex
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m unittest -v test
.\.venv\Scripts\python.exe run_tests.py
.\.venv\Scripts\python.exe bibtex_syncode.py --compare --trace-steps 8 --revision 7ae557604adf67be50417f59c2c2f167def9a775 --output results/reproduction.json
.\.venv\Scripts\python.exe review_demo.py --offline
```

Open **http://127.0.0.1:8765/** for the local console. The generation command above runs all three prompts with and without SynCode and saves fresh evidence.

For the independent terminal menu:

```powershell
.\.venv\Scripts\python.exe terminal_demo.py --offline
```

To regenerate boundary measurements and export the static website:

```powershell
.\.venv\Scripts\python.exe evaluate_bounds.py
.\.venv\Scripts\python.exe export_pages.py
```

The export writes `docs/`, with saved results clearly distinguished from local execution. On macOS/Linux, use `python3.12` and `.venv/bin/python`; those platforms have not been verified here.

## Further detail

- [Implementation](IMPLEMENTATION.md): grammar design and integration details.
- [Evidence and reproduction guide](REVIEWER.md): configuration, provenance, and experimental interpretation.
- [Video walkthrough](VIDEO_WALKTHROUGH.md): terminal demonstration sequence.
- [Original assignment](https://github.com/uiuc-arc/syncode-bibtex): the upstream requirements, retained by reference rather than duplicated here.
