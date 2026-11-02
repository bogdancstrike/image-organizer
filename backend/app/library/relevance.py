"""Open-set semantic retrieval: abstain when a query has no supporting image, tag or text evidence."""
from __future__ import annotations

import re
import numpy as np

from app.recognition.tagging import VOCAB, tokens
from app.recognition.scenes import ROOMS, room_evidence

STOP = {'a','an','the','in','on','at','of','with','and','or','to','for','by','me','show','find','photo','photos','image','images'}


def concepts(clause: str) -> list[tuple[str, str, str]]:
    wanted = tokens(clause)-STOP
    matches = []
    for group, (reference, labels) in VOCAB.items():
        for label, description in labels.items():
            words = tokens(label)-STOP
            if words and words <= wanted:
                # Multi-word labels require the actual phrase, avoiding black dress + white shoes => monochrome.
                if len(words)>1 and label not in clause.casefold():
                    continue
                matches.append((label, description, reference))
    if any(label=='black and white'for label,_,_ in matches):
        matches=[entry for entry in matches if entry[0]not in {'black','white'}]
    return matches


def rank_query(E: np.ndarray, query: str, embedder, tag_lists: list[list[dict]], text: list[str], browse=False):
    """Return scores, eligibility and short evidence messages. Scores are similarities, not probabilities."""
    clauses = [c.strip() for c in re.split(r'\bor\b', query, flags=re.I) if c.strip()]
    prompts = ['a photograph']
    definitions = []
    for clause in clauses:
        full = len(prompts);prompts.append(f'a photo of {clause}')
        checks = []
        for label, description, reference in concepts(clause):
            position = len(prompts)
            prompts.extend([f'a photo of {description}', f'a photo of {reference}'])
            checks.append((label, position))
        definitions.append((clause, full, checks))
    T = np.asarray(embedder.embed_texts(prompts),np.float32)
    T /= np.linalg.norm(T,axis=1,keepdims=True)+1e-9
    X = E/(np.linalg.norm(E,axis=1,keepdims=True)+1e-9)
    similarity=X@T.T
    scores=np.full(len(X),-np.inf);eligible=np.zeros(len(X),bool);messages=['']*len(X)
    rooms = room_evidence(X, embedder) if any(label in ROOMS for _,_,checks in definitions for label,_ in checks) else {}
    vocabularies=[set().union(*(tokens(tag['label']) for tag in tags))for tags in tag_lists]
    labels=[{tag['label']for tag in tags}for tags in tag_lists]
    for clause, full, checks in definitions:
        words=tokens(clause)-STOP
        lexical=np.array([bool(words)and words<=v for v in vocabularies],bool)
        required=np.ones(len(X),bool)
        scene_support=np.zeros(len(X),bool)
        for label,position in checks:
            evidence=1/(1+np.exp(-np.clip(24*(similarity[:,position]-similarity[:,position+1]),-30,30)))
            from_tags=np.array([any(tokens(label)==tokens(value)for value in row)for row in labels],bool)
            context = rooms[label][0] if label in rooms else np.zeros(len(X),bool)
            scene_support |= context
            required &= from_tags | (evidence>=.62) | context
        text_words=[w for w in re.findall(r'\w{3,}',clause.casefold())if w not in STOP]
        ocr=np.array([bool(text_words)and all(w in value.casefold()for w in text_words)for value in text],bool)
        covered=set().union(*(tokens(label) for label,_ in checks)) if checks else set()
        # Context can recover a room hidden behind a subject, while every other requested concept remains mandatory.
        contextual = scene_support if words <= covered else np.zeros(len(X),bool)
        visual=((similarity[:,full]-similarity[:,0]>=.015)|contextual)&required
        accepted=visual|lexical|ocr
        if browse and not words:accepted[:]=True
        candidate=similarity[:,full]+.25*lexical+.17*ocr
        better=accepted & (candidate>scores)
        scores=np.where(better,candidate,scores);eligible|=accepted
        for i in np.where(better)[0]:
            messages[i]='Text in the photo matches the query (OCR).'if ocr[i]else 'Stored image tags match the query.'if lexical[i]else 'Visual evidence supports '+(', '.join(label for label,_ in checks)or 'the query')+'.'
    return scores,eligible,messages
