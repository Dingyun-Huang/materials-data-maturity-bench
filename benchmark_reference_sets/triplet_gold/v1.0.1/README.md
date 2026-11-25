# Triplet gold reference 1.0.1

Status: **released gold under owner-approved sampled human validation**.

100 papers, 799 triplets; 54 positive and 46 negative articles. AI annotations were owner-adjudicated and audited through 100 random triplets and ten positive-paper reviews. Independent second annotation and inter-annotator agreement are unavailable. The original audit predates corrections; it does not estimate this corrected release's exact accuracy.

`gold.jsonl` has one DOI and original-schema `records` list per article, including empty lists for justified negatives. `annotations.jsonl` retains evidence offsets, unpaired observations, exclusions, metadata states, and correction history. `pair_provenance.jsonl` links every exported record to its observations and preserves each property's conformer/form labels. The zero-based `record_index` and `record_id` identify rows for matching to `scoring_masks.jsonl`.

## Metadata scoring policy

Fifteen optional observation fields remain unresolved by explicit owner decision, including three on an unpaired gap. They are not confirmed absences. Twelve participate in exported triplets, affecting 41 records. Original-schema exports use null; **load `scoring_masks.jsonl` with the gold**. Ignore fields listed in `excluded_metadata_fields` on both prediction and reference: award neither credit nor penalty for them. Core fields and evidence are not masked. Label full-record scores as metadata-masked and report masking coverage. `unresolved_metadata.jsonl` retains the observation-level inventory.

`accepted_aliases.jsonl` provides source-backed material aliases and precision alternatives, without introducing numerical tolerances. Compound-level parent identifiers are used across forms; specific form labels remain per observation, not universal aliases. Numerical matching, quote support and one-to-one assignment must still follow a separately defined scorer; no model scores are included here.

## Provenance and use

`sampled_audit/` and `unresolved_review/` preserve human review histories and sample/reference hashes. `metadata_adjudications.jsonl`, `metadata_changes.jsonl`, `review_decisions.jsonl` and `release_policy.json` document decisions. Source texts stay at manifest paths in the repository; verify their hashes before reuse. Supplied articles are not republished in this package.

`SHA256SUMS` covers every other artifact recursively. Preserve this release; corrections require a new version and rescoring compared methods. From the repository root, reproduce with `python scripts/compile_triplet_annotations.py` and `python scripts/release_triplet_gold.py --output NEW_DIRECTORY`. Existing release directories are never overwritten. Saved scripts are archival copies; run them from the repository's scripts directory.

## Correction from v1.0.0

The owner overturned the exclusion of 510 nm fluorescence in 10.1039/D3TC01986A. Three unpaired PL observations are added for CzPyCHO/PhPyCHO microcrystals and PiPyCHO aggregates. No eligible gap is reported in this paper; it remains triplet-negative. All 799 exported triplets, the 54/46 classifications, and unresolved-field counts are unchanged. The old exclusion remains in historical review logs and is explicitly superseded in the new decision log. No other scientific annotations changed.

Core association/property scores projected from triplets are unchanged. Single-property scores over all rich PL observations require rescoring; the PL core reference grows from 601 to 604 claims. Saved comparisons under `evaluation_results/gold_v1_0_1/` use this version explicitly. Earlier evaluations and review sessions retain v1.0.0 provenance.

The copied extraction prompt and original sampled reviews are historical v1.0.0 artifacts, not newly generated prompt or validation runs. The current protocol records the owner correction. Reproduce this revision with `python scripts/revise_triplet_gold.py` from the repository scripts, starting from intact v1.0.0; v1.0.1 must not already exist. The older release script copied from the parent is historical.
