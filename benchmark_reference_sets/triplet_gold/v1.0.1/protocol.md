# Triplet Annotation Protocol

Version: 1.1. Status: owner-authorized gold release with sampled human validation and explicit unresolved-field scoring masks.

## 1. Purpose and scope

Build an exhaustive reference for extraction of (material, photoluminescence wavelength, singlet–triplet energy split) triplets from 50 RSC and 50 Elsevier articles. Follow the extraction instructions and output schema supplied for this experiment. Annotate what is available in the exact text supplied to the model.

The initial prediction files are `mining_results/naive-ds-flash-thinking/triplet/rsc_v1.jsonl` and `elsevier_v1.jsonl`. Each has 50 article entries. Their empty outputs are predictions, not evidence that the articles contain no triplets. Existing ST-only annotations may be used during a final cross-check, after independent annotation.

## 2. Decisions and outstanding questions

Confirmed by the benchmark owner:

- **Pairing:** generate every eligible PL × ΔEST combination for the same material, including different conditions and experimental/computational methods.
- **Computed estimates:** include precise computed estimates such as “estimated to be 0.0044 eV”; exclude approximate wording such as “about,” “around,” or “~.” The verb “estimated” alone does not disqualify a numerical computational result.
- **Identical exports:** export one copy of an identical record and retain all contributing observations and pair references internally.
- **Repeated precision variants:** an explicitly repeated result is one observation; accept each source-backed numerical spelling or precision variant during scoring. Do not create extra gold observations or an arbitrary numerical tolerance.
- **Exact inputs supplied:** the owner identifies `article_texts/` as the exact content passed to the mining LLMs. All 100 benchmark DOIs map to unique, nonempty UTF-8 files. Paths and byte-level SHA-256 hashes are recorded in `benchmark/triplet/manifest.jsonl`. This establishes input provenance, not correctness of the extracted claims.
- **Fluorescence scope:** include fluorescence (prompt and delayed), exclude explicitly assigned phosphorescence/RTP. Delayed peaks require explicit fluorescence identification in the supplied text; the word “delayed” alone is insufficient.
- **Polymorphs:** pair across polymorphs of the same compound. Preserve each form internally. Do not collapse different compounds into one material.
- **Temperature endpoints:** include precise peaks explicitly mapped to temperature endpoints; exclude unspecified ranges or unmapped trends.
- **Time trends:** exclude wavelength values stated only as endpoints of a shift over time when individual acquisition times are unspecified, even if a broad time window is given. A separately stated fixed fluorescence peak remains eligible; for example, retain the neat TTT-PTZ delayed-fluorescence peak at 540 nm while excluding its prompt-fluorescence shift endpoints.
- **Mode deduplication:** merge prompt and delayed fluorescence at the same wavelength and sample conditions. Preserve both channel labels, methods, and evidence internally.
- **Modeled dimers:** keep modeled dimers separate unless a PL value is explicitly assigned to them. Do not transfer bulk sample wavelengths to those dimers.
- **Host-doped material names:** use a stated systematic emitter name in `chemical_name` even when the article's identifier denotes a host-doped sample. Record the host on the appropriate property; do not transfer experimental conditions to a computed gap.
- **Ambient temperature wording:** preserve “ambient conditions” literally in the PL temperature field; do not replace it with a numerical temperature or “room temperature.”
- **Temperature sweeps as metadata:** retain an explicitly stated sweep as temperature context when it scopes over the fluorescence observation. The owner approved `298–443 K` for Aphe@HA's single 441 nm observation. A metadata range does not make a precise property value ineligible and does not create per-temperature observations without additional evidence.
- **DCM paragraph context:** for `10.1039/C9TC03954F`, the owner approved solution/DCM for both experimental gaps. The opening solution-spectra context applies to the subsequent low-temperature gap measurements before the paragraph introduces doped films. Computed gaps do not inherit these conditions.
- **TCzIPN gap context:** the owner approved this paper as negative for lack of a numerical PL wavelength. Its unpaired tabulated gap remains eligible, but phase/host/concentration are unresolved: the singlet footnote specifies a PS film while general methods specify frozen THF for the triplet. Preserve both contexts instead of assigning one to the whole gap.
- **LLM-output metadata exception:** retain the original extraction schema. The owner permits JSON null for unresolved optional metadata in model outputs. Required material IDs, values, units, and evidence still require support. Rich human annotations continue to distinguish `not_stated` from `unresolved`; a model-output null cannot establish which state applies.
- **Ag14-dcbdt experiment deduplication:** the owner identifies the ambient/283 K mentions of 665 nm as one observation and the 0.078/0.08 eV gap reports as one experimental result. Preserve both source descriptions, with 0.078 eV canonical and 0.08 eV accepted as an alternative. This paper contributes three wavelengths × two gaps = six triplets.

