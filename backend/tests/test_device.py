"""Device configuration and explicit ONNX providers; tests require no GPU hardware."""
import sys
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image

from app.config import load_settings
from app.embedder import ClipEmbedder, execution_providers, get_clip_embedder
import app.embedder as embedding


def test_device_defaults_to_cpu_and_rejects_typos(monkeypatch):
    monkeypatch.delenv('DEVICE',raising=False)
    assert load_settings().device=='cpu'
    monkeypatch.setenv('DEVICE','gpu');assert load_settings().device=='gpu'
    monkeypatch.setenv('DEVICE','gup')
    with pytest.raises(ValueError,match='DEVICE'):
        load_settings()


def install_runtime(monkeypatch, providers=('CPUExecutionProvider',), actual=None):
    preloads=[];calls=[]
    monkeypatch.setitem(sys.modules,'onnxruntime',SimpleNamespace(get_available_providers=lambda:list(providers),preload_dlls=lambda **kw:preloads.append(kw)))
    class Tower:
        def __init__(self,name,**kwargs):
            calls.append(kwargs)
            self.model=SimpleNamespace(model=SimpleNamespace(get_providers=lambda:actual if actual is not None else kwargs['providers']))
        def embed(self,items,**kwargs):
            return [np.array([1.0,2.0,3.0]) for _ in items]
    monkeypatch.setitem(sys.modules,'fastembed',SimpleNamespace(ImageEmbedding=Tower,TextEmbedding=Tower))
    return calls,preloads


def test_cpu_is_explicit_even_on_a_gpu_host(monkeypatch):
    calls,preloads=install_runtime(monkeypatch,('CPUExecutionProvider','CUDAExecutionProvider'))
    model=ClipEmbedder(device='cpu')
    assert all(c['providers']==['CPUExecutionProvider'] for c in calls)
    assert preloads==[]
    assert model.embed_images([Image.new('RGB',(4,4))]).shape==(1,3)
    assert model.embed_texts(['hello','hello']).shape==(2,3)


def test_gpu_propagates_to_both_towers(monkeypatch):
    calls,preloads=install_runtime(monkeypatch,('CPUExecutionProvider','CUDAExecutionProvider'))
    ClipEmbedder(device='gpu',model='siglip2')
    assert all(c['providers']==['CUDAExecutionProvider','CPUExecutionProvider'] for c in calls)
    assert len(preloads)==1


def test_missing_cuda_never_silently_falls_back(monkeypatch):
    install_runtime(monkeypatch)
    with pytest.raises(RuntimeError,match='DEVICE=gpu'):
        execution_providers('gpu')


def test_failed_cuda_session_never_silently_falls_back(monkeypatch):
    install_runtime(monkeypatch,('CPUExecutionProvider','CUDAExecutionProvider'),actual=['CPUExecutionProvider'])
    with pytest.raises(RuntimeError,match='CUDA'):
        ClipEmbedder(device='gpu')


def test_singletons_are_separate_by_device_model_and_cache(monkeypatch):
    monkeypatch.setattr(embedding,'_singletons',{})
    install_runtime(monkeypatch,('CPUExecutionProvider','CUDAExecutionProvider'))
    cpu=get_clip_embedder('/models',device='cpu')
    assert cpu is get_clip_embedder('/models',device='cpu')
    assert cpu is not get_clip_embedder('/models',device='gpu')
    assert cpu is not get_clip_embedder('/models',model='siglip2')
    assert cpu is not get_clip_embedder('/other')


def test_empty_siglip_embeddings_have_the_correct_width(monkeypatch):
    install_runtime(monkeypatch)
    model=ClipEmbedder(model='siglip2')
    assert model.embed_images([]).shape==(0,768)
    assert model.embed_texts([]).shape==(0,768)
