"""By person, OCR override, recipes/suggest, folder rename (fake face & OCR engines)."""
import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

import app.jobs as jobs_mod
from app.main import create_app
from app.people import FaceID, cluster_people
from tests.conftest import COLORS, make_image
from tests.test_api import RED_GREEN, client, wait  # noqa: F401  (fixture)


def _vec(seed):
    v = np.random.default_rng(seed).normal(size=128).astype(np.float32)
    return v / np.linalg.norm(v)


class FakeIdentifier:
    """Identity from the dominant colour: red photos = person A, green = person B, blue = nobody, white = group."""
    available = True

    def identify(self, img):
        r, g, b = np.asarray(img.convert("RGB").resize((4, 4))).reshape(-1, 3).mean(axis=0)
        if r > 200 and g > 200 and b > 200:
            return [FaceID(0.05, (0.1 * i, 0.2, 0.1 * i + 0.1, 0.4), _vec(10 + i)) for i in range(3)]
        if r > g and r > b:
            return [FaceID(0.05, (0.3, 0.2, 0.5, 0.5), _vec(1) + np.float32(0.01) * _vec(9))]
        if g > r and g > b:
            return [FaceID(0.05, (0.3, 0.2, 0.5, 0.5), _vec(2))]
        return []


def test_cluster_people_threshold():
    a, b = _vec(1), _vec(2)
    labels = cluster_people(np.vstack([a, a, b, b, a]))
    assert labels[0] == labels[1] == labels[4] != labels[2] == labels[3]


def test_by_person_strategy_and_rename(settings, fake_embedder, monkeypatch):
    monkeypatch.setattr(jobs_mod, "get_face_identifier", lambda: FakeIdentifier())
    lib = settings.library_root
    for i in range(3):
        Image.new("RGB", (200, 200), (220, 20, 20)).save(lib / f"anna{i}.jpg", quality=90 - i)
        Image.new("RGB", (200, 200), (20, 220, 20)).save(lib / f"bob{i}.jpg", quality=90 - i)
    Image.new("RGB", (200, 200), (20, 20, 220)).save(lib / "landscape.jpg")
    Image.new("RGB", (200, 200), (250, 250, 250)).save(lib / "party.jpg")
    with TestClient(create_app(settings, embedder_factory=lambda: fake_embedder, llm_factory=lambda: None)) as c:
        body = {"strategy": "people", "options": {"near_duplicates": False, "people_min_photos": 2}}
        job = wait(c, c.post("/api/jobs", json=body).json()["id"])
        cat = {p["name"]: p["category"] for p in job["plan"]}
        assert {cat[f"anna{i}.jpg"] for i in range(3)} == {"Person 1"} or {cat[f"anna{i}.jpg"] for i in range(3)} == {"Person 2"}
        assert len({cat[f"bob{i}.jpg"] for i in range(3)}) == 1 and cat["bob0.jpg"] != cat["anna0.jpg"]
        assert cat["landscape.jpg"] == "No people" and cat["party.jpg"] == "Groups"
        person = next(x for x in job["categories"] if x["id"] == "person-1")
        assert person["cover"].startswith("/api/thumbs/")
        r = c.patch(f"/api/jobs/{job['id']}/categories/person-1", json={"name": "Laura"})
        assert r.status_code == 200 and all(p["destination"].endswith("/Laura") for p in r.json()["plan"])
        assert c.patch(f"/api/jobs/{job['id']}/categories/person-1", json={"name": "a/b"}).status_code == 400


class FakeReader:
    available = True

    def read(self, img):
        bright = np.asarray(img.convert("L")).mean() > 200
        return {"chars": 120, "coverage": 0.3, "text": "INVOICE total 42 EUR"} if bright else {"chars": 0, "coverage": 0.0, "text": ""}


def test_ocr_moves_text_heavy_photos(settings, fake_embedder, monkeypatch):
    monkeypatch.setattr(jobs_mod, "get_text_reader", lambda: FakeReader())
    lib = settings.library_root
    make_image(lib / "red.jpg", COLORS["red"], fmt="JPEG", noise_seed=1)
    Image.new("RGB", (300, 200), (255, 215, 215)).save(lib / "scan.jpg")  # pinkish paper: CLIP says "red"
    sets = {"name": "Mix", "categories": [{"name": "Red things", "prompts": ["red"]}, {"name": "Documents", "prompts": ["blue"]}]}
    with TestClient(create_app(settings, embedder_factory=lambda: fake_embedder, llm_factory=lambda: None)) as c:
        sid = c.post("/api/category-sets", json=sets).json()["id"]
        job = wait(c, c.post("/api/jobs", json={"strategy": "custom", "set_id": sid, "options": {"ocr": True}}).json()["id"])
    by = {p["name"]: p for p in job["plan"]}
    assert by["scan.jpg"]["category"] == "Documents" and by["scan.jpg"]["source"] == "ocr"
    assert "INVOICE" in by["scan.jpg"]["text"] and by["red.jpg"]["category"] == "Red things"


def test_recipes_and_suggest(client, settings):
    for i in range(6):
        make_image(settings.library_root / f"p{i}.jpg", COLORS["red"], fmt="JPEG", noise_seed=i)
    rec = client.get("/api/recipes").json()
    assert {"camera-roll", "photoshoot", "people", "documents", "discover"} <= {r["id"] for r in rec}
    sug = client.get("/api/suggest", params={"path": ""}).json()
    assert sug["photos"] == 6 and 1 <= len(sug["suggestions"]) <= 3
    assert all(s["recipe"] in {r["id"] for r in rec} and "key" in s["reason"] for s in sug["suggestions"])
    assert client.get("/api/suggest", params={"path": "../.."}).status_code == 400
