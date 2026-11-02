from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image

from app.infrastructure.faces import FaceAnalyzer, unrotate_box
from app.culling.quality import Face, Quality, QualityRules, summary, verdict, analyze_image
from app.culling.ranking import expression


@pytest.mark.parametrize('angle,expected',[(90,(.6,.2,.75,.3)),(270,(.25,.7,.4,.8)),(180,(.7,.6,.8,.75))])
def test_rotated_detector_boxes_map_back_to_original_photo(angle,expected):
    assert unrotate_box((.2,.25,.3,.4),angle)==pytest.approx(expected)


def test_tilted_profile_fallback_is_counted_without_inventing_eye_or_smile_measurements(tmp_path,monkeypatch):
    model=tmp_path/'face.task';model.touch();analyzer=FaceAnalyzer(str(model))
    monkeypatch.setattr(analyzer,'_detect_one',lambda rgb:[])
    calls=[]
    def locate(image):
        calls.append(image.size)
        return [] if len(calls)==1 else [((.2,.25,.3,.4),.84)]
    monkeypatch.setattr('app.infrastructure.identity.get_face_identifier',lambda:SimpleNamespace(available=True,locate=locate))
    found=analyzer.detect(np.zeros((300,200,3),np.uint8))
    assert len(found)==1 and not found[0].landmarks_checked
    assert found[0].box==pytest.approx((.6,.2,.75,.3))
    q=Quality(.8,.5,0,0,found,True)
    result=summary(q,QualityRules())
    assert result['faces']==1 and result['faces_expression_unknown']==1
    assert result['faces_considered']==0 and result['eyes_open']==0
    assert result['blink'] is None and result['smile'] is None and result['face_regions'][0]['blink'] is None
    assert not result['smiling'] and expression(q) is None
    # Even a stale/default blink value is not evidence when landmarks were not measured.
    found[0].blink=1
    assert 'eyes-closed' not in verdict(q,QualityRules())[1]
    measured=analyze_image(Image.fromarray(np.random.default_rng(3).integers(0,255,(200,200,3),dtype=np.uint8)),
                           SimpleNamespace(available=True,detect=lambda rgb:found))
    assert measured.faces[0].sharpness is not None


def test_fallback_complements_group_faces_without_duplicate_counts_or_low_confidence_boxes(tmp_path,monkeypatch):
    model=tmp_path/'face.task';model.touch();analyzer=FaceAnalyzer(str(model));calls=[]
    def detect(rgb):
        calls.append(1)
        return [((.1,.1,.3,.3),.1,.2,{})] if len(calls)==1 else []
    monkeypatch.setattr(analyzer,'_detect_one',detect)
    boxes=[((.1,.1,.3,.3),.99),((.6,.2,.75,.4),.9),((.4,.2,.5,.4),.3),((0.,0.,.001,.001),.99)]
    monkeypatch.setattr('app.infrastructure.identity.get_face_identifier',lambda:SimpleNamespace(available=True,locate=lambda image:boxes))
    found=analyzer.detect(np.zeros((300,200,3),np.uint8))
    assert len(found)==2 and [f.landmarks_checked for f in found]==[True,False]

def test_optional_detector_failure_preserves_landmark_faces(tmp_path,monkeypatch):
    model=tmp_path/'face.task';model.touch();analyzer=FaceAnalyzer(str(model));calls=[]
    def detect(rgb):
        calls.append(1)
        return [((.1,.1,.3,.3),.1,.2,{})] if len(calls)==1 else []
    def broken(image):raise RuntimeError('optional detector failed')
    monkeypatch.setattr(analyzer,'_detect_one',detect)
    monkeypatch.setattr('app.infrastructure.identity.get_face_identifier',lambda:SimpleNamespace(available=True,locate=broken))
    found=analyzer.detect(np.zeros((300,200,3),np.uint8))
    assert len(found)==1 and found[0].landmarks_checked


def test_unmeasured_profile_face_does_not_degrade_verified_eye_focus():
    from app.culling.ranking import subject_focus
    measured=Face(.1,.2,.1,(.1,.1,.4,.4),sharpness=.65)
    profile=Face(0,0,.08,(.5,.1,.7,.4),sharpness=.3,landmarks_checked=False)
    assert subject_focus(Quality(.8,.5,0,0,[measured,profile]))==pytest.approx(.65)
