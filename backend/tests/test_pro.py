"""Pro features: quality verdicts, culling strategy, rejects overlay, RAW/JPEG + sidecar pairing."""
import numpy as np
from fastapi.testclient import TestClient
from PIL import Image, ImageFilter

from app.organizer import apply_plan, undo_run
from app.quality import Face, Quality, QualityRules, analyze_image, verdict
from app.scanner import scan
from tests.conftest import make_image
from tests.test_api import wait


def _q(sharp=0.8, bright=0.5, faces=()):
    return Quality(sharp, bright, 0.0, 0.0, list(faces), True)


def test_verdicts():
    r = QualityRules()
    assert verdict(_q(sharp=0.3), r)[0] == "blurry"
    assert verdict(_q(faces=[Face(0.8, 0.1, 0.05, (0, 0, 1, 1))]), r)[0] == "eyes-closed"
    assert verdict(_q(faces=[Face(0.1, 0.8, 0.05, (0, 0, 1, 1))]), r) == (None, [], True)
    dark = Quality(0.8, 0.05, 0.6, 0.0, [], True)
    assert verdict(dark, r)[0] == "too-dark"
    assert verdict(_q(sharp=0.3), QualityRules(blur=False))[0] is None


def test_sharpness_detects_blur():
    rng = np.random.default_rng(0)
    sharp = Image.fromarray(rng.integers(0, 255, (600, 800, 3), dtype=np.uint8))
    blurry = sharp.filter(ImageFilter.GaussianBlur(6))
    assert analyze_image(sharp, None).sharpness > 0.7 > analyze_image(blurry, None).sharpness


def test_raw_jpeg_and_xmp_pairing_and_apply(tmp_path):
    lib = tmp_path / "lib"
    make_image(lib / "DSC1.jpg", (200, 10, 10), fmt="JPEG")
    (lib / "DSC1.ARW").write_bytes(b"raw")
    (lib / "DSC1.ARW.xmp").write_text("<x/>")
    (lib / "DSC2.ARW").write_bytes(b"raw-only")  # lone RAW stays a file of its own
    files = scan(lib, lib)
    by = {f.name: f for f in files}
    assert set(by) == {"DSC1.jpg", "DSC2.ARW"}
    assert set(by["DSC1.jpg"].sidecars) == {"DSC1.ARW", "DSC1.ARW.xmp"}
    # destination already has a DSC1.jpg -> the whole group gets the same new stem
    make_image(lib / "out" / "DSC1.jpg", (1, 1, 1), fmt="JPEG")
    j = apply_plan(lib, [{"rel_path": "DSC1.jpg", "destination": "out", "sidecars": list(by["DSC1.jpg"].sidecars)}],
                   "move", tmp_path / "j", "job", "")
    assert sorted(o["dst"] for o in j["ops"]) == ["out/DSC1 (1).ARW", "out/DSC1 (1).ARW.xmp", "out/DSC1 (1).jpg"]
    undo_run(lib, tmp_path / "j", j["run_id"])
    assert (lib / "DSC1.ARW").exists() and (lib / "DSC1.ARW.xmp").exists() and (lib / "DSC1.jpg").exists()


def _noise(path, seed):
    rng = np.random.default_rng(seed)
    Image.fromarray(rng.integers(40, 220, (300, 400, 3), dtype=np.uint8)).save(path, "JPEG", quality=95)


def test_cull_strategy_and_reject_overlay(settings, fake_embedder):
    from app.main import create_app

    lib = settings.library_root
    _noise(lib / "sharp.jpg", 1)
    Image.open(lib / "sharp.jpg").filter(ImageFilter.GaussianBlur(8)).save(lib / "soft.jpg")
    Image.new("RGB", (400, 300), (3, 3, 3)).save(lib / "black.jpg")
    with TestClient(create_app(settings, embedder_factory=lambda: fake_embedder, llm_factory=lambda: None)) as c:
        job = wait(c, c.post("/api/jobs", json={"strategy": "cull", "options": {"near_duplicates": False, "quality": {"blur": True, "exposure": True}}}).json()["id"])
        cat = {p["name"]: p["category"] for p in job["plan"]}
        assert cat["sharp.jpg"] == "Keepers" and cat["soft.jpg"] == "Blurry"
        assert cat["black.jpg"] in ("Too dark", "Blurry")
        assert job["plan"][0]["quality"]["sharpness"] is not None

        body = {"strategy": "preset", "set_id": "lifestyle",
                "options": {"near_duplicates": False, "quality": {"enabled": True, "action": "reject", "blur": True, "exposure": True}}}
        job = wait(c, c.post("/api/jobs", json=body).json()["id"])
        dest = {p["name"]: p["destination"] for p in job["plan"]}
        assert dest["soft.jpg"] == "Organized/_Rejects/Blurry"
        assert not dest["sharp.jpg"].startswith("Organized/_Rejects")


