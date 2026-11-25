# M2 ST-Splitting Extraction Evaluation Protocol

This protocol records the evaluation decisions established while reviewing the Qwen RSC extraction. Use it when extending `scripts/evaluate.py` to new publishers, models, or extraction-result files. The protocol is intentionally audit-first: every cleanup and tolerant match must be visible in the output.

## 1. Scope and M2 definition

An extracted record is an M2 true positive only when one deduplicated annotation can be assigned to it one-to-one and all of the following are correct after approved deterministic preprocessing:

1. ST-splitting value
2. ST-splitting unit
3. Material ID used in the document
4. Chemical name, when supplied by the source; it should be systematic rather than merely repeating the material ID
5. Sample phase
6. Host or solvent
7. Mixture concentration or doping level

DOI identifies the source document and is part of the matching key. `value_error`, `method`, and `source_quote` are retained for auditing but are not M2-scored fields.

Use record-level metrics:

- `TP`: a prediction matched one-to-one to an annotation and passed every M2 field.
- `FP`: any prediction that is not a TP, including a duplicate prediction beyond the first matched instance.
- `FN`: any deduplicated annotation that has no one-to-one TP.
- `precision = TP / number_of_predictions`
- `recall = TP / number_of_annotations`
- `F1 = 2TP / (number_of_predictions + number_of_annotations)`

## 2. Null semantics

Treat blank strings and the literal `Null` as absent.

The default rule is strict: annotation `Null` means the information does not exist in the annotated context. A non-null prediction against annotation `Null` is therefore an error, not extra credit for specificity.

Approved exceptions are limited to deterministic cleanup or explicitly agreed inference rules:

- A predicted chemical name identical to `material_id_in_doc` is redundant and is removed before evaluation.
- For an explicitly theoretical/computational record, predicted `gas phase`, `vacuum`, or `single molecule` may match a null annotated phase.
- A blank predicted host with `neat` or `pristine` in the predicted phase may match annotated host `pure`.

Do not generalize these exceptions to unrelated non-null predictions.

## 3. Preserve raw data before preprocessing

For every M2 prediction field, preserve the raw value in the audit before changing it. The audit must contain both the raw and processed prediction plus a `processing_applied` column.

Preprocessing must be deterministic, reusable, and independent of which annotation happens to be selected, except for comparison-time equivalence rules.

## 4. Normalization and preprocessing

### 4.1 General null cleanup

- Apply Unicode NFKC normalization.
- Trim surrounding whitespace.
- Convert case-insensitive literal `Null` to an empty value.

### 4.2 Name normalization

Use the behavior established by `name_normalize` in `eval_qwen_stsplit_M2.py`:

- Remove ordinary and non-breaking whitespace.
- Normalize Unicode hyphen variants to ASCII `-`.
- Normalize prime variants to `'`.
- Compare case-insensitively.
- Preserve chemically meaningful brackets and punctuation.

Use this structure-preserving normalization for material IDs, chemical names, hosts/solvents, and exact concentration comparisons. Do not strip every punctuation character from chemical names.

The aggressive alphanumeric-only normalization is reserved for DOI/unit comparison and semantic category detection.

### 4.3 Redundant chemical names

If normalized `chemical_name` equals normalized `material_id_in_doc`, clear the predicted chemical name before evaluation. This is rule-based cleanup, not a chemical-name error.

Do not automatically clear a longer descriptive or guessed chemical name merely because it contains the material ID. If gold chemical name is null, such a prediction remains an error unless a new rule is explicitly approved.

### 4.4 Cross-field condition cleanup

Split simple composite conditions into their dedicated fields when the destination field is absent. Examples:

- `host_or_solvent = "CBP film 10%"`, blank phase/concentration → phase `film`, host `CBP`, concentration `10%`.
- `phase = "Zeonex 1% (w/w) film"`, blank host → phase `film`, host `Zeonex`, concentration `1% (w/w)` or its canonical percent value.

Recognized phase words include `film`, `solution`, `crystal/crystalline`, `solid/solid state`, and `powder` where supported by the evaluator.

Only split conditions with a clear syntactic pattern. Retain a trace of every move in `processing_applied`.

## 5. Core matching and duplicates

