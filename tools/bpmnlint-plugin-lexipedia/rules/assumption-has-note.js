const { sources, attr, children, localName } = require('./util');

/** Elements a modeller added without textual support must say why. */
module.exports = function() {
  function check(node, reporter) {
    for (const s of sources(node)) {
      const grounding = attr(s, 'grounding');
      if (grounding === 'assumed' || grounding === 'implied') {
        const hasNote = children(s).some(c => localName(c) === 'note' && (c.$body || '').trim());
        if (!hasNote && grounding === 'assumed') {
          reporter.report(node.id, `Assumed element cites ${attr(s, 'citation')} without a lex:note explaining the assumption`);
        }
      }
    }
  }
  return { check };
};