# ---------------------------------------------------------------- pro culling
from app.quality import find_bursts, score, stars  # noqa: E402


def test_score_and_stars_rank_shots():
    r = QualityRules()
    great = _q(sharp=0.85, faces=[Face(0.05, 0.9, 0.05, (0, 0, 1, 1))])
    blinked = _q(sharp=0.85, faces=[Face(0.9, 0.9, 0.05, (0, 0, 1, 1))])
    soft = _q(sharp=0.35)
    assert score(great, r) > score(blinked, r) > 0 and score(great, r) > score(soft, r)
    assert stars(score(great, r)) >= 4 and 1 <= stars(score(soft, r)) <= 2


def test_main_face_rule_ignores_background_blinks():
    main = Face(0.05, 0.8, 0.10, (0.3, 0.2, 0.6, 0.6))
    bystander = Face(0.95, 0.0, 0.002, (0.9, 0.1, 0.95, 0.15))
    q = _q(faces=[main, bystander])
    assert verdict(q, QualityRules(faces_rule="any"))[0] == "eyes-closed"
    assert verdict(q, QualityRules(faces_rule="main")) == (None, [], True)


def test_find_bursts():
    e = np.array([1.0, 0.0])
    other = np.array([0.0, 1.0])
    items = [
        ("a", "shoot", 10.0, e), ("b", "shoot", 10.5, e), ("c", "shoot", 11.4, e),  # one burst
        ("d", "shoot", 30.0, e),                                                   # too late
        ("e", "other", 10.2, e),                                                   # other folder
        ("f", "shoot", 30.5, other),                                               # different content
    ]
    g = find_bursts(items, seconds=2, similarity=0.9)
    assert g["a"] == g["b"] == g["c"] and len(g) == 3


def test_cull_best_of_burst_and_maybe(settings, fake_embedder):
    import os

    from app.main import create_app

    lib = settings.library_root
    for i in range(3):  # three sharp frames of a burst, 0.5 s apart
        _noise(lib / f"burst_{i}.jpg", 10 + i)
        os.utime(lib / f"burst_{i}.jpg", (1000 + i * 0.5, 1000 + i * 0.5))
    _noise(lib / "solo.jpg", 99)
    os.utime(lib / "solo.jpg", (5000, 5000))
    opts = {"near_duplicates": False, "quality": {"bursts": True, "burst_seconds": 2}}
    with TestClient(create_app(settings, embedder_factory=lambda: fake_embedder, llm_factory=lambda: None)) as c:
        job = wait(c, c.post("/api/jobs", json={"strategy": "cull", "options": opts}).json()["id"])
        cat = {p["name"]: p["category"] for p in job["plan"]}
        burst = [cat[f"burst_{i}.jpg"] for i in range(3)]
        assert sorted(burst) == ["Burst extras", "Burst extras", "Keepers"], burst
        assert job["stats"]["bursts"] == 1
        best = next(p for p in job["plan"] if p["burst"] and p["burst"]["best"])
        assert best["quality"]["stars"] >= 1 and 0 <= best["quality"]["score"] <= 1

        # a soft (but not rejected) frame scores below 5 stars -> "Maybe" when keepers need 5 stars
        Image.open(lib / "solo.jpg").filter(ImageFilter.GaussianBlur(3)).save(lib / "soft.jpg")
        opts = {"near_duplicates": False, "quality": {"bursts": False, "blur": False, "keeper_min_stars": 4}}
        job = wait(c, c.post("/api/jobs", json={"strategy": "cull", "options": opts}).json()["id"])
        cat = {p["name"]: p["category"] for p in job["plan"]}
        assert cat["soft.jpg"] == "Maybe" and cat["solo.jpg"] == "Keepers"


