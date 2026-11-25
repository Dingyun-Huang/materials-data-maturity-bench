"""Idempotent owner-adjudicated observation corrections after gold v1.0.0."""
from copy import deepcopy

DOI = '10.1039/D3TC01986A'
DECISION = 'd3tc01986a-include-510nm-20261109'
QUOTE = ('Moreover, the PL (510 nm) from the CzPyCHO and PhPyCHO microcrystals and the PiPyCHO aggregates '
         'decayed within 3–4 ns (Fig. S24, ESI), which confirmed the presence of short-lived fluorescent '
         'singlet excitons in the self-assemblies.')


def apply_observation_adjudications(article, text):
    if article['doi'].casefold() != DOI.casefold():
        return []
    if any(r.get('decision_id') == DECISION for r in article.get('observation_adjudications', [])):
        return []
    start = text.index(QUOTE)
    span = dict(start=start, end=start+len(QUOTE), quote=QUOTE)
    removed = [e for e in article['excluded_candidates'] if e['reason']=='acquisition_wavelength' and '510 nm' in e['evidence']['quote']]
    article['excluded_candidates'] = [e for e in article['excluded_candidates'] if e not in removed]
    old_issues = [i for i in article.get('issues', []) if 'exclude 510 nm' in i.get('description', '')]
    for issue in old_issues:
        issue['status'] = 'superseded_by_owner'
        issue['superseded_by'] = DECISION
    ids = []
    for material, phase, form in [('CzPyCHO','microcrystal','CzPyCHO microcrystals'),
                                  ('PhPyCHO','microcrystal','PhPyCHO microcrystals'),
                                  ('PiPyCHO','aggregate','PiPyCHO aggregates')]:
        oid = f'pl-510-{material}'
        assert not any(o['observation_id']==oid for o in article['observations'])
        fields = dict(error=None, phase=phase, host_or_solvent=None, concentration_or_doping=None,
                      temperature=None, method='PL decay')
        article['observations'].append(dict(observation_id=oid, kind='pl', material_id=material, value='510', unit='nm',
            fields=fields, field_status={f:'not_stated' if v is None else 'stated' for f,v in fields.items()},
            field_evidence={f:[0] for f,v in fields.items() if v is not None}, evidence=[deepcopy(span)],
            form_in_doc=form, note='Owner-approved explicit fluorescence wavelength; an emission-maximum label is not required for this passage.',
            accepted_value_variants=[]))
        ids.append(oid)
    article.setdefault('issues', []).append(dict(description='Owner correction: include the explicitly reported 510 nm fluorescence for all three self-assemblies; this supersedes the earlier monitoring-wavelength exclusion.',
        status='owner_resolved', blocks_eligibility=False, affected=ids, evidence=deepcopy(span)))
    change = dict(decision_id=DECISION, doi=DOI, added_observation_ids=ids,
                  superseded_exclusions=removed, authority='Explicit owner instruction: It should be included.',
                  decision='Include 510 nm for CzPyCHO/PhPyCHO microcrystals and PiPyCHO aggregates; retain absence of eligible gaps.')
    article.setdefault('observation_adjudications', []).append(change)
    return [change]
