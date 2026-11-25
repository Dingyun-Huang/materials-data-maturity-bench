#!/usr/bin/env python3
"""Validate and compile reviewed AI annotation drafts; never release gold."""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import unicodedata
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from triplet_metadata_rules import FILM_LABELS, QUALITATIVE_CONCENTRATIONS, VERSION, apply_metadata_rules
from triplet_observation_adjudications import apply_observation_adjudications

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "benchmark/triplet"


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(r, ensure_ascii=False, allow_nan=False) + "\n" for r in rows), encoding="utf-8")


def normalize_name(value):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", value)).casefold()


def number(value):
    try:
        result = Decimal(str(value).replace("−", "-"))
    except InvalidOperation:
        raise ValueError(f"Invalid annotation number: {value!r}") from None
    if not result.is_finite():
        raise ValueError(f"Nonfinite annotation number: {value!r}")
    return result


def value_in_evidence(value, quote):
    """Check a value-bearing excerpt, without mistaking XML attributes for data."""
    text = re.sub(r"</?[A-Za-z_][\w:.-]*(?:\s[^<>]*?)?\s*/?>", "", quote)
    tokens = re.findall(r"(?<![\w.])[-−+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?", text)
    target = number(value)
    if any(number(token) == target for token in tokens):
        return True
    for mantissa, exponent in re.findall(r"([-−+]?\d+(?:\.\d*)?)\s*[×x]\s*10\s*\^?\s*([-−+]?\d+)", text):
        if number(mantissa) * Decimal(10) ** int(exponent.replace("−", "-")) == target:
            return True
    return False


def unit_in_evidence(unit, quotes):
    for quote in quotes:
        text = re.sub(r"</?[A-Za-z_][\w:.-]*(?:\s[^<>]*?)?\s*/?>", "", quote)
        if re.search(r"(?<![A-Za-z])" + re.escape(unit) + r"(?![A-Za-z])", " ".join(text.split()), re.I):
            return True
    return False


