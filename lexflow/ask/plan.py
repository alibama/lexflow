"""Turn a question in plain words into what the statute search needs.

* ``groups``: two to four concepts, each a list of words a state code would use for it ("expunge", "seal",
  "sealing"); synonyms are OR'ed, concepts AND'ed.  They come from a small legal thesaurus, and a local model
  can add the code's own vocabulary ("canteen" for "commissary", "inmate" for "prisoner").
* ``kind``: ``process`` (how do I ...: steps, actors, deadlines), ``facts`` (how much, what rate, what limit), or
  ``either``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

STOP = frozenset("""a an the of to in on for by with from at as is are was were be been being do does did doing
how what when where which who whom whose why can could should would will shall may might must i me my we our you
your they their it its this that these those there here get got getting go going make made want need needs any some
all each every about into out over under if or and not no yes than then so such very just also only own same other
state states local city county town law laws legal rule rules require required requirements process procedure
step steps someone somebody person people much many item items thing things kind kinds type types
lot lots often usually there's i'm can't don't set sets setting keep keeps kept take takes taken give gives
put puts let lets say says said know tell find use used able happen happens happened instead option options
whether anything something one ones because since""".split())

# words a code uses for the same thing; keys and values are matched as written (FTS5 stems them)
THESAURUS: dict[str, list[str]] = {
    "prison": ["prison", "correctional", "inmate", "prisoner", "penitentiary", "incarcerated", "confined"],
    "jail": ["jail", "local correctional", "regional jail", "inmate", "prisoner", "detention"],
    "inmate": ["inmate", "prisoner", "incarcerated", "offender", "confined"],
    "commissary": ["commissary", "canteen", "store", "stores"],
    "phone": ["telephone", "phone", "communication", "calling", "inmate telephone"],
    "wage": ["wage", "wages", "compensation", "pay", "earnings"],
    "work": ["work", "labor", "employment", "work release", "industries"],
    "fee": ["fee", "fees", "charge", "charges", "cost", "costs"],
    "fine": ["fine", "fines", "costs", "penalty", "assessment"],
    "pay": ["pay", "payment", "installment", "deferred payment"],
    "bail": ["bail", "bond", "pretrial release", "recognizance"],
    "parole": ["parole", "probation", "supervision", "post-release"],
    "probation": ["probation", "supervision", "parole"],
    "expunge": ["expunge", "expungement", "expunged", "seal", "sealing", "sealed"],
    "seal": ["seal", "sealing", "sealed", "expunge", "expungement"],
    "record": ["record", "records", "criminal history", "conviction"],
    "conviction": ["conviction", "convicted", "criminal history", "offense"],
    "criminal": ["criminal", "conviction", "convicted", "criminal history", "criminal record"],
    # what a board or agency does, and what a person does about it ("deny", "challenge" alone are rare words a
    # code spreads over many sections; with their synonyms they become one concept the search can require)
    "deny": ["deny", "denial", "denied", "refuse", "refusal", "disqualify"],
    "denial": ["deny", "denial", "denied", "refuse", "refusal", "disqualify"],
    "challenge": ["challenge", "appeal", "hearing", "review", "reconsideration"],
    "license": ["license", "licence", "licensure", "permit", "certificate", "registration"],
    "licence": ["license", "licence", "licensure", "permit", "certificate"],
    "permit": ["permit", "license", "certificate", "approval"],
    "building": ["building", "construction", "uniform statewide building code", "building code"],
    "business": ["business", "company", "corporation", "limited liability company", "entity"],
    "restitution": ["restitution", "reparation", "victim compensation"],
    "child": ["child", "children", "minor"],
    "support": ["support", "child support", "obligation"],
    "vote": ["vote", "voting", "voter", "registration", "franchise"],
    "landlord": ["landlord", "lessor", "rental", "residential tenancy"],
    "tenant": ["tenant", "lessee", "rental", "residential tenancy"],
    "evict": ["eviction", "unlawful detainer", "possession", "landlord and tenant"],
    "records": ["public records", "records", "information", "freedom of information"],
    "foia": ["freedom of information", "public records", "public information"],
    "redact": ["redact", "redaction", "redacted", "exempt", "withhold"],
    "zoning": ["zoning", "land use", "special use", "variance"],
    "food": ["food", "restaurant", "food establishment", "health permit"],
    "tax": ["tax", "taxes", "taxation", "license tax"],
    "id": ["identification", "identification card", "driver's license"],
    "reentry": ["reentry", "release", "discharge", "transition"],
    # court debt: the code's words for what a person means by "afford", "waive", "a payment plan"
    "afford": ["ability to pay", "unable to pay", "inability to pay", "indigent", "financial hardship"],
    "waiver": ["waive", "waiver", "remit", "remission", "suspend", "forgive"],
    "waive": ["waive", "waiver", "remit", "remission", "suspend"],
    "reduction": ["reduce", "reduction", "remit", "modify"],
    "installment": ["installment", "installments", "deferred payment", "time for payment", "payment plan"],
    "plan": ["installment", "installments", "deferred payment", "time for payment"],
    "service": ["community service", "community work", "service in lieu"],
    "indicted": ["indictment", "indicted", "grand jury", "speedy trial"],
    "trial": ["trial", "speedy trial", "brought to trial", "commencement of trial"],
    "custody": ["custody", "held in custody", "detained", "confinement", "jail"],
}
PHRASES = ["building permit", "public records", "criminal record", "child support", "work release", "payment plan",
           "community service", "occupational license", "licensing board", "speedy trial", "video visit",
           "business license", "occupational license", "pretrial release", "ability to pay", "community service",
           "inmate telephone", "freedom of information", "limited liability company", "certificate of occupancy",
           "food establishment", "driver's license", "identification card", "time served", "good conduct",
           "earned sentence credit", "sentence credit"]


def stem(w: str) -> str:
    """A crude stem for thesaurus lookups: 'expunged', 'expungement' -> 'expung'; 'prisons' -> 'prison'."""
    w = w.lower()
    for suf in ("ements", "ement", "ations", "ation", "ings", "ing", "ies", "ied", "ed", "es", "s", "e"):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[: -len(suf)]
    return w


_BY_STEM = {stem(k): k for k in THESAURUS}


def synonyms(word: str) -> list[str]:
    # the word, then its plain plural forms ('fees' -> 'fee', 'taxes' -> 'tax': too short for stem()), then the stem
    for cand in (word, word[:-1] if word.endswith("s") else None, word[:-2] if word.endswith("es") else None):
        if cand and cand in THESAURUS:
            return THESAURUS[cand]
    key = _BY_STEM.get(stem(word))
    return THESAURUS.get(key, []) if key else []


@dataclass
class Plan:
    text: str
    groups: list[list[str]]
    kind: str = "either"
    goal: str = ""
    source: str = "rules"
    notes: list[str] = field(default_factory=list)


def slug(text: str, n: int = 48) -> str:
    words = [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP]
    s = "_".join(words)[:n].strip("_")
    return s or "question"


def kind_of(text: str) -> str:
    t = text.lower()
    if re.search(r"\bhow (much|many|long)\b|\bwhat (is|are) the (rate|fee|cost|cap|limit|maximum|minimum|price|"
                 r"wage|amount)|\b(rate|cap|maximum|minimum|limit) (on|for)\b|\bhow high\b", t):
        return "facts"
    if re.search(r"\bhow (do|can|does|would|should) (i|we|you|a|an|someone|my|the)\b|\bsteps?\b|\bapply\b|"
                 r"\bprocess\b|\bprocedure\b|\brequest\b|\bget\b|\bfile\b|\bappeal\b", t):
        return "process"
    return "either"


# A phrase keeps its own words' multi-word synonyms ("building code" for "building permit") but not their bare
# words: "building" OR "permit" would make the concept as common as either word, and retrieval then treats it
# as background.  The bare words become a concept of their own, which ranks but rarely constrains.
PHRASE_SPLIT = False    # measured on AskBench: recall@20 0.210 -> 0.229, @80 0.427 -> 0.425 (no gain, off)


def rule_groups(text: str) -> list[list[str]]:
    """Concepts from the words of the question: phrases first, then content words with their synonyms."""
    t = text.lower().replace("’", "'")
    groups: list[list[str]] = []
    used: set[str] = set()
    for p in PHRASES:
        if p in t:
            head = p.split()[-1]
            syn = synonyms(p.split()[0]) + synonyms(head)
            if PHRASE_SPLIT:
                groups.append(list(dict.fromkeys([p] + [x for x in syn if x != p and " " in x]))[:6])
                bare = [x for x in syn if " " not in x]
                if bare:
                    groups.append(list(dict.fromkeys(bare))[:6])
            else:
                groups.append(list(dict.fromkeys([p] + [x for x in syn if x != p]))[:6])
            used.update(p.split())
            used.add(head)
    for w in re.findall(r"[a-z][a-z'\-]+", t):
        w = w.strip("'")
        if w in STOP or w in used or len(w) < 3:
            continue
        groups.append(list(dict.fromkeys([w] + synonyms(w))))
        used.add(w)
    # concepts that share a synonym describe one thing ("prison" and "inmate"): merge them
    merged: list[list[str]] = []
    for g in groups:
        for m in merged:
            if set(g) & set(m):
                m.extend(x for x in g if x not in m)
                break
        else:
            merged.append(g)
    return merged[:10]          # retrieval keeps the rarest few in each state's code; the rest only rank


PLAN_SYSTEM = """You help search a US state's statutes. For the question, list the 2 to 4 key legal concepts.
For each concept give 3 to 6 words or short phrases that a state code's section HEADINGS or text would use
(official legal vocabulary and synonyms, e.g. "inmate" and "prisoner" for people in prison, "canteen" for
commissary, "expungement" and "sealing" for clearing a record). Do not answer the question."""
PLAN_SCHEMA = {"type": "object", "properties": {"concepts": {"type": "array", "items": {"type": "object", "properties": {
    "concept": {"type": "string"}, "terms": {"type": "string"}}, "required": ["concept", "terms"]}}},
    "required": ["concepts"]}


def llm_groups(asker, text: str) -> list[list[str]]:
    r = asker.ask(PLAN_SYSTEM, f"Question: {text}", PLAN_SCHEMA)
    out = []
    for c in (r or {}).get("concepts", [])[:4]:
        if not isinstance(c, dict):
            continue
        raw = c.get("terms") or ""
        # in json mode (no grammar) the model may give the terms as a list rather than one string
        raw = ", ".join(str(x) for x in raw) if isinstance(raw, (list, tuple)) else str(raw)
        terms = [x.strip(" .;\"'").lower() for x in re.split(r"[,;/]| or ", raw) if x.strip()]
        terms = [x for x in terms if 2 < len(x) < 40 and len(x.split()) <= 4]
        head = (c.get("concept") or "").strip().lower()
        g = list(dict.fromkeys(([head] if head and len(head.split()) <= 3 else []) + terms))
        if g:
            out.append(g[:7])
    return out


# Japanese (and other CJK) questions: the runs of kanji, katakana and Latin letters are the terms (hiragana is
# grammar: particles and inflections), as the law writes them (手続き -> 手続)
_CJK = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff\u3005-\u3007]")
_CJK_RUN = re.compile(r"[\u3400-\u9fff\uf900-\ufaff\u3005-\u3007\u30a1-\u30ff\uff66-\uff9fA-Za-z0-9０-９Ａ-Ｚａ-ｚ]+")
CJK_STOP = frozenset("""場合 方法 必要 可能 以下 以上 何 誰 教 等 時 際 件 点 内容 規定 法律 法令 日本 制度 具体的
どの どこ いつ なぜ""".split())
CJK_PROCESS = re.compile(r"どう(?:すれば|したら|やって)|手続|申請|申立|届出|請求|方法|流れ")
CJK_FACTS = re.compile(r"いくら|何日|何年|期間|期限|金額|上限|手数料|料金")


def cjk_groups(text: str) -> list[list[str]]:
    """Concepts of a Japanese question: its kanji, katakana and Latin runs of two or more characters, in order,
    without the stop terms (場合, 方法 ...), one concept each (the trigram index matches each as a substring, so
    ``聴聞`` also finds 聴聞手続 and 聴聞調書)."""
    runs = [r for r in _CJK_RUN.findall(text or "") if len(r) >= 2 and r not in CJK_STOP]
    return [[r] for r in dict.fromkeys(runs)][:10]


def cjk_kind(text: str) -> str:
    if CJK_FACTS.search(text or ""):
        return "facts"
    if CJK_PROCESS.search(text or ""):
        return "process"
    return "either"


# Portuguese questions (Brazil's law, lexflow/corpus/countries/brazil.py): the thesaurus above and the local model's
# prompt are English, so a Portuguese question plans from its own content words, each with its plural or singular
# and a few of the law's words for it (PT_THESAURUS); the phrases in PT_PHRASES stay one concept.  The Brazilian
# index folds accents (``unicode61 remove_diacritics 2``), so ``informacao`` finds ``informação``.
_PT = re.compile(r"[ãõ]|ç[ãõaoõu]|\b(?:qual|quais|quem|não|são|você|vocês|posso|devo|podem|devem|há|às|aos|pelo|pela|"
                 r"pelos|pelas|onde|quanto|quantos|quantas|até|após)\b", re.I)
PT_STOP = frozenset("""a o as os um uma uns umas de do da dos das no na nos nas em ao aos à às pelo pela pelos pelas por
para pra com sem sob sobre entre até após ante e ou nem mas que se é são ser sendo sido foi era há ter tem têm tenho
qual quais quem como onde quando quanto quanta quantos quantas porque porquê este esta estes estas esse essa esses
essas isso isto aquele aquela aqueles aquelas meu minha meus minhas seu sua seus suas nosso nossa lhe lhes me te nós
você vocês ele ela eles elas eu já não sim mais menos muito muita muitos muitas pouco também só apenas cada todo
toda todos todas outro outra outros outras mesmo mesma pode podem posso poderá poderão deve devem devo preciso precisa
precisam fazer faz feito está estão estar fica ficar vai vão existe existem algum alguma alguns algumas qualquer
quaisquer coisa coisas caso casos forma tipo tipos lei leis legal legislação norma normas brasil brasileiro brasileira
federal artigo artigos art regra regras direito afinal então""".split())
PT_PHRASES: dict[str, list[str]] = {
    "acesso à informação": ["acesso à informação", "acesso a informações", "acesso às informações"],
    "dados pessoais": ["dados pessoais", "dado pessoal", "tratamento de dados"],
    "pessoa jurídica": ["pessoa jurídica", "pessoas jurídicas"], "pessoa física": ["pessoa física", "pessoas físicas"],
    "contrato de trabalho": ["contrato de trabalho", "relação de emprego", "empregado"],
    "pensão alimentícia": ["alimentos", "pensão alimentícia"], "união estável": ["união estável", "companheiro"],
    "violência doméstica": ["violência doméstica", "violência doméstica e familiar"],
    "medida protetiva": ["medidas protetivas", "medida protetiva"],
    "incorporação imobiliária": ["incorporação imobiliária", "incorporações imobiliárias", "incorporador"],
    "justa causa": ["justa causa"], "horas extras": ["horas extras", "horas suplementares", "jornada"],
    "habeas corpus": ["habeas corpus"], "mandado de segurança": ["mandado de segurança"],
    "direitos autorais": ["direitos autorais", "direito autoral", "direitos de autor"],
    "defesa do consumidor": ["consumidor", "defesa do consumidor", "fornecedor"],
    "prisão preventiva": ["prisão preventiva"], "liberdade provisória": ["liberdade provisória", "fiança"],
    "improbidade administrativa": ["improbidade administrativa", "improbidade"],
    "servidor público": ["servidor público", "servidores públicos", "servidor"],
}
PT_THESAURUS: dict[str, list[str]] = {
    "resposta": ["resposta", "respostas", "responder", "pedido", "requerimento", "solicitação"],
    "responder": ["resposta", "responder", "pedido", "requerimento", "solicitação"],
    "pedido": ["pedido", "pedidos", "requerimento", "requerimentos", "solicitação"],
    "pedir": ["pedido", "requerimento", "requerer", "solicitação"],
    "multa": ["multa", "multas", "penalidade", "sanção"], "pena": ["pena", "penas", "reclusão", "detenção"],
    "salário": ["salário", "remuneração", "vencimento"], "demissão": ["demissão", "dispensa", "despedida", "rescisão"],
    "aluguel": ["aluguel", "locação", "locatário", "locador"], "inquilino": ["locatário", "inquilino", "locação"],
    "herança": ["herança", "sucessão", "herdeiro", "herdeiros"], "empresa": ["empresa", "empresário", "sociedade"],
    "criança": ["criança", "adolescente"], "idoso": ["idoso", "pessoa idosa"],
    "incorporador": ["incorporador", "incorporadores", "incorporação"],
    "aposentadoria": ["aposentadoria", "aposentado", "benefício"], "recurso": ["recurso", "recursos", "apelação"],
    "prisão": ["prisão", "preso", "custódia"], "divórcio": ["divórcio", "dissolução do casamento"],
}
PT_PROCESS = re.compile(r"\bcomo\b|\bprocedimento|\bpedir\b|\brequerer\b|\bsolicitar\b|\brecorrer\b|\bpasso", re.I)
PT_FACTS = re.compile(r"\bprazo|\bquanto|\bquantos|\bquantas|\bvalor\b|\bmulta\b|\blimite|\bmáximo|\bmínimo|\bidade\b",
                      re.I)


def is_portuguese(text: str) -> bool:
    return bool(_PT.search(text or "")) and not _CJK.search(text or "")


def _fold_pt(s: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


def pt_forms(w: str) -> list[str]:
    """The other number of a Portuguese noun or adjective: ``pedido`` <-> ``pedidos``, ``informação`` <->
    ``informações``, ``legal`` <-> ``legais``, ``mulher`` <-> ``mulheres``."""
    out = []
    if w.endswith("ções"):
        out.append(w[:-4] + "ção")
    elif w.endswith("ção"):
        out.append(w[:-3] + "ções")
    elif w.endswith("ões"):
        out += [w[:-3] + "ão"]
    elif w.endswith("ão"):
        out += [w[:-2] + "ões"]
    elif w.endswith("ns"):
        out.append(w[:-2] + "m")
    elif w.endswith("is") and len(w) > 4:
        out.append(w[:-2] + "l")
    elif w.endswith("es") and len(w) > 4 and w[-3] in "rzs":
        out.append(w[:-2])
    elif w.endswith("s") and len(w) > 3:
        out.append(w[:-1])
    elif w.endswith("m"):
        out.append(w[:-1] + "ns")
    elif w.endswith("l"):
        out.append(w[:-1] + "is")
    elif w.endswith(("r", "z")):
        out.append(w + "es")
    elif w[-1] in "aeiouáéíóú":
        out.append(w + "s")
    return out


def pt_groups(text: str) -> list[list[str]]:
    """Concepts of a Portuguese question: its phrases (PT_PHRASES), then its content words without the stop words,
    each with its other number and its PT_THESAURUS words; concepts that share a word are merged."""
    t = (text or "").lower().replace("’", "'")
    ft = _fold_pt(t)
    groups: list[list[str]] = []
    used: set[str] = set()
    for p, syn in PT_PHRASES.items():
        if _fold_pt(p) in ft:
            groups.append(list(dict.fromkeys([p] + syn)))
            used.update(_fold_pt(w) for w in p.split())
    stop = {_fold_pt(w) for w in PT_STOP}
    for w in re.findall(r"[a-zà-ÿ]+(?:-[a-zà-ÿ]+)*", t):
        f = _fold_pt(w)
        if f in stop or f in used or len(w) < 3:
            continue
        syn = PT_THESAURUS.get(w) or PT_THESAURUS.get(next((k for k in PT_THESAURUS if _fold_pt(k) == f), ""), [])
        groups.append(list(dict.fromkeys([w] + pt_forms(w) + syn)))
        used.add(f)
    merged: list[list[str]] = []
    for g in groups:
        for m in merged:
            if {_fold_pt(x) for x in g} & {_fold_pt(x) for x in m}:
                m.extend(x for x in g if x not in m)
                break
        else:
            merged.append(g)
    return [g[:10] for g in merged][:10]


def pt_kind(text: str) -> str:
    if PT_FACTS.search(text or ""):
        return "facts"
    if PT_PROCESS.search(text or ""):
        return "process"
    return "either"


def plan(text: str, asker=None) -> Plan:
    if _CJK.search(text or ""):
        # the planner's thesaurus and the local model's prompt are English: a CJK question plans from its own terms
        p = Plan(text=text.strip(), groups=cjk_groups(text), kind=cjk_kind(text), goal=text.strip().rstrip("?？"),
                 source="rules-cjk")
        return p
    if is_portuguese(text):
        return Plan(text=text.strip(), groups=pt_groups(text), kind=pt_kind(text), goal=text.strip().rstrip("?"),
                    source="rules-pt")
    groups = rule_groups(text)
    p = Plan(text=text.strip(), groups=groups, kind=kind_of(text), goal=text.strip().rstrip("?"))
    if asker is not None:
        extra = llm_groups(asker, text)
        if extra:
            # add the model's vocabulary to the concept it overlaps, or as a concept of its own
            for g in extra:
                hit = next((m for m in p.groups if set(m) & set(g)), None)
                if hit is not None:
                    hit.extend(x for x in g if x not in hit)
                else:
                    p.groups.append(g)
            p.source = "rules+model"
            p.notes.append(f"{len(extra)} concepts from the local model")
    p.groups = [g[:10] for g in p.groups if g][:10]
    return p
