"""Retirement benefits: which programs apply to a person in a place, who runs each, the law that creates it, its
eligibility rules, how to apply and appeal, and how the state taxes it (docs/design/retirement-benefits.md).

* ``census``: the Census Bureau's Annual Survey of Public Pensions (system-level unit files, public domain) into
  ``pension_systems``, joined to the ``governments`` table by state and name into ``pension_coverage``.
* ``ground``: lexflow's match of every quote a benefits fixture holds, against the statute index
  (``lexflow.ask.index``) or the page the quote cites as lexflow's quote fetch read it (``municipal.quotes``).
* ``programs``: the fixtures under ``fixtures/benefits/``: the statewide systems' enabling statutes and bodies,
  the state auto-IRA programs, the states' income-tax treatment of retirement income, and the federal layer.
* ``lookup``: ``lookup(place, person)`` -> the programs that apply, and ``ask`` the "Who do I ask" style answer.
* ``research``: read-only helpers for writing the fixtures (search the index, print a section, read a page
  politely, check a quote).

Privacy: programs, bodies and office channels only (``lexflow.privacy``); no individual's data.  A person's own
facts (age, service, membership date) are inputs to a computation and are never stored or synced here.
"""
