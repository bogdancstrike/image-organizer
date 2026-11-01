"""Natural-language search, find similar, places map and trip detection."""
import time

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

from app.geo import Item, detect_trips, read_geo
from app.main import create_app
from tests.conftest import COLORS, make_image
from tests.test_api import wait

BUCHAREST = (44.43, 26.10)
ROME = (41.90, 12.50)


def _dms(x):
    x = abs(x)
    d = int(x)
    m = int((x - d) * 60)
    return (float(d), float(m), round((x - d - m / 60) * 3600, 2))


def gps_jpeg(path, color, lat, lon, when: str):
    im = Image.new("RGB", (64, 64), color)
    exif = Image.Exif()
    exif.get_ifd(0x8825).update({1: "N" if lat >= 0 else "S", 2: _dms(lat), 3: "E" if lon >= 0 else "W", 4: _dms(lon)})
    exif.get_ifd(0x8769)[36867] = when
    im.save(path, "JPEG", exif=exif)


def test_read_geo_roundtrip(tmp_path):
    gps_jpeg(tmp_path / "a.jpg", (10, 20, 30), ROME[0], ROME[1], "2025:05:10 12:00:00")
    g = read_geo(tmp_path / "a.jpg")
    assert abs(g["lat"] - ROME[0]) < 1e-3 and abs(g["lon"] - ROME[1]) < 1e-3 and g["ts"]
    Image.new("RGB", (8, 8)).save(tmp_path / "b.jpg")
    assert read_geo(tmp_path / "b.jpg")["lat"] is None


def test_detect_trips_splits_on_home_and_gaps():
    day = 86400
    t0 = time.mktime((2025, 5, 1, 12, 0, 0, 0, 0, -1))
    items = [Item(f"h{i}", t0 + i * day, *BUCHAREST, {"city": "Bucharest", "country": "Romania"}) for i in range(10)]
    items += [Item(f"r{i}", t0 + 12 * day + i * 3600 * 5, *ROME, {"city": "Rome", "country": "Italy", "region": "Lazio"}) for i in range(6)]
    items += [Item("nogps", t0 + 12 * day + 3600)]  # another camera during the trip
    items += [Item("lonely", t0 + 40 * day, *ROME, {"city": "Rome"})]  # too few photos for a trip
    trips, home = detect_trips(items, min_photos=5)
    assert abs(home[0] - BUCHAREST[0]) < 0.1
    assert len(trips) == 1 and trips[0].name() == "Rome · May 2025" and "nogps" in trips[0].ids


def test_library_endpoints(settings, fake_embedder):
    lib = settings.library_root
    (lib / "pics").mkdir()
    for i in range(8):
        gps_jpeg(lib / "pics" / f"home{i}.jpg", (20, 200 - i, 20), *BUCHAREST, f"2025:04:{i + 1:02d} 10:00:00")
    for i in range(6):
        gps_jpeg(lib / "pics" / f"rome{i}.jpg", (200 - i, 20, 20), *ROME, f"2025:05:20 {10 + i:02d}:00:00")
    with TestClient(create_app(settings, embedder_factory=lambda: fake_embedder, llm_factory=lambda: None)) as c:
        assert c.get("/api/library/status", params={"folder": "pics"}).json()["indexed"] == 0
        wait(c, c.post("/api/jobs", json={"source": "pics", "strategy": "date"}).json()["id"])
        assert c.get("/api/library/status", params={"folder": "pics"}).json()["indexed"] == 14

        res = c.get("/api/library/search", params={"q": "red", "folder": "pics"}).json()["results"]
        assert res and res[0]["path"].startswith("pics/rome")
        sim = c.get("/api/library/similar", params={"path": "pics/rome0.jpg", "folder": "pics"}).json()["results"]
        assert sim and all(r["path"].startswith("pics/rome") for r in sim) and "pics/rome0.jpg" not in [r["path"] for r in sim]
        assert c.get("/api/library/search", params={"q": "x", "folder": "../.."}).status_code == 400

        places = c.get("/api/library/places", params={"folder": "pics"}).json()
        assert places["located"] == 14 and {x["name"] for x in places["countries"]} == {"Romania", "Italy"}
        trips = c.get("/api/library/trips", params={"folder": "pics"}).json()
        assert [t["name"] for t in trips["trips"]] == ["Rome · May 2025"] and trips["home"]["country"] == "Romania"

        job = wait(c, c.post("/api/jobs", json={"source": "pics", "strategy": "trips", "options": {"near_duplicates": False}}).json()["id"])
        assert {x["name"] for x in job["categories"]} == {"Rome · May 2025", "Everyday"}
        job = wait(c, c.post("/api/jobs", json={"source": "pics", "strategy": "places", "options": {"place_granularity": "city", "near_duplicates": False}}).json()["id"])
        assert any(x["name"].startswith("Rome") for x in job["categories"])


def test_suggest_reports_gps_share(settings, fake_embedder):
    lib = settings.library_root
    (lib / "g").mkdir()
    for i in range(4):
        gps_jpeg(lib / "g" / f"a{i}.jpg", (200 - i * 10, 30, 30), *ROME, f"2025:05:20 1{i}:00:00")
    for i in range(4):
        make_image(lib / "g" / f"b{i}.jpg", COLORS["green"], fmt="JPEG", noise_seed=90 + i)
    with TestClient(create_app(settings, embedder_factory=lambda: fake_embedder, llm_factory=lambda: None)) as c:
        s = c.get("/api/suggest", params={"path": "g"}).json()
        assert s["gps_share"] == 0.5
