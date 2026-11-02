"""Absent and compound concepts must not return nearest-but-unrelated photos."""
import numpy as np
from fastapi.testclient import TestClient

from app.library.relevance import rank_query, concepts
from app.main import create_app
from tests.conftest import COLORS, make_image
from tests.test_api import wait


class Subjects:
    def embed_texts(self,texts):
        result=[]
        for text in texts:
            text=text.lower();dog='dog'in text;snow='snow'in text
            result.append([float(dog),float(snow),float('person'in text),.2 if dog or snow or 'person'in text else 1.])
        return np.array(result,np.float32)


def test_compound_query_requires_all_known_concepts():
    E=np.array([[1,1,0,.2],[1,0,0,.2],[0,0,1,.2]],np.float32)
    scores,accepted,why=rank_query(E,'dog in a snow',Subjects(),[[],[],[]],['','',''])
    assert accepted.tolist()==[True,False,False]
    assert np.isfinite(scores[0]) and 'dog'in why[0]and'snow'in why[0]


def test_partial_stored_tag_match_does_not_override_missing_concept():
    E=np.array([[0,0,1,.2]],np.float32)
    assert not rank_query(E,'dog in snow',Subjects(),[[{'label':'dog'}]],[''])[1][0]
    assert rank_query(E,'dog in snow',Subjects(),[[{'label':'dog'},{'label':'snow'}]],[''])[1][0]


def test_ocr_exact_evidence_and_explicit_tag_browsing(fake_embedder):
    E=np.ones((1,4),np.float32)
    assert rank_query(E,'invoice 2026',fake_embedder,[[]],['INVOICE 2026'])[1][0]
    assert not rank_query(E,'invoice 2026',fake_embedder,[[]],['invoice 2025'])[1][0]
    assert rank_query(E,'photo',fake_embedder,[[{'label':'photo'}]],[''],browse=True)[1][0]
    assert not rank_query(E,'photo',fake_embedder,[[]],[''])[1][0]
    assert any(c[0]=='black and white'for c in concepts('black and white portrait'))
    assert not any(c[0]=='black and white'for c in concepts('black dress and white shoes'))


def test_no_minimum_result_fallback_in_small_and_large_libraries(settings,fake_embedder):
    for i in range(16):make_image(settings.library_root/f'p{i}.jpg',COLORS['red'],fmt='JPEG',noise_seed=i)
    with TestClient(create_app(settings,embedder_factory=lambda:fake_embedder,llm_factory=lambda:None))as c:
        job=wait(c,c.post('/api/jobs',json={'strategy':'date'}).json()['id']);assert job['status']=='done'
        missing=c.get('/api/library/search',params={'q':'dog in a snow'}).json()
        assert missing['results']==[] and missing['indexed']==16
        matching=c.get('/api/library/search',params={'q':'red'}).json()
        assert matching['results']and all(r['match_explanation']for r in matching['results'])
