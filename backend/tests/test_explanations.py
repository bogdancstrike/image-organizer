import json
import shutil
from types import SimpleNamespace

import numpy as np
import pytest

from app.organization.explanations import duplicate_evidence, explain_plan
from tests.conftest import COLORS, make_image
from tests.test_api import client, wait  # noqa: F401


@pytest.mark.parametrize('source', ['manual','quality','faces','appearance','ocr','date','rule','ai','clip','cluster','unknown'])
def test_all_decision_sources_have_specific_observable_reasons(source):
    item={'file_id':'x','rel_path':'x.jpg','source':source,'category':'Portraits','category_id':'portraits','destination':'Sorted',
          'person_evidence':['multiple reference views agree'],
          'quality':{'rating':4.6,'flags':['blurry']},'pick':{'rating':4.6,'reasons':['clear subject']},
          'burst':{'size':3,'best':False}}
    explain_plan([item],{'strategy':'cull','options':{'model':'siglip2','quality':{'pick_min_rating':4.7,'keeper_min_rating':4.1}}})
    assert item['decision']['explanation'] and item['decision']['action']
    if source=='quality':
        assert any('Picks ≥4.7' in v for v in item['decision']['evidence'])
        assert any('another frame ranked higher' in v for v in item['decision']['evidence'])
    if source=='clip':assert any('not a calibrated probability' in v for v in item['decision']['evidence'])


@pytest.mark.parametrize('category', ['other-people','no-people','groups'])
def test_unknown_people_explanations_do_not_claim_identity_matches(category):
    item={'file_id':'x','source':'faces','category_id':category,'category':category}
    explain_plan([item],{'strategy':'people'})
    assert 'Matched using' not in item['decision']['explanation']


def test_duplicate_pair_evidence_distinguishes_fingerprint_and_transitive_similarity():
    a=SimpleNamespace(sha256='same',phash='00',dhash='00')
    b=SimpleNamespace(sha256='other',phash='01',dhash='03')
    assert 'content fingerprint' in duplicate_evidence(a,a,np.ones(2),np.ones(2))[0]
    values=duplicate_evidence(a,b,np.array([1.,0]),np.array([.9,.1]))
    assert 'another group member' in values[0]
    assert any('1 bits' in v for v in values) and any('2 bits' in v for v in values)
    assert any('0.9000' in v for v in values)


def test_trashed_preview_keeps_explanation_and_recovers_destination_after_restart(client, settings):
    lib=settings.library_root
    make_image(lib/'original.jpg',COLORS['red'],fmt='JPEG')
    shutil.copy2(lib/'original.jpg',lib/'copy.jpg')
    request={'strategy':'date','options':{'duplicates_action':'delete'}}
    job=wait(client,client.post('/api/jobs',json=request).json()['id'])
    duplicate=next(p for p in job['plan']if p['duplicate_of'])
    decision=duplicate['decision']
    assert decision['action']=='recoverable-trash'
    assert 'recoverable trash' in decision['explanation'] and decision['kept_path']
    assert any('content fingerprint' in e for e in decision['evidence'])
    run=client.post(f"/api/jobs/{job['id']}/apply",json={'mode':'move'}).json()
    manager=client.app.state.manager
    applied=manager.get(job['id'])
    moved=next(p for p in applied.plan if p['duplicate_of'])
    assert client.get('/api/preview',params={'path':moved['preview_path']}).status_code==200
    assert client.get('/api/preview',params={'path':moved['decision']['kept_preview_path']}).status_code==200
    # Simulate an old saved job missing post-Apply preview fields.
    for p in applied.plan:p.pop('preview_path',None)
    manager._persist(applied);manager.jobs.clear()
    restored=client.get(f"/api/jobs/{job['id']}").json()
    moved=next(p for p in restored['plan']if p['duplicate_of'])
    assert moved['preview_path'].startswith('.aio-trash/')
    assert client.get('/api/preview',params={'path':moved['preview_path']}).status_code==200
    client.post(f"/api/runs/{run['run_id']}/undo")
    undone=client.get(f"/api/jobs/{job['id']}").json()
    assert all('preview_path' not in p for p in undone['plan'])
    assert all((lib/p['rel_path']).exists()for p in undone['plan'])


def test_manual_override_retains_original_suggestion(client,settings):
    make_image(settings.library_root/'photo.jpg',COLORS['red'],fmt='JPEG')
    job=wait(client,client.post('/api/jobs',json={'strategy':'date'}).json()['id'])
    original=job['plan'][0]
    for category in ('_duplicates','_unsorted'):
        result=client.patch(f"/api/jobs/{job['id']}/plan",json={'file_ids':[original['file_id']],'category_id':category})
        assert result.status_code==200,result.text
        changed=result.json()['changed'][0]
        assert changed['decision']['action']=='manual'
        assert changed['decision']['previous']['category']==original['category']
        assert changed['decision']['previous']['explanation']==original['decision']['explanation']
