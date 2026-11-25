# Core association evaluator

`scripts/evaluate_triplet_core.py` evaluates the released triplet gold using Python's standard library. It is separate from the older ST-only M2 evaluator and does not change its rules.

## Run

From the repository root:

```sh
python scripts/evaluate_triplet_core.py \
  --predictions mining_results/naive-ds-flash-non-thinking/triplet/rsc_v2.1.jsonl \
                mining_results/naive-ds-flash-non-thinking/triplet/elsevier_v2.1.jsonl \
  --gold-release benchmark/triplet/releases/v1.0.0 \
  --output /tmp/triplet-core-v2-1-check
```

Current DS Flash triplet predictions are under `mining_results/naive-ds-flash-non-thinking/triplet/`. Select files explicitly by version; this directory contains both v1 and v2.1 outputs. Historical evaluation artifacts retain their original paths; `archive/root_cleanup/move_manifest.json` maps moved inputs to their current paths. Pass another directory, one JSONL file, or multiple non-overlapping JSONL files to evaluate other methods. An existing output directory is never overwritten; choose a new output name for another run.

The default scope is the entire gold roster. To evaluate only one publisher, add `--publisher rsc` or `--publisher elsevier`. Supplying just one publisher's file without specifying its scope leaves the other publisher's papers missing and their gold associations in the recall denominator.

## Scored association

The article DOI identifies the document. All five fields must match together:

1. `material.material_id_in_doc`;
2. `pl_wavelength.value` and `pl_wavelength.unit`;
3. `st_gap.value` and `st_gap.unit`.

Chemical name, uncertainty, phase, solvent/host, temperature, concentration, method, and source quotations are not scored or used to infer matches. Consequently, these are **core association** results, not evidence-grounded or full-record results. Metadata scoring masks are unnecessary at this stage.

**Collapse records with identical normalized cores on both sides.** Two records differing only in solvent, method, quoted evidence, or another excluded field represent one evaluable association. The 799 gold records reduce to 735 unique core associations in this release. Repeated predicted cores neither increase true positives nor incur penalties for distinctions this evaluator cannot assess. Every raw record and its duplicate membership remain in the audit. This set-based metric differs from record-level scoring that penalizes duplicate emissions; do not compare them without identifying their denominators.

## Matching and normalization

- Normalize DOI prefixes/case and match within each document. Never match across papers.
- Ruleset 1.1 processes **predicted names only**. Gold material identifiers remain literal in comparison cores, and gold files are never rewritten. A document-specific spelling/alias lookup maps compatible extracted names to the exact reference spelling. Normalize extracted typography using NFKC, case folding, whitespace/invisible-format removal, prime/apostrophe expansion and dash equivalence; preserve digits, prime multiplicity, stereochemistry, brackets, chemical punctuation and component separators.
- NFKC expands `″`, `‴`, and `⁗` to repeated single primes; the prediction spelling key then uses two, three, or four ASCII apostrophes. Curly apostrophes also map to ASCII apostrophes. The final prediction label uses the reference's original spelling when uniquely supported. Neither current gold nor the v2.1 predictions contain `‴`; before 1.1 the evaluator would nevertheless have converted it on both sides' comparison keys. Original stored files were not altered by that earlier evaluator either.
- Use released aliases, systematic names explicitly linked to an identifier in the reference, and reference-supported name decorations. A systematic name actually supplied as the prediction's material ID can resolve to its declared identifier; the separate chemical_name field cannot rescue a wrong ID. A `parent (form)` label resolves only when both names point to the same reference compound. Emitter–host labels such as `emitter@host` or `host/emitter` resolve only when that emitter/host association is explicitly recorded in the released rich annotations. A literal reference identifier always takes priority over decomposition. The TCTA/UGH2/PO-T2T spacer-label rule additionally requires its released same-exciplex architecture alias. Unknown hosts, hydrates, complexes, spacer systems and substituent changes are not stripped speculatively.
- Redundant whole-name parentheses may be removed only to reach a uniquely supported reference spelling. Internal parentheses, `(R)-` versus `(S)-`, bracketed complexes, substitution positions and prime counts remain distinct. No fuzzy name similarity or synonym inference is used. Systematic `chemical_name` spelling is normalized and audited as well, but is not used to rescue an incorrect material ID or to change core scores.
- Compare exact finite decimal quantities, preserving signs. Equivalent decimal spellings match; no numerical tolerance, approximate matching, or nearest-value matching is used.
- Convert eV/meV/MeV to eV and standard wavelength units (nm, μm/µm/um, pm, m, Å/angstrom) to nm by exact powers of ten. Distinguish the `M` and `m` energy prefixes. Normalize `cm−1`/`cm^-1` typography, but do not convert wavenumbers to eV or photon energies to wavelengths. Unknown nonempty units compare literally after Unicode/whitespace cleanup.
- Accept only documented numerical alternatives from the released rich observations. Construct alternatives using the actual observation-pair provenance, so alternatives from unrelated observations are not combined. Quote support for an alternative is outside this core-only assessment.
- Collapse canonical gold cores that differ only in excluded metadata. Keep a maximum-cardinality one-to-one assignment between predicted core groups and gold core groups. This handles ambiguous aliases/alternatives without a greedy loss of true positives. Ties are deterministic for fixed inputs.
- Precision alternatives that have different numerical cores compete for the same gold association. Predicting both an accepted rounded value and its canonical value cannot obtain two true positives; an unmatched competing association is a false positive.

