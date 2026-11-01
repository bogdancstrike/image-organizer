"""OpenAI Luna client: cluster naming and assist for uncertain files (REQ-CAT-5, 7, 9).

Token efficiency:
- Images are small JPEGs sent with `detail: "low"`.
- Cluster naming sends one 3x2 contact sheet per cluster, all clusters in ONE request.
- Assist batches up to 12 thumbnails per request.
- `reasoning.effort` defaults to "low"; output is constrained to compact JSON.
"""
from __future__ import annotations

import base64
import io
import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

log = logging.getLogger(__name__)

ASSIST_BATCH = 12


def _data_url(img: Image.Image, quality: int = 70) -> str:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "JPEG", quality=quality)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def contact_sheet(thumb_paths: list[Path], cols: int = 3, rows: int = 2, cell: int = 128) -> Image.Image:
    sheet = Image.new("RGB", (cols * cell, rows * cell), (255, 255, 255))
    for i, p in enumerate(thumb_paths[: cols * rows]):
        try:
            with Image.open(p) as t:
                t = t.convert("RGB")
                t.thumbnail((cell, cell))
                x = (i % cols) * cell + (cell - t.width) // 2
                y = (i // cols) * cell + (cell - t.height) // 2
                sheet.paste(t, (x, y))
        except OSError:
            continue
    return sheet


def load_thumb(p: Path) -> Image.Image | None:
    try:
        with Image.open(p) as t:
            return t.convert("RGB")
    except OSError:
        return None


class LLMClient:
    def __init__(self, api_key: str, model: str, effort: str = "low", timeout: float = 60.0, client=None):
        if client is None:
            from openai import OpenAI

            client = OpenAI(api_key=api_key, timeout=timeout, max_retries=1)
        self.client = client
        self.model = model
        self.effort = effort
        self.usage = {"calls": 0, "input_tokens": 0, "output_tokens": 0}
        self._lock = threading.Lock()

    def _call(self, content: list[dict], max_output_tokens: int) -> dict:
        resp = self.client.responses.create(
            model=self.model,
            reasoning={"effort": self.effort},
            input=[{"role": "user", "content": content}],
            text={"format": {"type": "json_object"}},
            max_output_tokens=max_output_tokens,
        )
        u = getattr(resp, "usage", None)
        with self._lock:
            self.usage["calls"] += 1
            if u is not None:
                self.usage["input_tokens"] += int(getattr(u, "input_tokens", 0) or 0)
                self.usage["output_tokens"] += int(getattr(u, "output_tokens", 0) or 0)
        return json.loads(resp.output_text or "{}")

    # --- cluster naming -------------------------------------------------
    def name_clusters(self, sheets: list[Image.Image]) -> list[tuple[str, str]]:
        content: list[dict] = [{
            "type": "input_text",
            "text": (
                f"You name photo folders. Below are {len(sheets)} contact sheets; each shows sample photos from ONE "
                "group of a person's photos/videos. Give each group a short, specific, human folder name "
                "(1-3 words, Title Case, e.g. 'Beach Days', 'Outfits', 'Food & Cafés', 'Screenshots', 'Gym') and one emoji. "
                "Names must be distinct. Reply JSON: {\"groups\":[{\"i\":1,\"name\":\"...\",\"emoji\":\"...\"}]}"
            ),
        }]
        for i, s in enumerate(sheets, 1):
            content.append({"type": "input_text", "text": f"Group {i}:"})
            content.append({"type": "input_image", "image_url": _data_url(s), "detail": "low"})
        data = self._call(content, max_output_tokens=1500)
        out: list[tuple[str, str]] = [("", "") for _ in sheets]
        for g in data.get("groups", []):
            try:
                i = int(g.get("i")) - 1
            except (TypeError, ValueError):
                continue
            if 0 <= i < len(sheets):
                name = str(g.get("name", "")).strip()[:40]
                out[i] = (name, str(g.get("emoji", "📁"))[:4] or "📁")
        return out

    # --- assist ---------------------------------------------------------
    def _assist_batch(self, thumbs: list[Image.Image], names: list[str]) -> list[str]:
        folder_list = "; ".join(names)
        content: list[dict] = [{
            "type": "input_text",
            "text": (
                f"Put each of the {len(thumbs)} images into exactly one folder from this list: {folder_list}. "
                "If none fits, use \"Unsorted\". Reply JSON: {\"labels\":[\"<folder>\", ...]} with one label per image, in order."
            ),
        }]
        for t in thumbs:
            content.append({"type": "input_image", "image_url": _data_url(t, 65), "detail": "low"})
        data = self._call(content, max_output_tokens=600)
        labels = [str(x) for x in data.get("labels", [])]
        valid = {n.lower(): n for n in names}
        return [valid.get(labels[i].strip().lower(), "Unsorted") if i < len(labels) else "Unsorted" for i in range(len(thumbs))]

    def assist(self, thumbs: list[Image.Image], names: list[str], parallel: int = 4) -> list[str]:
        batches = [thumbs[i : i + ASSIST_BATCH] for i in range(0, len(thumbs), ASSIST_BATCH)]
        with ThreadPoolExecutor(max_workers=parallel) as ex:
            results = list(ex.map(lambda b: self._assist_batch(b, names), batches))
        return [x for r in results for x in r]
