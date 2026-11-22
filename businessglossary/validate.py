"""Consistency checks the schema alone cannot express.

``validate`` returns a list of problems (empty means valid); it never raises, so a caller
can report them all at once.
"""

from __future__ import annotations

import re
from collections import Counter

from businessglossary.model import LANG_PATTERN, PIVOT_LANGUAGE, Concept, Scheme


def _all_concepts(schemes: tuple[Scheme, ...]) -> list[Concept]:
    return [c for s in schemes for c in s.concepts]


def _duplicate_ids(concepts: list[Concept]) -> list[str]:
    counts = Counter(c.id for c in concepts)
    return [f"duplicate id: {i} ({n} times)" for i, n in counts.items() if n > 1]


def _label_problems(concept: Concept) -> list[str]:
    problems = []
    langs = [*concept.pref_label, *concept.alt_labels]
    problems += [f"{concept.id}: bad language tag {lang!r}" for lang in langs if not re.match(LANG_PATTERN, lang)]
    if PIVOT_LANGUAGE not in concept.pref_label:
        problems.append(f"{concept.id}: no {PIVOT_LANGUAGE!r} prefLabel")
    problems += [
        f"{concept.id}: empty prefLabel for {lang!r}" for lang, v in concept.pref_label.items() if not v.strip()
    ]
    if concept.status == "approved" and not concept.owner:
        problems.append(f"{concept.id}: approved terms need an owner")
    return problems


def _link_problems(concept: Concept, ids: set[str]) -> list[str]:
    problems = []
    for field in ("broader", "related"):
        for target in getattr(concept, field):
            if target == concept.id:
                problems.append(f"{concept.id}: {field} points at itself")
            elif target not in ids:
                problems.append(f"{concept.id}: {field} -> unknown id {target!r}")
    return problems


def _broader_cycles(concepts: list[Concept]) -> list[str]:
    parents = {c.id: c.broader for c in concepts}
    problems: list[str] = []
    for start, start_parents in parents.items():
        stack, seen = list(start_parents), set()
        while stack:
            node = stack.pop()
            if node == start:
                problems.append(f"{start}: broader cycle")
                break
            if node not in seen:
                seen.add(node)
                stack.extend(parents.get(node, ()))
    return problems


def validate(schemes: tuple[Scheme, ...]) -> list[str]:
    """Every problem found across ``schemes``."""
    concepts = _all_concepts(schemes)
    ids = {c.id for c in concepts}
    problems = _duplicate_ids(concepts)
    for concept in concepts:
        problems += _label_problems(concept)
        problems += _link_problems(concept, ids)
    return problems + _broader_cycles(concepts)
