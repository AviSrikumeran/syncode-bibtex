# Reviewer guide: what this experiment establishes

## Start with the observable claim

We implement a BibTeX citation grammar and use it to constrain a language model's
generation. The goal is a response that a downstream parser can consume exactly
as returned. The grammar is a supported citation subset, not a complete BibTeX
processor or a fact-checking system.

The demonstration shows actual model output and actual next-token scores. It
does not expose private model reasoning. Its eight-step traces are observations
of the decoding process, not explanations of the model's internal intentions.

## Reproduce from the review branch

Use Python 3.12. Windows is the verified platform; the Windows C++ x64 runtime
must be available for PyTorch. The model requires about 1 GB of download space,
plus installed dependencies and runtime caches. No paid API or API key is used.

```powershell
git clone --branch reviewer-demo https://github.com/AviSrikumeran/syncode-bibtex.git
cd syncode-bibtex
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe run_tests.py
.\.venv\Scripts\python.exe bibtex_syncode.py --compare --trace-steps 8 --revision 7ae557604adf67be50417f59c2c2f167def9a775 --output results/reproduction.json
.\.venv\Scripts\python.exe review_demo.py
```

Open `http://127.0.0.1:8765`. After the first model download, `--offline` on
`review_demo.py` makes live runs use only the cached model. The page binds only
to localhost. It is a demonstration server, not a hosted production service.

On macOS/Linux, use `python3.12` and `.venv/bin/python`. Those operating systems
have not been verified here; the lock records the tested Windows environment.

To test another prompt without modifying code:

```powershell
.\.venv\Scripts\python.exe bibtex_syncode.py --compare --trace-steps 8 --revision 7ae557604adf67be50417f59c2c2f167def9a775 --prompt "Generate one BibTeX entry with a nested title and an accented author name." --output results/custom-prompt.json
```

## Inspect the system in five steps

1. **Components.** Trace text through the tokenizer, Qwen, the SynCode mask, and
   final Lark validation. Qwen and SynCode repeat at every generated token.
2. **Evidence.** Compare raw responses for the same model, prompt, decoding
   settings, and budget. Also inspect the baseline after removing only one
   surrounding Markdown fence. No citation content is repaired.
3. **Token choices.** At step one, see the actual scores for a Markdown fence,
   `@`, and conversational text. The trace shows what the mask blocks and which
   token greedy decoding selects. Move the step slider to inspect later prefixes.
4. **Try the parser.** Remove a closing brace and observe rejection. Then parse
   the explicitly invented publication: it passes syntax, demonstrating the
   boundary between structure and truth.
5. **Reproduce.** Inspect the model commit, grammar hash, source hash, dependency
   versions, environment, decoding settings, and the original evidence filename.

The live button launches the same Python command used by the CLI. It does not
return a stored success. Logs and new JSON reports are saved locally, a running
job cannot be duplicated, and failures are displayed rather than hidden.

## Why each component exists

| Component | Responsibility | Why it is here |
| --- | --- | --- |
| Tokenizer | Convert text to/from model token IDs | A model token may cross several grammar symbols; constraints must handle token boundaries |
| Qwen2.5-0.5B-Instruct | Score candidate next tokens | Supplies the generated content; it is small enough for the demonstrated CPU experiment |
| `bibtex.lark` | Define the accepted citation syntax | Makes the output contract explicit and inspectable |
| SynCode | Apply grammar-based masks during decoding | Changes token selection before an invalid continuation is emitted |
| Lark | Parse the entire final response independently | Detects malformed or truncated outputs, including permissive-mask failures |
| Tests and reports | Exercise acceptance/rejection and retain evidence | Give the reviewer repeatable checks rather than narrative claims |

Nested groups require recursive rules because any fixed-depth pattern would
eventually fail at deeper nesting. LALR satisfies the assignment's parser
requirement. Explicit whitespace prevents split bare identifiers from being
silently joined. Nonoverlapping terminal classes support SynCode's basic lexer.
Fields are general identifiers rather than a whitelist tailored to the seven
examples. Bibliographic completeness and duplicate keys are semantic concerns.

## Is SynCode necessary?

That depends on the required output contract. It is one way to enforce structure
during generation, not the only possible design.

| Approach | Useful property | Limitation |
| --- | --- | --- |
| Prompt instructions only | Simple baseline | A model can ignore the requested raw format |
| Remove a Markdown wrapper | Solves the observed baseline wrapper issue cheaply | Does not fix malformed citation content or incomplete groups |
| Parse and retry | Detects syntax errors after generation | Requires a retry policy and more generation; completion is not guaranteed |
| Grammar-guided decoding | Restricts choices during generation | Adds runtime machinery; mask mode and token budget affect behavior |

