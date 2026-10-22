"""From the chosen sections to an answer that never says more than the law's own words.

* ``evidence``  - the clauses most likely to answer the question, as numbered verbatim quotes [Q1..Qn]: scored by
                  meaning (embedding similarity to the question), by the question's concepts, and by "slots" the
                  question asks for (fees and caps, deadlines, offices, orders of priority).
* ``process``   - for how-do-I questions, the learned selector's steps (exact quotes), compiled to BPMN.
* ``summarise`` - optionally, a local model writes two to six plain sentences, each citing quote ids.  Every claim
                  is checked: its ids must exist, and every number it states must appear in a quote it cites.
                  Claims that fail are dropped, never repaired.
* ``deterministic answer`` - always: the governing sections, the steps, the key quotes.  It is the answer when no
                  model is available and the fallback when the model's claims do not check out.
"""
from __future__ import annotations

import re

from ..extract.segment import Clause, segment
from .plan import Plan

SLOTS = {
    "fee": re.compile(r"\$\s?\d|\b\d[\d,.]* (?:dollars|cents)\b|\bpercent\b|%|\bfee|\bcharge|\bcost|\bcommission|"
                      r"\bsurcharge|\brate\b|\bprice", re.I),
    "cap": re.compile(r"\bnot (?:to )?exceed|\bmaximum\b|\bup to\b|\bno more than\b|\blesser of\b|\bgreater of\b|"
                      r"\bat least\b|\bminimum\b|\bno less than\b", re.I),
    # deadlines come from the segmenter's parsed time limits (Clause.deadline), not from a loose pattern here:
    # "within any local correctional facility" is not a time limit
    "order": re.compile(r"order of priority|following order|in the order|first,|second,|thereafter|priority", re.I),
    "office": re.compile(r"\b(clerk|court|judge|sheriff|director|department|board|commission|officer|custodian|"
                         r"secretary|superintendent|warden|attorney|magistrate)\b", re.I),
}
NUMBER = re.compile(r"\$?\d[\d,]*(?:\.\d+)?%?")
CITES = re.compile(r"\s*\[(?:\s*Q\d+\s*[,;]?)+\s*\]", re.I)                 # [Q2], [Q1, Q4]
SECTION = re.compile(r"(?:§+|\bsections?\b)\s*(\d[\w.:/\-]*)", re.I)          # § 19.2-354, Section 4-203
WORDS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen "
                                    "fourteen fifteen sixteen seventeen eighteen nineteen".split())}
WORDS.update({w: 10 * i for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split(), 2)})
SCALES = {"hundred": 100, "thousand": 1000, "million": 10 ** 6}


CJK = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff\u3005-\u3007]")


def is_cjk(text: str) -> bool:
    """Whether a text is mostly Japanese (or Chinese, Korean): more than a fifth of its first 400 characters."""
    head = (text or "")[:400]
    return bool(head) and len(CJK.findall(head)) * 5 > len(head)


def _terms(plan: Plan) -> list[re.Pattern]:
    """One pattern per concept: English words from a word boundary (``\\bexpung``), CJK terms anywhere (Japanese
    has no word boundaries), two characters being enough for a CJK term (``聴聞``)."""
    out = []
    for g in plan.groups:
        latin = [re.escape(t.lower()) for t in g if len(t) > 2 and not CJK.search(t)]
        cjk = [re.escape(t) for t in g if CJK.search(t) and len(t) >= 2]
        parts = ([r"\b(?:" + "|".join(latin) + ")"] if latin else []) + (["(?:" + "|".join(cjk) + ")"] if cjk else [])
        if parts:
            out.append(re.compile("|".join(parts), re.I))
    return out


_HEAD_LINE = re.compile(r"^§ (\S+)\. ?(.*)$")
_ITEM_LABEL = re.compile(r"^([０-９0-9]+|[一二三四五六七八九十百]+|[イロハニホヘトチリヌルヲワカヨタレソツネナラム])　")


