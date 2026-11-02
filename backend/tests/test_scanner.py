from pathlib import Path

import pytest

from app.media.scanning import PathError, list_folders, resolve_in_library, scan
from tests.conftest import make_image


def test_scan_finds_media_and_skips_others(settings):
    lib = settings.library_root
    make_image(lib / "a.JPG", (1, 2, 3), fmt="JPEG")
    (lib / "b.mov").write_bytes(b"x")
    (lib / "notes.txt").write_text("hi")
    make_image(lib / "sub" / "c.png", (9, 9, 9))
    make_image(lib / ".hidden" / "d.png", (9, 9, 9))
    make_image(lib / "Organized" / "Photos" / "x.png", (9, 9, 9))
    files = scan(lib, lib)
    assert [(f.rel_path, f.kind) for f in files] == [("a.JPG", "image"), ("b.mov", "video"), ("sub/c.png", "image")]


def test_traversal_rejected(settings):
    with pytest.raises(PathError):
        resolve_in_library(settings.library_root, "../../etc")


def test_symlink_outside_ignored(settings, tmp_path):
    outside = make_image(tmp_path / "outside.png", (1, 1, 1))
    (settings.library_root / "link.png").symlink_to(outside)
    assert scan(settings.library_root, settings.library_root) == []


def test_list_folders(settings):
    lib = settings.library_root
    make_image(lib / "trip" / "a.png", (1, 1, 1))
    make_image(lib / "Organized" / "b.png", (1, 1, 1))
    (lib / ".git").mkdir()
    res = list_folders(lib, "")
    assert [f["name"] for f in res["folders"]] == ["trip"]
    assert res["folders"][0]["media_count"] == 1
