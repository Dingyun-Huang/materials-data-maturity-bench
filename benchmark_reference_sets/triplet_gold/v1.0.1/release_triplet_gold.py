#!/usr/bin/env python3
"""Build an immutable gold release under the explicit owner-approved release policy."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from compile_triplet_annotations import BASE, ROOT, export_groups, read_jsonl, validate, write_jsonl


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def latest_reviews(path):
    return {row['item_id']: row for row in read_jsonl(path)}


def gold_records(articles, manifest, version):
    docs, pairs, masks, unresolved, aliases = [], [], [], [], []
    for article in sorted(articles, key=lambda a: a['doi'].casefold()):
        validate(article, manifest)
        assert not any(i.get('status')=='needs_owner_decision' for i in article.get('issues', [])), article['doi']
        groups = export_groups(article)
        if not groups:
            assert article['draft_eligibility']=='negative' and article['negative_reasons'], article['doi']
        docs.append(dict(doi=article['doi'], records=[g['record'] for g in groups]))
        obs = {o['observation_id']: o for o in article['observations']}
        linked = {oid for g in groups for p in g['observation_pairs'] for oid in p.values()}
        for o in obs.values():
            for field, status in o['field_status'].items():
                if status=='unresolved':
                    unresolved.append(dict(doi=article['doi'], observation_id=o['observation_id'],
                        field=field, status='owner_accepted_unresolved', participates_in_triplets=o['observation_id'] in linked))
            if o.get('accepted_value_variants'):
                aliases.append(dict(doi=article['doi'], observation_id=o['observation_id'],
                                    accepted_value_variants=o['accepted_value_variants']))
        for material in article['materials']:
            names = material.get('aliases', [])
            if article['doi'].casefold()=='10.1016/j.optmat.2022.112320' and material['material_id']=='2':
                names = sorted(set([*names, '2', 'Dye 2', 'dye 2']))
            if names:
                aliases.append(dict(doi=article['doi'], material_id=material['material_id'],
                                    material_id_in_doc=material['material_id_in_doc'], aliases=names))
        for index, group in enumerate(groups):
            key = f'{version}:{article["doi"]}:{index}'
            masked = sorted(group['unresolved_fields'])
            optional = [f'{prop}.{field}' for prop in ('pl_wavelength','st_gap')
                        for field in ('error','phase','host_or_solvent','concentration_or_doping','method')]
            optional.append('pl_wavelength.temperature')
            assert set(masked) <= set(optional), (key, masked)
            masks.append(dict(record_id=key, doi=article['doi'], record_index=index,
                core_evaluable=True, excluded_metadata_fields=masked,
                metadata_field_evaluable={field:field not in masked for field in optional}))
            forms = [dict(pl=p['pl'],gap=p['gap'],pl_form=obs[p['pl']].get('form_in_doc'),
                          gap_form=obs[p['gap']].get('form_in_doc')) for p in group['observation_pairs']]
            pairs.append(dict(group, record_id=key, record_index=index, observation_forms=forms))
    return docs, pairs, masks, unresolved, aliases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=BASE/'releases/v1.0.0')
    args = parser.parse_args()
    target = args.output.resolve()
    if target.exists():
        parser.error('Release exists; choose a new version directory. Existing gold is never overwritten.')
    policy = json.loads((BASE/'release_policy.json').read_text())
    assert policy['status']=='owner_authorized'
    version = policy['version']
    articles = read_jsonl(BASE/'reference_draft/annotations.jsonl')
    roster = read_jsonl(BASE/'manifest.jsonl')
    manifest = {r['doi'].casefold(): r for r in roster}
    assert len(articles)==len(manifest)==len(roster)==100
    assert len({a['doi'].casefold() for a in articles})==100
    assert {a['doi'].casefold() for a in articles}==set(manifest)
    audit_path = BASE/'human_review/session_v1'
    plan = json.loads((audit_path/'sample_plan.json').read_text())
    audit = latest_reviews(audit_path/'reviews.jsonl')
    assert len(plan['triplet_sample'])==policy['required_triplet_audits']
    assert len(plan['paper_sample'])==policy['required_positive_paper_audits']
    for key in plan['triplet_sample']+plan['paper_sample']:
        assert audit[key]['status']=='completed'
        assert audit[key]['reference_sha256']==plan['reference_sha256']
    for name, expected in plan['reference_sha256'].items():
        assert sha(BASE/'release_candidates/v1.0.0-rc1'/name)==expected
    unresolved_path = BASE/'human_review/unresolved_v1'
    dispositions = latest_reviews(unresolved_path/'reviews.jsonl')
    unresolved_plan = json.loads((unresolved_path/'sample_plan.json').read_text())
    assert len(unresolved_plan['unresolved_sample'])==policy['required_unresolved_field_dispositions']
    for key in unresolved_plan['unresolved_sample']:
        row = dispositions[key]
        assert row['status']=='completed' and row['answers']['resolution']=='unresolved'
        assert row['reference_sha256']==unresolved_plan['reference_sha256']
    # The review snapshot's annotations, groups and inputs must be this corrected draft.
    for name in ('annotations.jsonl','pair_provenance.jsonl'):
        assert sha(BASE/'reference_draft'/name)==unresolved_plan['reference_sha256'][name]
    assert sha(BASE/'manifest.jsonl')==unresolved_plan['reference_sha256']['manifest.jsonl']
    compiled_summary = json.loads((BASE/'reference_draft/summary.json').read_text())
    assert compiled_summary['protocol_sha256']==sha(BASE/'protocol.md'), 'Recompile after protocol changes'
    docs, pairs, masks, unresolved, aliases = gold_records(articles,manifest,version)
    assert len(unresolved)==policy['required_unresolved_field_dispositions']
    counts = Counter('positive' if d['records'] else 'negative' for d in docs)
    report = dict(status='released_gold',version=version,released_at=datetime.now(timezone.utc).isoformat(),
        papers=len(docs),classifications=dict(counts),triplets=len(pairs),
        unresolved_observation_fields=len(unresolved),
        unresolved_fields_in_paired_observations=sum(r['participates_in_triplets'] for r in unresolved),
        triplets_with_metadata_masks=sum(bool(m['excluded_metadata_fields']) for m in masks),
        masked_record_fields=sum(len(m['excluded_metadata_fields']) for m in masks),
        completed_triplet_audits=len(plan['triplet_sample']),completed_positive_paper_audits=len(plan['paper_sample']),
        completed_unresolved_field_reviews=len(unresolved_plan['unresolved_sample']),
        independent_second_annotation='not_performed',validation_policy=policy['validation_policy'],
        input_hashes_evidence_offsets_and_observation_references='passed',
        annotation_source_sha256=sha(BASE/'reference_draft/annotations.jsonl'),
        original_audit_is_pre_correction=True,model_performance_metrics='not_computed')
    target.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent,prefix='.gold-staging-') as work:
        stage = Path(work)/target.name
        stage.mkdir()
        for name in ('manifest.jsonl','protocol.md','extraction_prompt.txt','PROMPT.md','release_policy.json','metadata_adjudications.jsonl'):
            shutil.copyfile(BASE/name,stage/name)
        for name in ('metadata_changes.jsonl','metadata_aliases.json'):
            shutil.copyfile(BASE/'reference_draft'/name,stage/name)
        for name in ('compile_triplet_annotations.py','triplet_metadata_rules.py','release_triplet_gold.py'):
            shutil.copyfile(ROOT/'scripts'/name,stage/name)
        write_jsonl(stage/'gold.jsonl',docs)
        write_jsonl(stage/'pair_provenance.jsonl',pairs)
        write_jsonl(stage/'scoring_masks.jsonl',masks)
        write_jsonl(stage/'unresolved_metadata.jsonl',unresolved)
        write_jsonl(stage/'accepted_aliases.jsonl',aliases)
        for article in articles:
            article['annotation_protocol_version'] = article['protocol_version']
            article['protocol_version'] = '1.0'
            article['prior_annotation_status'] = article['status']
            article['status'] = 'released_gold'
            article['release_version'] = version
        write_jsonl(stage/'annotations.jsonl',articles)
        decisions = [dict(r,annotation_scope=scope) for scope in ('calibration','remaining90')
                     for r in read_jsonl(BASE/scope/'review_decisions.jsonl')]
        decisions.append(dict(status='owner_resolved',decision='Release v1.0.0 with sampled validation; retain 15 unresolved optional fields and exclude them from metadata scoring.',authority='Explicit owner request in conversation',policy_file='release_policy.json'))
        write_jsonl(stage/'review_decisions.jsonl',decisions)
        for scope, source in [('sampled_audit',audit_path),('unresolved_review',unresolved_path)]:
            destination = stage/scope
            destination.mkdir()
            for name in ('sample_plan.json','reviews.jsonl'):
                shutil.copyfile(source/name,destination/name)
        (stage/'release_checks.json').write_text(json.dumps(report,indent=2)+'\n')
        (stage/'README.md').write_text(f'''# Triplet gold reference {version}

Status: **released gold under owner-approved sampled human validation**.

{len(docs)} papers, {len(pairs)} triplets; {counts['positive']} positive and {counts['negative']} negative articles. AI annotations were owner-adjudicated and audited through 100 random triplets and ten positive-paper reviews. Independent second annotation and inter-annotator agreement are unavailable. The original audit predates corrections; it does not estimate this corrected release's exact accuracy.

`gold.jsonl` has one DOI and original-schema `records` list per article, including empty lists for justified negatives. `annotations.jsonl` retains evidence offsets, unpaired observations, exclusions, metadata states, and correction history. `pair_provenance.jsonl` links every exported record to its observations and preserves each property's conformer/form labels. The zero-based `record_index` and `record_id` identify rows for matching to `scoring_masks.jsonl`.

## Metadata scoring policy

Fifteen optional observation fields remain unresolved by explicit owner decision, including three on an unpaired gap. They are not confirmed absences. Twelve participate in exported triplets, affecting {report['triplets_with_metadata_masks']} records. Original-schema exports use null; **load `scoring_masks.jsonl` with the gold**. Ignore fields listed in `excluded_metadata_fields` on both prediction and reference: award neither credit nor penalty for them. Core fields and evidence are not masked. Label full-record scores as metadata-masked and report masking coverage. `unresolved_metadata.jsonl` retains the observation-level inventory.

`accepted_aliases.jsonl` provides source-backed material aliases and precision alternatives, without introducing numerical tolerances. Compound-level parent identifiers are used across forms; specific form labels remain per observation, not universal aliases. Numerical matching, quote support and one-to-one assignment must still follow a separately defined scorer; no model scores are included here.

## Provenance and use

`sampled_audit/` and `unresolved_review/` preserve human review histories and sample/reference hashes. `metadata_adjudications.jsonl`, `metadata_changes.jsonl`, `review_decisions.jsonl` and `release_policy.json` document decisions. Source texts stay at manifest paths in the repository; verify their hashes before reuse. Supplied articles are not republished in this package.

`SHA256SUMS` covers every other artifact recursively. Preserve this release; corrections require a new version and rescoring compared methods. From the repository root, reproduce with `python scripts/compile_triplet_annotations.py` and `python scripts/release_triplet_gold.py --output NEW_DIRECTORY`. Existing release directories are never overwritten. Saved scripts are archival copies; run them from the repository's scripts directory.
''',encoding='utf-8')
        files = sorted(p for p in stage.rglob('*') if p.is_file())
        (stage/'SHA256SUMS').write_text(''.join(f'{sha(p)}  {p.relative_to(stage).as_posix()}\n' for p in files))
        stage.rename(target)
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
