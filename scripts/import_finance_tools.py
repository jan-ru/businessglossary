"""One-off migration: finance-tools Markdown glossaries -> ``glossary/*.yaml``.

Usage: ``python scripts/import_finance_tools.py /path/to/finance-tools``

Three sources, each becoming one scheme: the Dutch GAAP/RGS glossary (caseware), the a-bos
investment-domain glossary and the repo vocabulary. Everything is imported as ``draft``.
After this runs once the YAML is the source of truth and this script is not re-run.
"""

from __future__ import annotations

import posixpath
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import yaml

REPO_URL = "https://github.com/jan-ru/finance-tools/blob/main/"
LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


@dataclass(frozen=True)
class Source:
    scheme_id: str
    path: str  # relative to the finance-tools checkout
    title: dict[str, str]
    description: str
    default_language: str


SOURCES = {
    "caseware": Source(
        "dutch-gaap",
        "caseware/docs/glossary.md",
        {"en": "Dutch GAAP and RGS", "nl": "Nederlandse jaarrekening en RGS"},
        "Dutch-accounting terminology used by caseware and the rendered jaarrekening.",
        "nl",
    ),
    "abos": Source(
        "investment",
        "a-bos/docs/events/glossary.md",
        {"en": "Investment and governance domain"},
        "Business concepts of the a-bos event model: investment lifecycle, governance, risk.",
        "en",
    ),
    "repo": Source(
        "finance-tools-repo",
        "docs/glossary.md",
        {"en": "finance-tools repository vocabulary"},
        "Engineering vocabulary of the finance-tools monorepo (structure, gates, release).",
        "en",
    ),
}

# Caseware rows whose first column is English, not Dutch.
ENGLISH_FIRST = {
    "level0 / level1",
    "balance side",
    "display order",
    "mapping (account → rgs)",
    "crosswalk (categorie → concept)",
    "override (account → concept)",
    "decision",
    "provenance",
}

# Links the source text states outright (not inferred): (concept, field, target).
RELATIONS = [
    ("geplaatst-kapitaal", "broader", "eigen-vermogen"),
    ("agio", "broader", "eigen-vermogen"),
    ("wettelijke-reserves", "broader", "eigen-vermogen"),
    ("statutaire-reserves", "broader", "eigen-vermogen"),
    ("overige-reserves", "broader", "eigen-vermogen"),
    ("onverdeeld-resultaat-van-het-boekjaar", "broader", "eigen-vermogen"),
    ("tegenboeking", "related", "correctieboeking"),
    ("rgs", "related", "nt"),
    ("nt", "related", "sbr"),
    ("rgs", "related", "sbr"),
    ("mapping-account-rgs", "related", "crosswalk-categorie-concept"),
    ("override-account-concept", "related", "crosswalk-categorie-concept"),
    ("decision", "related", "override-account-concept"),
    ("decision", "related", "provenance"),
    ("risk", "related", "risk-appetite"),
    ("risk", "related", "control"),
    ("governance", "related", "control"),
    ("governance", "related", "budget"),
    ("governance", "related", "approval"),
    ("governance", "related", "risk"),
]


