"""Inspectable multi-label tags from existing local embeddings; no network or image upload."""
from __future__ import annotations

import re
import unicodedata

import numpy as np

VERSION = 3
# Each group has its own reference. Multiple subjects may be present; none is required.
VOCAB = {
    "subject": ("an empty scene with no main subject", {
        "person": "a person", "couple": "a couple together", "group": "a group of people", "dog": "a dog",
        "cat": "a cat", "bird": "a bird", "horse": "a horse", "food": "food on a plate", "flowers": "flowers",
        "car": "a car", "motorcycle": "a motorcycle", "building": "a building", "document": "a printed document",
        "screen": "a computer or phone screen", "jewelry": "jewelry", "product": "a product on display", "shoes": "shoes", "bag": "a bag", "coffee": "a cup of coffee", "hands": "human hands", "table": "a table", "trees": "trees", "water": "water", "rocks": "rocks"}),
    "scene": ("an unspecified location", {
        "beach": "a beach by the sea", "mountains": "mountains", "forest": "a forest", "lake": "a lake",
        "city": "a city street", "garden": "a garden", "snow": "a snowy landscape", "studio": "a photography studio",
        "kitchen": "a kitchen", "bathroom": "a bathroom", "living room": "a living room",
        "hallway": "a hallway", "balcony": "a balcony", "bedroom": "a bedroom", "restaurant": "a restaurant", "cafe": "a cafe", "office": "an office",
        "indoors": "an indoor scene", "outdoors": "an outdoor scene", "river": "a river", "waterfall": "a waterfall"}),
    "clothing": ("a scene without visible clothing", {
        "dress": "a person wearing a dress", "suit": "a person wearing a suit", "jacket": "a person wearing a jacket",
        "swimwear": "a person wearing swimwear", "hat": "a person wearing a hat", "sportswear": "a person in sportswear"}),
    "activity": ("a still scene without an activity", {
        "wedding": "a wedding ceremony", "dancing": "people dancing", "running": "a person running",
        "hiking": "people hiking", "cycling": "a person riding a bicycle", "swimming": "a person swimming",
        "music": "a person playing music", "cooking": "a person cooking", "travel": "a travel photograph"}),
    "lighting": ("a photograph in ordinary diffuse light", {
        "sunset": "a sunset", "sunrise": "a sunrise", "night": "a night scene", "golden hour": "golden hour lighting",
        "backlit": "a backlit subject", "silhouette": "a silhouette against a bright background"}),
    "style": ("an ordinary color photograph", {
        "black and white": "a black and white photograph", "portrait": "a close-up portrait",
        "landscape": "a wide landscape photograph", "macro": "a macro close-up of a tiny subject",
        "fashion": "a fashion photograph showing an outfit", "selfie": "a selfie"}),
    "color": ("a photograph with neutral muted colors", {
        "red": "red clothing or a red object", "blue": "blue clothing or a blue object",
        "green": "green clothing or green plants", "yellow": "yellow clothing or a yellow object",
        "pink": "pink clothing or a pink object", "white": "white clothing or a white object",
        "black": "black clothing or a black object"}),
}
ALIASES = {"dogs": "dog", "puppy": "dog", "puppies": "dog", "cats": "cat", "kitten": "cat", "kittens": "cat",
           "people": "person", "portraits": "portrait", "dresses": "dress", "outfits": "fashion", "bw": "black and white",
           "mountain": "mountains", "floral": "flowers", "motorbike": "motorcycle", "seaside": "beach"}


def tokens(text: str) -> set[str]:
    text = "".join(c for c in unicodedata.normalize("NFKD", text.casefold()) if not unicodedata.combining(c))
    return {piece for word in re.findall(r"\w+", text) for piece in ALIASES.get(word, word).split()}


def predict(E: np.ndarray, embedder) -> list[list[dict]]:
    """Independent evidence against references; scores are heuristic strengths, not calibrated probabilities."""
    if not len(E):
        return []
    prompts, entries = [], []
    for group, (reference, labels) in VOCAB.items():
        for label, description in labels.items():
            entries.append((group, label))
            prompts.extend([f"a photo of {description}", f"a photo of {reference}"])
    T = np.asarray(embedder.embed_texts(prompts), dtype=np.float32)
    T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-9
    X = E / (np.linalg.norm(E, axis=1, keepdims=True) + 1e-9)
    paired = (X @ T.T).reshape(len(E), len(entries), 2)
    strengths = 1 / (1 + np.exp(-np.clip(24 * (paired[:, :, 0] - paired[:, :, 1]), -30, 30)))
    from app.recognition.scenes import room_evidence
    rooms = room_evidence(X, embedder)
    out = []
    for index, row in enumerate(strengths):
        chosen, groups = [], {}
        for i in np.argsort(-row, kind="stable"):
            group, label = entries[i]
            # Specific action/selfie claims need stronger evidence than broad scene/person labels.
            threshold = .72 if group in ("activity", "lighting") else .64 if group == "color" else .60
            if label in ("screen", "table"):
                threshold = .72
            if label == "portrait":
                threshold = .66
            if label in ("selfie", "couple", "group", "macro"):
                threshold = .78
            if row[i] < threshold or groups.get(group, 0) >= (4 if group == "scene" else 3 if group == "subject" else 2):
                continue
            indoor = {"cafe", "restaurant", "office", "bedroom", "studio"}
            if label in indoor and any(t["label"] in indoor for t in chosen):
                continue
            chosen.append({"label": label, "score": round(float(row[i]), 3), "group": group, "source": "local-ai"})
            groups[group] = groups.get(group, 0) + 1
            if len(chosen) >= 12:
                break
        supported = [(room, float(context[index])) for room, (yes, context) in rooms.items() if yes[index]]
        if supported:
            room, context = max(supported, key=lambda item: item[1])
            indoor = set(rooms)
            chosen = [tag for tag in chosen if tag["label"] not in indoor]
            chosen.append({"label": room, "score": round(float(1/(1+np.exp(-24*context))),3), "group": "scene", "source": "local-ai"})
        out.append(chosen)
    return out


def tag_images(cache, ordered, embedder) -> dict[str, list[dict]]:
    out, pending = {}, []
    for f, analysis, emb in ordered:
        hit = cache.get_json("tags", str(f.path), f.size, f.mtime)
        if hit and hit.get("v") == VERSION:
            out[f.id] = hit["tags"]
        else:
            pending.append((f, analysis, emb))
    predicted = predict(np.vstack([e for _, _, e in pending]), embedder) if pending else []
    for (f, analysis, _), tags in zip(pending, predicted):
        orientation = "square" if abs(analysis.width / max(1, analysis.height) - 1) < .05 else "vertical" if analysis.height > analysis.width else "horizontal"
        labels = [orientation, "video" if f.kind == "video" else "photo"]
        if analysis.is_screenshot:
            labels.append("screenshot")
        tags.extend({"label": label, "score": 1.0, "group": "format", "source": "metadata"} for label in labels)
        cache.put_json("tags", str(f.path), f.size, f.mtime, {"v": VERSION, "tags": tags})
        out[f.id] = tags
    return out