def cjk_clauses(text: str, min_chars: int = 8) -> list[Clause]:
    """Clauses of a Japanese text as japan.py writes articles: one paragraph or item per line (``２　...``,
    ``　一　...``), a long line split at each 。 outside brackets; ``§ <citation>. <title>`` lines (the joined text
    of several articles, statutes.combined_text) name the section of what follows.  Each clause is the source's own
    characters, so a quote is checked verbatim."""
    out: list[Clause] = []
    section, pos, para = None, 0, 0
    for line in text.split("\n"):
        start, pos = pos, pos + len(line) + 1
        m = _HEAD_LINE.match(line)
        if m and CJK.search(m.group(1)):
            section = m.group(1)
            continue
        body = line.strip(" \t\u3000")
        if not body:
            continue
        para += 1
        lab = _ITEM_LABEL.match(body)
        off = start + line.index(body)
        depth, cut, pieces = 0, 0, []
        for i, ch in enumerate(body):
            if ch in "（「『(":
                depth += 1
            elif ch in "）」』)":
                depth = max(0, depth - 1)
            elif ch == "。" and depth == 0 and len(body) > 120:
                pieces.append((cut, body[cut:i + 1]))
                cut = i + 1
        if cut < len(body):
            pieces.append((cut, body[cut:]))
        for k, (o, sent) in enumerate(pieces):
            if len(sent.strip()) < min_chars:
                continue
            out.append(Clause(id=f"c{len(out) + 1}", label=lab.group(1) if lab else "", text=sent, start=off + o,
                              paragraph=para, section=section))
    return out


ASKS_FOR = {   # what a question asks for -> the slot whose clauses it most needs
    "deadline": re.compile(r"\bhow long|\bdeadline|\bwhen\b|\bdays?\b|\bwait|\btime limit|\bhow soon|\bclock", re.I),
    "fee": re.compile(r"\bcost|\bfee|\bcharge|\bpay\b|\bprice|\bhow much|\bcommission|\bwage|\bdeduct|\bafford", re.I),
    "office": re.compile(r"\bwho\b|\bwhich (office|agency|court|board)|\bwhere do i", re.I),
    "order": re.compile(r"\border\b|\bpriority|\bfirst\b", re.I),
    "cap": re.compile(r"\bmaximum|\blimit|\bcap\b|\bat most|\bhow much", re.I),
}


def asks_for(question: str) -> list[str]:
    return [k for k, pat in ASKS_FOR.items() if pat.search(question)]


def evidence(question: str, plan: Plan, text: str, embedder=None, k: int | None = None,
             default_section: str | None = None) -> list[dict]:
    """The clauses that best answer the question, as quotes with ids, in the order they appear in the law: at
    least one from every section, then the best by meaning, concepts and the slots the question asks for.
    ``k`` grows with the number of sections; ``default_section`` names the section when the text is a single one
    (its clauses carry no section)."""
    cjk = is_cjk(text)
    clauses = cjk_clauses(text) if cjk else [c for c in segment(text) if len(c.text.split()) >= 5]
    if not clauses:
        return []
    if cjk:
        embedder = None             # the embedding model is English; Japanese clauses rank by the question's terms
    n_sections = len({c.section for c in clauses})
    k = k or max(8, min(24, 6 + 2 * n_sections))
    wanted = set(asks_for(question))
    sims = [0.0] * len(clauses)
    if embedder is not None:
        try:
            q = embedder([question], prefix="search_query")
            d = embedder([c.text for c in clauses], prefix="search_document")
            sims = [float(x) for x in (d @ q.T)[:, 0]]
        except Exception:  # noqa: BLE001 - no embedding server: words only
            pass
    terms = _terms(plan)
    scored = []
    for c, sim in zip(clauses, sims):
        hits = sum(1 for t in terms if t.search(c.text))
        slots = [name for name, pat in SLOTS.items() if pat.search(c.text)]
        if c.deadline and "deadline" not in slots:
            slots.append("deadline")
        s = sim + 0.12 * hits + 0.04 * len(slots) + 0.08 * len(wanted & set(slots)) \
            + (0.05 if c.modal else 0.0) + (0.05 if c.deadline else 0.0)
        scored.append((s, c, slots, hits))
    scored.sort(key=lambda x: -x[0])
    keep, seen_sections = [], set()
    for item in scored:                              # the best clause of every section first
        if item[1].section not in seen_sections:
            keep.append(item)
            seen_sections.add(item[1].section)
    for item in scored:
        if len(keep) >= k:
            break
        if item not in keep:
            keep.append(item)
    keep.sort(key=lambda x: x[1].start)
    return [{"id": f"Q{i}", "section": c.section or default_section, "label": c.label, "text": c.text, "score": round(s, 3),
             "slots": slots, "concepts": hits, "deadline": c.deadline}
            for i, (s, c, slots, hits) in enumerate(keep, 1)]


def relevance(question: str, plan: Plan, clauses: list[Clause], embedder=None) -> list[float]:
    """How much each clause is about the question: meaning (cosine to the question) and the question's concepts."""
    sims = [0.0] * len(clauses)
    if embedder is not None and clauses:
        try:
            q = embedder([question], prefix="search_query")
            d = embedder([c.text for c in clauses], prefix="search_document")
            sims = [float(x) for x in (d @ q.T)[:, 0]]
        except Exception:  # noqa: BLE001 - no embedding server: concepts only
            pass
    terms = _terms(plan)
    return [s + 0.12 * sum(1 for t in terms if t.search(c.text)) for s, c in zip(sims, clauses)]


