const { is } = require('bpmnlint-utils');

const DURATION = /^-?P(?!$)(\d+Y)?(\d+M)?(\d+W)?(\d+D)?(T(?=\d)(\d+H)?(\d+M)?(\d+(\.\d+)?S)?)?$/;
const CYCLE = /^R\d*\/.+$/;
const DATE = /^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}(:\d{2})?(Z|[+-]\d{2}:\d{2})?)?$/;

function unquote(s) { return (s || '').trim().replace(/^"(.*)"$/, '$1'); }

/** Timer values must be ISO 8601 so engines and readers agree on the deadline. */
module.exports = function() {
  function check(node, reporter) {
    if (!is(node, 'bpmn:TimerEventDefinition')) return;
    const d = node.timeDuration && unquote(node.timeDuration.body);
    const t = node.timeDate && unquote(node.timeDate.body);
    const c = node.timeCycle && unquote(node.timeCycle.body);
    if (!d && !t && !c) {
      reporter.report(node.id, 'Timer has no timeDuration/timeDate/timeCycle');
      return;
    }
    if (d && !DURATION.test(d)) reporter.report(node.id, `timeDuration "${d}" is not an ISO 8601 duration`);
    if (t && !DATE.test(t)) reporter.report(node.id, `timeDate "${t}" is not an ISO 8601 date-time`);
    if (c && !CYCLE.test(c)) reporter.report(node.id, `timeCycle "${c}" is not an ISO 8601 repeating interval`);
  }
  return { check };
};
