"""End-to-end API tests with the FakeEmbedder: sort → plan → apply → undo, SSE replay, cache, LLM fallback."""
import json
import time
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.llm import LLMClient
from app.main import create_app
from tests.conftest import COLORS, HAS_FFMPEG, FakeEmbedder, make_image, make_video

RED_GREEN = {
    "name": "Colors",
    "categories": [
        {"name": "Red things", "prompts": ["red"]},
        {"name": "Green things", "prompts": ["green"]},
        {"name": "Screenshots", "prompts": ["blue"]},
    ],
}


def build_library(lib):
    for i in range(4):
        make_image(lib / f"r{i}.jpg", COLORS["red"], fmt="JPEG", noise_seed=i)
        make_image(lib / f"g{i}.jpg", COLORS["green"], fmt="JPEG", noise_seed=100 + i)
    # exact duplicate of r0
    (lib / "r0 (1).jpg").write_bytes((lib / "r0.jpg").read_bytes())
    make_image(lib / "Screenshot_1.png", COLORS["green"], size=(200, 420), noise_seed=7)
    (lib / "broken.jpg").write_bytes(b"garbage")


def wait(client, job_id, timeout=30):
    end = time.time() + timeout
    while time.time() < end:
        j = client.get(f"/api/jobs/{job_id}").json()
        if j["status"] != "running":
            return j
        time.sleep(0.05)
    raise AssertionError("job did not finish")


@pytest.fixture
def client(settings, fake_embedder):
    app = create_app(settings, embedder_factory=lambda: fake_embedder, llm_factory=lambda: None)
    with TestClient(app) as c:
        yield c


def snapshot(lib):
    return sorted(p.relative_to(lib).as_posix() for p in lib.rglob("*") if p.is_file())


def test_full_round_trip(client, settings):
    lib = settings.library_root
    build_library(lib)
    before = snapshot(lib)
    set_id = client.post("/api/category-sets", json=RED_GREEN).json()["id"]
    job_id = client.post("/api/jobs", json={"strategy": "custom", "set_id": set_id}).json()["id"]
    job = wait(client, job_id)
    assert job["status"] == "done", job
    assert snapshot(lib) == before  # plan only, nothing moved (AC-10)

    by_name = {p["name"]: p for p in job["plan"]}
    assert by_name["r1.jpg"]["category"] == "Red things"
    assert by_name["g2.jpg"]["category"] == "Green things"
    assert by_name["Screenshot_1.png"]["category"] == "Screenshots"
    assert by_name["r0 (1).jpg"]["category"] == "Duplicates"
    assert by_name["r0 (1).jpg"]["duplicate_of"] == by_name["r0.jpg"]["file_id"]
    assert job["errors"][0]["rel_path"] == "broken.jpg"
    assert by_name["r1.jpg"]["destination"] == "Organized/Photos/Red things"

    r = client.post(f"/api/jobs/{job_id}/apply", json={"mode": "move"})
    assert r.status_code == 200, r.text
    run_id = r.json()["run_id"]
    assert (lib / "Organized/Photos/Red things/r1.jpg").exists()
    assert (lib / "Organized/_Duplicates/r0 (1).jpg").exists()
    assert client.post(f"/api/jobs/{job_id}/apply", json={"mode": "move"}).status_code == 409  # once only

    runs = client.get("/api/runs").json()
    assert runs[0]["run_id"] == run_id and runs[0]["status"] == "applied"

    u = client.post(f"/api/runs/{run_id}/undo").json()
    assert u["status"] == "undone" and u["undo"]["problems"] == []
    assert snapshot(lib) == before
    assert not (lib / "Organized").exists()


def test_sse_replays_events(client, settings):
    build_library(settings.library_root)
    job_id = client.post("/api/jobs", json={"strategy": "preset", "set_id": "lifestyle"}).json()["id"]
    wait(client, job_id)
    with client.stream("GET", f"/api/jobs/{job_id}/events") as resp:
        body = "".join(resp.iter_text())
    events = [e for line in body.splitlines() if line.startswith("data: [") for e in json.loads(line[6:])]
    types = [e["type"] for e in events]
    assert types[0] == "phase" and types[-1] == "done"
    assert types.count("file") == 10 and types.count("assign") == 10
    assert [e["seq"] for e in events] == list(range(len(events)))


def test_cache_second_run_embeds_nothing(client, settings, fake_embedder):
    build_library(settings.library_root)
    j1 = client.post("/api/jobs", json={"strategy": "date"}).json()["id"]
    assert wait(client, j1)["stats"]["embedded"] == 10
    calls = fake_embedder.image_calls
    j2 = client.post("/api/jobs", json={"strategy": "date"}).json()["id"]
    job2 = wait(client, j2)
    assert job2["stats"]["embedded"] == 0 and fake_embedder.image_calls == calls
    assert all("/" in p["category"] for p in job2["plan"] if p["category"] != "Duplicates")


def test_auto_without_key_uses_vocabulary(client, settings):
    build_library(settings.library_root)
    job = wait(client, client.post("/api/jobs", json={"strategy": "auto"}).json()["id"])
    assert job["status"] == "done"
    assert len([c for c in job["categories"] if not c["id"].startswith("_")]) >= 1
    assert job["usage"] is None


