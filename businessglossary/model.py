"""The glossary data model: SKOS-shaped, immutable, loaded from YAML.

A *scheme* (``skos:ConceptScheme``) groups *concepts* (``skos:Concept``). Labels are per
language, ``broader`` / ``related`` hold concept ids, and ``properties`` carries domain
attributes that SKOS has no slot for (an aggregate's states, its events, ...).
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

ID_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"
LANG_PATTERN = r"^[a-z]{2}$"
PIVOT_LANGUAGE = "en"  # every concept must carry a label in this language

Status = Literal["draft", "approved", "deprecated"]


class Concept(BaseModel):
    """One glossary term."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=ID_PATTERN)
    pref_label: dict[str, str]
    definition: str = Field(min_length=1)
    alt_labels: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    broader: tuple[str, ...] = ()
    related: tuple[str, ...] = ()
    group: str | None = None
    sources: tuple[str, ...] = ()
    properties: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    status: Status = "draft"
    owner: str | None = None


class Scheme(BaseModel):
    """A set of concepts from one source or domain."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=ID_PATTERN)
    title: dict[str, str]
    description: str = ""
    default_language: str = Field(default=PIVOT_LANGUAGE, pattern=LANG_PATTERN)
    definition_language: str = Field(default=PIVOT_LANGUAGE, pattern=LANG_PATTERN)
    imported_from: str | None = None
    concepts: tuple[Concept, ...] = ()


def load_scheme(path: Path) -> Scheme:
    """Read one scheme file."""
    return Scheme.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def load_glossary(directory: Path) -> tuple[Scheme, ...]:
    """Read every ``*.yaml`` scheme in ``directory``, in file-name order."""
    return tuple(load_scheme(p) for p in sorted(directory.glob("*.yaml")))
