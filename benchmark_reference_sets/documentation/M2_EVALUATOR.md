# Consolidated M2 evaluator — usage and historical v2.0 results

Current aligned DS Flash/Qwen/CDE results use 171 RSC / 127 Elsevier labels and
ruleset 2.2. See `evaluation_results/M2_DS_FLASH_SPREADSHEET_RERUN.md` and
`evaluation_results/M2_SHARED_171_127_COMPARISON.json`. DS input export uses
`scripts/export_ds_st_predictions.py`; older manual and 166-row results below
are historical, not the current comparison.

`scripts/evaluate.py` is the maintained ST-only M2 evaluator (currently ruleset 2.2). Run it
with explicit dataset paths. The agreed scoring policy remains in
`M2_EVALUATION_PROTOCOL.md`.

## Usage

Run from the repository root with fresh output directories:

```sh
python scripts/evaluate.py \
  --predictions mining_results/naive-ollama-qwen3.5-9b-non-thinking/delta_est_elsevier_v3.csv \
  --annotations annotation/elsevier_50_stsplit_annotated.csv \
  --output /tmp/elsevier-m2-check

python scripts/evaluate.py \
  --predictions mining_results/naive-ollama-qwen3.5-9b-non-thinking/delta_est_rsc_v3.csv \
  --annotations annotation/rsc_50_stsplit_annotated.csv \
  --output /tmp/rsc-m2-check
```

The Elsevier example uses the current 125-record reference. To reproduce the saved
127-record evaluations, use `mining_results/naive-ds-flash-non-thinking/elsevier_50_annotated.csv`.
See `evaluation_results/M2_RULESET_2_2_RERUN.md` for current results and archived runs.
Inputs must match by hash when attributing score changes to an evaluator change.


The defaults use pipe-delimited predictions and comma-delimited annotations.
Override them with `--prediction-delimiter` and `--annotation-delimiter`.
Both input readers recognize `delta_est_value`/`stsplit_value`,
`unit`/`stsplit_unit`, and `concentration_or_doping`/`concentration`.
Quoted delimiters and multiline fields are supported. Invalid column counts,
missing required fields, ambiguous column mappings, and nonfinite or invalid
ST-splitting values stop evaluation with an error instead of silently dropping rows.

## Consolidated behavior

- Preserves raw predictions and logs field redistribution and duplicate-name cleaning.
- Preserves chemical-name structure and accepts balanced whole-name outer brackets.
- Splits Zeonex/CBP composite conditions into the relevant fields. The host must
  have a recognized identity; adjectives such as `state`, `solid-state`, `neat`,
  and `theoretical` are not promoted to host names.
- Accepts approved percentage, exponent, solvent-alias, host-expansion, and
  theoretical-phase conventions. Host aliases are explicit and included in the summary.
- Recognizes host trademark typography (`Zeonex®`, `Zeonex™`).
- Distinguishes `PPF/CBP` from `PPF` and `toluene-d8` from `toluene`.
- Retains raw-condition checks so a conflicting percentage or emitter host label
  cannot be hidden by redistribution.
- Keeps DOI punctuation and numeric signs. Decimal spelling differences and
  equivalent eV/meV quantities are accepted; fuzzy values are not used.
- Assigns records one-to-one, maximizing complete matches first. Equal-quality
  assignments prefer earlier prediction/annotation rows deterministically.
- Keeps strict null semantics except for the explicitly agreed cleanup and
  theoretical-phase exceptions. `pristine` establishes purity, not crystallinity.

Method and source-quote text can establish that a record is theoretical; they are
not independent scored fields and are not checked against an external article.
Unknown composite host descriptions should be reviewed before adding a new alias
or parser pattern. The evaluator does not resolve arbitrary chemical synonyms or
infer missing experimental context.

## Outputs and reproducibility

Each output folder contains:

- `prediction_audit.csv`: every prediction, processed/raw attributes, rules,
  error text, and an `errors_json` list for downstream analysis.
