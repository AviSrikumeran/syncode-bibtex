"""Parse BibTeX examples and generate citations with the same grammar."""

import argparse
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path

from lark import Lark, UnexpectedInput


ROOT = Path(__file__).resolve().parent
GRAMMAR_PATH = ROOT / 'bibtex.lark'
PROMPTS = (
    'Generate one BibTeX article entry for a paper about LLM security.',
    'Generate one BibTeX inproceedings entry for a conference paper by Smith and Johnson.',
    'Generate one BibTeX book entry for Reinforcement Learning by Sutton and Barto.',
)


def load_parser():
    return Lark(GRAMMAR_PATH.read_text(encoding='utf-8'), start='start', parser='lalr', lexer='basic')


def validate(parser, source):
    try:
        parser.parse(source)
    except UnexpectedInput as error:
        return False, str(error)
    return True, None


def parsing_demo(parser):
    examples = (
        ('article', '@article{smith2024,author={John Smith},title={A Study},year=2024}'),
        ('mixed fields', '@book{sutton,title="Reinforcement Learning",author={Sutton and Barto}}'),
        ('multiple entries', '@misc{a,title={One}} @techreport{b,title={Two}}'),
        ('40 nested groups', '@article{deep,title={' + '{' * 40 + 'Nested' + '}' * 40 + '}}'),
        ('malformed input', '@article{broken,title={Unfinished}'),
    )
    results = []
    for name, source in examples:
        valid, error = validate(parser, source)
        expected = name != 'malformed input'
        passed = valid == expected
        print(f'{"PASS" if passed else "FAIL"}: {name} ({"accepted" if valid else "rejected"})')
        results.append(dict(name=name, source=source, valid=valid, expected_valid=expected,
                            passed=passed, error=error))
    return results


def generate(parser, args):
    # Keep the parser-only demonstration independent of the model dependencies.
    import torch
    os.environ.setdefault('SYNCODE_CACHE', (ROOT / '.cache' / 'syncode').as_posix() + '/')
    from syncode import Grammar, SyncodeLogitsProcessor
    from transformers import AutoModelForCausalLM, AutoTokenizer, StoppingCriteria, StoppingCriteriaList

    torch.manual_seed(args.seed)
    torch.set_num_threads(args.threads)
    tokenizer = AutoTokenizer.from_pretrained(args.model, revision=args.revision,
                                             cache_dir=ROOT / '.cache' / 'huggingface')
    model = AutoModelForCausalLM.from_pretrained(
        args.model, revision=args.revision, cache_dir=ROOT / '.cache' / 'huggingface', torch_dtype=torch.float32,
    ).to('cpu').eval()

    class CompleteCitation(StoppingCriteria):
        def __init__(self, prompt_length):
            self.prompt_length = prompt_length

        def __call__(self, input_ids, scores, **kwargs):
            text = tokenizer.decode(input_ids[0, self.prompt_length:], skip_special_tokens=True)
            return validate(parser, text)[0]

    print('Building SynCode token masks...', flush=True)
    processor = SyncodeLogitsProcessor(
        grammar=Grammar(GRAMMAR_PATH.read_text(encoding='utf-8')), tokenizer=tokenizer,
        parse_output_only=True, mode=args.mode, dev_mode=True,
    )
    records = []
    for prompt in PROMPTS:
        messages = [
            {'role': 'system', 'content': 'Return only one complete BibTeX citation. No explanation or Markdown. Keep fields short.'},
            {'role': 'user', 'content': prompt},
        ]
        rendered = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(rendered, return_tensors='pt')
        modes = ('unconstrained', 'constrained') if args.compare else ('constrained',)
        for mode in modes:
            processors = []
            if mode == 'constrained':
                processor.reset()
                processors = [processor]
            with torch.inference_mode():
                output = model.generate(
                    **inputs, logits_processor=processors,
                    stopping_criteria=StoppingCriteriaList([CompleteCitation(inputs.input_ids.shape[1])]),
                    max_new_tokens=args.max_new_tokens, do_sample=False,
                    pad_token_id=tokenizer.eos_token_id,
                )
            source = tokenizer.decode(output[0, inputs.input_ids.shape[1]:], skip_special_tokens=True)
            valid, error = validate(parser, source)
            print(f'\n{mode}: {prompt}\n{source}\nLark validation: {"PASS" if valid else "FAIL"}', flush=True)
            records.append(dict(prompt=prompt, mode=mode, output=source, valid=valid, error=error,
                                new_tokens=output.shape[1] - inputs.input_ids.shape[1]))
    return records, model.config._commit_hash


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--parse-only', action='store_true', help='Run offline examples without loading a model')
    cli.add_argument('--compare', action='store_true', help='Also generate without grammar constraints')
    cli.add_argument('--model', default='Qwen/Qwen2.5-0.5B-Instruct')
    cli.add_argument('--revision', default='main', help='Model revision; use the saved commit hash for reproduction')
    cli.add_argument('--mode', choices=('grammar_mask', 'grammar_strict'), default='grammar_mask')
    cli.add_argument('--max-new-tokens', type=int, default=256)
    cli.add_argument('--seed', type=int, default=0)
    cli.add_argument('--threads', type=int, default=4)
    cli.add_argument('--output', type=Path, help='Save actual inputs, outputs, and validation results as JSON')
    args = cli.parse_args()
    parser = load_parser()
    examples = parsing_demo(parser)
    generations, revision = ([], None) if args.parse_only else generate(parser, args)
    report = dict(model=None if args.parse_only else args.model, seed=args.seed, mode=args.mode,
                  revision=revision, grammar_sha256=hashlib.sha256(GRAMMAR_PATH.read_bytes()).hexdigest(),
                  versions={package: version(package) for package in ('lark',)} if args.parse_only else
                  {package: version(package) for package in ('lark', 'syncode', 'torch', 'transformers')},
                  max_new_tokens=args.max_new_tokens, examples=examples, generations=generations)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    passed = all(example['passed'] for example in examples)
    passed = passed and all(record['valid'] for record in generations if record['mode'] == 'constrained')
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
