"""By person, OCR override, recipes/suggest, folder rename (fake face & OCR engines)."""
import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

import app.organization.jobs as jobs_mod
from app.main import create_app
from app.recognition.people import FaceID, cluster_people
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
    # Color embeddings do not model semantic presence; this test isolates face identities.
    monkeypatch.setattr(jobs_mod, "person_presence", lambda E, bank: np.zeros(len(E)))
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


def test_stats_settings_history_in_db(client, settings):
    for i in range(3):
        make_image(settings.library_root / f"s{i}.jpg", COLORS["green"], fmt="JPEG", noise_seed=40 + i)
    job = wait(client, client.post("/api/jobs", json={"strategy": "date"}).json()["id"])
    import time as _t
    for _ in range(50):
        st = client.get("/api/stats").json()
        if st["sorts"]:
            break
        _t.sleep(0.05)
    assert st["sorts"] == 1 and st["files_processed"] == 3 and "analyzing" in st["phase_seconds"]
    run = client.post(f"/api/jobs/{job['id']}/apply", json={"mode": "move"}).json()
    assert client.get("/api/runs").json()[0]["run_id"] == run["run_id"]
    client.post(f"/api/runs/{run['run_id']}/undo")
    assert client.get("/api/runs").json()[0]["status"] == "undone"
    assert client.put("/api/settings", json={"strategy": "cull"}).json()["ok"]
    assert client.get("/api/settings").json() == {"strategy": "cull"}


class TwoPeople(FakeIdentifier):
    def identify(self, img):
        r, g, b = np.asarray(img.convert("RGB").resize((4, 4))).reshape(-1, 3).mean(axis=0)
        if r > 200 and g > 200:  # yellow = person A (big) + person B (smaller)
            return [FaceID(0.06, (0.1, 0.2, 0.3, 0.5), _vec(1)), FaceID(0.04, (0.6, 0.2, 0.8, 0.5), _vec(2))]
        return super().identify(img)


def test_people_copy_into_every_person(settings, fake_embedder, monkeypatch):
    monkeypatch.setattr(jobs_mod, "get_face_identifier", lambda: TwoPeople())
    lib = settings.library_root
    for i in range(3):
        Image.new("RGB", (200, 200), (220, 20, 20)).save(lib / f"anna{i}.jpg", quality=90 - i)
        Image.new("RGB", (200, 200), (20, 220, 20)).save(lib / f"bob{i}.jpg", quality=90 - i)
    Image.new("RGB", (200, 200), (230, 230, 20)).save(lib / "both.jpg")
    with TestClient(create_app(settings, embedder_factory=lambda: fake_embedder, llm_factory=lambda: None)) as c:
        body = {"strategy": "people", "options": {"near_duplicates": False, "people_min_photos": 2, "people_multi": "copy"}}
        job = wait(c, c.post("/api/jobs", json=body).json()["id"])
        both = next(p for p in job["plan"] if p["name"] == "both.jpg")
        assert both["also"] and len(both["also"]) == 1 and both["also"][0] != both["destination"]
        run = c.post(f"/api/jobs/{job['id']}/apply", json={"mode": "move"}).json()
        assert len(list(lib.rglob("both.jpg"))) == 2
        c.post(f"/api/runs/{run['run_id']}/undo")
        assert [p.relative_to(lib).as_posix() for p in lib.rglob("both.jpg")] == ["both.jpg"]