- `unmatched_annotations.csv`: every false negative, including annotations whose
  paired prediction failed an M2 attribute.
- `summary.json`: counts, metrics, status distribution, ruleset version, aliases,
  delimiters, input paths, and SHA-256 hashes of inputs and evaluator.
- `evaluator_snapshot.py`: the exact evaluator used for this run. Replay it with
  explicit input and output arguments as in the first example above.

`matched_annotation_row` is populated only for an actual one-to-one assignment.
`reference_annotation_row` also includes diagnostic comparisons for duplicates
and predictions without a core match; these references do not count as matches.
Source row numbers count CSV records including the header. `physical_end_line`
locates the end of a prediction record when quoted fields contain newlines.

The evaluator checks audit totals, unique assignments, and error coverage before
reporting metrics. A metric with an empty denominator is JSON `null`.

## Regression checks and reviewed changes

Run `PYTHONPATH=scripts python -m unittest discover -s tests -v` for the full suite.
The ST-only evaluator tests cover the
agreed examples, counterexamples, quoted multiline inputs, duplicates, and FN
accounting. The results below are historical ruleset 2.0 results, not current scores.

Historical `consolidated_v2` outputs and earlier audits are preserved under
`evaluation_results/archive/`. Current evaluations occupy the top-level
`evaluation_results/m2_evaluation_*` folders.

| Dataset | Earlier TP | Revised TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| RSC | 67 | 73 | 79 | 93 | 48.03% | 43.98% | 45.91% |
| Elsevier | 60 | 62 | 65 | 65 | 48.82% | 48.82% | 48.82% |

All net score changes fix hosts invented by the earlier condition parser:

| Dataset / prediction row | Material | Removed erroneous host assignment |
|---|---|---|
| RSC 3 | PmPmP | `amorphous neat` (the phase establishes pure film) |
| RSC 18 | OPDPO | `solid-state` |
| RSC 27, 28 | Ag14-dcbdt | `state` |
| RSC 106 | TB2CZ-ACTRZ | `state` |
| RSC 107 | TB14CZ-ACTRZ | `state` |
| Elsevier 56 | 2-Ac | `solid state` |
| Elsevier 57 | 4-Ac | `solid state` |

Deterministic tie-breaking also changes which identical prediction receives the
TP without changing any group count: RSC 138 replaces 142; Elsevier 66/67 replace
70/71 and 93/94 replace 97/98. All surplus duplicates remain false positives.

## Released-gold CDE single-property evaluations

The historical ST-only CSV evaluations above remain preserved. A separate comparison against **all eligible observations** in triplet gold v1.0.0 is available for both CDE properties:

- PL: `evaluation_results/pl_cde_all_observations_v1/README.md`.
- Gap: `evaluation_results/stsplit_cde_all_observations_v1/README.md`.

Use `scripts/evaluate_cde_pl.py --property pl` (default) or `--property gap`, with explicit `--predictions` files and a fresh `--output`. Both reuse triplet-core 1.1 material/quantity normalization and ST M2 2.2 metadata equivalences. Core scores deduplicate value/unit/material claims; M2 scores one-to-one metadata records and penalizes surplus predictions. PL adds temperature; gap does not. Unresolved fields in rich annotations are masked. Method, uncertainty, and source quotes are audit-only.

The gap reference projects 305 observations to 293 unique core claims and 302 scored-metadata records. These are not automatically interchangeable with either the earlier 293-record ST-only reference or the 223 gap cores participating in released triplets. Read the source/reference hashes and scope before comparing scores.

CDE adapter version 1.1 accepts table-header punctuation artifacts around recognized unit tokens (`eV)(`, `(meV}`, `nm)/(`). It directly calls this M2 evaluator's `process_prediction` and `field_comparison`; parser placeholder/unit cleanup, released material aliases, core set counting and PL temperature handling are additional adapter/core-module behavior. Current all-observation CDE outputs against gold v1.0.1 are under `evaluation_results/gold_v1_0_1/*_cde_all_observations_units_v1_1/`. Earlier outputs remain historical.
