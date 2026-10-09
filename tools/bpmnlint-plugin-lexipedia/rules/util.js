// Helpers for reading the lex: extension through bpmn-moddle's generic (untyped) elements.
const LEX = 'https://lexipedia.xyz/ns/lex/1.0';

function extValues(node) {
  return (node.extensionElements && node.extensionElements.values) || [];
}

function localName(el) {
  const t = el.$type || '';
  return t.includes(':') ? t.split(':').pop() : t;
}

function isLex(el, name) {
  if (localName(el) !== name) return false;
  const ns = el.$descriptor && el.$descriptor.ns && el.$descriptor.ns.uri;
  return !ns || ns === LEX || (el.$type || '').startsWith('lex:');
}

function children(el) {
  return el.$children || [];
}

function attr(el, name) {
  if (el[name] !== undefined) return el[name];
  if (el.$attrs && el.$attrs[name] !== undefined) return el.$attrs[name];
  return undefined;
}

function sources(node) {
  const out = [];
  for (const v of extValues(node)) {
    if (isLex(v, 'grounding')) {
      for (const s of children(v)) if (localName(s) === 'source') out.push(s);
    }
  }
  return out;
}

function lexChild(node, name) {
  return extValues(node).find(v => isLex(v, name));
}

module.exports = { extValues, localName, isLex, children, attr, sources, lexChild };
