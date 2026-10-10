"""Example questions for the ask page: the AskBench questions (scored against Claude's references) and the
catalogue in docs/questions.md."""

SUGGESTIONS = [
    {"group": "Prisons and court debt (AskBench)", "questions": [
        {"id": "court_debt", "text": "I can't afford to pay my court fines, costs or restitution. Can I get a payment "
                                     "plan, a reduction or waiver, or do community service instead, and what happens "
                                     "if I miss payments?"},
        {"id": "prison_wages", "text": "If I work while I'm incarcerated, in a prison job or on work release, how is my "
                                       "pay set, what can the state deduct from my earnings and in what order, and what "
                                       "do I get back when I'm released?"},
        {"id": "pretrial_clock", "text": "If I'm held in jail awaiting trial, how long can I be held before I must be "
                                         "indicted and tried, and what happens if that deadline passes?"},
        {"id": "record_sealing", "text": "How do I get my criminal record sealed or expunged, how long do I have to "
                                         "wait, and what does it cost?"},
        {"id": "license_conviction", "text": "Can a state licensing board deny me an occupational license because of a "
                                             "criminal conviction, and how can I challenge the denial?"},
        {"id": "phone_commissary", "text": "Who sets the prices of phone calls, video visits and commissary items in "
                                           "prisons and jails, and can the facility or sheriff keep a commission?"},
    ]},
    {"group": "Everyday questions", "questions": [
        {"text": "Do I need a building permit for a deck or a shed, and how do I get one?"},
        {"text": "My property assessment went up. How do I appeal it, and what is the deadline?"},
        {"text": "My landlord won't make repairs. What can I do, and can I withhold rent?"},
    ]},
    {"group": "Records and redaction work", "questions": [
        {"text": "What can a public body charge for records, and can the fees be waived?"},
        {"text": "My records request was denied or the deadline passed. How do I appeal?"},
        {"text": "What personal information must be redacted before a document is filed in court?"},
    ]},
    {"group": "For city and county staff", "questions": [
        {"text": "We received a records request. How long do we have to respond, and when can we extend?"},
        {"text": "When can a public body hold a closed meeting, and what notice is required?"},
        {"text": "When does a purchase need competitive bidding instead of informal quotes?"},
    ]},
]
