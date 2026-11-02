"""Exercise model adapters with deterministic model results, including empty detections."""
import sys
import threading
from types import SimpleNamespace

import numpy as np
from PIL import Image

from app.ocr import TextReader
from app.people import FaceIdentifier, FaceID
from app.quality import FaceAnalyzer, _expression, sharpness, Face


def test_ocr_reads_confident_text_and_caps_coverage(monkeypatch):
    box=[[0,0],[100,0],[100,50],[0,50]]
    calls=[]
    class Engine:
        def __call__(self,img):
            calls.append(img.shape)
            return [[box,'INVOICE 2026',.99],[box,'ignore',.1]],None
    monkeypatch.setitem(sys.modules,'rapidocr_onnxruntime',SimpleNamespace(RapidOCR=Engine))
    reader=TextReader();assert reader.available
    result=reader.read(Image.new('RGB',(100,50)))
    assert result=={'chars':11,'coverage':1.0,'text':'INVOICE 2026'}
    assert reader._engine() is reader._engine()
    reader._local.ocr=lambda img:(None,None)
    assert reader.read(Image.new('RGB',(100,50)))=={'chars':0,'coverage':0.0,'text':''}


def test_face_identifier_normalizes_embeddings_clamps_boxes_and_skips_tiny_faces(tmp_path,monkeypatch):
    import cv2
    model=tmp_path/'face.onnx';model.touch()
    detector=SimpleNamespace(setInputSize=lambda size:None,detect=lambda img:(None,np.array([[10,20,50,60],[0,0,10,10]],np.float32)))
    recognizer=SimpleNamespace(alignCrop=lambda img,f:img,feature=lambda img:np.array([[3,4]],np.float32))
    monkeypatch.setattr(cv2.FaceDetectorYN,'create',lambda *args:detector)
    monkeypatch.setattr(cv2.FaceRecognizerSF,'create',lambda *args:recognizer)
    ident=FaceIdentifier(str(model),str(model));assert ident.available
    faces=ident.identify(Image.new('RGB',(100,100)))
    assert len(faces)==1 and faces[0].box==(.1,.2,.6,.8)
    np.testing.assert_allclose(faces[0].emb,[.6,.8])
    roundtrip=FaceID.from_dict(faces[0].to_dict());assert roundtrip.box==faces[0].box
    detector.detect=lambda img:(None,None)
    assert ident.identify(Image.new('RGB',(100,100)))==[]
    assert not FaceIdentifier(None,None).available


def test_expression_extracts_gaze_mouth_and_head_turn_from_landmarks():
    landmarks=[SimpleNamespace(x=.5) for _ in range(264)]
    landmarks[33].x=.2;landmarks[263].x=.8;landmarks[1].x=.75
    result=_expression({'eyeLookOutLeft':.8,'eyeLookInRight':.8,'jawOpen':.7,'mouthFrownLeft':.4},landmarks)
    assert result['gaze']==.8 and result['mouth']==.7 and result['yaw']>.8 and result['frown']==.2
    assert _expression({},[])['yaw']==0


def test_group_face_tiles_deduplicate_and_preserve_expression(tmp_path,monkeypatch):
    model=tmp_path/'face.task';model.touch();analyzer=FaceAnalyzer(str(model))
    calls=[]
    def detect(rgb):
        calls.append(rgb.shape)
        return [((.3,.3,.5,.5),.1,.8,{'gaze':.1}),((0,0,.001,.001),0,0,{})] if len(calls)==1 else []
    monkeypatch.setattr(analyzer,'_detect_one',detect)
    faces=analyzer.detect(np.zeros((240,320,3),np.uint8))
    assert len(faces)==1 and faces[0].expr=={'gaze':.1} and len(calls)==14
    gray=np.random.default_rng(1).integers(0,255,(200,200),dtype=np.uint8)
    assert sharpness(gray,[Face(.1,.5,.1,(.1,.1,.9,.9))])>0


def test_detected_face_eye_focus_is_cached_with_the_new_analysis_version():
    from app.quality import analyze_image, QUALITY_VERSION
    face=Face(.1,.8,.25,(.2,.2,.8,.8))
    analyzer=SimpleNamespace(available=True,detect=lambda rgb:[face])
    noise=np.random.default_rng(1).integers(0,255,(240,320,3),dtype=np.uint8)
    result=analyze_image(Image.fromarray(noise),analyzer)
    assert result.v==QUALITY_VERSION==5 and result.faces[0].sharpness is not None
    assert result.faces_checked and result.sharpness>0
    restored=type(result).from_dict(result.to_dict());assert restored.faces[0].sharpness==face.sharpness


def test_identity_anchors_require_readable_landmarks_and_confident_detection(tmp_path,monkeypatch):
    import cv2
    path=tmp_path/'model';path.touch()
    frontal=[10,10,80,90,30,40,70,40,50,60,35,80,65,80,.99]
    profile=[10,10,80,90,30,40,40,40,55,60,35,80,45,80,.99]
    low=frontal.copy();low[-1]=.85
    detector=SimpleNamespace(setInputSize=lambda size:None,detect=lambda img:(None,np.array([frontal,profile,low],np.float32)))
    recognizer=SimpleNamespace(alignCrop=lambda img,f:img,feature=lambda img:np.array([[3,4]],np.float32))
    monkeypatch.setattr(cv2.FaceDetectorYN,'create',lambda *a:detector)
    monkeypatch.setattr(cv2.FaceRecognizerSF,'create',lambda *a:recognizer)
    faces=FaceIdentifier(str(path),str(path)).identify(Image.new('RGB',(200,200)))
    assert [f.reliable for f in faces]==[True,False,False]
    assert FaceID.from_dict(faces[1].to_dict()).reliable is False
