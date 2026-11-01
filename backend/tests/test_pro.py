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
        job = wait(c, c.post("/api/jobs", json={"strategy": "cull", "options": {"near_duplicates": False}}).json()["id"])
        cat = {p["name"]: p["category"] for p in job["plan"]}
        assert cat["sharp.jpg"] == "Keepers" and cat["soft.jpg"] == "Blurry"
        assert cat["black.jpg"] in ("Too dark", "Blurry")
        assert job["plan"][0]["quality"]["sharpness"] is not None

        body = {"strategy": "preset", "set_id": "lifestyle",
                "options": {"near_duplicates": False, "quality": {"enabled": True, "action": "reject"}}}
        job = wait(c, c.post("/api/jobs", json=body).json()["id"])
        dest = {p["name"]: p["destination"] for p in job["plan"]}
        assert dest["soft.jpg"] == "Organized/_Rejects/Blurry"
        assert not dest["sharp.jpg"].startswith("Organized/_Rejects")
