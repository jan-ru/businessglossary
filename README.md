# businessglossary

A business glossary modelled as SKOS concepts, kept as YAML in git, validated in CI and
exported as JSON (for apps) and JSON-LD (for semantic tooling).

## Layout

| Path | What |
|---|---|
| `glossary/*.yaml` | The terms: one file per scheme (source of truth) |
| `businessglossary/model.py` | Frozen pydantic model: `Scheme`, `Concept` |
| `businessglossary/validate.py` | Unique ids, links resolve, no `broader` cycles, `en` label required |
| `businessglossary/export.py` | `to_json` (adds `narrower`, symmetric `related`) and `to_jsonld` (SKOS) |
| `scripts/import_finance_tools.py` | One-off migration from the finance-tools Markdown glossaries |

## Use

```bash
uv sync                                   # Python 3.13+, installs deps into .venv
uv run python -m businessglossary validate
uv run python -m businessglossary export --format json --out dist/glossary.json
uv run python -m businessglossary export --format jsonld --out dist/glossary.jsonld
uv run pytest
uv run ruff check && uv run ruff format --check
```

## Term shape

```yaml
- id: eigen-vermogen          # lowercase slug, unique across all schemes
  pref_label: {nl: Eigen vermogen, en: Shareholders' equity}   # `en` is required
  definition: ...
  alt_labels: {nl: [...]}
  broader: [...]              # skos:broader (is-a / part-of)
  related: [...]              # skos:related (symmetric in the export)
  group: ...                  # heading it was listed under
  sources: [https://...]
  properties: {states: [...], events: [...]}   # domain attributes SKOS has no slot for
  status: draft               # draft | approved | deprecated (approved needs an owner)
  owner: ...
```

## Seeded content

`glossary/` was seeded from three finance-tools glossaries (Dutch GAAP/RGS, the a-bos
investment domain, and the repo vocabulary). Every imported term is `draft`; links
(`broader`/`related`) were added only where the source text states them.
