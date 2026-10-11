"""Named human review: who read a page against the law, in what role, on what date, and which text they read.

**Reviewers come from a list the operator keeps.**  No check on a name can prove that a reviewer is a person, so
lexflow does not try: the operator of a lexflow copy adds each reviewer to the ``reviewers`` table with ``lexflow
reviewer add`` (name, a role from ``ROLES``, ``licensed_in`` for an attorney, who added them and when), and so
vouches that each one is a person with that role.  The table is this copy's own: push and pull refuse it (they take
only the tables in ``db.SYNCED``), and of lexflow's code only the ``lexflow reviewer`` commands write it (the API and
the dashboard only read it).  A review names a reviewer by their id on that list, and the name, role and licence a
page prints come from the list, never from the review; a review naming an id that is not on this copy's list counts
as not reviewed, and a log line says so.  Removing a reviewer (``lexflow reviewer remove``) takes their name off
every page at the next render.

**A page names a reviewer only for a review this copy recorded.**  For an asked answer, that is a review this
copy's review API recorded with the reviewer's own token: the last ``review_log`` entry for the answer is that
review, with the same reviewer, text_hash and date (lexflow/reviewers.py, ``recorded``).  For a curated model, a
place file or a researched process, it is a sign-off in this copy's own file.  Any other review field, one that
arrived through sync or was written into the database by hand, counts as not reviewed, and one log line per item
says so (``unrecorded``).

A curated model (``curated/<state>/<question>.json``), a researched place file or process
(``curated/places/<state>/<place>.json``, ``.../<place>/<process>.json``) and an asked answer (the
``asked_answers.reviewed_by`` column) may carry::

    "reviewed_by": {"reviewer": "<an id from `lexflow reviewer list`>", "date": "YYYY-MM-DD", "attested": true,
                    "text_hash": "<what `lexflow review-hash <file>` prints for the text they read>"}

``attested`` is the statement that the reviewer, a person, read this exact text against the law; without it the
record is not a sign-off.  Through the API it is recorded only with that reviewer's own token (lexflow/reviewers.py);
in a curated file, by whoever edits the file, so a curated sign-off is not bound to any token and the operator answers
for it.  A record that carries a typed name, role or state instead of a reviewer id is not a sign-off either.
Public pages then say "Reviewed by <name>, <role>, on <date>", "Reviewed by <name>, attorney licensed in <state>, on
<date>", or, for "other person", "Reviewed by <name> on <date>".  The older
``reviewed_by`` strings in curated models record the AI system that drafted and checked them ("Claude
(claude-opus-5-5), 2026-10-10; ..."), and pages built from them say "Not yet reviewed by a person".

A review applies only to the text it was given.  ``text_hash`` is the SHA-256 of that text (the file without its
``reviewed_by`` entries, or one answer of a place file, or an asked answer's stored content), and a page names
the reviewer only while the text it is built from still has that hash: an edited file, a re-asked answer or a
newer copy pulled through sync shows "Not yet reviewed by a person" again until someone signs the new text here.  A
review dated in the future or before the text it reviews (an asked answer's ``answered_at``, a place file's
``researched``) is refused, and so is one of a curated model dated before the model was first built
(``first_built``, lexflow/municipal/build.py: stored at the model's first build on this copy, from the date its
drafting note opens with, or that build's own date; then kept, so a later build, an edited note or a pull never
moves it back).  When a curated file is loaded, its sign-off is checked against the file and then bound to the
stored copy (``bind``), so the stored row keeps the reviewer's id and the hash of the text together; a page still
names the reviewer only while this copy's file carries that sign-off.

A name is cleaned when it is added (``clean_name``): NFKC, then 2 to 80 characters of letters (any script),
spaces, hyphens, apostrophes and full stops; no invisible character (Unicode's Default_Ignorable code points, the
Hangul fillers among them); each word in one script (UTS #39's single-script rule, with Common and Inherited
characters allowed and Han written with Hiragana, Katakana, Hangul or Bopomofo); and none of the role and
credential words and placeholders the lists here hold, read through a table of look-alike letters, each letter in
its own case or folded ("Аttorney" with a Cyrillic А is "attorney", and the Cyrillic capitals "ЕЅԚ" are "esq").  A
role word that is also a surname (Lawyer, Clerk, Staff) is taken as the surname only after one given name ("Jane
Lawyer"), and refused anywhere else.  The lists catch only what they hold: the operator answers for every name on the
list.
``is_ai_name`` looks for the name of an AI system, model family, assistant or agent product in it; that is only a
warning at ``reviewer add``, which the operator overrides with ``--confirm-person`` for a person whose name happens
to contain one (Wenxin Li, Marie Lechat), and it proves nothing either way.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import unicodedata
from datetime import date, datetime, timezone

LOG = logging.getLogger("lexflow.signoff")

MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December")
# the roles a reviewer can give: a page prints the role as it is listed here ("other person": no role printed)
ROLES = ("attorney", "paralegal", "law student", "clerk", "records officer", "planner", "municipal attorney",
         "researcher", "student", "volunteer", "other person")
ATTORNEY_ROLES = ("attorney", "municipal attorney")
NO_ROLE_SHOWN = "other person"
HASH = re.compile(r"[0-9a-f]{64}")
# a reviewer's id on the operator's list ("rv-" and eight hex digits, made by `lexflow reviewer add`)
REVIEWER_ID = re.compile(r"rv-[0-9a-f]{8}")
# what a review record holds; a name, role or state typed into it is refused (they come from the list)
REVIEW_KEYS = ("reviewer", "date", "attested", "text_hash")
TYPED = ("name", "role", "licensed_in")

# ------------------------------------------------------------------ names on the reviewer list
NAME_MIN, NAME_MAX = 2, 80
# role, credential and title words: a name is a name, and the role and licence come from the list's own fields
# ("Jane Roe, attorney licensed in all 50 states" is refused).  Words that are also surnames ("Law", "Judge",
# "Justice", "Doctor", "Hon") are left out; "law" is refused only in a role phrase.
# The words are compared in plain letters (``skeleton``: look-alikes read as Latin letters, accents dropped).
ROLE_WORDS = {
    "attorney", "attorneys", "atty", "attys", "lawyer", "lawyers", "counsel", "counsellor", "counselor", "solicitor",
    "barrister", "advocate", "advocates", "paralegal", "paralegals", "clerk", "clerks", "officer", "officers",
    "planner", "planners", "researcher", "researchers", "reviewer", "reviewers", "volunteer", "volunteers",
    "student", "students", "intern", "municipal", "records", "licensed", "licenced", "license", "licence",
    "certified", "notary", "esq", "esquire", "dr", "prof", "professor", "honorable", "honourable", "staff", "team",
    "admin", "administrator", "office", "department", "dept", "bureau", "agency", "committee", "firm", "llp", "pllc",
    "inc", "llc", "ltd", "corp",
    # other jobs a name is not ("Fact Checker", "Wiki Editor", "Moderator")
    "editor", "editors", "moderator", "moderators", "checker", "checkers", "factchecker", "verifier", "verifiers",
    "validator", "auditor", "auditors", "proofreader", "approver", "signatory", "magistrate", "jurist",
    # the same in other languages ("Abogada", "Avocat", "Rechtsanwältin")
    "abogado", "abogada", "abogados", "abogadas", "avocat", "avocate", "avocats", "avocates", "avvocato", "avvocata",
    "avvocati", "advogado", "advogada", "advogados", "rechtsanwalt", "rechtsanwaltin", "rechtsanwalte",
    "rechtsanwaltinnen", "anwalt", "anwaltin", "advokat", "advokatin", "notario", "notaria", "notaire", "licenciado",
    "licenciada", "procurador", "procuradora", "solicitador", "juriste", "jurista"}
ROLE_PHRASES = ("law student", "law clerk", "law office", "law firm", "law school", "other person", "legal team",
                "legal aid", "legal services", "bar member", "member of the bar", "admitted to the bar",
                "juris doctor", "juris doctorate", "doctor of law", "doctor of laws", "doctor of jurisprudence",
                "at law", "state bar", "the bar", "bar association", "bar number", "bar no", "fact check",
                "wiki editor",
                # a clerk's or a staff's office, not a surname after a given name ("City Clerk", "Legal Staff")
                "city clerk", "county clerk", "court clerk", "town clerk", "deputy clerk", "chief clerk",
                "clerk of court", "clerk of the court", "legal staff", "office staff", "support staff", "city staff",
                "county staff", "staff member", "the lawyer", "my lawyer", "your lawyer")
# role words that are also surnames: taken as the surname when the name is one given name and that word ("Jane
# Lawyer", "Agnes Clerk", "John Staff"), and refused anywhere else ("Lawyer", "Jane Doe Lawyer", "Clerk Smith")
SURNAME_ROLE_WORDS = {"lawyer", "clerk", "staff"}
# letters after a name that claim a degree or a licence; as a first word they are initials ("J. D. Salinger")
CREDENTIALS = {"jd", "llm", "llb", "lld", "phd", "md", "mba", "mpa", "mpp", "cpa", "dds", "rn", "esq", "jsd", "sjd"}
# whole names that stand for no one, written without spaces, stops, apostrophes or hyphens
PLACEHOLDERS = {"na", "nan", "none", "null", "nil", "void", "anonymous", "anon", "unknown", "reviewer", "test",
                "testing", "testuser", "staff", "admin", "user", "nobody", "noone", "someone", "somebody", "name",
                "fullname", "yourname", "firstlast", "firstnamelastname", "tbd", "tba", "todo", "xxx", "xx", "abc",
                "asdf", "qwerty", "example", "sample", "demo", "dummy", "placeholder", "fake", "johndoe", "janedoe",
                "jdoe", "johnqpublic", "lexflow", "operator", "system"}
# placeholder words anywhere in a name ("Test User", "Anonymous Reviewer", "Unknown Staff")
PLACEHOLDER_WORDS = {"anonymous", "anon", "unknown", "test", "placeholder", "example", "sample", "dummy", "demo",
                     "tbd", "todo", "nobody", "someone", "unnamed", "redacted"}
APOSTROPHES = {"’": "'", "‘": "'", "ʼ": "'", "＇": "'"}
HYPHENS = {"‐": "-", "‑": "-"}
# Unicode's Default_Ignorable_Code_Point (DerivedCoreProperties.txt): characters that draw nothing, or nothing of
# their own (soft hyphen, zero-width and bidirectional controls, variation selectors, the Hangul fillers U+115F,
# U+1160, U+3164 and U+FFA0, the Khmer inherent vowels U+17B4 and U+17B5, tags).  A name holding one is refused.
DEFAULT_IGNORABLE = ((0x00AD, 0x00AD), (0x034F, 0x034F), (0x061C, 0x061C), (0x115F, 0x1160), (0x17B4, 0x17B5),
                     (0x180B, 0x180F), (0x200B, 0x200F), (0x202A, 0x202E), (0x2060, 0x206F), (0x3164, 0x3164),
                     (0xFE00, 0xFE0F), (0xFEFF, 0xFEFF), (0xFFA0, 0xFFA0), (0xFFF0, 0xFFF8), (0x1BCA0, 0x1BCA3),
                     (0x1D173, 0x1D17A), (0xE0000, 0xE0FFF))
# UTS #39's augmented script sets: Han is written with Hiragana and Katakana (Japanese), Hangul (Korean) and Bopomofo
AUGMENT = {"Hani": {"Hanb", "Jpan", "Kore"}, "Hira": {"Jpan"}, "Kana": {"Jpan"}, "Hang": {"Kore"}, "Bopo": {"Hanb"}}


def ignorable(c: str) -> bool:
    """Whether ``c`` is a Default_Ignorable code point (``DEFAULT_IGNORABLE``)."""
    o = ord(c)
    return any(a <= o <= b for a, b in DEFAULT_IGNORABLE)


def _script_set(c: str) -> set[str] | None:
    """A character's scripts as UTS #39 resolves them (Script_Extensions, augmented); None for Common and Inherited,
    which go with any script."""
    from fontTools import unicodedata as fu       # Unicode's Scripts.txt and ScriptExtensions.txt
    sx = set(fu.script_extension(c))
    if sx & {"Zyyy", "Zinh"}:
        return None
    for code in list(sx):
        sx |= AUGMENT.get(code, set())
    return sx


def mixed_script(word: str) -> bool:
    """Whether one word mixes scripts (UTS #39, single script): "Аttorney" with a Cyrillic А does, "Клод" does not,
    and nor do "山田たろう" (Han and Hiragana) or a Latin word with combining accents."""
    resolved = None
    for c in word:
        sx = _script_set(c)
        if sx is None:
            continue
        resolved = sx if resolved is None else resolved & sx
        if not resolved:
            return True
    return False


def _state_bar() -> re.Pattern:
    """' virginia bar ', ' dc bar ': a state's bar after a name ("Member Virginia Bar"), by the state's full name
    (the two-letter codes are also words in names: "de", "la")."""
    global _STATE_BAR
    if _STATE_BAR is None:
        from .municipal import states as S
        names = sorted({skeleton(n) for n in S.NAME.values()} | {"dc"}, key=len, reverse=True)
        _STATE_BAR = re.compile(r" (?:%s) bar " % "|".join(re.escape(n) for n in names))
    return _STATE_BAR


_STATE_BAR = None


def clean_name(name) -> tuple[str, list[str]]:
    """A reviewer's name as the list stores it, and why it cannot be stored (empty when it can).  The name is put in
    NFKC form, curly apostrophes and Unicode hyphens become plain ones, and tabs, line breaks and runs of spaces
    become one space.  Then it must be 2 to 80 characters of letters (any script, with their combining marks),
    spaces, hyphens, apostrophes and full stops only; start with a letter and hold at least two; hold no invisible
    character (``DEFAULT_IGNORABLE``: zero-width and bidirectional controls, the Hangul fillers, the Khmer inherent
    vowels); keep each word in one script (``mixed_script``); and carry none of the role and credential words and
    placeholders listed here, read in plain letters (``skeleton``).  This says nothing about whether the name is a
    person's, and the lists catch only what they hold: the operator vouches for the person and answers for the
    name."""
    raw = str(name or "")
    hidden = sorted({c for c in raw + unicodedata.normalize("NFKC", raw) if ignorable(c)})
    s = unicodedata.normalize("NFKC", raw)
    s = "".join(APOSTROPHES.get(c, HYPHENS.get(c, c)) for c in s)
    s = "".join(" " if c in "\t\n\r" or unicodedata.category(c) in ("Zs", "Zl", "Zp") else c for c in s)
    s = " ".join(s.split())
    out = []
    if hidden:
        out.append("a reviewer's name has no invisible characters (not "
                   + " ".join(f"U+{ord(c):04X}" for c in hidden[:6]) + "): type it again in plain letters")
    if not NAME_MIN <= len(s) <= NAME_MAX:
        out.append(f"a reviewer's name is {NAME_MIN} to {NAME_MAX} characters")
    bad = sorted({c for i, c in enumerate(s) if not ignorable(c) and not (
        unicodedata.category(c).startswith("L") or c in " -'."
        or (unicodedata.category(c).startswith("M") and i and unicodedata.category(s[i - 1])[0] in "LM"))})
    if bad:
        out.append("a reviewer's name has only letters, spaces, hyphens, apostrophes and full stops (not "
                   + " ".join(repr(c) for c in bad[:6]) + ")")
    letters = sum(1 for c in s if unicodedata.category(c).startswith("L") and not ignorable(c))
    if s and not unicodedata.category(s[0]).startswith("L"):
        out.append("a reviewer's name starts with a letter")
    elif letters < 2:
        out.append("a reviewer's name has at least two letters")
    mixed = [w for w in s.split() if mixed_script(w)]
    if mixed:
        out.append("each word of a reviewer's name is in one script (not " + ", ".join(repr(w) for w in mixed[:3])
                   + ": letters from two scripts in one word, such as a Cyrillic а in a Latin name, look like others)")
    plain = skeleton(s)
    words = [w for w in re.split(r"[\s\-]+", plain) if w]
    keys = [re.sub(r"[.']", "", w) for w in words]
    spaced = " " + " ".join(keys) + " "
    # "Jane Lawyer": one given name (hyphenated or not) and a role word that is also a surname, as the surname
    parts = plain.split()
    given = [re.sub(r"[.']", "", w) for w in re.split(r"-+", parts[0]) if w] if len(parts) == 2 else []
    surname = (len(parts) == 2 and re.sub(r"[.']", "", parts[1]) in SURNAME_ROLE_WORDS and bool(given)
               and not any(w in ROLE_WORDS or w in CREDENTIALS or w in PLACEHOLDER_WORDS for w in given))
    found = [w for i, w in enumerate(keys) if w in ROLE_WORDS and not (surname and i == len(keys) - 1)] + [
        p for p in ROLE_PHRASES if f" {p} " in spaced] + [
        w for w in keys[1:] if w in CREDENTIALS] + [m.group(0).strip() for m in _state_bar().finditer(spaced)]
    if found:
        out.append(f"a reviewer's name has no role or credential words ({', '.join(dict.fromkeys(found))}): the "
                   "role and the state of an attorney's licence are their own fields")
    whole = "".join(keys)
    if whole in PLACEHOLDERS or any(w in PLACEHOLDER_WORDS for w in keys):
        out.append("a reviewer's name is a person's name, not a placeholder (N/A, Anonymous, Reviewer, test, Staff, "
                   "Unknown)")
    return s, out


def entry_problems(entry) -> list[str]:
    """Why a row of the reviewer list cannot be shown (empty when it can): its name as ``clean_name`` would store
    it, a role from ``ROLES``, and ``licensed_in`` only for an attorney's role, naming a state.  A row written by
    hand or by older code is checked again here, so a page never prints a name the list would not take."""
    if not isinstance(entry, dict):
        return ["a reviewer is a row of the reviewer list"]
    out = []
    if not REVIEWER_ID.fullmatch(str(entry.get("id") or "")):
        out.append("a reviewer's id is rv- and eight hex digits")
    name, bad = clean_name(entry.get("name"))
    out += bad
    if not bad and name != entry.get("name"):
        out.append("the name is not stored as clean_name gives it")
    role = role_of(entry.get("role"))
    if not role:
        out.append(f"the role must be one of {', '.join(ROLES)}")
    if entry.get("licensed_in"):
        if role not in ATTORNEY_ROLES:
            out.append(f"licensed_in is for an attorney: give the role {' or '.join(ATTORNEY_ROLES)}")
        elif not state_of(entry["licensed_in"]):
            out.append("licensed_in is the state where the attorney is licensed ('va' or 'Virginia')")
    return out

# Names of AI systems, model families, assistants and agent products, and of lexflow itself: ``reviewer add`` warns
# when a name contains one, and the operator confirms that the reviewer is a person (``--confirm-person``) or does
# not add them.  This is a warning, not a test: it cannot prove a name is a person's, and it catches only what it
# lists.  Each entry is a regular expression over a name in plain lower-case letters and digits, with one space
# between words; a space here may also be missing ("deep seek" is DeepSeek too), but a "\s" may not ("palm\se" is
# PaLM-E, not Palme).  An entry matches only as a whole word: no letter may come right before it or after it (a
# digit may: "llama3", "gemma3"), except a product suffix ("claudebot", "geminiai").  Entries that are also common
# names or words ("Bing", "Watson", "Palme", "Cline", "Jasper", "Meena", "Bixby") are listed only in the form that
# names the product.
AI_NAMES = (
    # makers
    "anthropic", "open ai", "deep mind", "xai", "mistral ai", "cohere", "ai 21", "aleph alpha", "inflection ai",
    "hugging face", "stability ai", "midjourney", "mid journey", "zhipu", "minimax", "moonshot ai", "baichuan",
    "lex flow", "sourcegraph", "anysphere", "cognition labs", "nous research", "together ai",
    # model families and chat products
    "claude", "chat gpt", "gpt", "o1", "o3", "o4 mini", "codex", r"dall\se", "chat glm", "glm",
    "gemini", "gemma", "bard", r"palm \d", r"palm\se", "lamda", "notebook lm", "chinchilla", "gopher",
    "llama", "code llama", "alpaca", "vicuna", "llamafile", "lm studio", "ollama",
    "mistral", "mixtral", "codestral", "pixtral", "ministral", "magistral", "devstral", "le chat",
    "qwen", "qwq", "tongyi", "qianwen", "ernie bot", "wenxin", "yiyan", "doubao", "hunyuan", "kimi", "internlm",
    "deep seek", "nemotron", "megatron", "grok", "sonnet", "opus", "haiku", "fable",
    "command r", "aya expanse", r"jurassic \d", "jamba", r"phi \d", r"mpt \d", r"falcon \d", "bloomz",
    "starcoder", "santacoder", "wizard lm", "wizard coder", "open chat", r"olmo \d", "stable lm", "stable diffusion",
    r"orca \d", "orca mini", r"dolly v?\d", r"zephyr \d", r"granite \d", "ibm granite", "watsonx", "ibm watson",
    "pi", "replika", "xiaoice", "perplexity", "phind", "hugging chat", "poe ai", "you com",
    "character ai", "copilot", "co pilot", "bing chat", "bing copilot", "bing ai", "cortana", "sydney ai",
    # assistants
    "siri", "alexa", "samsung bixby", "google assistant", "assistant", "chatbot", "chat bot", "bot", "bots", "robot",
    # agent products
    "devin", "manus", "open hands", "open devin", "swe agent", "aider", "cursor", "windsurf", "codeium", "tabnine",
    "code whisperer", "amazon q", "q developer", "replit", "roo code", "sourcegraph cody", "auto gpt", "baby agi",
    "agent gpt", "meta gpt", "crew ai", "lang chain", "lang graph", "auto gen", "semantic kernel", "computer use",
    "openai operator", "project mariner", "project astra", "co counsel", "casetext", "harvey ai", "agent", "agents",
    # what such systems are called
    "llms?", "language models?", "large language models?", "artificial intelligence", "machine intelligence",
    r"neural net(?:work)?s?", "generative ai", "gen ai",
)
AI_SUFFIX = "bot|ai|gpt|chat|code|assistant|agent|llm"
AI_NAME = re.compile(r"(?<![a-z])(?:%s)(?:%s)?(?![a-z])" % (
    "|".join(n.replace(" ", " ?") for n in AI_NAMES), AI_SUFFIX))
# a.i. written with stops or spaces ("A.I. Reviewer"); "AI" as a word is checked on its own (is_ai_name)
SPACED_AI = re.compile(r"(?<![a-z0-9])a i(?![a-z0-9])")
# Letters that look like Latin ones, read as those letters: a table of the Cyrillic, Greek, Armenian, Cherokee and
# Lisu look-alikes, small capitals and IPA letters.  It is lexflow's own short table, not the whole of Unicode's
# confusables.txt, and catches only what it holds.
LOOKALIKE = {**dict(zip("АВСЕНІЈКМОРЅТХУаеорсухіјѕԁӏкмтвнԛԝѡһ", "ABCEHIJKMOPSTXYaeopcyxijsdlkmtbhqwwh")),
             **dict(zip("ΑΒΕΖΗΙΚΜΝΟΡΤΥΧαεικνορτυχϲϹϳ", "ABEZHIKMNOPTYXaeikvoptuxcCj")), "ɩ": "i", "ı": "i",
             # small capitals and Cherokee letters that look like Latin ones ("Cʟaude", "ᴄlaude", "Ꮯlaude")
             **dict(zip("ᴀʙᴄᴅᴇɢʜɪᴊᴋʟᴍɴᴏᴘʀꜱᴛᴜᴠᴡʏᴢ", "abcdeghijklmnoprstuvwyz")),
             **dict(zip("ᎪᏴᏟᎠᎬᏀᎻᏆᎫᏦᏞᎷᏒᏚᎢᏙᏔᏃ", "ABCDEGHIJKLMRSTVWZ")),
             # Latin letters drawn like others ("Clɑude", "ɡemini"), Armenian ("Cօpilot") and Lisu capitals
             **dict(zip("ɑɡǀƖɪʏ", "aglliy")),
             **dict(zip("օսցհոռզաՕՍՏԼ", "oughnnqwOUSL")),
             **dict(zip("ꓮꓐꓚꓓꓰꓝꓖꓧꓲꓙꓗꓡꓟꓠꓳꓑꓣꓢꓔꓴꓦꓪꓫꓬꓜ", "ABCDEFGHIJKLMNOPRSTUVWXYZ"))}
# characters written for letters ("C1aude", "Cl@ude", "0llama"): a digit or sign next to a letter, read both ways
LEET = ({"1": "l", "|": "l", "0": "o", "3": "e", "4": "a", "@": "a", "5": "s", "$": "s", "7": "t", "8": "b", "!": "i"},
        {"1": "i", "|": "i", "0": "o", "3": "e", "4": "a", "@": "a", "5": "s", "$": "s", "7": "t", "8": "b", "!": "l"})
LEET_AT = re.compile(r"(?<=[a-z])[0-9|!@$]|[0-9|!@$](?=[a-z])")

# what a page is built from, by table: the columns a review covers (True: stored as JSON text)
ASKED_TEXT = {"question_text": False, "status": False, "sections": True, "facts": True, "answer": True,
              "local": True, "bpmn": False}
LOCAL_TEXT = {"summary": False, "steps": True, "contacts": True, "local_law": True, "fees": False,
              "caveats": True, "sources": True}


def iso_date(value) -> str | None:
    """'2026-10-10' (or a timestamp starting with one) as an ISO date; None when it is not one."""
    m = re.match(r"(\d{4}-\d{2}-\d{2})", str(value or ""))
    if not m:
        return None
    try:
        return date.fromisoformat(m.group(1)).isoformat()
    except ValueError:
        return None


def past_date(value) -> str | None:
    """``iso_date``, or None for a date after today (UTC): a check is never dated in the future, so a check date
    that is (in a process file, a stored model, a pulled row) is not shown as when anything was checked."""
    d = iso_date(value)
    return d if d and d <= datetime.now(timezone.utc).date().isoformat() else None


def long_date(value) -> str | None:
    """'2026-10-10' -> '10 October 2026'."""
    d = iso_date(value)
    if not d:
        return None
    y, m, day = (int(x) for x in d.split("-"))
    return f"{day} {MONTHS[m - 1]} {y}"


def skeleton(text: str) -> str:
    """A name in plain lower-case letters for comparing it with the lists: NFKC, look-alike letters as Latin ones
    (``LOOKALIKE``, each letter in its own case or folded), accents dropped, case folded.  "Аttorney" (Cyrillic А),
    "Lawyеr" (Cyrillic е), "Еѕq", the capitals "ЕЅԚ" and "Rechtsanwältin" read "attorney", "lawyer", "esq", "esq" and
    "rechtsanwaltin"."""
    return _letters(text).casefold()


def _look(c: str) -> str:
    """The Latin letter a look-alike stands for: the table's entry for the letter, else for the letter with its
    case folded (the table holds "ԛ", so the capital "Ԛ" reads "q" too), else the letter itself."""
    return LOOKALIKE.get(c) or LOOKALIKE.get(c.casefold()) or c


def _letters(name: str) -> str:
    """A name in plain letters: full-width and other compatibility forms as their ASCII letters, look-alike Cyrillic
    and Greek letters as Latin ones (in either case: ``_look``), and accents and invisible characters dropped."""
    # look-alikes are read before NFKC too, which turns some of them into other letters (Ϲ, a lunate sigma, into Σ)
    s = unicodedata.normalize("NFKC", "".join(_look(c) for c in str(name or "")))
    s = "".join(_look(c) for c in s if unicodedata.category(c) != "Cf")
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def _camel(letters: str) -> str:
    """Run-together words split at a change of case: "ClaudeBot" -> "Claude Bot", "AIReviewer" -> "AI Reviewer"."""
    return re.sub(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", " ", letters)


def _spellings(letters: str) -> list[list[str]]:
    """The words of a name in lower case, as written and split at changes of case, each also with digits and signs
    next to letters read as letters."""
    out = []
    for low in {letters.lower(), _camel(letters).lower()}:
        out.append(re.findall(r"[a-z0-9]+", low))
        for table in LEET:
            out.append(re.findall(r"[a-z0-9]+", LEET_AT.sub(lambda m, t=table: t[m.group(0)], low)))
    return out


def is_ai_name(name: str) -> bool:
    """Whether a reviewer's name contains, as a whole word in any case, the name of an AI system, model family,
    assistant or agent product (``AI_NAMES``), or "AI" itself, however it is spelt: look-alike letters, digits for
    letters, letters spaced out ("Cl aude", "C.l.a.u.d.e")."""
    letters = _letters(name)
    # "AI" on its own, in any case but the given name "Ai" ("Ai Weiwei"): "AI reviewer", "Example AI", "an ai"
    if any(w.lower() == "ai" and w != "Ai" for w in re.findall(r"[A-Za-z0-9]+", _camel(letters))):
        return True
    for words in _spellings(letters):
        text = " ".join(words)
        if AI_NAME.search(text) or SPACED_AI.search(text):
            return True
        # letters spaced out or split: every run of two or more words, read as one word
        for i in range(len(words)):
            for j in range(i + 2, min(len(words), i + 12) + 1):
                if AI_NAME.search("".join(words[i:j])):
                    return True
    return False


def role_of(value) -> str | None:
    """The role as ``ROLES`` lists it ('Records  Officer' -> 'records officer'), or None when it is not one."""
    role = " ".join(str(value or "").lower().split())
    return role if role in ROLES else None


def state_of(value) -> str | None:
    """A state given as its code or name ('va', 'Virginia') as its name, or None."""
    from .municipal import states as S
    st = " ".join(str(value or "").split()).lower()
    code = st if st in S.NAME else S.BY_NAME.get(st)
    return S.NAME[code] if code else None


NOT_ON_LIST = "the reviewer is not on the operator's list of reviewers (`lexflow reviewer list`)"
_UNLISTED: set[str] = set()


def _unlisted(reviewer_id: str) -> None:
    """One log line per reviewer id that a review names but this copy's list does not hold (a review pulled from
    another copy, or by someone since removed): it counts as not reviewed."""
    if reviewer_id not in _UNLISTED:
        _UNLISTED.add(reviewer_id)
        LOG.warning("a review names reviewer %s, who is not on this copy's reviewer list (`lexflow reviewer list`): "
                    "it counts as not reviewed", reviewer_id)


_UNRECORDED: set[str] = set()


def unrecorded(item: str, why: str) -> None:
    """One log line per item (an asked answer, a model, a place's answer, a process) whose review field names
    someone on the list but was not recorded by this copy (``why``): it counts as not reviewed."""
    if item not in _UNRECORDED:
        _UNRECORDED.add(item)
        LOG.warning("%s carries a review this copy did not record (%s): it counts as not reviewed", item, why)


NEEDS_ID = ("name the reviewer by their id on the operator's list (`lexflow reviewer list`; the operator adds a "
            "reviewer with `lexflow reviewer add`)")


def record_problems(rev, *, not_before=None) -> list[str]:
    """Why ``rev`` is not a well-formed review record (empty when it is one), whatever the list holds: a reviewer
    id, the reviewer's own statement that they read this exact text (``attested: true``), a date that is not in the
    future or before the text (``not_before``), and a well-formed ``text_hash`` if one is given.  A record that
    types in a name, a role or a state is refused: those come from the list."""
    if not isinstance(rev, dict):
        return ["a review is an object: {reviewer, date, attested, text_hash}"]
    out = []
    typed = [k for k in TYPED if k in rev]
    if typed:
        out.append(f"a review does not carry {', '.join(typed)}: it names the reviewer by their id on the operator's "
                   "list, and the name, role and licence come from the list")
    if not REVIEWER_ID.fullmatch(str(rev.get("reviewer") or "")):
        out.append(NEEDS_ID)
    if rev.get("attested") is not True:
        out.append("the reviewer must state that they, a person, read this exact text against the law "
                   "(attested: true)")
    d = iso_date(rev.get("date"))
    if not d:
        out.append("give the review date as YYYY-MM-DD")
    elif d > datetime.now(timezone.utc).date().isoformat():
        out.append("the review date is in the future")
    elif iso_date(not_before) and d < iso_date(not_before):
        out.append(f"the review date is before the text it reviews ({iso_date(not_before)})")
    if rev.get("text_hash") is not None and not HASH.fullmatch(str(rev.get("text_hash"))):
        out.append("text_hash is the 64-character SHA-256 that `lexflow review-hash` prints")
    return out


def problems(rev, roster, *, not_before=None) -> list[str]:
    """Why ``rev`` is not a person's sign-off (empty when it is one): ``record_problems``, and a reviewer who is on
    this copy's list now (``roster``: id -> list row, as ``lexflow.reviewers.roster`` reads it).  An id the list
    does not hold is logged once (``_unlisted``)."""
    out = record_problems(rev, not_before=not_before)
    if isinstance(rev, dict) and REVIEWER_ID.fullmatch(str(rev.get("reviewer") or "")) and \
            rev["reviewer"] not in (roster or {}):
        out.append(NOT_ON_LIST)
        _unlisted(rev["reviewer"])
    return out


def person(rev, roster, *, not_before=None) -> dict | None:
    """The reviewer as a page shows them: ``{"reviewer", "name", "role", "date", "attested"[, "licensed_in"][,
    "text_hash"]}``, with the name, role and licence from the operator's list; or None when ``rev`` is not a
    person's sign-off (missing, a legacy string, a typed name, no attestation, a reviewer not on the list, a date
    before ``not_before``).  This does not say which text they reviewed: ``bound`` does."""
    if problems(rev, roster, not_before=not_before):
        return None
    entry = roster[rev["reviewer"]]
    out = {"reviewer": rev["reviewer"], "name": entry["name"], "role": role_of(entry["role"]),
           "date": iso_date(rev["date"]), "attested": True}
    if entry.get("licensed_in"):
        out["licensed_in"] = state_of(entry["licensed_in"])
    if rev.get("text_hash"):
        out["text_hash"] = str(rev["text_hash"])
    return out


# ------------------------------------------------------------------ which text a review covers
def canonical(value) -> str:
    """One spelling of a JSON value, whatever order or spacing it was stored with."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def text_hash(value) -> str:
    """The SHA-256 of a text (any JSON value: a file's content, a stored answer)."""
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def strip_signoffs(value):
    """A curated file's content without its sign-offs (every ``reviewed_by``): what a reviewer signs."""
    if isinstance(value, dict):
        return {k: strip_signoffs(v) for k, v in value.items() if k != "reviewed_by"}
    if isinstance(value, list):
        return [strip_signoffs(v) for v in value]
    return value


