const { isAny, is } = require('bpmnlint-utils');
const { sources } = require('./util');

/**
 * Every activity and every catching/throwing event that carries a trigger or
 * a deadline must cite the law (lex:grounding/lex:source).  Plain start/end
 * events and unnamed join gateways are exempt.
 */
module.exports = function() {
  function check(node, reporter) {
    const isActivity = isAny(node, ['bpmn:Task', 'bpmn:SubProcess', 'bpmn:CallActivity']);
    const isTypedEvent = isAny(node, ['bpmn:IntermediateCatchEvent', 'bpmn:BoundaryEvent', 'bpmn:IntermediateThrowEvent'])
      || (is(node, 'bpmn:StartEvent') && (node.eventDefinitions || []).length > 0);
    if (!isActivity && !isTypedEvent) return;
    if (sources(node).length === 0) {
      reporter.report(node.id, 'No legal grounding: add a lex:source citing the provision (or mark it grounding="assumed")');
    }
  }
  return { check };
};
