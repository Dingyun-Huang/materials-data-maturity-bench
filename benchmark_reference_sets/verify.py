"""Verify package checksums, reference populations and article coverage offline."""
from pathlib import Path
import csv,hashlib,json
ROOT=Path(__file__).resolve().parent

def read(name):
    return [json.loads(line) for line in (ROOT/name).read_text(encoding='utf-8').splitlines() if line.strip()]

def checks(path):
    entries=[]
    for line in path.read_text().splitlines():
        expected,name=line.split('  ',1)
        file=path.parent/name
        assert file.resolve().is_relative_to(ROOT),name
        assert hashlib.sha256(file.read_bytes()).hexdigest()==expected,name
        entries.append(file.relative_to(ROOT).as_posix())
    return entries

def main():
    listed=set(checks(ROOT/'SHA256SUMS'))
    actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and p.name!='.DS_Store' and '__pycache__' not in p.parts and p!=ROOT/'SHA256SUMS'}
    assert listed==actual,('Unlisted/missing files',actual^listed)
    checks(ROOT/'triplet_gold/v1.0.1/SHA256SUMS')
    corpus=read('corpus.jsonl');roster={a['doi'] for a in corpus}
    assert len(corpus)==len(roster)==100
    assert sum(a['publisher']=='rsc' for a in corpus)==50
    for name,n in [('rsc',171),('elsevier',127)]:
        with (ROOT/f'st_only/{name}.csv').open(encoding='utf-8-sig',newline='') as stream:
            rows=list(csv.DictReader(stream));assert len(rows)==n
            assert all(row['doi'].lower().removeprefix('https://doi.org/') in roster for row in rows)
    for name,n in [('triplet_gold/core_associations.jsonl',735),('triplet_component_properties/pl_core.jsonl',382),('triplet_component_properties/gap_core.jsonl',223),('all_observations/pl_core.jsonl',604),('all_observations/gap_core.jsonl',293),('all_observations/pl_metadata.jsonl',624),('all_observations/gap_metadata.jsonl',302),('triplet_gold/v1.0.1/gold.jsonl',799)]:
        rows=read(name);assert len(rows)==100
        assert {r['doi'].lower() for r in rows}==roster,name
        assert sum(len(r['records']) for r in rows)==n,name
    gold=read('triplet_gold/v1.0.1/gold.jsonl')
    assert sum(bool(r['records']) for r in gold)==54
    print('PASS: checksums, original release, 100-paper roster and all reference populations verified.')

if __name__=='__main__':
    main()
