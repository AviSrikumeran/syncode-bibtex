# Independent terminal demonstration

Use the terminal as the primary evidence. The website is an optional visual
aid for explaining the pipeline and inspecting a token trace. A dashboard alone
does not establish that you can reproduce or explain the implementation.

## Start on this prepared Windows machine

Open a terminal in this repository and run:

```powershell
.\.venv\Scripts\python.exe terminal_demo.py --offline
```

The menu lets you show the grammar, run tests, enter a new model prompt, validate
your own BibTeX, and inspect saved token decisions. No Codex session, browser,
or assistant is needed for this command to work. Offline mode requires that the
model has already been downloaded. For a fresh machine, follow REVIEWER.md first.

Menu option 3 performs real model inference; option 5 is explicitly a replay of
saved evidence. Do not present replayed output as a fresh generation.

## Suggested 10-minute sequence

| Time | Show | Explain in your own words |
| --- | --- | --- |
| 0:00–0:45 | Repository and problem statement | Why a citation-shaped response still needs a precise output contract |
| 0:45–2:15 | Menu 1: actual grammar | Entry, field, value, recursive braces, explicit whitespace, and the supported subset |
| 2:15–3:15 | Menu 6: boundary spectrum; menu 2 if time permits | Matched valid/invalid cases, sizes and depths, semantic limits, and the Unicode defect found and fixed |
| 3:15–5:30 | Menu 3: type a new prompt | Same Qwen, prompt, revision, and budget; constraints are the comparison variable |
| 5:30–6:45 | Token table and raw outputs | Which candidate was blocked, which was selected, and why scores are not private reasoning |
| 6:45–8:15 | Menu 4: a citation, then remove a brace | Actual Lark acceptance/rejection; why syntactic validity differs from factual accuracy |
| 8:15–9:15 | Optional website: Test cases, evidence, and token tabs | Run a fixture/group, trace its requirement, and distinguish raw format, extracted syntax, and factual truth |
| 9:15–10:00 | REVIEWER.md and saved JSON report | Reproduction steps, pinned model revision, hashes, limitations, and next evaluation work |

Generation time varies. Rehearse first and allow a longer recording if needed.
If you edit out waiting time, label the cut rather than implying instant output.
You may also start generation earlier and explain the grammar while it runs.

## A direct command, without the menu

```powershell
.\.venv\Scripts\python.exe terminal_demo.py --offline --action generate --prompt "Generate one BibTeX book entry for a fictional book titled Grammar Lab by Alex Rivera, published in 2025." --output results/my-video-run.json
```

This deliberately fictional example tests structure and task fit without implying
that an invented citation is a verified publication. Change the prompt yourself;
the implementation is not restricted to the supplied examples. Show whatever the
model actually produces, including failures or ignored details.

## What demonstrates understanding

- Explain why recursion handles arbitrary nesting while one flat text pattern does not.
- Distinguish next-token filtering from final parsing and from post-generation repair.
- Demonstrate a deliberate invalid input, not just successful examples.
- Show the boundary spectrum and distinguish a tested point from a proven limit.
- Explain why stripping fences fixes the observed unconstrained outputs, and why
  that does not repair malformed BibTeX in general.
- Explain that the grammar does not check publication existence, topic relevance,
  required bibliographic fields, or macro definitions.
- Describe your actual contribution, what AI assisted with, and what you tested
  and verified yourself. Follow the lab's disclosure rules. A video cannot establish
  independent authorship merely by showing a terminal or dashboard.

This is an outline for a technical demonstration, not a script to memorize or a
claim that the repository is production-ready.
