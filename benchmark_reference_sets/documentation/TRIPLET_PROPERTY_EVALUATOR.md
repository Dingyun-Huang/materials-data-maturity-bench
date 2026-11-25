# Individual-property scores and Cartesian-pairing diagnosis

`scripts/evaluate_triplet_properties.py` measures PL and ΔEST core claims separately, then tests the effect of complete same-material Cartesian pairing. It reuses the core evaluator's exact quantity normalization, explicit material aliases, accepted precision alternatives, and maximum one-to-one assignment. No metadata or source-quote correctness is scored.

Ruleset 1.1 uses prediction-only chemical-name/identifier normalization, preserving literal gold names, as documented in `TRIPLET_CORE_EVALUATOR.md`. Each run includes `name_normalization_audit.jsonl`; `chemical_name` remains unscored. Gold checksums are verified before and after evaluation. Name-normalization changes must be held constant when comparing extraction methods or prompt versions.

## Run

```sh
python scripts/evaluate_triplet_properties.py \
  --predictions mining_results/naive-ds-flash-non-thinking/triplet/rsc_v2.1.jsonl \
                mining_results/naive-ds-flash-non-thinking/triplet/elsevier_v2.1.jsonl \
  --gold-release benchmark/triplet/releases/v1.0.0 \
  --output /tmp/triplet-properties-v2-1-check
```

Use another prediction directory or multiple JSONL files for other methods. Select files explicitly when a directory contains multiple versions; the example above uses only v2.1. Add `--publisher rsc` or `--publisher elsevier` to restrict the roster; otherwise the complete gold roster remains in the recall denominator. Existing output directories are not overwritten. The CLI verifies gold release checksums and saves input/evaluator hashes and snapshots.

## Individual properties

- PL claim: `(DOI, material identifier, wavelength value, wavelength unit)`.
- Gap claim: `(DOI, material identifier, gap value, gap unit)`.

Deduplicate each property independently of its paired property and optional metadata. Repeating one wavelength with four gaps produces one PL claim, not four. Score a valid property even if its partner is malformed; a malformed property is retained as an invalid FP. A wrong material ID or unit still prevents a property match.

The gold property denominator is the projection of **eligible released triplets**. Unpaired observations retained in rich annotations are excluded: the original task explicitly requires both properties before emitting a record. These scores therefore evaluate property coverage within the triplet extraction task, not independent extraction of every numerical property in the corpus.

Count TP/FP/FN by maximum-cardinality one-to-one matching. Precision is `TP / predicted claims`, recall is `TP / gold claims`; aggregate counts across papers before computing micro metrics. Explicit numerical alternatives share one gold claim's matching capacity. Empty denominators are null. Unit conversions and strict numerical equality follow `TRIPLET_CORE_EVALUATOR.md`.

## Cartesian diagnostic

1. Score the original output's core associations using the existing evaluator.
2. Collect all independently valid material–PL and material–gap claims present in that output, including valid components with a malformed partner.
3. For each document and normalized material identity, generate every PL × gap combination. Do not create new values, fix material IDs, or mix values from different materials.
4. Score these hypothetical pairs against the same gold core associations with the same one-to-one rules.
5. Report the additional true positives, remaining FNs, added FPs, recall change, and the proportion of original FNs recovered.

The increase in TP is the demonstrated recall loss recoverable by recombining **existing output claims**. Full recombination may also add FPs; the report includes its hypothetical precision. This is an analytical intervention, not a fresh LLM run or a guarantee that the new combinations are scientifically valid.

Each original FN also receives a diagnostic category:

| Category | Interpretation |
| --- | --- |
| Missing/wrong PL | An accepted gap claim is present; an accepted material–PL claim is not. |
| Missing/wrong gap | An accepted PL claim is present; an accepted material–gap claim is not. |
| Missing/wrong both | Neither accepted component is present under the required material identity. |
| Cartesian omission candidate | Both components are present and a new same-material pair can match this missing gold association. |
| Capacity/variant ambiguity | An original pair can match, but competing alternatives exhaust one-to-one capacity. |
| Incompatible variant/material context | Components individually match but cannot jointly form an accepted pair under the released provenance/alias rules. |

These categories sum to original FNs. Candidate counts need not equal recoverable TP gain in ambiguous cases: maximum matching gives the definitive gain. Property coverage checks use candidate presence rather than consuming each property again for every gold pair; a single correct wavelength can support multiple pairings.

## Outputs

- `summary.json`: overall and publisher property precision/recall/F1, original and recombined association scores, FN decomposition, failure coverage and hashes.
- `README.md`: short report, FN causes and papers benefiting from complete pairing, with DOI links.
- `property_audit.jsonl`: every unique predicted property, its contributing original record indexes and matching decision.
- `property_false_negatives.jsonl`: unmatched gold property cores and contributing gold record IDs.
- `association_false_negative_diagnosis.jsonl`: every original association FN, component-presence indicators and category.
- `cartesian_added_pairs.jsonl`: every hypothetical pair absent from the original core set, with candidate gold matches. These are diagnostic pairs, not corrected predictions.
- `paper_audit.jsonl`: source file/line, extraction status, property scores and pairing diagnosis for every paper.
- `prediction_inputs/`, `property_evaluator_snapshot.py`, `evaluate_triplet_core.py`: exact inputs and both evaluator implementations. Replay snapshots with explicit input, gold and output paths.

Property records visible here come only from emitted triplets. The analysis cannot tell whether the model internally recognized a property but failed to emit it, nor whether a missing accepted claim is caused by omission, wrong numerical value, wrong unit, or wrong material labeling. Failed or missing positive papers remain false negatives. Reference uncertainty does not automatically adjust these metrics.

Run all regression tests with `PYTHONPATH=scripts python -m unittest discover -s tests -v`.
