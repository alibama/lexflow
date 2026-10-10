"""How answers are scored.  Every number here can be changed from the dashboard (Method page).

confidence = w_state * state_score + w_local * local_score + w_contact * contact_score

* state_score   - from the tier of the state process model (``found`` is scaled by how sure
                  the locator is that it found the right law);
* local_score   - local ordinances found in LOCUS (a local *model* would score higher, but
                  none are built yet);
* contact_score - the best contact level the government has for that question.
"""
from __future__ import annotations

import copy
import json

from ..store import db

TIERS = ["none", "found", "single", "agreed", "reviewed"]
TIER_LABEL = {
    "reviewed": "Checked by Claude or a person",
    "agreed": "Two independent extractions agree",
    "single": "One extraction",
    "found": "Law found, no steps yet",
    "none": "No state law found",
}
STAGES = ["located", "text", "extracted", "cross_checked", "compiled", "validated", "reviewed", "published"]
STAGE_LABEL = {
    "located": "Law located", "text": "Text loaded", "extracted": "Facts extracted",
    "cross_checked": "Cross-checked", "compiled": "BPMN/DMN compiled", "validated": "Checks pass",
    "reviewed": "Reviewed", "published": "Published",
}
CONTACT_LABEL = {
    "page": "Records or licence page / named contact", "direct": "Email or phone",
    "website": "Website only", "postal": "Mailing address only", "none": "No contact",
}

DEFAULTS = {
    "weights": {
        "records": {"state": 0.6, "local": 0.1, "contact": 0.3},
        "business": {"state": 0.45, "local": 0.35, "contact": 0.2},
    },
    "tier_score": {"reviewed": 1.0, "agreed": 0.8, "single": 0.5, "found": 0.3, "none": 0.0},
    "contact_score": {"page": 1.0, "direct": 0.6, "website": 0.35, "postal": 0.15, "none": 0.0},
    "local_found_score": 0.6,
    "local_researched_score": {"verified": 1.0, "unverified": 0.8},
    "agreement_threshold": 0.6,
}


def get(con) -> dict:
    m = copy.deepcopy(DEFAULTS)
    stored = db.loads(db.scalar(con, "SELECT value FROM settings WHERE key='method'"), {})
    for k, v in stored.items():
        if isinstance(v, dict) and isinstance(m.get(k), dict):
            for k2, v2 in v.items():
                if isinstance(v2, dict) and isinstance(m[k].get(k2), dict):
                    m[k][k2].update(v2)
                else:
                    m[k][k2] = v2
        else:
            m[k] = v
    return m


def save(con, value: dict) -> dict:
    con.execute("INSERT INTO settings(key, value, updated_at) VALUES ('method', ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                (json.dumps(value), db.now()))
    con.commit()
    return get(con)


def describe() -> dict:
    return {"tiers": TIERS, "tier_label": TIER_LABEL, "stages": STAGES, "stage_label": STAGE_LABEL,
            "contact_label": CONTACT_LABEL}
