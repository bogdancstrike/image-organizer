"""Picks: expression, composition, story coverage, no near-duplicates."""
import numpy as np

from app.picks import Ranking, PickInfo, composition, expression, select
from app.quality import Face, Quality


def q(faces=(), sharp=0.8, tilt=None):
    return Quality(sharp, 0.45, 0.0, 0.0, list(faces), True, 0.01, tilt, 2)


def face(blink=0.05, smile=0.3, gaze=0.05, mouth=0.05, yaw=0.05, box=(0.28, 0.2, 0.4, 0.4)):
    return Face(blink, smile, 0.03, box, {"gaze": gaze, "mouth": mouth, "frown": 0.0, "squint": 0.1, "yaw": yaw})


def test_expression_prefers_open_eyes_and_camera_gaze():
    good = expression(q([face()]))
    assert expression(q([face(blink=0.9)])) < good - 0.2
    assert expression(q([face(gaze=0.8)])) < good - 0.1
    assert expression(q([face(mouth=0.7)])) < good  # caught mid-word
    assert expression(q([face(mouth=0.7, smile=0.9)])) >= good - 0.02  # laughing is fine
    # one blink spoils a group shot
    assert expression(q([face(), face(), face(blink=0.95)])) < expression(q([face(), face(), face()])) - 0.15
    assert expression(q([])) is None


def test_composition_thirds_and_cut_faces():
    on_third = composition(q([face(box=(0.28, 0.25, 0.4, 0.42))]))
    cut = composition(q([face(box=(0.0, 0.25, 0.1, 0.42))]))
    assert on_third > cut + 0.3
    assert composition(q([], tilt=6)) < composition(q([]))


def test_select_tells_the_story_and_skips_near_duplicates():
    rng = np.random.default_rng(0)
    base = [rng.normal(size=16) for _ in range(3)]
    ids, E, labels, info = [], [], [], {}
    for scene, (b, n) in enumerate(zip(base, (12, 6, 4))):
        for k in range(n):
            fid = f"s{scene}-{k}"
            ids.append(fid)
            E.append(b + rng.normal(scale=0.05 if k < 3 else 0.6, size=16))
            labels.append(scene)
            info[fid] = PickInfo(score=(0.95 if scene == 0 else 0.7) - k * 0.01)
    E = np.vstack(E)
    picks = select(ids, Ranking(info, np.array(labels)), E, 6)
    assert len(picks) == 6
    assert {p.split("-")[0] for p in picks} == {"s0", "s1", "s2"}  # every moment is represented
    En = E / np.linalg.norm(E, axis=1, keepdims=True)
    pos = {f: i for i, f in enumerate(ids)}
    sims = [float(En[pos[a]] @ En[pos[b]]) for i, a in enumerate(picks) for b in picks[i + 1:]]
    assert max(sims) < 0.93  # no two picks are the same frame
