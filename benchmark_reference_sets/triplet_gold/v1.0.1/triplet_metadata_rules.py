"""Owner-adjudicated metadata rules, applied to observations before Cartesian pairing."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.9-draft'
QUALITATIVE_CONCENTRATIONS = {'dilute', 'diluted', 'very low concentrations', 'high concentrations', 'neat'}
FILM_LABELS = {'thin film', 'doped thin film', 'doped film', 'neat film', 'pristine thin film',
               'solid film', 'solid-state film'}


def apply_metadata_rules(article):
    """Idempotently update rich annotations; retain raw values and evidence in history."""
    changes = []
    text = (ROOT / article['text_path']).read_text(encoding='utf-8')

    def set_field(observation, field, value, rule, excerpt=None, evidence_indexes=None):
        status = 'not_stated' if value is None else 'stated'
        if observation['fields'][field] == value and observation['field_status'][field] == status:
            return
        previous = dict(value=observation['fields'][field], status=observation['field_status'][field],
                        evidence_indexes=observation.get('field_evidence', {}).get(field, []))
        indexes = list(evidence_indexes if evidence_indexes is not None else previous['evidence_indexes'])
        if excerpt:
            match = re.search(r'\s+'.join(re.escape(s) for s in excerpt.split()), text)
            assert match, (article['doi'], excerpt)
            span = dict(start=match.start(), end=match.end(), quote=text[match.start():match.end()])
            if span not in observation['evidence']:
                observation['evidence'].append(span)
            indexes.append(observation['evidence'].index(span))
        if value is not None:
            assert indexes, (article['doi'], field, 'missing supporting context')
        observation['fields'][field] = value
        observation['field_status'][field] = status
        if value is None:
            observation['field_evidence'].pop(field, None)
        else:
            observation['field_evidence'][field] = sorted(set(indexes))
        change = dict(doi=article['doi'], observation_id=observation['observation_id'], field=field,
                      previous=previous, value=value, rule=rule, protocol_version=VERSION)
        observation.setdefault('metadata_revision_history', []).append(change)
        changes.append(change)

    for o in article['observations']:
        phase = o['fields']['phase']
        if phase in {'neat film', 'pristine thin film'} and o['fields']['host_or_solvent'] is None:
            set_field(o, 'host_or_solvent', 'pure', 'explicit-neat-or-pristine-film',
                      evidence_indexes=o['field_evidence'].get('phase', []))
        if phase in FILM_LABELS:
            set_field(o, 'phase', 'film', 'canonical-film-label')
        if o['fields']['concentration_or_doping'] in QUALITATIVE_CONCENTRATIONS:
            set_field(o, 'concentration_or_doping', None, 'numeric-concentration-only')

        doi = article['doi'].casefold()
        if doi == '10.1016/j.optmat.2022.112320' and o['kind'] == 'gap':
            set_field(o, 'host_or_solvent', 'pure', 'owner-confirmed-non-doped-gap-sample',
                      'non-doped dye 2 on solid film is higher than its amount in dye 1.')
        if doi == '10.1039/c8qm00064f' and o['fields']['phase'] == 'film':
            set_field(o, 'host_or_solvent', 'pure', 'owner-confirmed-opdpo-photophysical-film',
                      'The UV-vis absorption spectra of OPDPO in solution and in the solid film-state are depicted in Fig. 1a.')
        if doi == '10.1039/c7tc04460g' and o['fields']['phase'] == 'film':
            set_field(o, 'host_or_solvent', 'pure', 'owner-confirmed-non-doped-photophysical-films',
                      'the transient PL spectra of the dendrimers in their neat film state')
        if doi == '10.1039/d4tc03925d' and o['fields']['phase'] == 'film':
            set_field(o, 'phase', 'amorphous film', 'explicit-amorphous-film-context',
                      'In amorphous films, the excited-state relaxation and solvent reorganisation are strongly inhibited.')
        if doi == '10.1016/j.dyepig.2023.111113' and o['kind'] == 'pl' and o['material_id'] == 'Aphe@HA':
            set_field(o, 'concentration_or_doping', None, 'owner-rejected-weak-concentration-link')
        if doi == '10.1039/c5mh00258c' and o['kind'] == 'gap' and o['fields']['method'] and '77 K' in o['fields']['method']:
            context = 'All the compounds show blue emission in toluene'
            set_field(o, 'phase', 'solution', 'owner-reviewed-toluene-gap-context-supersedes-unresolved', context)
            set_field(o, 'host_or_solvent', 'toluene', 'owner-reviewed-toluene-gap-context-supersedes-unresolved', context)
    article['protocol_version'] = VERSION
    return changes