Build the core key from:

1. normalized DOI
2. numerically normalized ST-splitting value (for example `0.10` equals `0.1`)
3. normalized unit
4. name-normalized material ID

Do not use fuzzy value matching unless separately reviewed and approved. A substantively different value is not a formatting variant.

Within each identical core-key group, perform one-to-one assignment that maximizes, in order:

1. number of complete M2 matches
2. number of correct individual M2 fields
3. number of paired records

An annotation can be used at most once. If three predictions fully match one annotation, one is TP and the other two are duplicate FPs.

## 6. Approved field equivalences

### 6.1 Chemical name

Accept:

- Name-normalized equality.
- A pair differing only by one or more balanced outermost wrapping brackets, while preserving all internal structure.

Example accepted:

`(3-(4-(diphenylamino)phenyl)acenaphtho[1,2-b]pyrazino[2,3-e]pyrazine-9,10-dicarbonitrile)`

equals the same name without the outermost parentheses.

Reject:

- Material abbreviations presented as systematic names when gold expects a systematic name.
- Guessed descriptive names when the annotation is null, unless they were removed by the exact material-ID duplication rule.
- Structural differences that are not explained solely by approved Unicode/spacing/hyphen/prime normalization or whole-name outer brackets.

### 6.2 Phase

Accept compatible category wording when other condition fields do not conflict:

- `solution` versus `toluene solution` when host/solvent confirms toluene.
- `film` versus `film doped into Zeonex (1 wt%)` when host and concentration agree.
- `toluene solution` versus `toluene solution at 77 K`.
- `solid-state film`, `doped film`, or `film state` versus `film` when host/concentration agree.
- `crystalline state` versus `crystal`.

For records explicitly identified as theoretical/computational by method or source quote, accept `gas phase`, `vacuum`, or `single molecule` against a null gold phase. Evidence terms currently include DFT, TD-DFT, density functional, theoretical, level of theory, calculation, computed, and computational.

Do not infer that `pristine sample` means `crystal`; `pristine` only supports host `pure`. Do not accept contradictory categories such as film versus solution or microcrystal versus solution.

### 6.3 Host or solvent

Accept:

- Exact name-normalized equality.
- Standard aliases recorded in the evaluator, currently including `CHCl3` = chloroform and `CH2Cl2`/DCM = dichloromethane.
- An identifier plus a non-conflicting expansion or qualifier:
  - `PPF` equals `PPF (2,8-bis(diphenylphosphoryl)dibenzo[b,d]furan)`.
  - `PPF` equals `2,8-bis(diphenylphosphoryl)dibenzo[b,d]furan (PPF)`.
  - `polystyrene` equals `polystyrene (PS)`.
- A blank host plus an explicit `neat` or `pristine` predicted phase when gold host is `pure`.
- Host recovered deterministically from a composite phase/condition string.

Identifier matching must be boundary-aware. Do not accept arbitrary short string prefixes inside unrelated names.

### 6.4 Concentration

Accept:

- Name-normalized equality.
- Equal decimal percentages across `6%`, `6 wt%`, and `6% w/w`.
- A leading percent followed by a condition label, such as `18 wt%-emitter:PPF`, when gold is `18 wt%`.
- Scientific-notation typography variants such as `10−5 M` and `10^-5 M`.

Do not equate concentrations with different numeric values or incompatible concentration bases unless explicitly reviewed.

## 7. Cases that remain errors

Unless a new rule is approved, retain these as errors:

- Wrong ST-splitting value, unit, or material ID.
- A prediction from a DOI absent from the annotation set.
- Missing annotated phase, host/solvent, concentration, or chemical name.
- Non-null predicted context where gold is null, except the narrow approved exceptions above.
- Contradictory experimental conditions, such as DPEPO film versus 2-MeTHF solution.
- More predictions than matching annotations; surplus records are FPs even when textually identical.
- Vague inferences such as `pristine sample` = `crystal` without stronger evidence.

## 8. Audit outputs

Each run should create a new output folder and preserve at least:

### `prediction_audit.csv`

One row per prediction containing:

