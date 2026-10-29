/* Real Lark parsing in a browser worker; no Qwen inference or Python server. */
let runtime;
const indexURL = 'https://cdn.jsdelivr.net/pyodide/v0.27.7/full/';
self.onmessage = async ({data}) => {
  const {id, action, grammar, source} = data;
  try {
    if (action === 'init') {
      importScripts(indexURL + 'pyodide.js');
      runtime = await loadPyodide({indexURL});
      await runtime.loadPackage('micropip');
      await runtime.runPythonAsync('import micropip\nawait micropip.install("lark==1.2.2")');
      runtime.globals.set('bibtex_grammar', grammar);
      runtime.runPython(`
import json, re
from lark import Lark, Tree, UnexpectedInput
bibtex_parser = Lark(bibtex_grammar, start='start', parser='lalr', lexer='basic')

def bounded_tree(root):
    lines, pending = [], [(root, 0)]
    while pending and len(lines) < 160:
        node, depth = pending.pop()
        if isinstance(node, Tree):
            lines.append('  ' * min(depth, 20) + str(node.data))
            if depth < 20:
                pending.extend((child, depth + 1) for child in reversed(node.children))
            else:
                lines.append('  ' * 20 + '[deeper nodes omitted]')
        else:
            lines.append('  ' * min(depth, 20) + repr(str(node)[:120]))
    if pending:
        lines.append('[remaining nodes omitted]')
    return '\\n'.join(lines)

def assess(text):
    try:
        tree = bibtex_parser.parse(text)
        return True, None, bounded_tree(tree)
    except UnexpectedInput as error:
        return False, str(error)[:6000], None

def validate_browser(text):
    if len(text) > 20000:
        raise ValueError('Use at most 20,000 characters in this editor.')
    valid, error, tree = assess(text)
    fence = re.fullmatch(r'\\s*' + '\x60' * 3 + r'(?:bibtex)?[ \\t]*\\r?\\n(.*?)\\r?\\n' + '\x60' * 3 + r'\\s*', text, re.S | re.I)
    extracted = fence.group(1) if fence else text
    return json.dumps(dict(raw_valid=valid, raw_error=error, tree=tree,
                           fence_removed=bool(fence), extracted_valid=assess(extracted)[0]))
`);
      self.postMessage({id, result: {ready: true, parser: 'Lark 1.2.2'}});
      return;
    }
    if (!runtime) throw Error('Lark has not finished loading.');
    runtime.globals.set('bibtex_source', source);
    const result = JSON.parse(runtime.runPython('validate_browser(bibtex_source)'));
    self.postMessage({id, result});
  } catch (error) {
    self.postMessage({id, error: String(error.message || error)});
  }
};