def test_reference_face_moves_only_that_person(settings, fake_embedder, monkeypatch):
    monkeypatch.setattr(jobs_mod, "get_face_identifier", lambda: FakeIdentifier())
    lib = settings.library_root
    for i in range(3):
        Image.new("RGB", (200, 200), (220, 20, 20)).save(lib / f"anna{i}.jpg", quality=90 - i)
        Image.new("RGB", (200, 200), (20, 220, 20)).save(lib / f"bob{i}.jpg", quality=90 - i)
    Image.new("RGB", (200, 200), (128, 128, 128)).save(lib / "landscape.jpg")
    import io
    buf = io.BytesIO()
    Image.new("RGB", (200, 200), (220, 20, 20)).save(buf, "JPEG")
    with TestClient(create_app(settings, embedder_factory=lambda: fake_embedder, llm_factory=lambda: None)) as c:
        assert c.post("/api/faces", content=b"not an image").status_code == 422
        ref = c.post("/api/faces?name=Anna", content=buf.getvalue()).json()
        assert ref["name"] == "Anna" and ref["cover"].startswith("/api/thumbs/")
        assert [r["id"] for r in c.get("/api/faces").json()] == [ref["id"]]
        body = {"strategy": "people", "options": {"near_duplicates": False, "people_reference": ref["id"]}}
        job = wait(c, c.post("/api/jobs", json=body).json()["id"])
        cat = {p["name"]: p["category"] for p in job["plan"]}
        assert {cat[f"anna{i}.jpg"] for i in range(3)} == {"Anna"}
        assert cat["bob0.jpg"] == cat["landscape.jpg"] == "Everything else (left in place)"
        run = c.post(f"/api/jobs/{job['id']}/apply", json={"mode": "move"}).json()
        assert run["moved"] == 3 and (lib / "bob0.jpg").exists() and (lib / "landscape.jpg").exists()
        c.post(f"/api/runs/{run['run_id']}/undo")
        assert (lib / "anna0.jpg").exists()
        assert c.post("/api/jobs", json={**body, "options": {"people_reference": "0" * 12}}).status_code == 404
        assert c.delete(f"/api/faces/{ref['id']}").status_code == 204


def test_assign_by_appearance_gender_decides_then_outfit():
    from app.recognition.people import assign_by_appearance

    groom, bride = np.array([1.0, 0, 0]), np.array([0, 1.0, 0])
    protos = np.vstack([groom, bride])
    # boots shot looks like the bride's B&W photos (appearance) but clearly reads as a man → groom
    shots = np.vstack([[0.2, 0.8, 0.1], [0.1, 0.9, 0.0], [0.6, 0.5, 0.0], [-0.5, -0.5, 0.7]])
    shots /= np.linalg.norm(shots, axis=1, keepdims=True)
    res = assign_by_appearance(shots, protos, np.array([0.9, 0.1]), np.array([0.95, 0.1, 0.5, 0.5]))
    assert [r[0] for r in res] == [0, 1, 0, -1]


def test_finished_sort_survives_restart(settings, fake_embedder):
    for i in range(3):
        make_image(settings.library_root / f"p{i}.jpg", COLORS["green"], fmt="JPEG", noise_seed=60 + i)
    with TestClient(create_app(settings, embedder_factory=lambda: fake_embedder, llm_factory=lambda: None)) as c:
        job = wait(c, c.post("/api/jobs", json={"strategy": "date"}).json()["id"])
    with TestClient(create_app(settings, embedder_factory=lambda: fake_embedder, llm_factory=lambda: None)) as c:  # "restart"
        again = c.get(f"/api/jobs/{job['id']}").json()
        assert again["status"] == "done" and len(again["plan"]) == 3
        run = c.post(f"/api/jobs/{job['id']}/apply", json={"mode": "move"}).json()
        c.post(f"/api/runs/{run['run_id']}/undo")
    with TestClient(create_app(settings, embedder_factory=lambda: fake_embedder, llm_factory=lambda: None)) as c:
        assert c.get(f"/api/jobs/{job['id']}").json()["status"] == "done"  # undone → editable plan again


