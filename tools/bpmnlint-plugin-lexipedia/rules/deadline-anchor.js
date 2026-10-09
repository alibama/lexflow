const { is } = require('bpmnlint-utils');
const { lexChild, attr } = require('./util');

/** A legal deadline needs its anchor ("30 days after <what>") recorded in lex:deadline. */
module.exports = function() {
  function check(node, reporter) {
    if (!is(node, 'bpmn:Event')) return;
    const timers = (node.eventDefinitions || []).filter(d => is(d, 'bpmn:TimerEventDefinition'));
    if (!timers.length) return;
    const deadline = lexChild(node, 'deadline');
    if (!deadline || !attr(deadline, 'anchor')) {
      reporter.report(node.id, 'Timer has no lex:deadline anchor (what event starts the clock?)');
    }
  }
  return { check };
};