def file_hash(spec: dict) -> str:
    """The text_hash a reviewer records for a curated file (`lexflow review-hash <file>` prints it)."""
    return text_hash(strip_signoffs(spec))


def row_text(row: dict, cols: dict[str, bool]) -> dict:
    """The part of a stored row a review covers (ASKED_TEXT, LOCAL_TEXT), with JSON columns read as JSON, so the
    hash is the same whether the row was read from the database, a sync page or a curated file."""
    out = {}
    for c, is_json in cols.items():
        v = row.get(c)
        if is_json and isinstance(v, str):
            try:
                v = json.loads(v) if v else None
            except ValueError:
                pass
        out[c] = None if v in (None, "", [], {}) else v      # an empty list stored as NULL is the same text
    return out


def model_text(facts, metrics: dict | None) -> dict:
    """What a state model's page is built from: its facts, sections and plain-language notes."""
    m = metrics or {}
    if isinstance(facts, str):
        try:
            facts = json.loads(facts)
        except ValueError:
            facts = None
    return {"facts": facts or {}, "sections": m.get("sections") or [], "reader_gaps": m.get("reader_gaps") or [],
            "reader_notes": m.get("reader_notes") or {}}


def fits(rev, text, *, not_before=None) -> bool:
    """Whether ``rev`` is a well-formed review of ``text`` (its hash and date fit), whoever the list holds now: what
    sync checks, so a review is not dropped because the list has not arrived yet."""
    return not record_problems(rev, not_before=not_before) and rev.get("text_hash") == text_hash(text)


