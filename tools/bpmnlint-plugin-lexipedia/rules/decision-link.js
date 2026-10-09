const { is } = require('bpmnlint-utils');
const { extValues, localName } = require('./util');

/** Business rule tasks must name the DMN decision they evaluate. */
module.exports = function() {
  function check(node, reporter) {
    if (!is(node, 'bpmn:BusinessRuleTask')) return;
    const attrs = node.$attrs || {};
    const camunda = Object.keys(attrs).some(k => k.endsWith(':decisionRef') && attrs[k]);
    const spiff = extValues(node).some(v => localName(v) === 'calledDecisionId');
    if (!camunda && !spiff) reporter.report(node.id, 'Business rule task does not reference a DMN decision');
  }
  return { check };
};
