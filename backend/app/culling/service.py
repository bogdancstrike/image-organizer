"""Culling decisions independent of HTTP, persistence and job lifecycle."""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from app.culling import ranking as picks_mod
from app.culling.quality import REASONS, score, verdict


@dataclass
class CullingResult:
    assignments: dict
    categories: list[dict]
    recommendations: dict


def categorize(keep, quality, rules, bursts, embedder, opts) -> CullingResult:
    assignment = {}
    embs = np.vstack([e for _, _, e in keep]) if keep else np.zeros((0, 0), np.float32)
    qopts = opts.get("quality") or {}
    smiles = qopts.get("smiles", True)
    min_stars = int(qopts.get("keeper_min_stars", 0))
    cats = [{"id": "keepers", "name": "Keepers", "emoji": "✅"}]
    if smiles:
        cats.append({"id": "smiling", "name": "Smiling", "emoji": "😄"})
    cats.append({"id": "maybe", "name": "Maybe", "emoji": "🤔"})
    for reason, (name, emoji) in REASONS.items():
        cats.append({"id": reason, "name": name, "emoji": emoji})
    cats.append({"id": "videos", "name": "Videos", "emoji": "🎬", "media": "video"})
    pick_rating = float(qopts.get("pick_min_rating", 4.5))
    keeper_rating = float(qopts.get("keeper_min_rating", 4.0))
    if min_stars:
        keeper_rating = min(pick_rating, float(min_stars))
    cats.insert(0, {"id": "picks", "name": "Picks ★", "emoji": "🏆"})
    cats.append({"id": "alternates", "name": "Similar alternatives", "emoji": "🎞️"})
    photos = [(f.id, e) for f, _, e in keep if f.kind == "image" and f.id in (quality or {})]
    ids = [fid for fid, _ in photos]
    E = np.vstack([e for _, e in photos]).astype(np.float32) if photos else np.empty((0, embs.shape[1]))
    ranking = picks_mod.rank(ids, quality or {}, E, embedder, rules, qopts.get("pick_profile", "auto"), options=qopts)
    recommendations = {fid: {"score": pi.score, "reasons": pi.reasons, "picked": False,
                           "parts": pi.parts, "profile": pi.profile, "rating": round(1 + pi.score * 4, 2)} for fid, pi in ranking.info.items()}
    # Choose the strongest expression/presentation within each burst, not merely its sharpest frame.
    for group in {b["group"] for b in (bursts or {}).values()}:
        members = [fid for fid in ids if (bursts or {}).get(fid, {}).get("group") == group]
        if members:
            best = max(members, key=lambda fid: ranking.info[fid].score)
            ranked = sorted(members, key=lambda fid: ranking.info[fid].score, reverse=True)
            margin = ranking.info[ranked[0]].score-ranking.info[ranked[1]].score if len(ranked)>1 else 1.
            for fid in members:
                bursts[fid]["best"] = fid == best
                bursts[fid]["margin"] = round(margin, 3)
                if margin < .025:
                    recommendations[fid]["reasons"].insert(0, "close burst alternatives; compare before choosing")
    used: set[str] = set()
    for f, _, _ in keep:
        if f.kind == "video":
            cid = "videos"
        else:
            q = (quality or {}).get(f.id)
            reason, _, smiling = verdict(q, rules) if q else (None, [], False)
            b = (bursts or {}).get(f.id)
            if not reason and b and not b["best"]:
                reason = "burst"
            if reason:
                cid = reason
            elif q and recommendations.get(f.id, {"rating": round(1 + score(q, rules) * 4, 2)})["rating"] < keeper_rating:
                cid = "maybe"
            else:
                cid = "smiling" if smiles and smiling else "keepers"
        assignment[f.id] = (cid, 1.0, "quality")
        used.add(cid)
    eligible = [(fid, e) for fid, e in photos if assignment[fid][0] in ("keepers", "smiling")
                and recommendations[fid]["rating"] >= pick_rating]
    if eligible:
        selected_ids = [fid for fid, _ in eligible]
        selected_E = np.vstack([e for _, e in eligible])
        positions = {fid: i for i, fid in enumerate(ranking.info)}
        subset = picks_mod.Ranking(ranking.info, np.array([ranking.labels[positions[fid]] for fid in selected_ids]))
        chosen = set(picks_mod.select(selected_ids, subset, selected_E, len(selected_ids), min_score=0.0))
        for fid in selected_ids:
            cid = "picks" if fid in chosen else "alternates"
            assignment[fid] = (cid, ranking.info[fid].score, "quality")
            recommendations[fid]["picked"] = fid in chosen
            if fid not in chosen:
                recommendations[fid]["reasons"] = ["similar to a stronger pick", *recommendations[fid]["reasons"]][:4]
            used.add(cid)
    return CullingResult(assignment, [c for c in cats if c["id"] in used], recommendations)