These calibration decisions refine the original task. In particular, fluorescence-only eligibility narrows the original PL wording. Future extraction prompts must explicitly state this restriction, the delayed-peak rule, pairing scope, and deduplication rules. Historical outputs can be audited under this policy, but exclusions introduced here do not establish that the historical model violated its original prompt.

Outstanding before freezing the reference:

- Calibrate observation identity and handling of conflicting repeated reports (Section 6).
- Resolve ambiguous candidates in a decision log; do not silently interpret an uncertain candidate as absent.

Rules below implement the supplied prompt. Any additional rule introduced during calibration must be recorded with an example and applied to all affected articles.

## 3. Freeze the article inputs

For each article, store DOI, publisher, original source path, source SHA-256, model-input text path, text SHA-256, and preprocessing version. Preserve the exact input text as UTF-8. Record truncation, included sections, and whether tables, captions, or supplementary content were supplied.

The current manifest fixes the roster from the two initial prediction files: 50 RSC and 50 Elsevier papers. The other 100 text files currently in `article_texts/` are outside this benchmark. Input provenance is owner-confirmed. Historical preprocessing details are unknown (`preprocessing_version: null`); do not reconstruct or regenerate the supplied texts. Original HTML/XML hashes are not yet captured; the supplied text hashes define the evaluation inputs independently of those source files. Manifest entries do not imply completed annotation.

Only the supplied text is evidence. Do not consult external articles, chemical databases, unavailable supplements, or figures that were not represented in the input. If exact input recovery is pending, mark annotations `input_unverified`; they cannot enter a frozen gold release.

Assign character offsets against this immutable text, using zero-based Unicode code-point indices and half-open intervals `[start, end)`. A stored evidence excerpt must equal `text[start:end]`.

Decode the hashed bytes directly as UTF-8 without newline conversion or Unicode normalization (for example, `path.read_bytes().decode("utf-8")`). `text_characters` in the manifest uses that representation. Check the hash before annotation and evaluation; any changed input requires an explicit manifest revision.

## 4. Eligible materials and property claims

### Material

- Copy an identifier used in the article. Do not create a chemical identity from outside knowledge.
- Link aliases only when the article establishes their equivalence. Keep all stated aliases and evidence; use one stable internal material ID.
- Copy `chemical_name` only when the article supplies an IUPAC or systematic name. An identifier, acronym, formula, or inferred expanded name does not satisfy this requirement.
- A name declaration may occur far from the property result. Record the evidence linking the name to the identifier.
- Keep host–guest systems, blends, complexes, and individual components distinct unless the article explicitly establishes the relevant material association. Flag unclear associations for adjudication.

### Photoluminescence wavelength

Include an explicit PL wavelength, λPL, or PL peak with a numerical wavelength and an explicit unit. Units may be established by a table heading or surrounding text. Exclude electroluminescence, absorption, excitation wavelengths, lifetimes, and energy-only emission values. Do not infer a peak from a plot or convert an energy to a wavelength.