def test_history_lists_every_sort_with_outcome_and_pages(settings, fake_embedder):
    for i in range(3):
        make_image(settings.library_root / f"h{i}.jpg", COLORS["green"], fmt="JPEG", noise_seed=70 + i)
    with TestClient(create_app(settings, embedder_factory=lambda: fake_embedder, llm_factory=lambda: None)) as c:
        a = wait(c, c.post("/api/jobs", json={"strategy": "date"}).json()["id"])
        b = wait(c, c.post("/api/jobs", json={"strategy": "date"}).json()["id"])
        c.post(f"/api/jobs/{b['id']}/apply", json={"mode": "copy"})
        import time as _t
        _t.sleep(0.2)
        h = c.get("/api/history").json()
        assert h["counts"]["applied"] == 1 and h["counts"]["not_applied"] == 1 and h["total"] == 2
        assert {i["job_id"]: i["outcome"] for i in h["items"]} == {a["id"]: "not_applied", b["id"]: "applied"}
        assert next(i for i in h["items"] if i["job_id"] == a["id"])["reopen"] is True
        page = c.get("/api/history", params={"outcome": "applied", "limit": 1}).json()
        assert page["total"] == 1 and page["items"][0]["run"]["moved"] == 3
        assert c.get("/api/history", params={"outcome": "nope"}).status_code == 400


def test_partial_faces_match_known_galleries_without_creating_new_identities():
    from app.recognition.people import match_identity
    a,b=_vec(1),_vec(2)
    galleries=[np.vstack([a,a]),np.vstack([b,b])]
    assert match_identity(a,galleries)[0]==0
    assert match_identity(b,galleries)[0]==1
    assert match_identity(_vec(99),galleries)[0]==-1
    assert match_identity(a,[np.vstack([a]),np.vstack([a])])[0]==-1
    assert match_identity(a,[])[0]==-1


def test_partial_face_fragments_do_not_create_new_people(settings,fake_embedder,monkeypatch):
    class Partial(FakeIdentifier):
        def identify(self,img):
            faces=super().identify(img)
            if faces and img.width==205:faces[0].reliable=False
            return faces
    monkeypatch.setattr(jobs_mod,'get_face_identifier',lambda:Partial())
    for i in range(3):Image.new('RGB',(200+i,200),(220,20,20)).save(settings.library_root/f'clear{i}.jpg',quality=90-i)
    Image.new('RGB',(205,200),(220,20,20)).save(settings.library_root/'partial.png')
    with TestClient(create_app(settings,embedder_factory=lambda:fake_embedder,llm_factory=lambda:None))as c:
        j=wait(c,c.post('/api/jobs',json={'strategy':'people','options':{'near_duplicates':False,'people_min_photos':2}}).json()['id'])
        assert j['status']=='done',j
        assert len([cat for cat in j['categories']if cat['id'].startswith('person-')])==1
        assert next(p for p in j['plan']if p['name']=='partial.png')['category_id']=='person-1'


def test_identity_consolidation_recovers_pose_fragments_and_respects_cooccurrence():
    # Weak individual views fragment the pair-verification cut, but the three galleries remain distinct.
    from sklearn.cluster import AgglomerativeClustering
    rng=np.random.default_rng(5)
    E=np.vstack([np.eye(128)[i]+rng.normal(0,.105,(40,128))for i in range(3)])
    E/=np.linalg.norm(E,axis=1,keepdims=True)
    base=AgglomerativeClustering(n_clusters=None,metric="cosine",linkage="average",distance_threshold=.637).fit_predict(E)
    assert len(set(base))>3
    labels=cluster_people(E)
    assert len(set(labels))==3
    assert all(len(set(labels[start:start+40]))==1 for start in (0,40,80))
    pair=next((0,i)for i in range(1,40)if base[0]!=base[i])
    constrained=cluster_people(E,cannot_link=[pair])
    assert constrained[pair[0]]!=constrained[pair[1]]
    assert len(set(cluster_people(E,threshold=.6)))>3


def test_random_face_embeddings_do_not_collapse_to_an_invented_identity():
    E=np.random.default_rng(8).normal(size=(35,128)).astype(np.float32)
    assert len(set(cluster_people(E)))>20


def test_presence_and_gender_do_not_force_a_faceless_identity():
    from app.recognition.people import assign_by_appearance
    protos=np.eye(3)[:2]
    assert assign_by_appearance(np.array([[-.6,-.5,.1]]),protos,np.array([.9,.1]),np.array([.95]),present=np.array([.99]))[0][0]==-1
    assert assign_by_appearance(np.array([[.5,.5,.1]]),protos,np.array([.5,.5]),np.array([.5]),present=np.array([.99]))[0][0]==-1
