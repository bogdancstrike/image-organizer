"""Automatic tags: multi-label evidence, abstention, cache freshness, scoped hybrid search."""
from dataclasses import replace
from unittest.mock import Mock

import numpy as np
from fastapi.testclient import TestClient

from app.infrastructure.cache import AnalysisCache
from app.main import create_app
from app.media.decoding import decode_image
from app.media.scanning import scan
from app.recognition.tagging import VERSION, predict, tag_images, tokens
from tests.conftest import COLORS, make_image
from tests.test_api import wait


def test_independent_tags_abstain_without_evidence_and_recognize_color(fake_embedder):
    assert predict(np.empty((0,4)),fake_embedder)==[]
    assert predict(np.zeros((1,4)),fake_embedder)==[[]]
    out=predict(np.array([[1,0,0,.05],[0,0,1,.05]],np.float32),fake_embedder)
    assert 'red' in {t['label']for t in out[0]} and 'blue' in {t['label']for t in out[1]}
    assert all(len(tags)<=12 and all(.72<=t['score']<=1 for t in tags)for tags in out)
    assert tokens('Puppies, dresses and MOUNTAIN')==tokens('dog dress and mountains')
    assert tokens('café')==tokens('cafe')


def test_tag_cache_reuses_vectors_and_invalidates_on_version_size_and_mtime(settings,fake_embedder,monkeypatch):
    import app.recognition.tagging as tagging
    path=make_image(settings.library_root/'screenshot-red.png',COLORS['red'])
    f=scan(settings.library_root,settings.library_root)[0]
    a=decode_image(path,f.mtime).analysis
    E=np.array([1,0,0,.05],np.float32)
    cache=AnalysisCache(settings.data_dir/'test.db')
    spy=Mock(wraps=fake_embedder);ordered=[(f,a,E)]
    first=tag_images(cache,ordered,spy)
    assert {'horizontal','screenshot','photo'}<={t['label']for t in first[f.id]}
    spy.embed_texts.reset_mock();assert tag_images(cache,ordered,spy)==first;spy.embed_texts.assert_not_called()
    monkeypatch.setattr(tagging,'VERSION',VERSION+1);tag_images(cache,ordered,spy);assert spy.embed_texts.called
    spy.embed_texts.reset_mock()
    tag_images(cache,[(replace(f,size=f.size+1,mtime=f.mtime+1),a,E)],spy);assert spy.embed_texts.called
    assert tag_images(cache,[],spy)=={}
    cache.close()


def test_tag_facets_exact_and_filters_aliases_and_stale_files(settings,fake_embedder):
    for name,color in [('Trip/red.jpg','red'),('Trip/blue.jpg','blue'),('Elsewhere/red.jpg','red')]:
        make_image(settings.library_root/name,COLORS[color],fmt='JPEG')
    app=create_app(settings,embedder_factory=lambda:fake_embedder,llm_factory=lambda:None)
    with TestClient(app)as c:
        assert c.get('/api/library/tags',params={'folder':'Trip'}).json()['tagged']==0
        j=wait(c,c.post('/api/jobs',json={'strategy':'date'}).json()['id']);assert j['status']=='done',j
        assert all(p['tags']for p in j['plan'])
        facets=c.get('/api/library/tags',params={'folder':'Trip'}).json()
        assert facets['tagged']==2 and {t['label']:t['count']for t in facets['tags']}['red']==1
        results=c.get('/api/library/search',params=[('q','red'),('folder','Trip'),('tag','red'),('tag','horizontal')]).json()['results']
        assert len(results)==1 and results[0]['path']=='Trip/red.jpg' and results[0]['tags']
        assert not c.get('/api/library/search',params={'q':'red','folder':'Trip','tag':'red dress'}).json()['results']
        # Add an inspectable subject tag to verify whole-word aliases; not semantic probability assertions.
        path=settings.library_root/'Trip/red.jpg';stat=path.stat();cache=app.state.manager.cache
        cache.put_json('tags',str(path),stat.st_size,stat.st_mtime,{'v':VERSION,'tags':[{'label':'dog','score':.9,'group':'subject','source':'local-ai'}]})
        assert c.get('/api/library/search',params={'q':'puppy','folder':'Trip','tag':'dogs'}).json()['results'][0]['path']=='Trip/red.jpg'
        (settings.library_root/'Trip/blue.jpg').unlink()
        assert c.get('/api/library/tags',params={'folder':'Trip'}).json()['tagged']==1
        path.write_bytes(b'changed')
        assert c.get('/api/library/tags',params={'folder':'Trip'}).json()['tagged']==0
        assert not c.get('/api/library/search',params={'q':'dog','folder':'Trip','tag':'dog'}).json()['results']
        assert c.get('/api/library/tags',params={'folder':'../../'}).status_code==400
        assert c.get('/api/library/tags',params={'model':'wrong'}).status_code==400


