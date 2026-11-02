"""Media HTTP routes."""
from __future__ import annotations

import hashlib
import re
from fastapi import HTTPException, Query
from fastapi.responses import FileResponse
from PIL import Image, ImageOps
from app.media.decoding import open_any
from app.media.scanning import PathError, list_folders, list_places, media_kind
from fastapi import APIRouter
from app.api.context import Runtime

SHA_RE = re.compile(r"^[0-9a-f]{64}$")


def create_router(ctx: Runtime) -> APIRouter:
    router = APIRouter(tags=["media"])
    s = ctx.settings
    manager = ctx.manager

    @router.get("/api/folders")
    def folders(path: str = Query("")):
        try:
            return list_folders(s.library_root, path, s.output_dir_name)
        except PathError as exc:
            raise HTTPException(400, str(exc)) from exc


    @router.get("/api/places")
    def places():
        return list_places(s.library_root)


    @router.get("/api/thumb")
    def thumb_by_path(path: str = Query(..., min_length=1)):
        """Small cached thumbnail (≤ 320 px WebP) for any photo in the library: folder previews, search results."""
        root = s.library_root
        p = (root / path.lstrip("/")).resolve()
        if root not in p.parents or not p.is_file() or media_kind(p.name) != "image":
            raise HTTPException(404, "not found")
        st = p.stat()
        key = hashlib.sha1(f"{p}|{st.st_size}|{st.st_mtime}".encode()).hexdigest()
        out = s.data_dir / "previews" / "t" / key[:2] / f"{key}.webp"
        if not out.exists():
            try:
                with open_any(p) as im:
                    if im.format == "JPEG":
                        im.draft("RGB", (640, 640))
                    im = ImageOps.exif_transpose(im).convert("RGB")
                    im.thumbnail((320, 320), Image.Resampling.LANCZOS)
                    out.parent.mkdir(parents=True, exist_ok=True)
                    tmp = out.with_suffix(".tmp")
                    im.save(tmp, "WEBP", quality=78)
                    tmp.replace(out)
            except Exception as exc:  # noqa: BLE001
                raise HTTPException(422, f"cannot render thumbnail: {exc}") from exc
        return FileResponse(out, media_type="image/webp", headers={"Cache-Control": "public, max-age=86400"})


    @router.get("/api/thumbs/{sha}")
    def thumb(sha: str):
        if not SHA_RE.match(sha):
            raise HTTPException(400, "bad id")
        p = manager.thumb_path(sha)
        if not p.exists():
            raise HTTPException(404, "no thumbnail")
        return FileResponse(p, media_type="image/webp", headers={"Cache-Control": "public, max-age=31536000, immutable"})


    @router.get("/api/preview")
    def preview(path: str = Query(..., min_length=1)):
        """Large view for the lightbox: photos as a cached 1600 px JPEG, videos streamed (range requests)."""
        root = s.library_root
        p = (root / path.lstrip("/")).resolve()
        if not (root in p.parents) or not p.is_file():
            raise HTTPException(404, "file not found (it may have been moved)")
        kind = media_kind(p.name)
        if kind == "video":
            return FileResponse(p)
        if kind != "image":
            raise HTTPException(400, "not a media file")
        st = p.stat()
        key = hashlib.sha1(f"{p}|{st.st_size}|{st.st_mtime}".encode()).hexdigest()
        out = s.data_dir / "previews" / key[:2] / f"{key}.jpg"
        if not out.exists():
            try:
                with open_any(p) as im:
                    if im.format == "JPEG":
                        im.draft("RGB", (2000, 2000))
                    im = ImageOps.exif_transpose(im).convert("RGB")
                    im.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
                    out.parent.mkdir(parents=True, exist_ok=True)
                    im.save(out, "JPEG", quality=85)
            except Exception as exc:  # noqa: BLE001
                raise HTTPException(422, f"cannot render preview: {exc}") from exc
        return FileResponse(out, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})


    return router
