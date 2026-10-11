"""The website crawl: stored website values that are not addresses, hosts it must not reach, and a run that
survives any one site's failure."""
import socket

import pytest

from lexflow.municipal import crawl as CR
from lexflow.store import db


@pytest.mark.parametrize("raw, ok", [
    ("www.charlottesville.gov", True),
    ("https://www.baltimorecity.gov/dhcd", True),
    ("münchen.de", True),                                   # an international domain, sent as punycode
    ("www.cityofelginor.org..under.construction", False),   # the Census value that stopped the crawl
    ("http://www.example .org", False),
    ("ftp://records.example.org", False),
    ("http://records.example.org:8080", False),
    ("http://localhost", False),
    ("http://-bad-.example.org", False),
    ("http://" + "a" * 64 + ".example.org", False),
    ("http://example.123", False),
    ("", False),
    (None, False),
])
def test_clean_url(raw, ok):
    assert (CR.clean_url(raw) is not None) is ok


def _resolve(ip):
    return lambda host, port, *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))]


def test_hosts_that_reach_this_machine_are_refused(monkeypatch):
    for ip in ("127.0.0.1", "10.0.0.5", "172.18.0.3", "192.168.1.1", "169.254.169.254"):
        monkeypatch.setattr(socket, "getaddrinfo", _resolve(ip))
        with pytest.raises(CR.Refused):
            CR._check_host("http://hijacked.example.org/")
    with pytest.raises(CR.Refused):
        CR._check_host("http://ollama:11434/api/tags")
    monkeypatch.setattr(socket, "getaddrinfo", _resolve("93.184.215.14"))
    CR._check_host("https://www.example.org/")              # a public address passes


def test_a_lapsed_domain_is_reported_as_dns(monkeypatch):
    def fail(*a, **k):
        raise socket.gaierror("Name or service not known")
    monkeypatch.setattr(socket, "getaddrinfo", fail)
    assert CR.scan_page("http://lapsed.example.org")["status"] == "dns"


def test_an_invalid_value_is_never_fetched(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: pytest.fail("no lookup for an invalid value"))
    assert CR.scan_page("www.cityofelginor.org..under.construction")["status"] == "invalid-url"


class _Resp:
    def __init__(self, location):
        self.headers, self.is_redirect, self.status_code, self.url = {"Location": location}, True, 302, ""

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_redirects_are_checked_hop_by_hop(monkeypatch):
    seen = []

    def resolve(host, port, *a, **k):
        seen.append(host)
        ip = "127.0.0.1" if host == "inside.example.org" else "93.184.215.14"
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))]
    monkeypatch.setattr(socket, "getaddrinfo", resolve)

    class Session:
        def get(self, url, **kw):
            assert kw.get("allow_redirects") is False
            return _Resp("http://inside.example.org/admin")
    with pytest.raises(CR.Refused):
        CR._get(Session(), "http://www.example.org/")
    assert seen == ["www.example.org", "inside.example.org"]


def test_one_failing_site_does_not_end_the_run(con, monkeypatch):
    db.upsert(con, "governments", [
        {"gov_id": f"g{i}", "state": "or", "name": f"Town {i}", "kind": "municipality", "website": w}
        for i, w in enumerate(["www.one.example.org", "www.cityofelginor.org..under.construction", "www.three.example.org"])])
    con.commit()

    def scan(url):
        if "three" in url:
            raise RuntimeError("boom")
        return {"status": "invalid-url" if not CR.clean_url(url) else "ok", "url": url, "pages": {}, "emails": [],
                "phones": []}
    monkeypatch.setattr(CR, "scan_page", scan)
    out = CR.run(con, "or", log=lambda *_: None, workers=1)
    assert out["sites"] == 3 and out["invalid"] == 1 and out["failed"] == 1
    status = dict(con.execute("SELECT gov_id, status FROM crawl_log").fetchall())
    assert status == {"g0": "ok", "g1": "invalid-url", "g2": "error"}
