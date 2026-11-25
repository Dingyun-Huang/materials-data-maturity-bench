# Materials extraction benchmark reference sets

Reference data accompanying the manuscript on materials-data maturity and
ChemDataExtractor, DeepSeek Flash and Qwen extraction. This folder is portable:
copy it into the manuscript repository without the surrounding workspace.

## Choose the correct reference population

| Reference set | Files | Population |
|---|---|---|
| Historical single-property ΔE_ST (M1/M2) | `st_only/rsc.csv`, `st_only/elsevier.csv` | 171 RSC + 127 Elsevier = 298 observations |
| Released material–λ_PL–ΔE_ST associations | `triplet_gold/v1.0.1/gold.jsonl` | 799 complete records, 100 articles; 54 positive and 46 negative |
| Unique association cores (M3) | `triplet_gold/core_associations.jsonl` | 735 distinct DOI/material/λ_PL/ΔE_ST cores |
| Properties participating in reference associations | `triplet_component_properties/{pl,gap}_core.jsonl` | 382 λ_PL and 223 ΔE_ST cores |
| All eligible property claims, including unpaired observations | `all_observations/{pl,gap}_core.jsonl` | 604 λ_PL and 293 ΔE_ST cores |
| All-observation metadata reference views | `all_observations/{pl,gap}_metadata.jsonl` | 624 λ_PL and 302 ΔE_ST records, distinguished by conditions/masks |

These populations answer different questions. The 298 historical ΔE_ST labels
are not interchangeable with the 293 all-observation cores. Association and
standalone-property recall denominators also differ. Metadata records may share
a core value while retaining different sample conditions.

`corpus.jsonl` indexes the 100 articles (50 RSC/50 Elsevier) with DOI links,
publisher, expected input filename, text length and SHA-256. Full article texts
and publisher HTML/XML are not included. Article hash/offset verification
requires obtaining the exact corresponding text separately.

## Data layout and interpretation

`triplet_gold/v1.0.1/` is a byte-for-byte copy of the immutable gold release,
including its original checksums, protocol, rich observations, evidence,
provenance, accepted aliases, masks and review history. Its README documents
validation and release limitations. Historical local paths in its original
manifest are provenance; use the portable top-level corpus index instead.
Script snapshots and extraction prompts inside that release are archival
artifacts, not a new recommended extraction prompt or standalone evaluator.

The derived JSONL views each contain one object per article, with `doi`,
`publisher` and `records`; empty lists are retained. Property records identify
`material_id_in_doc`, `value` and `unit`. Values in these derived views are
normalised numeric strings using the existing reference loader; the original
release remains unchanged. Metadata views retain `metadata`, observation IDs,
explicit accepted variants and `excluded_metadata_fields`.

Association `accepted_core_variants` entries have the order
`[material ID, PL value, PL unit, gap value, gap unit]`. Property variants have
`[material ID, value, unit]`, or equivalent named objects in all-observation
views. `source_record_ids` link projections to the released association records.
Accepted variants express documented alternatives; they are not extra claims.

The historical CSVs are copied unchanged. RSC uses `delta_est_value`, `unit`
and `concentration_or_doping`; Elsevier uses `stsplit_value`, `stsplit_unit`
and `concentration`. Open with UTF-8/BOM-aware CSV parsing. Do not replace the
127-row Elsevier file here with the earlier 125-row workspace snapshot.

## Matching and unresolved metadata

See `documentation/` for the M2 protocol and core/property evaluator guides.
The historical ST-only M2 ruleset is 2.2; association and projected-property
core rulesets are 1.1. Historical M1 manuscript comparisons retain their
method-specific conventions, as described in the evaluator documentation.
This data folder does not supply or replace executable performance evaluators.

Always load `triplet_gold/v1.0.1/scoring_masks.jsonl` with full-record gold.
Unresolved fields are excluded on both reference and prediction sides, receiving
neither credit nor penalty. They are not confirmed absent values. Metadata-view
`excluded_metadata_fields` provides the corresponding property-level masks,
including unpaired observations. Other absent metadata retains its annotation
meaning. Honour accepted source-backed variants and one-to-one matching.

Reference-supported aliases assist evaluation; do not use them to construct
prediction joins in a gold-independent pairing workflow. Apply prediction
normalisation without rewriting the released reference labels.

## Integrity and provenance

Run from anywhere using standard-library Python:

```sh
python verify.py
```

`SHA256SUMS` covers all other files recursively. The embedded original release
also retains its own checksum file. `REFERENCE_MANIFEST.json` identifies source
paths, input hashes, projection-code hashes and populations. Derived property
metadata views were checked against the reference-only projections saved by
the manuscript's standalone-property evaluations. No model predictions or
correctness flags were used to create labels, and no references were reannotated.
No new data licence is assigned by this packaging step.
