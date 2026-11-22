"""Exports: a plain JSON document for apps, and SKOS as JSON-LD for semantic tooling.

``to_json`` is the shape ``finance-tools`` and ``my-svelte-app`` consume; it adds the
inverse ``narrower`` and symmetric ``related`` links so a reader needs no graph logic.
``to_jsonld`` is the same data as ``skos:Concept`` nodes (load it with ``rdflib`` to get
Turtle, ``rdflib.Graph().parse(data=..., format="json-ld")``).
"""

from __future__ import annotations

from typing import Any

from businessglossary.model import Concept, Scheme

BASE_IRI = "https://jan-ru.github.io/businessglossary/"
SKOS_CONTEXT = {
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "dcterms": "http://purl.org/dc/terms/",
    "bg": BASE_IRI + "vocab#",
}


def _concept_iri(concept_id: str) -> str:
    return f"{BASE_IRI}term/{concept_id}"


def _scheme_iri(scheme_id: str) -> str:
    return f"{BASE_IRI}scheme/{scheme_id}"


def _narrower(concepts: list[Concept]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {c.id: [] for c in concepts}
    for c in concepts:
        for parent in c.broader:
            out[parent].append(c.id)
    return out


def _related(concepts: list[Concept]) -> dict[str, list[str]]:
    out: dict[str, set[str]] = {c.id: set() for c in concepts}
    for c in concepts:
        for other in c.related:
            out[c.id].add(other)
            out[other].add(c.id)
    return {k: sorted(v) for k, v in out.items()}


def to_json(schemes: tuple[Scheme, ...]) -> dict[str, Any]:
    """The plain JSON export, with ``narrower`` and symmetric ``related`` filled in."""
    concepts = [c for s in schemes for c in s.concepts]
    narrower, related = _narrower(concepts), _related(concepts)
    return {
        "schemes": [
            {"id": s.id, "title": s.title, "description": s.description, "imported_from": s.imported_from}
            for s in schemes
        ],
        "concepts": [
            {
                **c.model_dump(mode="json", exclude={"related"}),
                "scheme": s.id,
                "iri": _concept_iri(c.id),
                "narrower": narrower[c.id],
                "related": related[c.id],
            }
            for s in schemes
            for c in s.concepts
        ],
    }


def _lang_values(by_lang: dict[str, str | tuple[str, ...]]) -> list[dict[str, str]]:
    out = []
    for lang, value in by_lang.items():
        for v in [value] if isinstance(value, str) else value:
            out.append({"@language": lang, "@value": v})
    return out


def _concept_node(c: Concept, scheme: Scheme, related: list[str]) -> dict[str, Any]:
    node: dict[str, Any] = {
        "@id": _concept_iri(c.id),
        "@type": "skos:Concept",
        "skos:inScheme": {"@id": _scheme_iri(scheme.id)},
        "skos:prefLabel": _lang_values(c.pref_label),
        "skos:definition": {"@language": scheme.definition_language, "@value": c.definition},
        "bg:status": c.status,
    }
    if c.alt_labels:
        node["skos:altLabel"] = _lang_values(c.alt_labels)
    if c.broader:
        node["skos:broader"] = [{"@id": _concept_iri(b)} for b in c.broader]
    if related:
        node["skos:related"] = [{"@id": _concept_iri(r)} for r in related]
    if c.sources:
        node["dcterms:source"] = [{"@id": s} for s in c.sources]
    return node


def to_jsonld(schemes: tuple[Scheme, ...]) -> dict[str, Any]:
    """The glossary as SKOS in JSON-LD."""
    related = _related([c for s in schemes for c in s.concepts])
    graph: list[dict[str, Any]] = []
    for s in schemes:
        graph.append(
            {
                "@id": _scheme_iri(s.id),
                "@type": "skos:ConceptScheme",
                "dcterms:title": _lang_values(s.title),
            }
        )
        graph += [_concept_node(c, s, related[c.id]) for c in s.concepts]
    return {"@context": SKOS_CONTEXT, "@graph": graph}
