"""The compute pool: the model servers (Ollama nodes) lexflow can send work to (docs/compute.md).

Nothing here runs unless ``LEXFLOW_LLM_NODES`` or ``LEXFLOW_OVERLAY`` is set: with neither, every call goes
straight to ``OLLAMA_URL`` as before and ``data/compute.db`` is not touched.

* ``nodes``   - the node list (``data/compute.db``, this copy's own, never synced), the environment parser, the
                URL allow-list;
* ``health``  - read-only checks of each node (``/api/version``, ``/api/tags``, ``/api/ps``, a status URL) with
                back-off, and the poller thread;
* ``pool``    - the dispatcher: a node that has the model and a free slot, failover, the ``calls`` log;
* ``overlay`` - NetBird (and a Headscale stub) as the source of the node list;
* ``migrate`` - the one-time relabel of benchmark rows made before the pool existed;
* ``api``     - the ``/api/compute/*`` endpoints and the shape the Compute page reads.
"""
from __future__ import annotations

from .nodes import pool_on, db_path  # noqa: F401