For this benchmark, PL eligibility is restricted to fluorescence, including prompt fluorescence, delayed fluorescence, and TADF. Exclude peaks explicitly identified as phosphorescence/RTP, even when the article calls their spectrum PL. For delayed peaks, require explicit fluorescence assignment with clear scope over the peak; otherwise record `delayed_channel_unresolved` as an ineligible candidate pending supporting evidence. Do not infer fluorescence from the word “delayed.” Ordinary prompt emission in an explicit fluorescence/PL context may be established by the surrounding text and captions.

### Singlet–triplet split

Include an explicit numerical ΔEST or stated singlet–triplet energy gap, including an explicitly reported S_n–T_n split. Record the stated state labels as internal annotation metadata when available. Do not calculate a difference from separate singlet and triplet energies. Exclude unrelated gaps and energy levels.

### Rules shared by both properties

- Include experimental and computational claims, with the article's stated method.
- Exclude values merely cited as prior work. A citation marker alone does not prove the current result is prior work; examine attribution.
- Exclude inequalities, intervals, and explicitly approximate values. Preserve them as excluded candidates with reasons.
- Explicitly mapped endpoint observations are eligible: “83 K to 283 K ... 673 nm to 665 nm” establishes 673 nm at 83 K and 665 nm at 283 K. It does not establish intervening values. An unmapped range remains excluded. A temperature range describing how the intensity of a fixed 441 nm peak varies does not make that wavelength a range.
- A wavelength stated only as an endpoint of a time trend needs its individual acquisition time. “During the first 50 ns, the PLmax shifts from 420 nm to 455 nm” does not assign either value to a particular delay and yields no endpoint observations. Distinct bands explicitly identified at a stated temperature are evaluated separately from such a trend.
- Include `value ± error` when both are explicitly reported; keep the uncertainty separate. Never estimate it.
- Require unambiguous material attribution. For “A and B give 510 and 530 nm, respectively,” associate values in the stated order and retain the entire mapping as evidence.
- Shared values may apply to multiple materials only when the text explicitly supports that reading.
- A comparison containing individually precise values is eligible: “A (510 nm) is redshifted from B (500 nm).” Exclude comparative bounds such as “less than 510 nm.”
- A missing unit or unclear property identity requires review; do not supply a conventional unit from domain knowledge.

## 5. Metadata and evidence

Annotate the fields in the extraction schema:

| Entity | Fields beyond value/unit or material identifier |
| --- | --- |
| Material | `chemical_name` |
| PL | `error`, `phase`, `host_or_solvent`, `temperature`, `concentration_or_doping`, `method`, `source_quote` |
| ΔEST | `error`, `phase`, `host_or_solvent`, `concentration_or_doping`, `method`, `source_quote` |

Copy explicitly stated information. Nearby prose, experimental sections, captions, and table footnotes can establish metadata when their scope clearly includes the observation. Record that scope evidence. Do not transfer a PL condition to ΔEST simply because the values will be paired.

Use `pure` for an explicitly pure, pristine, neat, or non-doped measured sample. “Film,” “solid,” and the absence of a stated host do not establish purity. A human adjudication may establish the sample context across sections; record that paper-specific decision and supporting passages without generalizing it to unrelated samples. Do not infer room temperature, a theoretical phase, or a solvent from customary practice.

`concentration_or_doping` requires an explicitly applicable numerical concentration, loading, or composition ratio. Use null when only “dilute,” “diluted,” “very low concentrations,” “high concentrations,” or “neat” is supplied. Preserve that qualitative wording in rich evidence/history. For an explicitly neat/non-doped film, use phase `film`, host `pure`, and null concentration unless a numerical loading such as `100 wt%` is explicitly reported. Do not infer 100 wt% from neatness. A numerical preparation concentration elsewhere is insufficient unless its scope clearly includes this measurement; owner review rejected the 0.2% assignment for Aphe@HA's temperature-dependent PL peak on this basis.

