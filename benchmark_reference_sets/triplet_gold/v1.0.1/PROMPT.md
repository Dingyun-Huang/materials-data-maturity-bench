# Triplet extraction prompt

Prompt version: 1.1. Extraction rules are unchanged from annotation protocol 0.9 and retained in release protocol 1.0. Qualitative concentration-only descriptions export null; film labels are normalized while explicit morphology is preserved. Release protocol 1.0 additionally defines sampled validation and unresolved-field scoring masks.

Use `extraction_prompt.txt` as the extraction instruction message and pass one exact article text as the user message. Continue supplying the original `TripletExtractionResult` JSON schema. This prompt introduces no schema changes.

Example loading code:

```python
from pathlib import Path

EXTRACTION_INSTRUCTIONS = Path(
    "benchmark/triplet/extraction_prompt.txt"
).read_bytes().decode("utf-8")

article_text = Path(article_text_path).read_bytes().decode("utf-8")
```

The bytes-to-UTF-8 decoding preserves the text representation used by the benchmark's input hashes and evidence offsets. Do not normalize whitespace, reserialize included tables, or truncate the article without recording a distinct input version.

## Scope and compatibility

The prompt specifies fluorescence-only eligibility, full Cartesian pairing across conditions and polymorphs, higher-state singlet–triplet gaps, separate property metadata, and consolidation of repeated observations. It contains no article-specific calibration answers or DOI overrides. Article-specific owner adjudications remain in the annotations and evaluation rules; the prompt asks the model to apply general extraction principles to the supplied evidence.

The owner approved an explicit extraction-only exception: optional metadata that is genuinely unresolved may be JSON null. The original schema has no review-status field. Consequently, model-output null can mean absent or unresolved; human reference annotations retain those states separately. Ambiguous required material/value/unit/evidence associations must still be omitted rather than guessed.

This prompt narrows the historical task's broad PL wording to fluorescence. Use the same prompt, schema, article inputs, and run settings across compared models. Historical extractions used a different prompt and should be labeled accordingly.

Record the prompt version and SHA-256 hash alongside the schema, model identifier, generation settings, exact input hashes, responses, and failures for every run. The prompt requests exact quotes; verify substring occurrence programmatically and assess semantic support separately.

The prompt is a reusable instruction artifact. It has not yet been tested in a new extraction-model run.
