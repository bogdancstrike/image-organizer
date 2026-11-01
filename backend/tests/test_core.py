"""Unit tests: media, dedupe, classification, planner, categories."""
from datetime import datetime

import numpy as np
import pytest
from pydantic import ValidationError

from app import classify
from app.categories import CategorySetIn, CategoryStore
from app.dedupe import DupItem, find_duplicates
from app.media import MediaError, decode_image, is_screenshot_like
from app.planner import DUPLICATES, destination
from tests.conftest import FakeEmbedder, make_image


# ---- media ---------------------------------------------------------------
def test_decode_image_and_thumb(tmp_path):
    p = make_image(tmp_path / "a.jpg", (200, 10, 10), size=(800, 600), fmt="JPEG")
    d = decode_image(p, 123.0)
    assert (d.analysis.width, d.analysis.height) == (800, 600)
    assert d.analysis.captured_at == 123.0  # no EXIF -> mtime
    assert d.thumb[:4] == b"RIFF" and len(d.analysis.sha256) == 64
    assert d.frames and max(d.frames[0].size) <= 448


def test_corrupt_image(tmp_path):
    p = tmp_path / "broken.jpg"
    p.write_bytes(b"not an image at all")
    with pytest.raises(MediaError):
        decode_image(p, 0)


def test_screenshot_signal():
    assert is_screenshot_like("Screenshot_2026-05-01.png", "PNG", False, 1080, 2400)
    assert is_screenshot_like("IMG_1.png", "PNG", False, 1080, 2340)
    assert not is_screenshot_like("IMG_1.jpg", "JPEG", True, 3000, 4000)


# ---- dedupe ----------------------------------------------------------------
def _item(id, sha, phash, pixels, size=100, kind="image"):
    return DupItem(id, kind, sha, phash, pixels, size, 0.0, f"{id}.jpg")


def test_exact_and_near_duplicates_keep_largest():
    items = [
        _item("big", "s1", "ffff000000000000", 12_000_000),
        _item("small", "s2", "ffff000000000001", 2_000_000),  # near (1 bit)
        _item("copy", "s1", "ffff000000000000", 12_000_000, size=99),  # exact of big
        _item("other", "s3", "0000ffffffff0000", 12_000_000),
    ]
    m = find_duplicates(items)
    assert m == {"small": "big", "copy": "big"}


def test_near_duplicates_can_be_disabled():
    items = [_item("a", "s1", "ff00000000000000", 10), _item("b", "s2", "ff00000000000000", 5)]
    assert find_duplicates(items, near=False) == {}


def test_near_duplicate_requires_similar_embedding():
    a = _item("a", "s1", "ff00000000000000", 10)
    b = _item("b", "s2", "ff00000000000000", 5)
    a.embedding, b.embedding = np.array([1.0, 0.0]), np.array([0.0, 1.0])
    assert find_duplicates([a, b]) == {}


# ---- classification ----------------------------------------------------------
CATS = [
    {"id": "r", "name": "Red things", "prompts": ["red"]},
    {"id": "g", "name": "Green things", "prompts": ["green"]},
    {"id": "screenshots", "name": "Screenshots", "prompts": ["blue"]},
]


def _embs(colors):
    from PIL import Image

    return FakeEmbedder().embed_images([Image.new("RGB", (8, 8), c) for c in colors])


def test_zero_shot_and_screenshot_override():
    embs = _embs([(230, 10, 10), (10, 230, 10), (10, 230, 10)])
    res = classify.classify_with_set(embs, [False, False, True], CATS, FakeEmbedder(), 0.3)
    assert [r[0] for r in res] == ["r", "g", "screenshots"]
    assert res[2][2] == "rule"


def test_screenshot_needs_rule_or_high_confidence():
    # purple-ish: CLIP leans "screenshots" (~55%) but below the 0.6 floor -> runner-up "red"
    embs = _embs([(200, 80, 201)])
    probs = classify.softmax(100 * (embs @ classify.category_matrix(FakeEmbedder(), CATS).T))[0]
    assert 0.5 < probs[2] < classify.STRICT_SCREENSHOT
    res = classify.classify_with_set(embs, [False], CATS, FakeEmbedder(), 0.1)
    assert res[0][0] == "r"


def test_low_confidence_unsorted():
    embs = _embs([(120, 120, 120)])  # gray: ambiguous
    res = classify.classify_with_set(embs, [False], CATS, FakeEmbedder(), 0.9)
    assert res[0][0] is None


def test_auto_clusters_and_vocab_names():
    rng = np.random.default_rng(0)
    base = np.eye(4)[:3]
    embs = np.vstack([base[i] + rng.normal(0, 0.02, 4) for i in range(3) for _ in range(10)])
    embs /= np.linalg.norm(embs, axis=1, keepdims=True)
    labels, cents = classify.choose_k(embs, 8)
    assert len(set(labels)) == 3
    names = classify.name_by_vocabulary(cents, FakeEmbedder())
    assert len({n for n, _ in names}) == 3


def test_date_category():
    ts = datetime(2025, 7, 14, 12).timestamp()
    assert classify.date_category(ts) == "2025/07 - July"
    assert classify.date_category(ts, "year") == "2025"
    assert classify.date_category(ts, "day") == "2025/07/2025-07-14"


