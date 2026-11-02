"""Guard inward dependencies and per-application HTTP service isolation."""
import ast
import importlib.util
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import COLORS, make_image
from tests.test_api import wait

CORE = [
    'app.catalog.categories','app.catalog.presets','app.culling.quality','app.culling.ports',
    'app.culling.ranking','app.culling.social','app.culling.service',
    'app.recognition.classification','app.recognition.people','app.recognition.ocr',
    'app.recognition.ports','app.recognition.rules','app.recognition.tagging',
]


@pytest.mark.parametrize('module',CORE)
def test_domain_logic_does_not_import_delivery_storage_or_model_providers(module):
    spec=importlib.util.find_spec(module)
    tree=ast.parse(Path(spec.origin).read_text())
    forbidden=('app.api','app.main','app.infrastructure','app.organization.jobs','fastapi','sqlite3','openai','fastembed','mediapipe','rapidocr_onnxruntime')
    for node in ast.walk(tree):
        imports=[alias.name for alias in node.names]if isinstance(node,ast.Import)else[node.module or '']if isinstance(node,ast.ImportFrom)else[]
        assert not any(name==prefix or name.startswith(prefix+'.')for name in imports for prefix in forbidden), (module,imports)


def test_library_does_not_reach_into_private_cache_connections():
    spec=importlib.util.find_spec('app.library.service')
    tree=ast.parse(Path(spec.origin).read_text())
    assert not any(isinstance(node,ast.Attribute)and node.attr=='_db'for node in ast.walk(tree))


def test_router_factories_keep_library_and_settings_isolated_between_apps(settings,fake_embedder,tmp_path):
    second_root=tmp_path/'second-library';second_root.mkdir()
    second=replace(settings,library_root=second_root,data_dir=tmp_path/'second-data')
    make_image(settings.library_root/'first.jpg',COLORS['red'],fmt='JPEG')
    make_image(second.library_root/'second.jpg',COLORS['blue'],fmt='JPEG')
    first_app=create_app(settings,embedder_factory=lambda:fake_embedder,llm_factory=lambda:None)
    second_app=create_app(second,embedder_factory=lambda:fake_embedder,llm_factory=lambda:None)
    with TestClient(first_app)as a,TestClient(second_app)as b:
        a.put('/api/settings',json={'source':'first'})
        assert b.get('/api/settings').json()=={}
        for client,name in ((a,'first.jpg'),(b,'second.jpg')):
            job=wait(client,client.post('/api/jobs',json={'strategy':'date'}).json()['id'])
            assert job['status']=='done' and [p['name']for p in job['plan']]==[name]