# ---------------------------------------------------------------- more pro checks
from app.quality import horizon_tilt, noise_sigma  # noqa: E402


def test_noise_estimate_separates_grainy_from_clean():
    rng = np.random.default_rng(1)
    clean = np.tile(np.linspace(40, 200, 400, dtype=np.float32), (300, 1))
    noisy = np.clip(clean + rng.normal(0, 18, clean.shape), 0, 255)
    assert noise_sigma(clean.astype(np.uint8)) < 0.02 < 0.045 < noise_sigma(noisy.astype(np.uint8))


def test_horizon_tilt_needs_consistent_lines():
    import cv2
    img = np.full((300, 400), 30, np.uint8)
    for y in (100, 150, 200):  # three parallel "horizons" leaning ~4 degrees
        cv2.line(img, (0, y), (399, y + 28), 230, 2)
    t = horizon_tilt(img)
    assert t is not None and 3 < abs(t) < 5
    assert horizon_tilt(np.full((300, 400), 30, np.uint8)) is None


def test_new_flags_and_face_crop():
    r = QualityRules(noise_check=True, tilt_check=True, face_crop=True)
    q = Quality(0.8, 0.5, 0, 0, [Face(0.1, 0.5, 0.05, (0.0, 0.3, 0.2, 0.6))], True, noise=0.08, tilt=3.0)
    _, flags, _ = verdict(q, r)
    assert {"noisy", "tilted", "cropped-face"} <= set(flags)
    assert verdict(q, QualityRules())[1] == []  # all opt-in


def test_quality_checks_are_off_by_default(settings, fake_embedder):
    from app.main import create_app

    lib = settings.library_root
    _noise(lib / "sharp.jpg", 1)
    Image.open(lib / "sharp.jpg").filter(ImageFilter.GaussianBlur(8)).save(lib / "soft.jpg")
    with TestClient(create_app(settings, embedder_factory=lambda: fake_embedder, llm_factory=lambda: None)) as c:
        job = wait(c, c.post("/api/jobs", json={"strategy": "cull", "options": {"near_duplicates": False}}).json()["id"])
        assert {p["category"] for p in job["plan"]} <= {"Picks ★", "Keepers", "Maybe", "Similar alternatives"}  # rating bands apply without technical rejects


def test_picks_and_xmp_ratings_with_undo(settings, fake_embedder):
    from app.main import create_app

    lib = settings.library_root
    for i in range(4):
        _noise(lib / f"k{i}.jpg", 50 + i)
    Image.open(lib / "k0.jpg").filter(ImageFilter.GaussianBlur(8)).save(lib / "soft.jpg")
    opts = {"near_duplicates": False, "quality": {"bursts": False, "blur": True, "pick_min_rating": 3, "keeper_min_rating": 2, "write_xmp": True}}
    with TestClient(create_app(settings, embedder_factory=lambda: fake_embedder, llm_factory=lambda: None)) as c:
        job = wait(c, c.post("/api/jobs", json={"strategy": "cull", "options": opts}).json()["id"])
        cats = [p["category"] for p in job["plan"]]
        assert cats.count("Picks ★") == 1 and "Blurry" in cats
        by = {p["name"]: p for p in job["plan"]}
        assert by["soft.jpg"]["xmp"] == {"rating": -1, "label": "Red"}
        pick = next(p for p in job["plan"] if p["category"] == "Picks ★")
        assert pick["xmp"] == {"rating": pick["quality"]["stars"], "label": "Green"}
        assert pick["quality"]["score"] == pick["pick"]["score"]
        r = c.post(f"/api/jobs/{job['id']}/apply", json={"mode": "move"}).json()
        assert r["moved"] == 5
        xmp = next(lib.rglob("soft.xmp"))
        assert 'xmp:Rating="-1"' in xmp.read_text() and 'xmp:Label="Red"' in xmp.read_text()
        c.post(f"/api/runs/{r['run_id']}/undo")
        assert not list(lib.rglob("*.xmp")) and (lib / "soft.jpg").exists()


