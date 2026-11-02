"""AI prompt routing: validated paths, exact labels, and a reversible plan."""
import json
from datetime import date
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.infrastructure.llm import LLMClient
from app.main import create_app
from app.recognition.rules import Rule, validate_rules
from tests.conftest import COLORS, make_image
from tests.test_api import wait


class Responses:
    def __init__(self, *data):
        self.data = list(data)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_text=json.dumps(self.data.pop(0)), usage=SimpleNamespace(input_tokens=10, output_tokens=5))


def llm_with(*data):
    responses = Responses(*data)
    return LLMClient('test', 'test-model', client=SimpleNamespace(responses=responses)), responses


def rule_data(rest=True):
    out = [{'what': 'red photos', 'folder': 'red/{date}', 'rest': False}]
    if rest:
        out.append({'what': '', 'folder': 'others/{iso}', 'rest': True})
    return out


def test_dates_and_nested_paths():
    rules = validate_rules(rule_data(), date(2026, 11, 2))
    assert rules == [Rule('red photos', 'red/02.11.2026'), Rule('', 'others/2026-11-02', True)]


@pytest.mark.parametrize('folder', ['/tmp/out', '../out', 'a/../out', 'a//out', 'a/./out', 'C:/out', 'a\\out', 'a/\x00out', 'a/.hidden', 'a/trailing.', 'a/{unknown}', 'x'*81])
def test_rejects_unsafe_or_changed_destinations(folder):
    with pytest.raises(ValueError, match='folder|destination'):
        validate_rules([{'what': 'red', 'folder': folder, 'rest': False}])


@pytest.mark.parametrize('data', [[], rule_data()*7, [rule_data()[1]], rule_data()+[rule_data()[1]],
    [{'what': '', 'folder': 'out', 'rest': False}], [{'what': 'red', 'folder': 'out', 'rest': 'false'}],
    [{'what': 'red', 'folder': 'out', 'rest': False}, {'what': 'blue', 'folder': 'OUT', 'rest': False}]])
def test_rejects_ambiguous_or_invalid_rules(data):
    with pytest.raises(ValueError):
        validate_rules(data)


def test_ai_compile_and_classification_are_structured_and_accounted():
    llm, responses = llm_with({'rules': rule_data()}, {'labels': [0, -1]})
    rules = llm.compile_rules('Red photos to red/{date}, everything else to others/{iso}', today=date(2026,11,2))
    labels = llm.classify_rules([Image.new('RGB',(20,20))]*2, rules)
    assert labels == [0, 1]
    assert responses.calls[0]['text']['format']['type'] == 'json_schema'
    assert responses.calls[1]['text']['format']['strict'] is True
    assert llm.usage == {'calls': 2, 'input_tokens': 20, 'output_tokens': 10}


@pytest.mark.parametrize('labels', [[], [0,0], [99], [True], ['0']])
def test_invalid_ai_labels_fail_instead_of_guessing(labels):
    llm, _ = llm_with({'labels': labels})
    with pytest.raises(ValueError):
        llm.classify_rules([Image.new('RGB',(20,20))], [Rule('red', 'red')])


def test_unmatched_without_catchall_stays_unsorted():
    llm, _ = llm_with({'labels': [-1]})
    assert llm.classify_rules([Image.new('RGB',(20,20))], [Rule('red','red')]) == [None]


def test_rules_need_a_prompt_and_ai(settings, fake_embedder):
    with TestClient(create_app(settings, embedder_factory=lambda:fake_embedder)) as c:
        assert c.post('/api/jobs', json={'strategy':'rules'}).status_code == 422
        r = c.post('/api/jobs', json={'strategy':'rules','options':{'rules_prompt':'red photos to red'}})
        assert r.status_code == 400 and 'AI' in r.json()['detail']


def test_rule_plan_apply_undo_and_usage(settings, fake_embedder):
    make_image(settings.library_root/'a_red.jpg', COLORS['red'])
    make_image(settings.library_root/'b_blue.jpg', COLORS['blue'])
    llm, _ = llm_with({'rules':rule_data()}, {'labels':[0,-1]})
    app=create_app(settings, embedder_factory=lambda:fake_embedder, llm_factory=lambda:llm)
    with TestClient(app) as c:
        r=c.post('/api/jobs',json={'strategy':'rules','options':{'rules_prompt':'red photos to red/{date}, everything else to others/{iso}', 'near_duplicates':False}})
        assert r.status_code==201,r.text
        job=wait(c,r.json()['id']); assert job['status']=='done',job
        by={p['name']:p for p in job['plan']}
        assert by['a_red.jpg']['destination']==f'Organized/red/{date.today():%d.%m.%Y}'
        assert by['b_blue.jpg']['destination']==f'Organized/others/{date.today().isoformat()}'
        assert all(p['source']=='ai' for p in job['plan'])
        assert job['usage']['calls']==2
        assert (settings.library_root/'a_red.jpg').exists()
        result=c.post(f"/api/jobs/{job['id']}/apply",json={'mode':'move'}).json()
        assert result['moved']==2
        undone=c.post(f"/api/runs/{result['run_id']}/undo").json()
        assert undone['undo']['problems']==[]
        assert (settings.library_root/'a_red.jpg').exists() and (settings.library_root/'b_blue.jpg').exists()


def test_unsafe_ai_output_fails_before_analyzing_or_moving(settings, fake_embedder):
    make_image(settings.library_root/'red.jpg',COLORS['red'])
    llm,_=llm_with({'rules':[{'what':'red','folder':'../escape','rest':False}]})
    with TestClient(create_app(settings,embedder_factory=lambda:fake_embedder,llm_factory=lambda:llm)) as c:
        r=c.post('/api/jobs',json={'strategy':'rules','options':{'rules_prompt':'red to ../escape'}})
        job=wait(c,r.json()['id'])
        assert job['status']=='error' and not job['plan']
        assert fake_embedder.image_calls==0
        assert c.post(f"/api/jobs/{job['id']}/apply",json={'mode':'move'}).status_code==409
