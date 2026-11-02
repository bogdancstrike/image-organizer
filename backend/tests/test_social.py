"""Social readiness and advanced culling: controlled defects, crop retention and ranking contracts."""
import numpy as np
import pytest
from PIL import Image, ImageFilter
from fastapi.testclient import TestClient

from app.culling.quality import Face, Quality, QualityRules, advanced_signals, analyze_image
from app.culling.social import assess, crop_fit
from app.culling.ranking import rank
from app.main import create_app
from app.culling.duplicates import DupItem, find_duplicates
from tests.conftest import make_image, COLORS
from tests.test_api import wait


def quality(aspect=1,faces=()):
    return Quality(.85,.5,0,0,list(faces),True,features={'aspect_ratio':aspect,'thumbnail':.8,'contrast':.8,'color':.7,'resolution':1})


def test_crop_suitability_preserves_important_faces_and_originals():
    centered=Face(.1,.7,.1,(.35,.2,.65,.6));edge=Face(.1,.7,.1,(0,.2,.2,.6))
    assert crop_fit(quality(2,[centered]),'portrait')>crop_fit(quality(2,[edge]),'portrait')
    assert crop_fit(quality(2,[edge]),'original')==1
    assert crop_fit(quality(.8),'portrait')==1
    assert crop_fit(quality(.3),'landscape')<.5


@pytest.mark.parametrize('format',['portrait','square','vertical','landscape','original'])
def test_social_signals_are_finite_and_format_aware(format,fake_embedder):
    out=assess(['a'],{'a':quality()},np.array([[1,0,0,.05]],np.float32),fake_embedder,format)
    assert set(out['a'])=={'crop','clarity','impact','contrast','color','social'}
    assert all(0<=v<=1 and np.isfinite(v)for v in out['a'].values())


def test_social_fallback_and_input_validation(fake_embedder):
    from unittest.mock import Mock
    broken=Mock(embed_texts=Mock(side_effect=RuntimeError('offline tower failure')))
    assert assess([],{},np.empty((0,4)),broken)=={}
    a=assess(['a'],{'a':quality()},np.ones((1,4)),broken)['a']
    assert a['impact']==.5
    with pytest.raises(ValueError):assess([],{},np.empty((0,4)),broken,'invalid')


def test_advanced_gradients_and_thumbnail_detail_decrease_with_blur():
    rng=np.random.default_rng(9);im=Image.fromarray(rng.integers(0,255,(256,256,3),dtype=np.uint8))
    sharp=analyze_image(im,None);soft=analyze_image(im.filter(ImageFilter.GaussianBlur(4)),None)
    assert sharp.features['tenengrad']>soft.features['tenengrad']
    assert sharp.features['thumbnail']>soft.features['thumbnail']
    flat=analyze_image(Image.new('RGB',(32,32),(90,90,90)),None)
    assert flat.features['color']==.5 and flat.features['directionality']==0
    # Block-boundary metric recognizes a controlled block artifact; it is not a learned JPEG quality score.
    gray=np.tile(np.repeat(np.array([30,200],np.uint8),8), (32,2))
    f=advanced_signals(np.repeat(gray[:,:,None],3,axis=2),gray,32,32)
    assert f['blocking']>.9


def test_social_overlay_subject_relevance_pareto_and_novelty_are_explainable(fake_embedder):
    ids=['a','b'];E=np.array([[1,0,0,.05],[0,0,1,.05]],np.float32)
    Q={'a':quality(.8), 'b':quality(2)}
    result=rank(ids,Q,E,fake_embedder,QualityRules(),options={'social_media':True,'subject_prompt':'red dress','preserve_unique':True})
    assert result.info['a'].parts['relevance']>result.info['b'].parts['relevance']
    assert all({'social','crop','novelty','pareto'}<=set(pi.parts)for pi in result.info.values())
    assert result.info['a'].parts['crop']>result.info['b'].parts['crop']
    plain=rank(ids,Q,E,fake_embedder,QualityRules(),options={'pareto_review':False,'preserve_unique':False})
    assert all(pi.parts['pareto']==0 for pi in plain.info.values())
    assert all('social'not in pi.parts for pi in plain.info.values())


def test_difference_hash_does_not_merge_distinct_burst_frames():
    a=DupItem('a','image','sha-a','0',100,100,1,'a.jpg',embedding=np.array([1.,0]),dhash='0000000000000000')
    b=DupItem('b','image','sha-b','0',100,100,2,'b.jpg',embedding=np.array([1.,0]),dhash='ffffffffffffffff')
    assert find_duplicates([a,b])=={}
    b.dhash='0000000000000001';assert find_duplicates([a,b])=={'b':'a'}


def test_social_media_preset_uses_culling_and_keeps_originals(settings,fake_embedder):
    path=make_image(settings.library_root/'post.jpg',COLORS['red'],fmt='JPEG')
    with TestClient(create_app(settings,embedder_factory=lambda:fake_embedder,llm_factory=lambda:None))as c:
        assert any(p['name']=='Social Media'for p in c.get('/api/presets').json())
        assert any(r['id']=='social-media'for r in c.get('/api/recipes').json())
        j=wait(c,c.post('/api/jobs',json={'strategy':'preset','set_id':'social-media'}).json()['id'])
        assert j['status']=='done' and j['request']['strategy']=='cull'
        assert j['request']['options']['quality']['social_media']
        assert 'social'in j['plan'][0]['pick']['parts'] and path.exists()
        assert c.post('/api/jobs',json={'strategy':'cull','options':{'quality':{'social_format':'bad'}}}).status_code==422


def test_burst_alternatives_have_review_labels_instead_of_technical_rejection(settings,fake_embedder):
    from app.organization.jobs import JobManager
    from app.infrastructure.category_store import CategoryStore
    m=JobManager(settings,lambda:fake_embedder,CategoryStore(settings.data_dir/'sets.db'))
    m._pick_info={'a':{'score':.85}}
    assert m._xmp_for('a','burst',{'a':quality()},QualityRules(),{'a':{'best':False}})=={'rating':4,'label':'Yellow'}
    assert m._xmp_for('a','blurry',{'a':quality()},QualityRules(),{})=={'rating':-1,'label':'Red'}
    m.cache.close()