Normalize thickness and composition descriptors separately from phase: `thin film`, `doped thin film`, `doped film`, `neat film`, `pristine thin film`, `solid film`, and `solid-state film` export as `film`. Keep host/doping in their own fields and retain original descriptions in evidence and metadata revision history. Preserve explicitly stated morphology such as `amorphous film` or crystalline forms; do not infer amorphous morphology from the word film. In D4TC03925D, the article's cross-paragraph amorphous-film discussion applies to its host-film fluorescence observations.

The completed owner review supersedes the earlier unresolved C5MH00258C experimental-gap metadata: all four measured gaps are assigned phase `solution` and solvent `toluene` using the common measurement context. Computed gaps retain their independent metadata. OPDPO's C8QM00064F photophysical films and the non-doped optical films in C7TC04460G and j.optmat.2022.112320 are owner-confirmed pure samples. These are scoped adjudications, not permission to infer pure from any unspecified film.

Internally, each optional field has status `stated`, `not_stated`, or `unresolved`. Both `not_stated` and owner-adjudicated `unresolved` export to JSON null, with their distinction preserved in rich annotations. For released gold, unresolved optional fields must have explicit scoring masks and owner disposition; do not score these nulls as absence judgments. Preserve raw wording; any canonical equivalent labels belong in a separate, versioned alias table.

For LLM extraction under the original schema, unresolved optional metadata may likewise be null because that schema cannot encode a review state. Do not infer an absence judgment from such an output. Preserve supported core triplets when only optional metadata is ambiguous. Required identifiers, property values, units, and source evidence cannot be guessed or null. Owner acceptance of uncertainty does not convert an unresolved field into an absent or scientifically resolved field.

Each property needs at least one verbatim evidence excerpt containing its numerical value. Store additional spans for units, material association, metadata, table headings, and cross-paragraph links. Quotes need not independently contain all context, but the combined evidence must establish the claim. Never stitch separated spans into a purported verbatim quote. Multiple alternative excerpts may support the same observation.

## 6. Observation identity and triplet generation

Annotate unique property observations first. Use stable internal IDs for article, material, PL observation, and ΔEST observation. Repeated mentions in an abstract, table, discussion, or conclusion should reference the same observation when they describe the same result.

Keep observations separate when the article distinguishes sample conditions, methods, electronic-state gaps, or distinct results, even if their numerical values coincide. Do not treat unknown metadata as proof that two observations are different or identical. Resolve such cases by reading their context.

Owner-approved exception: merge explicitly distinguished prompt and delayed fluorescence channels when wavelength and sample conditions match. Retain both channel assignments, methods, and evidence; accept the documented channel-specific descriptions at scoring time. Do not require one prediction to concatenate both methods, and do not award duplicate matching capacity.

Different descriptions of acquisition and analysis do not by themselves establish independent experiments. In the Ag14-dcbdt calibration, the owner identifies the 0.078 eV Boltzmann fit and 0.08 eV TRES report as one experiment because the fitted PL decay curves are acquired through TRES. Annotate one gap observation, retain both source-backed values and method descriptions, and give it one matching capacity. Likewise, merge the two 665 nm crystal mentions, preserving the source descriptions “ambient conditions” and “283 K” as accepted metadata alternatives for this observation. Do not generalize this adjudication into an ambient-temperature conversion or a blanket rule merging similar values across methods.

Merge explicitly repeated reports of one result, retaining all evidence and the most complete compatible metadata. When a table reports 0.041 eV and the conclusion explicitly repeats that result as 0.04 eV, annotate one observation with both source-backed values as accepted alternatives. Keep a verbatim evidence span and unit for every alternative. Use the most precise supported report as the canonical exported value; preserve the alternatives in the rich annotations for scoring. Precision variants must refer to the same result; nearby numbers or different measurements are not automatically alternatives. Flag substantive conflicts or contradictory metadata for adjudication.