def test_cull_recommendations_drive_keeper_thresholds_even_without_picks(settings, fake_embedder):
    from app.main import create_app
    from app.quality import stars
    lib=settings.library_root
    for i in range(4):
        _noise(lib/f'landscape{i}.jpg',50+i)
    with TestClient(create_app(settings,embedder_factory=lambda:fake_embedder,llm_factory=lambda:None)) as c:
        options={'near_duplicates':False,'quality':{'pick_profile':'landscape','keeper_min_stars':4,'write_xmp':True}}
        job=wait(c,c.post('/api/jobs',json={'strategy':'cull','options':options}).json()['id'])
        assert job['status']=='done',job
        for p in job['plan']:
            assert p['pick']['profile']=='landscape' and not p['pick']['picked']
            assert p['quality']['stars']==stars(p['pick']['score'])==p['xmp']['rating']
            assert (p['category']=='Maybe')==(p['quality']['rating']<4)


def test_manual_pick_changes_update_the_recommendation_marker_and_xmp_label(settings,fake_embedder):
    from app.main import create_app
    for i in range(4):_noise(settings.library_root/f'keep{i}.jpg',22+i)
    with TestClient(create_app(settings,embedder_factory=lambda:fake_embedder,llm_factory=lambda:None)) as c:
        j=wait(c,c.post('/api/jobs',json={'strategy':'cull','options':{'near_duplicates':False,'quality':{'pick_min_rating':3,'keeper_min_rating':2,'write_xmp':True}}}).json()['id'])
        picked=next(p for p in j['plan'] if p['category_id']=='picks')
        r=c.patch(f"/api/jobs/{j['id']}/plan",json={'file_ids':[picked['file_id']],'category_id':'alternates'})
        assert r.status_code==200,r.text
        item=r.json()['changed'][0]
        assert not item['pick']['picked'] and item['xmp']['label'] is None
        assert item['xmp']['rating']==item['quality']['stars']


def test_xmp_ratings_work_with_a_preset_without_enabling_reject_checks(settings,fake_embedder):
    from app.main import create_app
    _noise(settings.library_root/'photo.jpg',99)
    with TestClient(create_app(settings,embedder_factory=lambda:fake_embedder,llm_factory=lambda:None)) as c:
        j=wait(c,c.post('/api/jobs',json={'strategy':'preset','set_id':'lifestyle','options':{'quality':{'write_xmp':True}}}).json()['id'])
        item=j['plan'][0]
        assert item['quality'] is not None
        assert item['xmp']=={'rating':item['quality']['stars'],'label':None}
        assert not item['quality']['flags']


def test_rating_bands_use_decimal_scores_and_custom_thresholds(settings,fake_embedder,monkeypatch):
    from app.main import create_app
    import app.picks as picks
    for i in range(6):_noise(settings.library_root/f'{i}.jpg',i+80)
    scores=[.90,.875,.80,.75,.749,.74]  # 4.6, 4.5, 4.2, 4.0, 4.0 rounded
    def rank(ids,*args,**kwargs):
        return picks.Ranking({fid:picks.PickInfo(scores[i])for i,fid in enumerate(ids)},np.arange(len(ids)))
    monkeypatch.setattr(picks,'rank',rank)
    monkeypatch.setattr(picks,'select',lambda ids,*args,**kwargs:list(ids))
    with TestClient(create_app(settings,embedder_factory=lambda:fake_embedder,llm_factory=lambda:None))as c:
        for options in ({},{'pick_min_rating':4.2,'keeper_min_rating':3.8}):
            j=wait(c,c.post('/api/jobs',json={'strategy':'cull','options':{'near_duplicates':False,'quality':options}}).json()['id'])
            assert j['status']=='done',j
            for p in j['plan']:
                rating=p['quality']['rating'];assert rating==p['pick']['rating']
                expected='picks' if rating>=options.get('pick_min_rating',4.5)else 'keepers' if rating>=options.get('keeper_min_rating',4)else 'maybe'
                assert p['category_id']==expected
        for options in ({'keeper_min_rating':4.8,'pick_min_rating':4.5},{'pick_min_rating':5.1},{'keeper_min_rating':0}):
            assert c.post('/api/jobs',json={'strategy':'cull','options':{'quality':options}}).status_code==422
