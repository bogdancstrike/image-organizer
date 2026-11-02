"""Background room evidence: compare matching person/room contexts and competing locations."""
from __future__ import annotations

import numpy as np

from app.recognition.ports import normalize

ROOMS = ('kitchen', 'bedroom', 'bathroom', 'living room', 'studio', 'office', 'restaurant', 'hallway', 'balcony', 'cafe')


def room_evidence(E: np.ndarray, embedder) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    prompts = ['a photograph of a person in a room', 'a photograph of a room']
    for room in ROOMS:
        prompts.extend([f'a photo of a {room}', f'a person photographed in a {room}',
                        f'a photograph with a {room} in the background'])
    similarity = normalize(E) @ normalize(embedder.embed_texts(prompts)).T
    values = similarity[:, 2:].reshape(len(E), len(ROOMS), 3)
    strengths = values.max(axis=2)
    out = {}
    for i, room in enumerate(ROOMS):
        context = np.maximum(values[:, i, 0] - similarity[:, 1],
                             np.maximum(values[:, i, 1], values[:, i, 2]) - similarity[:, 0])
        alternatives = np.delete(strengths, i, axis=1).max(axis=1)
        # A person in an unspecified room is not evidence of a kitchen. Both comparisons must support it.
        supported = (context >= .012) & (strengths[:, i] - alternatives >= .003)
        out[room] = (supported, context)
    return out