def test_tags_can_be_disabled_and_failures_leave_a_reviewable_plan(settings,fake_embedder,monkeypatch):
    import app.recognition.tagging as tagging
    make_image(settings.library_root/'photo.jpg',COLORS['red'],fmt='JPEG')
    with TestClient(create_app(settings,embedder_factory=lambda:fake_embedder,llm_factory=lambda:None))as c:
        j=wait(c,c.post('/api/jobs',json={'strategy':'date','options':{'auto_tags':False}}).json()['id'])
        assert j['status']=='done' and not j['plan'][0]['tags']
        monkeypatch.setattr(tagging,'tag_images',Mock(side_effect=RuntimeError('tag model failed')))
        j=wait(c,c.post('/api/jobs',json={'strategy':'date'}).json()['id'])
        assert j['status']=='done' and any('tags' in warning for warning in j['warnings'])


def test_search_tags_and_vectors_survive_apply_and_undo(settings,fake_embedder):
    make_image(settings.library_root/'red.jpg',COLORS['red'],fmt='JPEG')
    app=create_app(settings,embedder_factory=lambda:fake_embedder,llm_factory=lambda:None)
    with TestClient(app)as c:
        j=wait(c,c.post('/api/jobs',json={'strategy':'date'}).json()['id'])
        applied=c.post(f"/api/jobs/{j['id']}/apply",json={'mode':'move'}).json()
        matches=c.get('/api/library/search',params={'q':'red','tag':'red'}).json()['results']
        assert len(matches)==1 and matches[0]['path']!='red.jpg' and matches[0]['tags']
        assert c.get('/api/library/status').json()['indexed']==1
        applied_plan=c.get(f"/api/jobs/{j['id']}").json()['plan']
        assert applied_plan[0]['preview_path']==matches[0]['path']
        c.post(f"/api/runs/{applied['run_id']}/undo")
        matches=c.get('/api/library/search',params={'q':'red','tag':'red'}).json()['results']
        assert len(matches)==1 and matches[0]['path']=='red.jpg'
        assert 'preview_path'not in c.get(f"/api/jobs/{j['id']}").json()['plan'][0]
        assert c.get('/api/library/status').json()['indexed']==1


def test_broad_tags_accept_evidence_while_specific_claims_and_indoor_venues_stay_conservative():
    # Controlled cosine margins exercise evidence gates, independent of any real model's accuracy.
    desired={'a photo of a cafe':.69,'a photo of an office':.65,'a photo of a selfie':.70,'a photo of a close-up portrait':.68}
    class Evidence:
        def embed_texts(self,texts):
            vectors=[]
            for text in texts:
                p=desired.get(text,.5);x=np.log(p/(1-p))/24
                vectors.append([x,np.sqrt(1-x*x)])
            return np.array(vectors,np.float32)
    tags=predict(np.array([[1.,0.]],np.float32),Evidence())[0]
    labels={t['label']for t in tags}
    assert 'cafe'in labels and 'office'not in labels and 'selfie'not in labels