- `evaluation`: `correct` or `incorrect`
- `match_status`: normalized exact, semantic tolerance, incorrect core match, duplicate, or no core match
- prediction source line
- matched annotation row, when available
- `processing_applied`
- `tolerances_applied`
- detailed `errors`
- raw prediction M2 fields
- processed prediction M2 fields
- matched annotation M2 fields
- prediction method and source quote

Every incorrect prediction must have a non-empty error explanation.

### `unmatched_annotations.csv`

One row per FN, including whether:

- no prediction had the same core key;
- a same-core prediction existed but failed M2;
- all candidates were consumed by one-to-one assignment.

### `summary.json`

Record input counts, TP, FP, FN, precision, recall, F1, number of semantic-tolerance TPs, input/output filenames, and a concise description of active cleanup and tolerance rules.

Keep the evaluator script itself in the output folder or otherwise version it with the audit so the result is reproducible.

## 9. Review procedure for a new extraction file

1. Confirm both schemas, delimiters, row counts, and null conventions.
2. Map publisher-specific column names to the canonical fields used by the evaluator.
3. Preserve raw prediction values, then apply only approved preprocessing.
4. Run one-to-one M2 matching.
5. Validate basic invariants:
   - audit rows equal prediction rows;
   - correct audit rows equal TP;
   - incorrect audit rows equal FP;
   - FN audit rows equal FN;
   - every incorrect prediction has an error;
   - `TP + FP = predictions`;
   - `TP + FN = annotations`.
6. Review `incorrect_core_match` rows first, grouped by the number and type of failed fields.
7. Inspect single-field near-misses before multi-field mismatches.
8. Use only the local prediction, annotation, method, and source quote at this stage. Do not search online for source context unless the user later authorizes it.
9. Propose or add a new tolerance only when it is deterministic, chemically/semantically justified, and unlikely to merge genuinely different records.
10. Add a named tolerance label and positive/negative regression examples for every new rule.
11. Regenerate all audit files and rerun the invariants after each rule change.

## 10. Developing `evaluate.py` safely

- Parameterize prediction path, annotation path, output folder, delimiter, and annotation column mapping before applying the evaluator to another dataset.
- Keep normalization functions field-specific. Chemical names must not use the same destructive normalization as DOIs.
- Keep preprocessing separate from comparison. Raw values must remain auditable.
- Keep every semantic exception named in `tolerances_applied`.
- Prefer small, boundary-aware rules over general substring matching.
- Do not silently change a past score: regenerate `prediction_audit.csv`, `unmatched_annotations.csv`, and `summary.json` together.
- If a proposed rule requires interpreting scientific context rather than formatting or deterministic field redistribution, present representative records to the user for confirmation before applying it broadly.

## 11. Current RSC reference result

At the time this protocol was written, the active RSC evaluator reports:

- Predictions: 152
- Deduplicated annotations: 166
- TP: 67
- FP: 85
- FN: 99
- Precision: 44.08%
- Recall: 40.36%
- F1: 42.14%

These numbers are a regression reference, not a permanent target. They should change only when the input data or an explicitly recorded evaluation rule changes.

## 12. Consolidated implementation (ruleset 2.0)

The maintained implementation is `scripts/evaluate.py`. See `M2_EVALUATOR.md` for CLI usage, regression cases, implementation
clarifications, and the complete list of changed verdicts. Ruleset 2.0 fixes host
names accidentally created from phase adjectives, uses bounded host equivalences,
and records input/code hashes and an evaluator snapshot with each run. The new
RSC baseline is 73 TP / 79 FP / 93 FN; Elsevier is 62 TP / 65 FP / 65 FN. These
results are saved in `consolidated_v2` subfolders, preserving the earlier audits.

## 13. Current layout and ruleset

The maintained evaluator uses ruleset 2.2. Run from the repository root with explicit prediction, annotation, output, and delimiter arguments; see `M2_EVALUATOR.md`. Sections 11–12 retain historical results. Older snapshots, launchers, and `consolidated_v2` results are preserved under `evaluation_results/archive/`. The current six DS Flash/Qwen results and two CDE results live in `evaluation_results/m2_evaluation_*`. See `evaluation_results/M2_RULESET_2_2_RERUN.md` for input versions: saved Elsevier evaluations use the historical 127-record reference, not the current 125-record file in `annotation/`.