def walk_spans(value):
    if isinstance(value, dict):
        if all(k in value for k in ("start", "end", "quote")):
            yield value
        for child in value.values():
            yield from walk_spans(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_spans(child)


def validate(article, manifest):
    doi = article["doi"]
    assert doi.casefold() in manifest, doi
    m = manifest[doi.casefold()]
    assert article["text_path"] == m["text_path"], doi
    data = (ROOT / m["text_path"]).read_bytes()
    assert hashlib.sha256(data).hexdigest() == m["text_sha256"] == article["text_sha256"], doi
    text = data.decode("utf-8")
    assert article.get("full_text_read") is True, (doi, "full text not reviewed")
    for span in walk_spans(article):
        assert 0 <= span["start"] < span["end"] <= len(text), (doi, span)
        assert text[span["start"]:span["end"]] == span["quote"], (doi, "bad evidence offset")
    ids = [m["material_id"] for m in article["materials"]]
    assert len(ids) == len(set(ids)), (doi, "duplicate material ids")
    obs_ids = [o["observation_id"] for o in article["observations"]]
    assert len(obs_ids) == len(set(obs_ids)), (doi, "duplicate observation ids")
    for o in article["observations"]:
        assert o["kind"] in ("pl", "gap") and o["material_id"] in ids, (doi, o)
        number(o["value"])
        assert o["unit"] and o["evidence"], (doi, o)
        assert value_in_evidence(o["value"], o["evidence"][0]["quote"]), (doi, o["observation_id"], "primary quote does not contain the value")
        assert unit_in_evidence(o["unit"], [e["quote"] for e in o["evidence"]]), (doi, o["observation_id"], "unit context not recorded")
        expected = {"error", "phase", "host_or_solvent", "concentration_or_doping", "method"}
        if o["kind"] == "pl":
            expected.add("temperature")
        assert set(o["fields"]) == expected, (doi, o["observation_id"], "unexpected fields")
        assert set(o["field_status"]) == expected, (doi, o["observation_id"], "missing statuses")
        for k, status in o["field_status"].items():
            assert status in ("stated", "not_stated", "unresolved"), (doi, status)
            assert (status != "not_stated" or o["fields"][k] is None), (doi, k)
            if status == "stated":
                assert o["fields"][k] is not None and o.get("field_evidence", {}).get(k), (doi, k)
        if o["fields"]["error"] is not None:
            assert number(o["fields"]["error"]) >= 0, doi
        for indexes in o.get("field_evidence", {}).values():
            assert all(0 <= i < len(o["evidence"]) for i in indexes), (doi, "bad evidence index")
        for variant in o.get("accepted_value_variants", []):
            assert isinstance(variant, dict) and variant.get("evidence"), (doi, variant)
            number(variant["value"])
    return text


def schema_property(observation):
    return dict(value=float(number(observation["value"])), unit=observation["unit"],
                **observation["fields"], source_quote=observation["evidence"][0]["quote"])


def export_groups(article):
    """Cartesian pairs grouped by schema content; alternate quotes do not multiply results."""
    groups = {}
    for material in article["materials"]:
        observations = [o for o in article["observations"] if o["material_id"] == material["material_id"]]
        wavelengths = [o for o in observations if o["kind"] == "pl"]
        gaps = [o for o in observations if o["kind"] == "gap"]
        for p in wavelengths:
            for g in gaps:
                record = dict(material=dict(material_id_in_doc=material["material_id_in_doc"],
                                            chemical_name=material["chemical_name"]),
                              pl_wavelength=schema_property(p), st_gap=schema_property(g))
                identity = dict(record, pl_wavelength={k:v for k,v in record["pl_wavelength"].items() if k != "source_quote"},
                                st_gap={k:v for k,v in record["st_gap"].items() if k != "source_quote"})
                key = json.dumps(identity, ensure_ascii=False, sort_keys=True)
                group = groups.setdefault(key, dict(doi=article["doi"], record=record,
                    material_id=material["material_id"], observation_pairs=[], unresolved_fields=[]))
                group["observation_pairs"].append(dict(pl=p["observation_id"], gap=g["observation_id"]))
                for label,o in (("pl_wavelength",p),("st_gap",g)):
                    for k,v in o["field_status"].items():
                        if v == "unresolved" and f"{label}.{k}" not in group["unresolved_fields"]:
                            group["unresolved_fields"].append(f"{label}.{k}")
    return list(groups.values())


def core_equal(pred, obs):
    variants = [dict(value=obs["value"], unit=obs["unit"]), *obs.get("accepted_value_variants", [])]
    return any(number(pred["value"]) == number(v["value"]) and pred["unit"] == v["unit"] for v in variants)


def cell(value):
    return html.escape(str(value if value is not None else "null")).replace("|", "\\|").replace("\n", " ")


def write_reports(target, articles, groups, summary):
    """Create a readable entry point and one evidence review page per article."""
    folder = target / "paper_reviews"
    folder.mkdir(exist_ok=True)
    rows = []
    questions = ["# Questions requiring review", "",
        "These questions remain separate from the owner-reviewed calibration decisions. "
        "Annotation nulls marked unresolved are not absence judgments. "
        "Evidence previews below are condensed; exact excerpts and offsets are in annotations.jsonl.", ""]
    for a in sorted(articles, key=lambda x:x["doi"].casefold()):
        filename = a["doi"].lower().replace("/", "_") + ".md"
        paper_groups = [g for g in groups if g["doi"] == a["doi"]]
        unresolved = [(o["observation_id"], k) for o in a["observations"] for k,v in o["field_status"].items() if v == "unresolved"]
        issues = [i for i in a.get("issues", []) if i.get("status") == "needs_owner_decision"]
        page = [f"# {a['doi']}", "", f"Status: {a['draft_eligibility']}; {len(paper_groups)} distinct candidate triplets. AI draft, not released gold.", "",
            f"[Supplied article text](../../../../{a['text_path']})", "", "## Observations", "",
            "| ID | Material | Property | Value | Phase | Host/solvent | Doping | Temperature | Method |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        for o in a["observations"]:
            f = o["fields"]
            page.append("| " + " | ".join(cell(v) for v in (
                o["observation_id"],o["material_id"],o["kind"],f"{o['value']} {o['unit']}",
                f["phase"],f["host_or_solvent"],f["concentration_or_doping"],f.get("temperature"),f["method"])) + " |")
        page += ["", "## Evidence previews", "", "Whitespace and markup are condensed for display. Use the JSON annotations for verbatim excerpts.", ""]
        for o in a["observations"]:
            q = re.sub(r"</?[A-Za-z_][\w:.-]*(?:\s[^<>]*?)?\s*/?>", "", o["evidence"][0]["quote"])
            q = " ".join(q.split())
            page.append(f"- **{o['observation_id']}**: {html.escape(q[:450])}" + (" … [preview shortened]" if len(q)>450 else ""))
        page += ["", "## Excluded candidates", ""]
        for e in a.get("excluded_candidates", []):
            page.append(f"- **{e['reason']}**: {html.escape(' '.join(e['evidence']['quote'].split())[:300])}")
        if not a.get("excluded_candidates"):
            page.append("No individually recorded exclusions.")
        page += ["", "## Review notes", ""]
        if a.get("negative_reasons"):
            page.append("Negative reasons: " + "; ".join(a["negative_reasons"]))
        for issue in a.get("issues", []):
            page.append(f"- [{issue.get('status','review')}] {issue['description']}")
        for observation_id,field in unresolved:
            page.append(f"- Unresolved metadata: `{observation_id}.{field}`.")
        for note in a.get("notes", []):
            page.append(f"- {note}")
        if issues or unresolved:
            questions += [f"## {a['doi']}", "", f"[Paper review](paper_reviews/{filename})", ""]
            for issue in issues:
                questions.append("- " + issue["description"])
            if unresolved:
                questions.append("- Unresolved fields: " + ", ".join(f"`{o}.{f}`" for o,f in unresolved))
            questions.append("")
        (folder/filename).write_text("\n".join(page)+"\n",encoding="utf-8")
        rows.append(dict(doi=a["doi"],classification=a["draft_eligibility"],triplets=len(paper_groups),
            observations=len(a["observations"]),open_questions=len(issues),unresolved_metadata=len(unresolved),filename=filename))
    lines = ["# Triplet annotation results", "",
        "Status: **source-anchored AI reference draft; not released gold**. An independent second annotation has not been performed.", "",
        f"Processed {summary['processed_papers']} of {summary['expected_papers']} expected papers; {summary['missing_papers']} missing. "
        f"Classifications: {summary['classifications']}. Distinct candidate triplets: {summary['distinct_candidate_triplets']}.", "",
        "Candidate counts apply the approved full Cartesian pairing and schema deduplication rules. "
        "They include provisional annotations with open identity or metadata questions; counts may change after owner review. "
        "Core coverage diagnostics are not one-to-one scored assignments and do not establish precision/recall.", "",
        "## Review files", "",
        "- [Open review questions](review_questions.md)",
        "- [Detailed annotations and exact evidence](annotations.jsonl)",
        "- [Schema-shaped draft triplets](draft_triplets.jsonl)",
        "- [Pair provenance and unresolved fields](pair_provenance.jsonl)",
        "- [Observation spreadsheet](observations.tsv)",
        "- [Prediction coverage crosscheck](prediction_crosscheck.jsonl)",
        "- [Summary and provenance hashes](summary.json)", "",
        "## Paper inventory", "",
        "| Paper | Draft classification | Candidate triplets | Observations | Open questions | Unresolved metadata |",
        "| --- | --- | ---: | ---: | ---: | ---: |"]
    for r in rows:
        lines.append(f"| [{r['doi']}](paper_reviews/{r['filename']}) | {r['classification']} | {r['triplets']} | {r['observations']} | {r['open_questions']} | {r['unresolved_metadata']} |")
    lines += ["", "## Rebuild", "", "From the repository root:", "", "```sh",
        "python benchmark/triplet/remaining90/annotate_batch1.py",
        "python benchmark/triplet/remaining90/annotate_batch2.py",
        "python benchmark/triplet/remaining90/annotate_batch3.py",
        "python scripts/compile_triplet_annotations.py", "```", "",
        "The batch scripts rebuild curated annotation drafts from immutable input texts; they do not call a model or rediscover annotations. "
        "Compilation requires all 90 drafts, validates hashes and exact source spans, and also writes the combined 100-paper draft. "
        "Use `--allow-partial` only during work; missing papers are listed rather than converted into empty gold outputs.", ""]
    (target/"README.md").write_text("\n".join(lines),encoding="utf-8")
    (target/"review_questions.md").write_text("\n".join(questions)+"\n",encoding="utf-8")


def compile_set(articles, expected, target, *, calibration=False):
    target.mkdir(parents=True, exist_ok=True)
    manifest = {r["doi"].casefold():r for r in expected}
    missing = sorted(set(manifest) - {a["doi"].casefold() for a in articles})
    groups, reviews, docs, crosses, audit_rows = [], [], [], [], []
    predictions = {}
    for publisher in ("rsc", "elsevier"):
        predictions.update({r["doi"].casefold():r for r in read_jsonl(ROOT / f"mining_results/naive-ds-flash-thinking/triplet/{publisher}_v1.jsonl")})
    for a in sorted(articles, key=lambda r:r["doi"].casefold()):
        text = validate(a, manifest)
        paper_groups = export_groups(a)
        groups.extend(paper_groups)
        issues = a.get("issues", [])
        blocking = any(i.get("blocks_eligibility") for i in issues)
        inferred = "positive" if paper_groups else "unresolved" if blocking else "negative"
        assert a["draft_eligibility"] == inferred, (a["doi"], a["draft_eligibility"], inferred)
        if inferred == "negative":
            assert a.get("negative_reasons"), (a["doi"], "negative reason missing")
        for issue in issues:
            if issue.get("status") == "needs_owner_decision":
                reviews.append(dict(doi=a["doi"], **issue))
        for o in a["observations"]:
            for field,status in o["field_status"].items():
                if status == "unresolved":
                    reviews.append(dict(doi=a["doi"], observation_id=o["observation_id"], field=field,
                        status="unresolved_metadata", description="Reference metadata remains unresolved; draft null is not an absence judgment."))
            audit_rows.append(dict(doi=a["doi"], observation_id=o["observation_id"], material=o["material_id"],
                kind=o["kind"], value=o["value"], unit=o["unit"], **o["fields"],
                unresolved_fields=",".join(k for k,v in o["field_status"].items() if v=="unresolved"),
                source_quote=o["evidence"][0]["quote"]))
        docs.append(dict(doi=a["doi"], source_file=manifest[a["doi"].casefold()]["source_file"],
            annotation_status="ai_reference_draft_not_gold", draft_eligibility=inferred,
            review_required=any(i.get("status") == "needs_owner_decision" for i in issues) or any(g["unresolved_fields"] for g in paper_groups),
            records=[g["record"] for g in paper_groups]))
        obs = {o["observation_id"]:o for o in a["observations"]}
        mats = {m["material_id"]:m for m in a["materials"]}
        for index,pred in enumerate(predictions[a["doi"].casefold()]["records"], 1):
            matches=[]
            for gid,group in enumerate(paper_groups,1):
                m=mats[group["material_id"]]
                names=[m["material_id_in_doc"],*m.get("aliases",[])]
                if normalize_name(pred["material"]["material_id_in_doc"]) not in {normalize_name(n) for n in names}:
                    continue
                if any(core_equal(pred["pl_wavelength"],obs[pair["pl"]]) and core_equal(pred["st_gap"],obs[pair["gap"]]) for pair in group["observation_pairs"]):
                    matches.append(gid)
            quotes={k: bool(pred[k]["source_quote"]) and pred[k]["source_quote"] in text for k in ("pl_wavelength","st_gap")}
            crosses.append(dict(doi=a["doi"],prediction_index=index,
                exact_value_unit_candidate_groups=matches, exact_quote_occurrence=quotes,
                status="coverage_diagnostic_not_a_scored_assignment"))
    write_jsonl(target/"annotations.jsonl",articles)
    write_jsonl(target/"metadata_changes.jsonl", [change for a in articles for o in a['observations']
                                               for change in o.get('metadata_revision_history', [])])
    (target/"metadata_aliases.json").write_text(json.dumps(dict(protocol_version=VERSION,
        phase_aliases={phase: 'film' for phase in sorted(FILM_LABELS)},
        qualitative_concentrations_exporting_null=sorted(QUALITATIVE_CONCENTRATIONS)), indent=2)+"\n", encoding="utf-8")
    write_jsonl(target/"draft_triplets.jsonl",docs)
    write_jsonl(target/"pair_provenance.jsonl",groups)
    write_jsonl(target/"review_queue.jsonl",reviews)
    write_jsonl(target/"prediction_crosscheck.jsonl",crosses)
    write_jsonl(target/"missing_articles.jsonl",[manifest[d] for d in missing])
    columns=["doi","observation_id","material","kind","value","unit","error","phase","host_or_solvent","concentration_or_doping","temperature","method","unresolved_fields","source_quote"]
    with (target/"observations.tsv").open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=columns,delimiter="\t")
        writer.writeheader(); writer.writerows(audit_rows)
    counts=Counter(d["draft_eligibility"] for d in docs)
    summary=dict(status="ai_annotation_draft_not_gold", complete_roster=not missing,
        expected_papers=len(expected),processed_papers=len(articles),missing_papers=len(missing),
        classifications=dict(counts),property_observations=len(audit_rows),distinct_candidate_triplets=len(groups),
        review_queue_items=len(reviews),includes_owner_reviewed_calibration=calibration,
        protocol_sha256=hashlib.sha256((BASE/"protocol.md").read_bytes()).hexdigest(),
        compiler_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        metadata_rules_sha256=hashlib.sha256((ROOT/'scripts/triplet_metadata_rules.py').read_bytes()).hexdigest(),
        annotation_sha256={a["doi"]:hashlib.sha256(json.dumps(a,ensure_ascii=False,sort_keys=True).encode()).hexdigest() for a in articles},
        prediction_sha256={publisher:hashlib.sha256((ROOT/f"mining_results/naive-ds-flash-thinking/triplet/{publisher}_v1.jsonl").read_bytes()).hexdigest() for publisher in ("rsc","elsevier")},
        independent_second_annotation="not_performed", performance_metrics="not_computed")
    (target/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    write_reports(target, articles, groups, summary)
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-partial",action="store_true")
    args=parser.parse_args()
    manifest=read_jsonl(BASE/"manifest.jsonl")
    calibration=read_jsonl(BASE/"calibration/annotations.jsonl")
    cal_ids={a["doi"].casefold() for a in calibration}
    remaining=[r for r in manifest if r["doi"].casefold() not in cal_ids]
    files=sorted((BASE/"remaining90/annotations").glob("*.json"))
    articles=[json.loads(p.read_text()) for p in files]
    for article in calibration + articles:
        apply_metadata_rules(article)
        apply_observation_adjudications(article, (ROOT/article['text_path']).read_bytes().decode('utf-8'))
    assert len({a["doi"].casefold() for a in articles})==len(articles), "Duplicate DOI files"
    assert {a["doi"].casefold() for a in articles} <= {r["doi"].casefold() for r in remaining}, "Outside remaining90 roster"
    if not args.allow_partial:
        assert len(articles)==90, f"Only {len(articles)}/90 drafts; incomplete articles are not negatives"
    print(json.dumps(compile_set(articles,remaining,BASE/"remaining90"),indent=2))
    print(json.dumps(compile_set(calibration+articles,manifest,BASE/"reference_draft",calibration=True),indent=2))


if __name__=="__main__":
    main()