def bound(rev, text, roster, *, not_before=None) -> dict | None:
    """The person who reviewed ``text``: ``person(rev, roster)`` when its text_hash is that text's and its date is
    not before ``not_before``; otherwise None (no sign-off, a reviewer not on the list, or a sign-off for another
    version of the text)."""
    if problems(rev, roster, not_before=not_before):
        return None
    p = person(rev, roster)
    return p if p and p.get("text_hash") == text_hash(text) else None


def bind(rev, text) -> dict | None:
    """The review record to store with a copy of ``text``: the reviewer's id, the date and the statement from
    ``rev`` (a record or a ``person``), with the hash of ``text``; None when ``rev`` is not a well-formed record.
    The name is never stored with it: a page reads it from the list."""
    if not isinstance(rev, dict):
        return None
    rec = {"reviewer": rev.get("reviewer"), "date": iso_date(rev.get("date")), "attested": rev.get("attested")}
    if record_problems(rec):
        return None
    return {**rec, "text_hash": text_hash(text)}


def line(who) -> str | None:
    """'Reviewed by <name>, <role>, on <date>' ('<role> licensed in <state>' for an attorney; no role for "other
    person": 'Reviewed by <name> on <date>'), for a reviewer as ``person`` or ``bound`` gives them; else None."""
    if not isinstance(who, dict) or not who.get("name") or not role_of(who.get("role")) or not iso_date(who.get("date")):
        return None
    role = role_of(who["role"])
    if role == NO_ROLE_SHOWN:
        return f"Reviewed by {who['name']} on {long_date(who['date'])}"
    if who.get("licensed_in"):
        role = f"{role} licensed in {who['licensed_in']}"
    return f"Reviewed by {who['name']}, {role}, on {long_date(who['date'])}"
