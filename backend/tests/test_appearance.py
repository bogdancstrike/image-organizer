"""Appearance recovery must generalize to held-out views without forcing strangers into a person."""
import numpy as np

from app.recognition.appearance import match_appearances, sequence_hints
from app.recognition.ports import normalize


def gallery():
    rng = np.random.default_rng(41)
    centers = normalize(rng.normal(size=(4, 64)))
    E = normalize(np.vstack([center + rng.normal(0, .025, (8, 64)) for center in centers]))
    return rng, centers, E, np.repeat(np.arange(4), 8)


def test_recovers_held_out_body_appearance_views_and_abstains_on_strangers():
    rng, centers, E, labels = gallery()
    held_out = normalize(centers + rng.normal(0, .035, centers.shape))
    stranger = normalize(rng.normal(size=(2, 64)))
    all_E = np.vstack([E, held_out, stranger])
    labels = np.r_[labels, [-1] * 6]
    result = match_appearances(all_E, labels, [f'frame-{i}.jpg' for i in range(38)], list(range(32, 38)))
    assert [m.person for m in result[:4]] == [0, 1, 2, 3]
    assert [m.person for m in result[4:]] == [-1, -1]
    assert all('face-confirmed' in m.evidence[0] for m in result[:4])


def test_ambiguous_appearance_is_left_for_review():
    _, centers, E, labels = gallery()
    mixture = normalize(centers[0] + centers[1])
    result = match_appearances(np.vstack([E, mixture]), np.r_[labels, -1], ['photo.jpg'] * 33, [32])
    assert result[0].person == -1


def test_sequence_support_requires_two_agreeing_anchors_and_same_camera_folder():
    paths = ['set/DSC0100.jpg', 'set/DSC0105.jpg', 'set/DSC0110.jpg', 'set/DSC0115.jpg',
             'set/DSC0120.jpg', 'other/DSC0105.jpg', 'set/IMG0105.jpg', 'set/DSC0200.jpg', 'plain.jpg']
    labels = np.array([0, -1, 0, -1, 1, -1, -1, -1, -1])
    assert sequence_hints(paths, labels) == [-1, 0, -1, -1, -1, -1, -1, -1, -1]
    # Two different people with the same counter do not provide a valid bracket.
    assert sequence_hints(paths + ['set/DSC0110-2.jpg'], np.r_[labels, 1])[1] == -1


def test_small_galleries_do_not_train_an_unjustified_classifier():
    E = np.array([[1., 0., 0.], [1., .01, 0.], [1., .02, 0.], [0., 0., 1.]])
    assert match_appearances(E, np.array([-1] * 4), ['x'] * 4, [3])[0].person == -1
    result = match_appearances(E, np.array([0, 0, -1, -1]), ['x'] * 4, [2, 3])
    assert result[0].person == 0 and result[1].person == -1
    assert match_appearances(E, np.array([0, 1, -1, -1]), ['x'] * 4, [2])[0].person == -1
    assert match_appearances(E, np.array([0, 0, -1, -1]), ['x'] * 4, []) == []