An adjudicated substantive conflict is not automatically an accepted precision variant. For TMCz-BO in room-temperature MCH, Table 1 gives 405 nm and results prose gives 403 nm for apparently the same fluorescence maximum. The owner selected 405 nm as canonical and retained 403 nm only as conflict evidence; do not create another observation or accept 403 nm as an equivalent value for scoring.

Accept only the enumerated source-backed alternatives, without an inferred tolerance interval. A prediction using an alternative must provide evidence for that alternative. All alternatives share one observation identity and one matching capacity: predicting both variants does not earn two true positives. In a paired record, all required fields and evidence must remain mutually supported; alternatives do not authorize combining incompatible measurement contexts.

After pair generation, export one copy of each identical record in the requested schema. Retain all contributing observation-pair references internally. Distinct verbatim excerpts supporting one result are alternative evidence, not additional observations or expected duplicate records. If distinct underlying pairs collapse to one exported record, that record has one matching capacity. Preserve distinctions representable in the schema, such as different conditions or methods.

For each material with PL observation set P and gap observation set S, generate P × S internally, then apply the export deduplication rule above. A material with either set empty contributes no triplets. For example, two PL observations and three gap observations produce six internal pairs; fewer exported records are possible if records collapse. Keep each property's own metadata. Triplet generation expresses a permitted association, not a claim that both properties were measured on the same sample.

Retain eligible unpaired observations internally to explain negative articles and diagnose omissions. Emit only valid paired records into the gold extraction output.

## 7. Annotation workflow

1. Select a calibration batch containing both publishers, predicted-empty papers, multiple observations, and computational results. Sampling may use prediction counts; annotators should not see prediction contents during independent reading.
2. Two annotators independently read each entire supplied text. Search terms and table scans can help locate candidates, but do not substitute for reading relevant context and checking completeness.
3. Record materials, eligible observations, evidence, excluded candidates, and unresolved questions. Confirm optional fields after checking relevant sections.
4. An adjudicator resolves disagreements against the supplied text. Log the disputed item, decision, evidence, reason, and protocol version. Escalate unresolved interpretation of the extraction instructions to the benchmark owner.
5. Update the protocol after calibration and recheck affected annotations. Then apply the frozen rules to all 100 papers.
6. Compare model predictions and existing ST annotations only after independent annotation. Review possible omissions and record any evidence-backed correction.
7. Generate triplets and run integrity checks before marking an article complete.

Record annotator identities, completion dates, and independent annotations before adjudication. Report pre-adjudication agreement on article eligibility, property observations, and metadata; retain disagreement counts and their causes.

## 8. Negative articles and review status

Article status is `unreviewed`, `in_progress`, `input_unverified`, `needs_adjudication`, or `complete`. A complete article may be positive or negative.

For a confirmed negative, explicitly record that full-text review found no material with both eligible properties. Add applicable reasons: `no_eligible_pl`, `no_eligible_gap`, `properties_on_different_materials`, or `only_excluded_candidates`. Multiple reasons are allowed. Store representative exclusion evidence where candidates exist.

Do not infer negativity from an empty model result, missing extraction output, or an unfinished review. Do not release an unresolved article as a gold-negative example.

## 9. Release checks and evaluation handoff

A gold release requires all 100 manifest articles to be accounted for; verified input hashes; completed owner adjudication; documented human validation coverage; valid evidence offsets; valid material/observation references; and generated triplets conforming to the supplied schema. For version 1.0.0, the owner authorizes sampled human validation instead of independent dual annotation: 100 randomly sampled triplets and ten positive-paper completeness reviews, alongside earlier calibration and negative-paper justifications. Disclose that independent second annotation and agreement statistics are unavailable.

The owner reviewed all 15 remaining unresolved optional fields and authorized retaining them. Twelve fields participate in triplets; three belong to an unpaired gap. Keep them unresolved internally, export null where applicable, and distribute a per-record scoring mask. Ignore each masked field on both prediction and reference when assessing metadata; it earns neither credit nor penalty. Core fields and supporting evidence remain evaluable. Report such full-record results as metadata-masked scores and disclose the masking coverage. Never treat acceptance of uncertainty as a core-label waiver or as confirmation of 100% completeness.