For these three original prompts, unconstrained Qwen produced valid citation
content inside Markdown fences: **0/3 raw outputs parse, but 3/3 parse after
fence removal**. The final constrained outputs parse **3/3 directly**. This
supports a raw-format improvement in this small demonstration. It does not
establish that constrained decoding generally outperforms extraction or that
Qwen cannot produce valid BibTeX unaided.

The constrained article changed LLM security to LSTM security. This is a task-fit
failure even though syntax passed. Publication facts have not been verified.
Unknown macro references and missing bibliographic fields can also be syntactically
valid; passing the parser is not evidence of bibliographic correctness.

Earlier `grammar_strict` experiments and the smaller SmolLM2 model are retained
in `results/`. Some constrained outputs hit the 256-token budget without
completion. `grammar_strict` can exclude useful tokens spanning several grammar
symbols; `grammar_mask` retains more choices but can overapproximate valid
continuations, which is why final parsing remains part of the implementation.

## Evidence integrity and limits

- Both comparison arms use the same rendered prompt, greedy decoding, seed,
  model revision, token budget, CPU/dtype, and completion stopping criterion.
- Reports retain raw text, generated token IDs, per-run time, termination status,
  parse errors, and first-eight-step traces. Instrumentation verifies that the
  selected IDs in every captured trace match the actual generated IDs.
- Scores are captured at the SynCode processor boundary, after Hugging Face's
  built-in processors, not directly from an unprocessed forward pass. The pinned
  Qwen configuration includes a repetition penalty of 1.1. These processed logits
  are not probabilities. Runtime measurements are descriptive;
  this is not a controlled performance benchmark.
- The recorded Git commit identifies the checkout at report creation. For an
  uncommitted development run, the script and grammar SHA-256 fields identify
  the exact source bytes; do not assume the base commit alone includes those edits.
- Three fixed prompts and one greedy configuration are insufficient to estimate
  general reliability or statistical significance. Broader held-out evaluation
  is required before making those claims.
- No claim of production readiness is made. CI across clean environments,
  broader grammar conformance, factual citation verification, and larger held-out
  generation evaluation remain separate engineering work.

The automated suite includes 7 supplied examples, 41 additional valid cases,
24 malformed cases, 2 SynCode parser compatibility tests, and 13 reviewer-demo
tests: **87 tests**. The original test harness required a one-line start-rule
correction; all seven original test bodies and assertions remain intact.

## Measured bounds, not a claim of exhaustive coverage

The **Test cases** tab is an interactive fixture runner, separate from the
recorded **Test spectrum**. Select a group and case to inspect its input,
expectation, reason, and requirement tags. Run the original fixture to get a
fresh parse-tree preview or actual error. The full source is used for stress
fixtures even when the browser shows only a preview. Tree previews are bounded
iteratively so deeply nested valid input does not crash display rendering.

The catalog has 224 fixtures: 7 original assignment inputs, extracted from the
unchanged test bodies with Python's AST/literal reader, plus the 217 selected
boundary observations. These counts overlap the regression suite. HTTP unit
tests and model-generation trials are separate evaluations, not additional
BibTeX fixtures in this tab.

You can run a group (or all groups) and inspect every observed result. Small
inputs can be edited and tested with an explicitly selected expectation;
edited experiments are labeled separately from original fixtures. Requirement
tags trace cases to the supported behavior and scope boundaries; counts are
evidence examples, not percentages of complete language conformance.

Run `evaluate_bounds.py` or choose option 6 in `terminal_demo.py`. The report
contains 217 parser observations, including the 65 existing valid/invalid
regression cases. It is not 217 independent tests of model generation.

The spectrum combines 48 deliberately chosen feature interactions, all 58
incomplete prefixes of one complete citation, matched valid/invalid stress cases,
semantic limits, and scope exclusions. Stress probes reach 1,000 additional
nested groups, 1,000 entries, and a 100,000-character field value. Those are the
largest tested points, not proven maximum supported inputs. Each case is timed
three times; the report gives descriptive medians, not a controlled speed claim.
The browser editor has a separate 20,000-character request cap.

The initial spectrum found a defect involving non-breaking and thin spaces
inside values. `results/boundary-before.json` preserves that failure. The fix
made structural ASCII whitespace distinct from literal Unicode spacing in
values and added a regression fixture. `results/boundary-report.json` records
the after-fix outcomes. Inputs remain reproducible through the case generator,
source previews, input hashes, and grammar hash.

Accepting invented publications or undefined macros demonstrates a semantic
limit, not successful fact-checking. Rejecting `@string` or `@preamble` demonstrates
the declared citation subset, not that those constructs are invalid BibTeX.

## Primary references

- [Assignment](https://github.com/uiuc-arc/syncode-bibtex)
- [Qwen model card](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct)
- [SynCode documentation and implementation](https://github.com/structuredllm/syncode)
- [Lark grammar reference](https://lark-parser.readthedocs.io/en/stable/grammar.html)
