import numpy as np

from app.library.relevance import rank_query
from app.recognition.scenes import room_evidence
from app.recognition.tagging import predict


class Rooms:
    def embed_texts(self, texts):
        rows=[]
        for text in texts:
            # Whole-image "photo of kitchen" underrepresents a room behind a dominant person.
            if 'kitchen' in text:
                rows.append([1., .5, 0., 0.] if 'person photographed' in text or 'background' in text else [0.,1.,0.,0.])
            elif 'bedroom' in text:
                rows.append([1., 0., .5, 0.] if 'person photographed' in text or 'background' in text else [0.,0.,1.,0.])
            elif 'dog' in text:rows.append([0.,0.,0.,1.])
            else:rows.append([1.,0.,0.,0.])
        return np.array(rows,np.float32)


def test_background_kitchen_is_retrieved_without_accepting_a_bedroom_or_unknown_room():
    E=np.array([[1.,.35,0.,0.],[1.,0.,.35,0.],[1.,0.,0.,0.]])
    _,yes,_=rank_query(E,'kitchen',Rooms(),[[],[],[]],['','',''])
    assert yes.tolist()==[True,False,False]
    assert room_evidence(E,Rooms())['kitchen'][0].tolist()==[True,False,False]


def test_background_room_does_not_override_a_missing_subject_in_compound_query():
    E=np.array([[1.,.35,0.,0.]])
    assert not rank_query(E,'dog in kitchen',Rooms(),[[]],[''])[1][0]
    assert not rank_query(E,'unicorn kitchen',Rooms(),[[]],[''])[1][0]


def test_room_evidence_also_improves_local_search_tags():
    tags=predict(np.array([[1.,.35,0.,0.],[1.,0.,.35,0.],[1.,0.,0.,0.]]),Rooms())
    assert any(tag['label']=='kitchen'for tag in tags[0])
    assert not any(tag['label']=='kitchen'for tag in tags[1])
    assert not any(tag['label']=='kitchen'for tag in tags[2])