def slug(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")


def plain(text: str) -> str:
    """Strip Markdown emphasis, code ticks and links to their text."""
    text = LINK.sub(r"\1", text)
    return re.sub(r"[`*]", "", text).strip()


def absolutize(text: str, file_dir: str) -> str:
    """Rewrite repo-relative Markdown links so they resolve outside finance-tools."""

    def fix(m: re.Match[str]) -> str:
        label, href = m.groups()
        if re.match(r"^(https?:|#)", href):
            return m.group(0)
        path, _, anchor = href.partition("#")
        url = REPO_URL + posixpath.normpath(posixpath.join(file_dir, path))
        return f"[{label}]({url}{'#' + anchor if anchor else ''})"

    return LINK.sub(fix, text)


def link_urls(text: str, file_dir: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(m.group(2) for m in LINK.finditer(absolutize(text, file_dir))))


def split_row(line: str) -> list[str]:
    return [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]


def tables(text: str):
    """Yield (heading, header cells, row cells) for every Markdown table."""
    heading, header, in_table = "", [], False
    for line in text.splitlines():
        if line.startswith("#"):
            heading, in_table = re.sub(r"^#+\s*(\d+\.\s*)?", "", line).strip(), False
        elif line.startswith("|"):
            cells = split_row(line)
            if not in_table:
                header, in_table = cells, True
            elif not set("".join(cells)) <= set("-: "):
                if len(cells) != len(header):
                    raise ValueError(f"row has {len(cells)} cells, header {len(header)}: {line[:80]}")
                yield heading, header, cells
        else:
            in_table = False


def labels(cell: str) -> tuple[str, list[str], list[str]]:
    """(preferred label, alternative labels, expansions) from a bold term cell."""
    head = cell.split(" (", 1)[0] if "(incl." in cell else cell
    bolds = [plain(b) for b in re.findall(r"\*\*(.+?)\*\*", head)]
    expansions = [plain(i) for i in re.findall(r"(?<!\*)\*([^*]+)\*(?!\*)", head)]
    return bolds[0], bolds[1:], expansions


def concept(pref: dict[str, str], definition: str, **extra) -> dict:
    out = {"id": slug(next(iter(pref.values()))), "pref_label": pref, "definition": definition}
    return {**out, **{k: v for k, v in extra.items() if v}}


def table_concepts(src: Source, text: str) -> list[dict]:
    file_dir = posixpath.dirname(src.path)
    lang, out = src.default_language, []
    for group, header, cells in tables(text):
        row = dict(zip((h.lower() for h in header), cells, strict=True))
        if header[0] == "Dutch term":
            first_text = plain(cells[0])
            if first_text.lower() in ENGLISH_FIRST:
                pref, alt = {"en": first_text}, {"en": [plain(cells[1])]}
                item_id = slug(first_text)
            else:
                nl, alts, expansions = labels(cells[0])
                pref, item_id = {"nl": nl, "en": plain(cells[1])}, slug(nl)
                alt = {"nl": alts + expansions}
            definition = absolutize(cells[2], file_dir)
            out.append(
                concept(pref, definition, id=item_id, alt_labels={k: v for k, v in alt.items() if v}, group=group)
            )
        elif header[0] == "Term" and "where it appears" in row:
            pref_label, alts, _ = labels(cells[0])
            out.append(
                concept(
                    {"en": pref_label},
                    absolutize(row["what it means here"], file_dir),
                    alt_labels={"en": alts},
                    group=group,
                    properties={"where": [plain(row["where it appears"])]},
                )
            )
        else:  # Term | Meaning | Owner
            pref_label, alts, _ = labels(cells[0])
            owner = row["owner"]
            out.append(
                concept(
                    {lang: pref_label},
                    absolutize(row["meaning"], file_dir),
                    alt_labels={lang: alts},
                    group=group,
                    sources=link_urls(owner, file_dir),
                    properties={"source_text": [plain(owner)]},
                )
            )
    return out


ABOS_LABELS = {
    "Aggregate": "aggregate",
    "Possible States": "states",
    "Related Events": "events",
    "Examples": "examples",
    "Relationship": "relationship",
}


def abos_concepts(src: Source, text: str) -> list[dict]:
    file_dir, out = posixpath.dirname(src.path), []
    for block in re.split(r"\n---\n", text):
        m = re.search(r"^## (.+)$", block, re.MULTILINE)
        if not m:
            continue
        title, lines = m.group(1).strip(), block[m.end() :].strip().splitlines()
        definition, props, current = [], {}, None
        for line in lines:
            label = re.match(r"^([A-Za-z ]+):$", line)
            if label and label.group(1) in ABOS_LABELS:
                current = props.setdefault(ABOS_LABELS[label.group(1)], [])
            elif current is not None and line.startswith("- "):
                current.append(line[2:].strip())
            elif current is None:
                definition.append(line)
        text_def = absolutize("\n".join(definition).strip(), file_dir)
        out.append(concept({"en": title}, text_def, sources=link_urls(text_def, file_dir), properties=props))
    return out


def with_relations(concepts: list[dict]) -> list[dict]:
    by_id = {c["id"]: c for c in concepts}
    for src_id, field, target in RELATIONS:
        if src_id in by_id:
            by_id[src_id][field] = [*by_id[src_id].get(field, []), target]
    return concepts


def dump(path: Path, data: dict) -> None:
    yaml.add_representer(
        str,
        lambda d, s: d.represent_scalar("tag:yaml.org,2002:str", s, style="|" if "\n" in s else None),
        Dumper=yaml.SafeDumper,
    )
    path.write_text(
        yaml.dump(data, Dumper=yaml.SafeDumper, sort_keys=False, allow_unicode=True, width=100), encoding="utf-8"
    )


def main(checkout: Path, out_dir: Path) -> None:
    out_dir.mkdir(exist_ok=True)
    all_concepts: dict[str, list[dict]] = {}
    for key, src in SOURCES.items():
        text = (checkout / src.path).read_text(encoding="utf-8")
        all_concepts[key] = abos_concepts(src, text) if key == "abos" else table_concepts(src, text)
    merged = with_relations([c for cs in all_concepts.values() for c in cs])
    ids = {c["id"] for c in merged}
    if len(ids) != len(merged):
        raise SystemExit("id collision across sources; resolve before writing")
    for key, src in SOURCES.items():
        dump(
            out_dir / f"{src.scheme_id}.yaml",
            {
                "id": src.scheme_id,
                "title": src.title,
                "description": src.description,
                "default_language": src.default_language,
                "imported_from": f"finance-tools:{src.path}",
                "concepts": all_concepts[key],
            },
        )
        print(f"{src.scheme_id}: {len(all_concepts[key])} concepts")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(__file__).resolve().parent.parent / "glossary")