# ---- planner / categories ----------------------------------------------------
def test_destinations():
    cat = {"id": "food", "name": "Food & cafés"}
    assert destination("", "Organized", "image", cat, True) == "Organized/Photos/Food & cafés"
    assert destination("trip", "Organized", "video", cat, True) == "trip/Organized/Videos/Food & cafés"
    assert destination("", "Organized", "image", cat, False) == "Organized/Food & cafés"
    assert destination("", "Organized", "image", DUPLICATES, True) == "Organized/_Duplicates"
    assert destination("", "", "image", DUPLICATES, True) == "_Duplicates"
    assert destination("", "", "image", cat, False) == "Food & cafés"
    assert destination("", "Organized", "image", {"id": "x", "name": "2025/07 - July"}, True) == "Organized/Photos/2025/07 - July"
    assert destination("", "Organized", "image", {"id": "x", "name": '../../etc'}, True) == "Organized/Photos/etc"


def test_custom_set_validation_and_store(tmp_path):
    with pytest.raises(ValidationError, match="duplicate"):
        CategorySetIn(name="W", categories=[{"name": "Cake"}, {"name": "cake"}])
    with pytest.raises(ValidationError):
        CategorySetIn(name="W", categories=[])
    store = CategoryStore(tmp_path / "sets.json")
    s = store.upsert(None, CategorySetIn(name="Wedding", categories=[{"name": "Ceremony"}, {"name": "Dress", "prompts": ["a white dress"]}]))
    assert s["id"] == "custom-wedding" and [c["id"] for c in s["categories"]] == ["ceremony", "dress"]
    assert store.get("custom-wedding")["name"] == "Wedding"
    assert store.get("lifestyle")["id"] == "lifestyle"
    assert store.delete("custom-wedding") and store.get("custom-wedding") is None


def test_media_specific_folders():
    cats = [
        {"id": "r", "name": "Red things", "prompts": ["red"]},
        {"id": "vid", "name": "video red", "prompts": ["red"], "media": "video"},
        {"id": "g", "name": "Green things", "prompts": ["green"]},
    ]
    embs = _embs([(230, 10, 10), (230, 10, 10), (10, 230, 10)])
    res = classify.classify_with_set(embs, [False] * 3, cats, FakeEmbedder(), 0.3, kinds=["image", "video", "video"])
    # photos never land in the video-only folder; videos go only to video folders
    assert [r[0] for r in res[:2]] == ["r", "vid"]
    assert res[2][0] in ("vid", None)


def test_custom_set_keeps_media():
    s = CategorySetIn(name="IG", categories=[{"name": "video indoor", "media": "video"}, {"name": "selfies"}])
    from app.categories import to_set_dict
    d = to_set_dict("x", s)
    assert [c["media"] for c in d["categories"]] == ["video", "any"]


def test_more_formats_detected():
    from app.scanner import media_kind
    for n in ["a.JXL", "b.jfif", "c.psd", "d.avif", "e.DNG", "f.tga"]:
        assert media_kind(n) == "image", n
    for n in ["a.MTS", "b.m2ts", "c.wmv", "d.mpg", "e.flv", "f.ogv"]:
        assert media_kind(n) == "video", n


def test_jxl_decodes(tmp_path):
    from PIL import Image
    p = tmp_path / "x.jxl"
    Image.new("RGB", (64, 48), (10, 200, 10)).save(p, "JXL")
    assert decode_image(p, 0).analysis.width == 64


def test_sampled_hash_for_big_files(tmp_path, monkeypatch):
    import app.media as m
    monkeypatch.setattr(m, "FULL_HASH_LIMIT", 1000)
    monkeypatch.setattr(m, "SAMPLE", 100)
    a, b = tmp_path / "a.bin", tmp_path / "b.bin"
    a.write_bytes(bytes(range(256)) * 20)
    b.write_bytes(a.read_bytes())
    assert m.sha256_file(a) == m.sha256_file(b)
    b.write_bytes(a.read_bytes()[:-1] + b"\x00")  # tail differs
    assert m.sha256_file(a) != m.sha256_file(b)


def test_store_seeds_presets_with_ai_hints_and_migrates(tmp_path):
    import json as _json
    legacy = tmp_path / "category_sets.json"
    legacy.write_text(_json.dumps({"custom-x": {"id": "custom-x", "name": "X", "categories": [{"id": "a", "name": "A"}], "custom": True}}))
    store = CategoryStore(legacy)
    assert (tmp_path / "app.db").exists() and not legacy.exists()
    assert [s["id"] for s in store.list()] == ["custom-x"]
    presets = store.presets()
    assert all(c.get("ai_hint") for p in presets for c in p["categories"]) and not any(p["modified"] for p in presets)
    edited = store.upsert("lifestyle", CategorySetIn(name="Lifestyle", categories=[{"name": "Coffee", "ai_hint": "only coffee"}]))
    assert next(p for p in store.presets() if p["id"] == "lifestyle")["modified"] and edited["categories"][0]["ai_hint"] == "only coffee"
    assert store.delete("lifestyle")  # reset to the seeded default, still in the database
    life = next(p for p in store.presets() if p["id"] == "lifestyle")
    assert not life["modified"] and len(life["categories"]) == 12 and store.get("lifestyle")["seeded"]
    assert CategoryStore(legacy).seed() == 0  # second start: nothing to seed
