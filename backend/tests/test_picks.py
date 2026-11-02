"""Picks: expression, composition, story coverage, no near-duplicates."""
import numpy as np

from app.culling.ranking import Ranking, PickInfo, composition, expression, select
from app.culling.quality import Face, Quality


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


def test_dark_intentional_photo_is_not_punished_for_mean_brightness():
    from app.culling.ranking import technical
    lit=q([],sharp=.8);dark=q([],sharp=.8);dark.brightness=.12
    assert abs(technical(lit)-technical(dark))<.1
    blown=q([],sharp=.8);blown.bright_clip=.8
    assert technical(blown)<technical(lit)-.1


def test_main_face_preference_and_small_background_faces():
    from app.culling.quality import QualityRules
    main=face();background=face(blink=.99);background.area=.001
    mixed=q([main,background])
    assert expression(mixed,QualityRules(faces_rule='any'))==expression(q([main]),QualityRules())
    other=face(blink=.99)
    assert expression(q([main,other]),QualityRules(faces_rule='main'))>expression(q([main,other]),QualityRules(faces_rule='any'))


def test_fashion_profile_does_not_require_eye_contact_or_a_smile():
    from app.culling.ranking import face_expression
    turned=face(gaze=.9,yaw=.7,smile=0)
    assert face_expression(turned,'fashion')>face_expression(turned,'portrait')


def test_rejected_or_low_scoring_frames_never_fill_the_picks_quota():
    ids=['bad','good'];E=np.eye(2,dtype=np.float32)
    info={'bad':PickInfo(.1), 'good':PickInfo(.85)}
    chosen=select(ids,Ranking(info,np.array([0,1])),E,2)
    assert chosen==['good']


def test_rank_includes_profile_and_absolute_quality_even_for_a_single_photo(fake_embedder):
    from app.culling.ranking import rank
    from app.culling.quality import QualityRules
    poor=q([],sharp=.15)
    rules=QualityRules(blur=False,eyes_closed=False,exposure=False)
    ranking=rank(['poor'],{'poor':poor},np.array([[1,0,0,.05]],np.float32),fake_embedder,rules,profile='landscape')
    assert ranking.info['poor'].profile=='landscape'
    assert ranking.info['poor'].score<.5
    assert set(ranking.info['poor'].parts)>={'tech','comp','aes','light'}


def test_group_focus_uses_the_weakest_important_face_but_honors_main_subject():
    from app.culling.ranking import technical
    from app.culling.quality import QualityRules
    main,other=face(),face();main.sharpness=.9;other.sharpness=.2
    assert technical(q([main,other]),QualityRules(faces_rule='any')) < technical(q([main,other]),QualityRules(faces_rule='main'))-.2


def test_semantic_genre_auto_detection_and_fallbacks(fake_embedder,monkeypatch):
    import app.culling.ranking as picks
    from app.culling.quality import QualityRules
    E=np.array([[1,0,0,.05],[0,1,0,.05]],np.float32)
    monkeypatch.setattr(picks,'_semantic',lambda E,e:(np.array([[.01,.97,.01,.01],[.01,.01,.97,.01]]),np.full((2,7),.9)))
    ranked=picks.rank(['fashion','landscape'],{'fashion':q([face()]),'landscape':q()},E,fake_embedder,QualityRules())
    assert ranked.info['fashion'].profile=='fashion' and ranked.info['landscape'].profile=='landscape'
    assert ranked.info['landscape'].score>.65
    monkeypatch.setattr(picks,'_semantic',lambda *args:(_ for _ in ()).throw(RuntimeError('text tower failed')))
    fallback=picks.rank(['group'],{'group':q([face(),face()])},E[:1],fake_embedder,QualityRules())
    assert fallback.info['group'].profile=='group' and np.isfinite(fallback.info['group'].score)
    assert picks.rank([],{},np.empty((0,4)),fake_embedder,QualityRules()).info=={}
    import pytest
    with pytest.raises(ValueError):picks.rank([],{},E,fake_embedder,QualityRules(),profile='bad')


def test_scene_assignment_scales_and_keeps_a_small_shoot_together():
    from app.culling.ranking import scenes
    assert scenes(np.eye(4)).tolist()==[0,0,0,0]
    rng=np.random.default_rng(12);E=rng.normal(size=(2501,8));E/=np.linalg.norm(E,axis=1,keepdims=True)
    assert len(scenes(E))==2501


def test_auto_landscapes_keep_landscape_criteria_when_people_are_incidental(fake_embedder,monkeypatch):
    import app.culling.ranking as picks
    from app.culling.quality import QualityRules
    monkeypatch.setattr(picks,'_semantic',lambda E,e:(np.array([[.01,.01,.97,.01]]),np.full((1,7),.7)))
    a,b=face(),face();a.area=b.area=.002
    result=picks.rank(['hike'],{'hike':q([a,b])},np.array([[1,0,0,.05]],np.float32),fake_embedder,QualityRules())
    assert result.info['hike'].profile=='landscape'
    assert 'expr' not in result.info['hike'].parts


def test_multiscale_detail_distinguishes_noise_from_real_edges():
    from app.culling.quality import perceptual_signals
    rng=np.random.default_rng(7)
    noise=rng.integers(0,255,(128,128),dtype=np.uint8)
    edges=np.zeros((128,128),np.uint8);edges[32:96,32:96]=220
    a=perceptual_signals(noise,[]);b=perceptual_signals(edges,[])
    assert b['detail']>a['detail']
    assert all(0<=value<=1 for value in a.values())
