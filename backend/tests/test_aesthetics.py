"""Pinned model parity, encoder compatibility, cache invalidation and bounded CPU inference."""
from types import SimpleNamespace

import numpy as np
import pytest

from app.infrastructure.aesthetics import AestheticPredictor, SPACE, VERSION
from app.infrastructure.category_store import CategoryStore
from app.media.decoding import Analysis
from app.media.scanning import MediaFile
from app.organization.aesthetic_analysis import analyze
from app.organization.jobs import Job, JobManager
from app.culling.quality import Quality, QualityRules
from app.culling.social import assess
from tests.conftest import COLORS, make_image


def test_numpy_inference_matches_pinned_upstream_pytorch_and_normalizes_inputs():
    model=AestheticPredictor()
    E=np.sin(np.arange(512)*.17).reshape(1,-1)
    # Generated from the pinned original .pth with torch.nn.functional.linear on normalized input.
    assert float(model.predict(E,SPACE)[0])==pytest.approx(3.690062999725342,abs=1e-5)
    np.testing.assert_allclose(model.predict(E,SPACE),model.predict(E*30,SPACE),atol=1e-5)
    assert model.predict(np.empty((0,512)),SPACE).shape==(0,)


@pytest.mark.parametrize('E,space',[(np.ones((1,512)),'siglip2'),(np.ones((1,768)),SPACE),
                                  (np.zeros((1,512)),SPACE),(np.full((1,512),np.nan),SPACE),
                                  (np.ones(512),SPACE)])
def test_incompatible_or_invalid_embeddings_cannot_silently_produce_scores(E,space):
    with pytest.raises(ValueError):AestheticPredictor().predict(E,space)


def test_model_integrity_is_checked_before_loading(tmp_path):
    path=tmp_path/'changed.json';path.write_text('{"weight":[]}')
    with pytest.raises(ValueError,match='checksum'):AestheticPredictor(path)


class Clip:
    embedding_space=SPACE
    calls=0
    def embed_images(self,images):
        self.calls+=len(images)
        return np.tile(np.sin(np.arange(512)*.17),(len(images),1))


def fixture(settings):
    clip=Clip()
    manager=JobManager(settings,lambda model:clip,CategoryStore(settings.data_dir/'sets.db'))
    ordered=[];quality={}
    for i in range(3):
        path=make_image(settings.library_root/f'photo{i}.jpg',COLORS['red'],fmt='JPEG')
        st=path.stat();f=MediaFile(str(i),path,path.name,'image',st.st_size,st.st_mtime)
        a=Analysis(320,240,0,str(i),None,False)
        ordered.append((f,a,np.ones(512)))
        quality[f.id]=Quality(.9,.5,0,0,[],True)
    return clip,manager,ordered,quality


def test_clip_reuses_existing_embeddings_and_cached_model_results(settings):
    clip,manager,ordered,quality=fixture(settings)
    job=Job('a',{})
    analyze(manager,job,ordered,quality,QualityRules(),clip)
    assert clip.calls==0 and job.stats['aesthetic_scored']==3
    assert all(0<=q.features['aesthetic']<=1 for q in quality.values())
    before=[q.features['aesthetic']for q in quality.values()]
    # Warm-cache result stays tied to file/model identity, independent of supplied vector changes.
    changed=[(f,a,-e)for f,a,e in ordered]
    analyze(manager,Job('b',{}),changed,quality,QualityRules(),clip)
    assert [q.features['aesthetic']for q in quality.values()]==before
    f=ordered[0][0]
    manager.cache.put_json('aesthetics',str(f.path),f.size,f.mtime,{'v':'old-model','raw':99})
    analyze(manager,Job('c',{}),changed,quality,QualityRules(),clip)
    assert manager.cache.get_json('aesthetics',str(f.path),f.size,f.mtime)['v']==VERSION
    assert quality[f.id].features['aesthetic']!=before[0]
    manager.cache.close()


def test_siglip_jobs_use_verified_clip_tower_with_bounded_shortlist_and_warm_cache(settings,monkeypatch):
    clip,manager,ordered,quality=fixture(settings)
    monkeypatch.setattr('app.organization.aesthetic_analysis.LIMIT',2)
    job=Job('a',{})
    analyze(manager,job,ordered,quality,QualityRules(),SimpleNamespace(embedding_space='siglip2'))
    assert clip.calls==2 and job.stats['aesthetic_scored']==2 and job.warnings
    assert sum('aesthetic'in q.features for q in quality.values())==2
    # Removing the head result can still reuse cached CLIP vectors without image inference.
    manager.cache.put_json('aesthetics',str(ordered[0][0].path),ordered[0][0].size,ordered[0][0].mtime,{'v':'old','raw':0})
    analyze(manager,Job('b',{}),ordered,quality,QualityRules(),SimpleNamespace())
    assert clip.calls==2
    job.cancel_requested=True
    analyze(manager,job,ordered,quality,QualityRules(),clip)
    analyze(manager,Job('c',{}),[],{},QualityRules(),clip)
    manager.embedder_factory=lambda model:SimpleNamespace()
    with pytest.raises(ValueError,match='compatibility'):analyze(manager,Job('d',{}),ordered,quality,QualityRules(),SimpleNamespace())
    manager.cache.close()


def test_learned_appeal_influences_social_ranking_and_is_exposed_separately(fake_embedder):
    high=Quality(.9,.5,0,0,[],True,features={'aesthetic':.8})
    low=Quality(.9,.5,0,0,[],True,features={'aesthetic':.2})
    result=assess(['a','b'],{'a':high,'b':low},np.ones((2,4)),fake_embedder)
    assert result['a']['social']>result['b']['social']
    assert result['a']['aesthetic']==.8 and result['b']['aesthetic']==.2
