"""lexflow.resolve: local models settle the Glass Database's open Wikidata questions.

The Glass Database's migration to its wiki (glass.wikibase.cloud) ends each staged item's Wikidata lookup in one
of a few states: *matched* (one candidate passed its narrow rules), *none*, or *unsure* (namesakes, a shortened
name, nothing in a description that says which one).  The unsure rows are a queue of small, well-posed
questions, "is this record the same thing as one of these Wikidata items?", with the candidates already
found.  That is work a local model can do with the evidence in front of it, and work that a benchmark can
measure, because the rows a person has already decided (and the ones the rules settled) are a gold set.

Pieces:

* ``source``   the queue itself, read over the Glass Database's public API; decisions and suggestions go back
               through its admin route with an API key.
* ``evidence`` what the judge reads: the record's own statements, each candidate's Wikidata facts and English
               Wikipedia summary, and web search snippets through SearXNG (the ``search`` profile).  Cached
               in the store, so a second model reads the same evidence as the first.
* ``judge``    the prompt, the answer's shape (``verdict``, ``confidence``, ``because``), and the sanity checks
               that no model is trusted on (a dead namesake, a candidate that is not among the candidates).
* ``bench``    ResolveBench, in AskBench's idiom: arms are models, rows are stored with a version hash of this
               code, the summary says how often each model is right, how much of the queue it would settle at
               a confidence threshold, and how often those settled answers are right (the number that has to
               reach 95% before a model's answers are applied without a person).  The live run uses the same
               judge on the open queue: a panel of models, a consensus, a suggestion written back for the
               reviewer, and (only when asked) a decision applied.
* ``api``      the dashboard's Resolve page.

Every model call goes through the compute pool (``lexflow/compute``): the models named for a run are spread over
the nodes that have them, so adding a machine is one line of ``LEXFLOW_LLM_NODES`` or a peer in the overlay's
compute group, and nothing here changes.
"""
