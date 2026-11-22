"""Tests for the glossary model, validation and export."""

from pathlib import Path

from businessglossary.export import to_json, to_jsonld
from businessglossary.model import Concept, Scheme, load_glossary
from businessglossary.validate import validate

GLOSSARY_DIR = Path(__file__).resolve().parent.parent / "glossary"


def concept(cid: str, **kw) -> Concept:
    return Concept(id=cid, pref_label=kw.pop("pref_label", {"en": cid}), definition="d", **kw)


def scheme(*concepts: Concept) -> tuple[Scheme, ...]:
    return (Scheme(id="s", title={"en": "S"}, concepts=concepts),)


def test_real_glossary_is_valid():
    assert validate(load_glossary(GLOSSARY_DIR)) == []


def test_duplicate_id():
    assert any("duplicate id: a" in p for p in validate(scheme(concept("a"), concept("a"))))


def test_dangling_and_self_links():
    problems = validate(scheme(concept("a", broader=("zzz",), related=("a",))))
    assert any("unknown id" in p for p in problems)
    assert any("points at itself" in p for p in problems)


def test_broader_cycle():
    problems = validate(scheme(concept("a", broader=("b",)), concept("b", broader=("a",))))
    assert any("broader cycle" in p for p in problems)


def test_pivot_label_required():
    assert any("no 'en' prefLabel" in p for p in validate(scheme(concept("a", pref_label={"nl": "a"}))))


def test_approved_needs_owner():
    assert any("need an owner" in p for p in validate(scheme(concept("a", status="approved"))))


def test_json_export_adds_inverse_links():
    data = to_json(scheme(concept("parent"), concept("child", broader=("parent",), related=("parent",))))
    by_id = {c["id"]: c for c in data["concepts"]}
    assert by_id["parent"]["narrower"] == ["child"]
    assert by_id["parent"]["related"] == ["child"]  # related is symmetric


def test_jsonld_is_skos():
    graph = to_jsonld(scheme(concept("a", pref_label={"en": "A", "nl": "Aa"})))["@graph"]
    node = next(n for n in graph if n["@type"] == "skos:Concept")
    assert {"@language": "nl", "@value": "Aa"} in node["skos:prefLabel"]
    assert any(n["@type"] == "skos:ConceptScheme" for n in graph)