def test_bad_requests(client):
    assert client.post("/api/jobs", json={"source": "../.."}).status_code == 400
    assert client.post("/api/jobs", json={"strategy": "custom", "set_id": "nope"}).status_code == 404
    bad = {"name": "x", "categories": [{"name": "A"}, {"name": "a"}]}
    assert client.post("/api/category-sets", json=bad).status_code == 422
    assert client.get("/api/thumbs/notasha").status_code == 400


def test_health_never_leaks_key(settings, fake_embedder):
    from dataclasses import replace

    s = replace(settings, openai_api_key="sk-secret-123")
    with TestClient(create_app(s, embedder_factory=lambda: fake_embedder)) as c:
        h = c.get("/api/health").json()
    assert h["ai_available"] is True and "sk-secret" not in json.dumps(h)


class _FakeResponses:
    def __init__(self, fail=False):
        self.calls = []
        self.fail = fail

    def create(self, **kw):
        self.calls.append(kw)
        if self.fail:
            raise TimeoutError("boom")
        n = sum(1 for c in kw["input"][0]["content"] if c["type"] == "input_image")
        text = kw["input"][0]["content"][0]["text"]
        if "contact sheets" in text:
            out = {"groups": [{"i": i + 1, "name": f"Group Name {i + 1}", "emoji": "✨"} for i in range(n)]}
        else:
            out = {"labels": ["Red things"] * n}
        return SimpleNamespace(output_text=json.dumps(out), usage=SimpleNamespace(input_tokens=10, output_tokens=5))


def _llm_app(settings, fake_embedder, responses):
    llm = LLMClient("k", "gpt-5.6-luna", client=SimpleNamespace(responses=responses))
    return create_app(settings, embedder_factory=lambda: fake_embedder, llm_factory=lambda: llm)


def test_auto_with_llm_makes_exactly_one_naming_call(settings, fake_embedder):
    build_library(settings.library_root)
    fr = _FakeResponses()
    with TestClient(_llm_app(settings, fake_embedder, fr)) as c:
        job = wait(c, c.post("/api/jobs", json={"strategy": "auto"}).json()["id"])
    assert job["status"] == "done" and len(fr.calls) == 1
    call = fr.calls[0]
    assert call["model"] == "gpt-5.6-luna" and call["reasoning"] == {"effort": "low"}
    assert all(x.get("detail") == "low" for x in call["input"][0]["content"] if x["type"] == "input_image")
    assert any(c["name"].startswith("Group Name") for c in job["categories"])
    assert job["usage"]["calls"] == 1


def test_llm_failure_falls_back_with_warning(settings, fake_embedder):
    build_library(settings.library_root)
    with TestClient(_llm_app(settings, fake_embedder, _FakeResponses(fail=True))) as c:
        job = wait(c, c.post("/api/jobs", json={"strategy": "auto"}).json()["id"])
    assert job["status"] == "done" and job["warnings"]


def test_ai_assist_rescues_unsure(settings, fake_embedder):
    from PIL import Image

    Image.new("RGB", (64, 64), (128, 128, 128)).save(settings.library_root / "gray.jpg")  # equally far from all
    fr = _FakeResponses()
    with TestClient(_llm_app(settings, fake_embedder, fr)) as c:
        sid = c.post("/api/category-sets", json=RED_GREEN).json()["id"]
        body = {"strategy": "custom", "set_id": sid, "options": {"ai_assist": True, "min_confidence": 0.95}}
        job = wait(c, c.post("/api/jobs", json=body).json()["id"])
    p = job["plan"][0]
    assert p["category"] == "Red things" and p["source"] == "ai"


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")
def test_video_pipeline(client, settings):
    make_video(settings.library_root / "clip.mp4", "red")
    job = wait(client, client.post("/api/jobs", json={"strategy": "preset", "set_id": "lifestyle"}).json()["id"])
    assert job["status"] == "done" and job["plan"][0]["kind"] == "video"
    assert job["plan"][0]["destination"].startswith("Organized/Videos/")
    assert client.get(job["plan"][0]["thumb"]).status_code == 200


def test_output_directly_in_folder_and_non_recursive(client, settings):
    lib = settings.library_root
    make_image(lib / "trip" / "r.jpg", COLORS["red"], fmt="JPEG", noise_seed=1)
    make_image(lib / "trip" / "nested" / "g.jpg", COLORS["green"], fmt="JPEG", noise_seed=2)
    set_id = client.post("/api/category-sets", json=RED_GREEN).json()["id"]
    body = {"source": "trip", "strategy": "custom", "set_id": set_id,
            "options": {"output_dir": "", "recursive": False}}
    job = wait(client, client.post("/api/jobs", json=body).json()["id"])
    assert [p["rel_path"] for p in job["plan"]] == ["trip/r.jpg"]
    assert job["plan"][0]["destination"] == "trip/Photos/Red things"
    assert client.post("/api/jobs", json={**body, "options": {"output_dir": ".."}}).status_code == 422
    assert client.post("/api/jobs", json={**body, "options": {"output_dir": "a/b"}}).status_code == 422


def test_preview_endpoint(client, settings):
    make_image(settings.library_root / "a" / "big.jpg", COLORS["red"], size=(3000, 2000), fmt="JPEG")
    r = client.get("/api/preview", params={"path": "a/big.jpg"})
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
    from io import BytesIO
    from PIL import Image
    assert max(Image.open(BytesIO(r.content)).size) == 1600
    assert client.get("/api/preview", params={"path": "../../etc/passwd"}).status_code == 404
