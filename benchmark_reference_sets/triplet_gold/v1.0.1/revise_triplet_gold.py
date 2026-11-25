#!/usr/bin/env python3
"""Release the owner-authorized 510 nm correction without modifying its parent."""
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import tempfile

from compile_triplet_annotations import BASE, ROOT, read_jsonl, write_jsonl
from evaluate_cde_pl import verify_checksums
from evaluate_triplet_core import sha
from release_triplet_gold import gold_records
from triplet_observation_adjudications import apply_observation_adjudications, DECISION


def main():
    parent=BASE/'releases/v1.0.0'
    target=BASE/'releases/v1.0.1'
    assert not target.exists(), 'Existing releases are immutable'
    verify_checksums(parent)
    articles=read_jsonl(parent/'annotations.jsonl')
    old=copy.deepcopy(articles)
    changes=[]
    for article in articles:
        changes.extend(apply_observation_adjudications(article,(ROOT/article['text_path']).read_bytes().decode('utf-8')))
    assert len(changes)==1
    assert sum(a!=b for a,b in zip(old,articles))==1
    manifest={r['doi'].casefold():r for r in read_jsonl(parent/'manifest.jsonl')}
    docs,pairs,masks,unresolved,aliases=gold_records(articles,manifest,'1.0.1')
    assert docs==read_jsonl(parent/'gold.jsonl'), 'This correction must not change exported triplets'
    with tempfile.TemporaryDirectory(dir=target.parent,prefix='.gold-revision-') as work:
        stage=Path(work)/'v1.0.1'
        shutil.copytree(parent,stage)
        for article in articles:
            article['release_version']='1.0.1'
            article['protocol_version']='1.1'
        write_jsonl(stage/'annotations.jsonl',articles)
        for name,rows in [('gold',docs),('pair_provenance',pairs),('scoring_masks',masks),
                          ('unresolved_metadata',unresolved),('accepted_aliases',aliases),('observation_adjudications',changes)]:
            write_jsonl(stage/(name+'.jsonl'),rows)
        decisions=read_jsonl(parent/'review_decisions.jsonl')
        decisions.append(dict(decision_id=DECISION,doi=changes[0]['doi'],status='owner_resolved',
            supersedes='remaining90-d3tc01986a-monitor-510nm-01',decision=changes[0]['decision'],authority=changes[0]['authority']))
        write_jsonl(stage/'review_decisions.jsonl',decisions)
        policy=json.loads((parent/'release_policy.json').read_text())
        policy.update(version='1.0.1',parent_version='1.0.0',authority=changes[0]['authority'],correction_decision_id=DECISION)
        (stage/'release_policy.json').write_text(json.dumps(policy,indent=2)+'\n')
        shutil.copyfile(BASE/'protocol.md',stage/'protocol.md')
        for name in ('triplet_observation_adjudications.py','revise_triplet_gold.py','compile_triplet_annotations.py'):
            shutil.copyfile(ROOT/'scripts'/name,stage/name)
        checks=json.loads((parent/'release_checks.json').read_text())
        checks.update(version='1.0.1',parent_version='1.0.0',correction_decision_id=DECISION,
                      released_at=datetime.now(timezone.utc).isoformat(),
                      added_unpaired_pl_observations=3,triplet_records_unchanged=True,
                      parent_annotations_sha256=sha(parent/'annotations.jsonl'),
                      protocol_sha256=sha(stage/'protocol.md'),
                      annotation_source_sha256=sha(stage/'annotations.jsonl'),
                      validation_scope='Original sampled audit retained with original hashes; the three additions were explicitly owner-adjudicated, not independently re-audited.')
        (stage/'release_checks.json').write_text(json.dumps(checks,indent=2)+'\n')
        readme=(parent/'README.md').read_text().replace('# Triplet gold reference 1.0.0','# Triplet gold reference 1.0.1')
        readme+='''\n## Correction from v1.0.0\n\nThe owner overturned the exclusion of 510 nm fluorescence in 10.1039/D3TC01986A. Three unpaired PL observations are added for CzPyCHO/PhPyCHO microcrystals and PiPyCHO aggregates. No eligible gap is reported in this paper; it remains triplet-negative. All 799 exported triplets, the 54/46 classifications, and unresolved-field counts are unchanged. The old exclusion remains in historical review logs and is explicitly superseded in the new decision log. No other scientific annotations changed.\n\nCore association/property scores projected from triplets are unchanged. Single-property scores over all rich PL observations require rescoring; the PL core reference grows from 601 to 604 claims. Saved comparisons under `evaluation_results/gold_v1_0_1/` use this version explicitly. Earlier evaluations and review sessions retain v1.0.0 provenance.\n\nThe copied extraction prompt and original sampled reviews are historical v1.0.0 artifacts, not newly generated prompt or validation runs. The current protocol records the owner correction. Reproduce this revision with `python scripts/revise_triplet_gold.py` from the repository scripts, starting from intact v1.0.0; v1.0.1 must not already exist. The older release script copied from the parent is historical.\n'''
        (stage/'README.md').write_text(readme)
        (stage/'SHA256SUMS').write_text(''.join(f'{sha(p)}  {p.relative_to(stage).as_posix()}\n'
            for p in sorted(stage.rglob('*')) if p.is_file() and p.name!='SHA256SUMS'))
        verify_checksums(stage)
        verify_checksums(parent)
        stage.rename(target)
    archive=BASE/'releases/triplet-gold-v1.0.1.zip'
    assert not archive.exists()
    shutil.make_archive(str(archive.with_suffix('')),'zip',root_dir=target.parent,base_dir=target.name)
    archive.with_suffix('.zip.sha256').write_text(f'{sha(archive)}  {archive.name}\n')
    (BASE/'releases/latest.json').write_text(json.dumps(dict(version='1.0.1',gold='v1.0.1/gold.jsonl',
        scoring_masks='v1.0.1/scoring_masks.jsonl',archive=archive.name,archive_sha256=sha(archive)),indent=2)+'\n')
    print('Released v1.0.1: three unpaired PL observations added; exported triplets unchanged.')


if __name__=='__main__':
    main()