## Failures and denominators

For unique associations, `TP` is a matched prediction group, `FP` an unmatched prediction group, and `FN` an unmatched gold group. Report micro precision `TP/(TP+FP)`, recall `TP/(TP+FN)`, and F1 `2TP/(predicted+gold)`. Undefined denominators are JSON null.

Every malformed prediction record is retained as a distinct invalid-core FP. Invalid outer JSON, unknown DOI, duplicate article entries, or unmarked malformed article output stops the run with a descriptive error. A missing article or an explicit failed extraction contributes no invented predictions, but all its gold associations remain FNs. If an explicit failed wrapper contains a parsed records list, that list is scored and the failure status remains visible. Never salvage records by parsing an error-message string. A failed empty negative article is not counted as a successful negative prediction.

Negatives have no gold associations but any predicted associations are FPs. The report separately counts hallucinating negative papers and successfully empty negative papers. All papers in the selected roster remain in the report, including failures and missing outputs.

## Outputs and reproducibility

- `summary.json`: overall and publisher TP/FP/FN, precision/recall/F1, raw and deduplicated counts, failure coverage, scoped roster, exact scored fields, and hashes of inputs, gold artifacts and evaluator.
- `paper_audit.jsonl`: metrics, input file/line, and extraction status/error for every scoped paper.
- `prediction_audit.jsonl`: every original parsed record, its normalized core and group, validation errors and duplicate status. `counted_status=duplicate_core` means that row adds no count; `association_status` describes its group's result.
- `name_normalization_audit.jsonl`: raw name fields, intermediate typographic keys, resolved prediction spellings, applied rules, and whether each field is scored. Original predictions are retained separately, and source quotations are not rewritten.
- `association_audit.jsonl`: the authoritative one-row-per-scored-association TP/FP ledger, candidate and assigned gold references, and unmatched reasons.
- `false_negatives.jsonl`: every unmatched gold core and all contributing gold record IDs/indexes.
- `evaluator_snapshot.py` and `prediction_inputs/`: the evaluator and exact prediction bytes used. Parsed JSONL audits serialize Decimal numeric literals as strings to preserve precision; original files retain their original types and bytes.

The CLI verifies all release checksums before and after scoring. Output creation is staged, and previous runs are preserved. Replay the evaluator snapshot with explicit `--predictions`, `--gold-release`, and `--output` paths; its defaults may differ when it is outside the repository's scripts directory. Gold validation estimates remain reference-quality information, not automatic corrections to model metrics. Extraction prompt/model settings are not inferred from filenames; record those separately for new runs. When a directory contains multiple versions for the same DOIs, pass the intended JSONL files explicitly rather than the whole directory.

Run regression tests with:

```sh
PYTHONPATH=scripts python -m unittest discover -s tests -v
```

Tests cover joint associations and nearby counterexamples, metadata exclusion and core deduplication, explicit aliases, exact decimals and unit conversions, invalid-core accounting, alternative-value capacity, maximum matching, missing/failed papers, negative-paper FPs, and gold provenance completeness.