def process(clauses: list[Clause], qid: str, state: str, notes: list | None = None, *, question: str = "",
            plan: Plan | None = None, embedder=None) -> list[dict]:
    """Steps for a new question.  The learned selector knows what a step looks like (trained on every reference
    model) but not what this question is about, so each candidate's step score is weighed by its relevance to the
    question, and the number kept is the number of steps the scores expect (4 to 14)."""
    import numpy as np
    from ..extract import selector as SEL
    from ..extract import strategies as ST
    cands = SEL.wide_drafts(clauses, qid)
    if not cands:
        return []
    vectors = ST.config_vectors()
    emb = (SEL.tfidf() if vectors == "tfidf" else SEL.Combo(SEL.tfidf(), SEL.Embedder()) if vectors == "combo"
           else SEL.Embedder() if vectors == "embed" else None)
    sel = SEL.Selector(qid, state, emb, use_embeddings=emb is not None)
    if sel.emb is None and vectors in ("embed", "combo"):
        sel = SEL.Selector(qid, state, SEL.tfidf())
    if not sel.refs:
        return []
    sel = sel.fit()
    p = np.asarray(sel.predict(cands), dtype=float)
    rel = np.asarray(relevance(question, plan, [d["clause"] for d in cands], embedder), dtype=float) if plan \
        else np.zeros(len(cands))
    if rel.max() > rel.min():
        rel = (rel - rel.min()) / (rel.max() - rel.min())
    score = p * (0.3 + rel)
    k = int(max(4, min(14, round(float(p.sum())))))
    keep = [cands[i] for i in np.argsort(-score)[:k]]
    ST.assign_actors(keep, cands, sel, qid)
    if notes is not None:
        notes.append(f"{len(keep)} of {len(cands)} candidates kept (step score x relevance to the question; "
                     f"{len(sel.refs)} references)")
    return sorted(keep, key=lambda d: d["clause"].start)


SUMMARY_SYSTEM = """You answer a question about US state law using ONLY the numbered quotes from the statute.
Write 2 to 6 short claims in plain language. Every claim must cite the quote ids it rests on, like [Q2] or [Q1][Q4].
Copy numbers, amounts and time limits exactly as the quotes give them. Do not add anything the quotes do not say.
If the quotes do not answer the question, set status to not_found and give no claims."""
SUMMARY_SCHEMA = {"type": "object", "properties": {
    "status": {"type": "string", "enum": ["answered", "partial", "not_found"]},
    "claims": {"type": "array", "items": {"type": "object", "properties": {
        "text": {"type": "string"}, "quotes": {"type": "array", "items": {"type": "string"}}},
        "required": ["text", "quotes"]}}},
    "required": ["status", "claims"]}


def summarise(asker, question: str, place: str, quotes: list[dict], sections: list[dict]) -> dict:
    """A local model's plain-language claims, each checked against the quotes it cites.  The quotes are grouped
    under their section's heading, so a small model knows what each one is about without reading the section."""
    titles = {s["ref"]: (s.get("title") or "").strip() for s in sections}
    groups: dict[str, list[dict]] = {}
    for q in quotes:
        groups.setdefault(q["section"] or sections[0]["ref"], []).append(q)
    listing = "\n".join(
        f"§ {ref}" + (f" ({titles[ref][:90]})" if titles.get(ref) else "") + "\n"
        + "\n".join(f"[{q['id']}] {' '.join(q['text'].split()[:70])}" for q in qs)
        for ref, qs in groups.items())
    user = f"Question: {question}\nPlace: {place}\n\nQuotes from the statute:\n{listing}"
    r = asker.ask(SUMMARY_SYSTEM, user, SUMMARY_SCHEMA)
    return verify(r or {}, quotes)


