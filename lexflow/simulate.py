"""Drive Lexipedia models through SpiffWorkflow to prove they execute as drawn.

Canonical files stay standards-first; :func:`prepare` writes the engine
dialect (quoted ISO timers, Python DMN cells) next to them for simulation.
"""
from __future__ import annotations

from pathlib import Path

from SpiffWorkflow.spiff.specs.event_definitions import MessageEventDefinition  # spiff parser builds this subclass; Spiff matches events by exact class
from SpiffWorkflow.bpmn.util.event import BpmnEvent
from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.util.task import TaskState

from .validate import spiff_dialect, spiff_parser


def _patch_spiff():
    """SpiffWorkflow 3.2.0 bug: NodeParser._resolve_data_object_ref never advances past the
    parent scope (``current = self.process_parser.parent``), so a data object declared two
    or more scopes up (process > sub-process > sub-process) hangs the parser forever.
    Upstream fix: ``current = current.parent``."""
    from SpiffWorkflow.bpmn.parser.node_parser import NodeParser

    def _resolve_data_object_ref(self, ref):
        if ref is None:
            return None
        current = self.process_parser
        while current is not None:
            data_obj = current.spec.data_objects.get(ref.get("dataObjectRef"))
            if data_obj is not None:
                return data_obj
            current = current.parent
        return None

    NodeParser._resolve_data_object_ref = _resolve_data_object_ref


_patch_spiff()


class RecordStore:
    """Factory for a minimal in-memory data store (SpiffWorkflow requires a class per store name)."""

    @staticmethod
    def for_name(name: str):
        from SpiffWorkflow.bpmn.specs.data_spec import BpmnDataStoreSpecification

        class _Store(BpmnDataStoreSpecification):
            records: dict = {}

            def get(self, my_task):
                my_task.data[self.bpmn_id] = _Store.records.get(self.bpmn_id, {"store": name})

            def set(self, my_task):
                if self.bpmn_id in my_task.data:
                    _Store.records[self.bpmn_id] = my_task.data.pop(self.bpmn_id)

        _Store.__name__ = f"RecordStore_{abs(hash(name))}"
        return _Store


def register_data_stores(bpmn_files: list[Path]):
    from lxml import etree
    from SpiffWorkflow.spiff.parser.process import SpiffBpmnParser
    for f in bpmn_files:
        for ds in etree.parse(str(f)).iter("{http://www.omg.org/spec/BPMN/20100524/MODEL}dataStore"):
            SpiffBpmnParser.DATA_STORE_CLASSES.setdefault(ds.get("name"), RecordStore.for_name(ds.get("name")))


def prepare(bpmn: Path, workdir: Path, timer_override: dict[str, str] | None = None) -> Path:
    workdir.mkdir(parents=True, exist_ok=True)
    out = workdir / bpmn.name.replace(".bpmn", ".spiff.bpmn")
    out.write_text(spiff_dialect(bpmn.read_text(), timer_override))
    return out


class Sim:
    def __init__(self, bpmn_files: list[Path], dmn_files: list[Path], process_id: str):
        register_data_stores(bpmn_files)
        self.parser = spiff_parser(bpmn_files, dmn_files)
        spec = self.parser.get_spec(process_id)
        subs = self.parser.get_subprocess_specs(process_id)
        self.wf = BpmnWorkflow(spec, subs)
        self.step()

    def step(self):
        self.wf.do_engine_steps(did_complete_task=self._fill_outputs)
        refresh = getattr(self.wf, "refresh_timers", None) or self.wf.refresh_waiting_tasks
        refresh()
        self.wf.do_engine_steps(did_complete_task=self._fill_outputs)

    @staticmethod
    def _outputs(task) -> list[str]:
        specs = getattr(task.task_spec, "data_output_associations", None) or []
        return [getattr(d, "bpmn_id", None) or getattr(d, "name", "") for d in specs]

    def _fill_outputs(self, task):
        """SpiffWorkflow treats data objects as variables; stand in for documents a step produces."""
        for name in self._outputs(task):
            task.data.setdefault(name, {"produced_by": self._id(task)})

    @staticmethod
    def _id(task) -> str:
        return getattr(task.task_spec, "bpmn_id", None) or task.task_spec.name

    def ready(self) -> list[str]:
        return [self._id(t) for t in self.wf.get_tasks(state=TaskState.READY, manual=True)]

    def waiting(self) -> list[str]:
        return [self._id(t) for t in self.wf.get_tasks(state=TaskState.WAITING)]

    def complete(self, bpmn_id: str, **data):
        task = next((t for t in self.wf.get_tasks(state=TaskState.READY, manual=True) if self._id(t) == bpmn_id), None)
        if task is None:
            raise AssertionError(f"{bpmn_id} is not ready; ready={self.ready()} waiting={self.waiting()}")
        task.data.update(data)
        for name in self._outputs(task):
            task.data.setdefault(name, {"produced_by": bpmn_id})
        task.run()
        self.step()

    def message(self, name: str, at: str | None = None, **data):
        """Deliver a message; optionally seed data on the catching task ``at``."""
        if at:
            for t in self.wf.get_tasks(state=TaskState.WAITING | TaskState.READY):
                if self._id(t) == at:
                    t.data.update(data)
        self.wf.catch(BpmnEvent(MessageEventDefinition(name), {}))
        self.step()

    def completed(self) -> list[str]:
        return [self._id(t) for t in self.wf.get_tasks(state=TaskState.COMPLETED)]

    def data(self) -> dict:
        last = self.wf.get_tasks(state=TaskState.COMPLETED)
        merged: dict = {}
        for t in last:
            merged.update(t.data)
        return merged

    @property
    def done(self) -> bool:
        return self.wf.is_completed()