Material identifiers follow compound-level identity for Cartesian pairing. In j.optmat.2022.112320, `2`, `Dye 2`, and `dye 2` are equivalent article identifiers; retain source-backed aliases. In D2TC01729F, retain parent `3Br` as the material identifier and retain `3Br-B` as the applicable observation's conformer label in provenance. Do not rename all parent-compound pairs to one conformer or equate a conformer label with the parent in every context. This disposes of the two sampled naming flags under the existing compound-level identity rule.

Check that every triplet links observations of the same material, every eligible pair is generated exactly once internally, and exported identical records are collapsed with their provenance retained. Repeated mentions and accepted precision alternatives must not inflate observation counts or matching capacity. Validate value/unit evidence and explicitly stated metadata. Numeric normalization must never create a value absent from the source.

Release a manifest, protocol, decision log, rich annotations, generated `gold.jsonl`, and versioned matching aliases. Preserve previous releases. Gold corrections require a new version and rescoring of all compared models.

The later scorer should report core, evidence-grounded, and full-record triplet results; unique-property results; and performance on negative articles. It must preserve duplicate and failure audits. Semantic quote support requires a defined review or validation procedure; substring occurrence alone is insufficient. Scoring equivalences and assignment rules must be specified separately before implementing the scorer.

## 10. Calibration artifacts

The first calibration is documented in `benchmark/triplet/calibration/README.md`. Its fixed selection contains five nonempty and five empty prediction papers, five from each publisher. Shortest texts were chosen within predefined publisher/stratum cells to make full-text review manageable; this is a calibration sample, not a representative performance estimate.

The owner reviewed all ten findings and approved or corrected their classifications and triplet counts. Outcomes are 26 distinct candidate triplets across five positive papers and five confirmed negatives within this calibration sample. Decisions and historical annotation snapshot hashes are retained in `calibration/review_decisions.jsonl`.

Rich annotations originated from one AI review followed by owner adjudication. An independent second annotation has not been performed. Version 1.0.0 is released under the sampled-validation and masked-metadata policy above; it does not provide final model precision/recall. Three metadata fields on the unpaired TCzIPN gap and twelve on paired observations remain unresolved by owner decision. Quote occurrence diagnostics preserve strict verbatim checks and show whitespace-equivalent matches separately; whitespace repair is not silently accepted as verbatim compliance.

## 11. Extraction prompt

The reusable model instructions are in `benchmark/triplet/extraction_prompt.txt`, with integration notes in `benchmark/triplet/PROMPT.md`. Prompt version 1.0 implements protocol version 0.8 using the original extraction schema and the owner-approved optional-metadata exception. The generic prompt contains no article-specific calibration answers. New model runs must record the prompt text/hash and the supplied schema and exact article inputs.

## 12. Owner correction after v1.0.0: explicit 510 nm fluorescence

On 2026-11-09 the owner overturned the monitoring-wavelength exclusion for 10.1039/D3TC01986A. The sentence explicitly identifies PL at 510 nm from CzPyCHO and PhPyCHO microcrystals and PiPyCHO aggregates and identifies fluorescent singlet excitons. Include one 510 nm observation per material even though the passage does not call this wavelength a maximum. Do not reject this explicitly identified fluorescence merely because it is discussed with a decay measurement. This supersedes decision `remaining90-d3tc01986a-monitor-510nm-01`. Preserve explicit microcrystal/aggregate form and leave unsupported temperature, host and concentration null. These observations remain unpaired because this paper supplies no eligible numerical gap.

This scoped adjudication does not authorize inferring a peak, converting an energy, or including an unlabeled detector setting. Other acquisition-only exclusions require their own source review. Gold v1.0.1 records the three additions, with unchanged triplets and classification; original audit sessions and v1.0.0 remain intact.