def number(s: str) -> str:
    """A number as one comparable token: '$1,500.00' -> '1500', '2.50%' -> '2.5' ('1,50' is not '150')."""
    s = s.strip("$%").rstrip(".,")
    if re.fullmatch(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?", s):
        s = s.replace(",", "")
    return s.rstrip("0").rstrip(".") if "." in s else s


def spelled(text: str) -> set[str]:
    """The numbers a text writes in words, as digits: 'thirty' -> '30', 'one hundred and twenty-five' -> '125'."""
    out, total, cur, prev = set(), 0, None, ""
    for w in re.findall(r"[a-z]+", text.lower()) + [""]:
        v = WORDS.get(w)
        if cur is not None and (w in SCALES or (w == "and" and prev == "scale")
                                or (v is not None and (prev == "scale" or (prev == "tens" and v < 10)))):
            if w == "hundred":
                cur, prev = cur * 100, "scale"
            elif w in SCALES:
                total, cur, prev = total + cur * SCALES[w], 0, "scale"
            elif v is not None:
                cur, prev = cur + v, "tens" if v >= 20 else "unit"
            continue
        if cur is not None:
            out.add(str(total + cur))
        total, cur, prev = 0, v, "tens" if v is not None and v >= 20 else "unit"
    return out


def verify(reply: dict, quotes: list[dict]) -> dict:
    """Keep the claims whose quote ids exist and whose numbers all appear, as whole numbers, in a quote they cite
    (or its section's number).  A section number the quotes are listed under is not checked as an amount."""
    by_id = {q["id"]: q for q in quotes}
    sections = {str(q.get("section") or "").lower() for q in quotes} - {""}
    kept, dropped = [], []
    for c in reply.get("claims") or []:
        text = (c.get("text") or "").strip()
        ids = [m.upper() for i in (c.get("quotes") or []) if i for m in re.findall(r"Q\d+", str(i), re.I)]
        ids += [m.upper() for g in CITES.findall(text) for m in re.findall(r"Q\d+", g, re.I)]
        ids = [i for i in dict.fromkeys(ids) if i in by_id]
        text = CITES.sub("", text).strip()
        cited = " ".join(f"{by_id[i]['text']} {by_id[i].get('section') or ''}" for i in ids)
        have = {number(n) for n in NUMBER.findall(cited)} | spelled(cited)
        bare = SECTION.sub(lambda m: "" if m.group(1).rstrip(".,:;-").lower() in sections else m.group(0), text)
        numbers = [number(n) for n in NUMBER.findall(bare)]
        if not text or not ids:
            dropped.append({"text": text, "why": "cites no quote"})
        elif any(n and n not in have for n in numbers):
            dropped.append({"text": text, "why": "a number is not in the quotes it cites"})
        else:
            kept.append({"text": text, "quotes": ids})
    status = reply.get("status") if reply.get("status") in ("answered", "partial", "not_found") else None
    if kept and status == "not_found":
        status = "partial"
    return {"status": status or ("answered" if kept else "not_found"), "claims": kept, "dropped": dropped}


def _sec(ref: str | None) -> str:
    """``§ 2.2-3704``; a citation in its own script (``行政手続法第十三条``) without the section sign."""
    ref = ref or ""
    return ref if CJK.search(ref) else f"§ {ref}"


def markdown(question: str, place: str, sections: list[dict], quotes: list[dict], steps: list[dict],
             summary: dict | None, status: str, credit: str | None = None) -> str:
    """The answer as Markdown: summary (if any), governing law, steps, key quotes; ``credit`` is the source
    statement a licence asks for (PDL1.0's 出典 for Japan's law)."""
    L = [f"**{question}** — {place}", ""]
    if status == "not_found":
        L += ["lexflow did not find a statute section that clearly governs this. The answer may be in regulations, "
              "court rules, agency policy, contracts or local ordinances, which lexflow does not search yet.", ""]
    if summary and summary.get("claims"):
        L += ["**In short** (written by a local model from the quotes below; every claim cites them):", ""]
        L += [f"- {c['text']} " + " ".join(f"[{i}]" for i in c["quotes"]) for c in summary["claims"]] + [""]
    if sections:
        L += ["**Governing law**", ""] + [f"- [{s['citation']}]({s['url']}) — {s['title']}" if s.get("url") else
                                          f"- {s['citation']} — {s['title']}" for s in sections] + [""]
    if steps:
        L += ["**Steps** (each from the words of the law)", ""]
        for i, s in enumerate(steps, 1):
            dl = f", within {s['deadline']}" if s.get("deadline") else ""
            L.append(f"{i}. **{s['actor']}**: {s['action']}{dl} (§ {s['section']})")
        L.append("")
    if quotes:
        L += ["**Key provisions**", ""] + [f"- [{q['id']}] {_sec(q['section'])}{('(' + q['label'] + ')') if q.get('label') else ''}: "
                                           f"“{q['text']}”" for q in quotes] + [""]
    if credit:
        L += [f"_{credit}_", ""]
    L += ["_Information from the statute text, not legal advice. Machine answer: not reviewed._"]
    return "\n".join(L)
